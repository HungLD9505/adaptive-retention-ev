"""Deterministic protocol, prefix-only scalers and lazy 24 -> 24 tensors."""
from __future__ import annotations
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.deps'))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SEED = '20261004'
HISTORY_FEATURES = ['energy_scaled', 'file_valid_mask', 'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos', 'weekend']
FUTURE_FEATURES = HISTORY_FEATURES[2:]

def split_entities(records, seed=SEED):
    """Round source and development counts to nearest integer; final gets remainder."""
    result = []
    cities = sorted({r['city'] for r in records})
    for city in cities:
        group = [dict(r) for r in records if r['city'] == city]
        for r in group:
            r['split_hash'] = hashlib.sha256(f"{seed}|{r['entity_id']}".encode()).hexdigest()
        group.sort(key=lambda r: (r['split_hash'], r['entity_id']))
        ns, nd = round(len(group) * .6), round(len(group) * .2)
        for i, r in enumerate(group):
            r['role'] = 'source' if i < ns else 'development' if i < ns + nd else 'final'
        result.extend(group)
    if len({r['entity_id'] for r in result}) != len(result):
        raise ValueError('Entity IDs must be unique')
    return result

def canonical(frame):
    frame = frame.sort_values('interval_start_local').copy()
    t = pd.DatetimeIndex(frame['interval_start_local'])
    if t.has_duplicates or t.tz is not None or not (t == t.floor('h')).all():
        raise ValueError('Require unique naive hourly boundaries')
    if not (pd.DatetimeIndex(frame['interval_end_local']) == t + pd.Timedelta(hours=1)).all():
        raise ValueError('Require exactly one-hour panel intervals')
    y = frame['energy_kwh'].to_numpy(dtype=float)
    valid = frame['file_value_valid'].fillna(False).to_numpy(bool) & np.isfinite(y) & (y >= 0)
    return pd.Series(np.where(valid, y, np.nan), index=t)

def grid(series, start, hours=24):
    return series.reindex(pd.date_range(start, periods=hours, freq='h')).to_numpy(float)

def origins(series, start, end):
    """Origins with both windows inside [start,end), aligned to released midnight."""
    first = (pd.Timestamp(start) + pd.Timedelta(hours=24)).ceil('D')
    last = (pd.Timestamp(end) - pd.Timedelta(hours=24)).floor('D')
    return pd.date_range(first, last, freq='D') if first <= last else pd.DatetimeIndex([])

def full_window_exists(series, start, end):
    return any(np.isfinite(grid(series, o - pd.Timedelta(hours=24), 48)).all() for o in origins(series, start, end))

def fit_scale(series, start, end, fallback):
    values = series[(series.index >= start) & (series.index < end)].dropna().to_numpy()
    q = float(np.quantile(values, .95, method='linear')) if len(values) else 0.
    return {'scale_kwh': q if q > 0 else float(fallback), 'station_p95_kwh': q,
            'fallback_used': q <= 0, 'valid_fit_hours': len(values),
            'zero_fit_hours': int((values == 0).sum()), 'all_zero_initial': bool(len(values) and (values == 0).all()),
            'fit_start': str(start), 'fit_end_exclusive': str(end)}

def calendar(times):
    h = times.hour.to_numpy() * (2 * np.pi / 24)
    d = times.dayofweek.to_numpy() * (2 * np.pi / 7)
    return np.column_stack([np.sin(h), np.cos(h), np.sin(d), np.cos(d), times.dayofweek >= 5]).astype('float32')

def tensors(series, origin, scale):
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Scale must be positive and finite')
    origin = pd.Timestamp(origin)
    xt = pd.date_range(origin - pd.Timedelta(hours=24), periods=24, freq='h')
    yt = pd.date_range(origin, periods=24, freq='h')
    x, y = series.reindex(xt).to_numpy(float), series.reindex(yt).to_numpy(float)
    mask = np.isfinite(x)
    if not mask.any():
        raise ValueError('All history missing')
    X = np.column_stack([np.where(mask, x / scale, 0), mask.astype(float), calendar(xt)]).astype('float32')
    C = calendar(yt)
    # Inference may succeed with unknown labels; scoring must enforce the mask separately.
    Y = (y / scale).astype('float32')
    if not np.isfinite(X).all() or not np.isfinite(C).all():
        raise ValueError('Non-finite input tensor')
    return X, C, Y

class InputLoader:
    """Labels require explicit benchmark as_of >= assumed_available_at.

    Dataset roles are explicit; model training callers must restrict to source,
    warmup or legally available stream rows. This loader does not train models.
    """
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.index = pq.read_table(self.run_dir / 'window_index.parquet').to_pandas()

    @lru_cache(maxsize=8)
    def _series(self, panel_file, row_group):
        return canonical(pq.ParquetFile(ROOT / panel_file).read_row_group(int(row_group), columns=[
            'interval_start_local', 'interval_end_local', 'energy_kwh', 'file_value_valid']).to_pandas())

    def load(self, i, *, include_labels=False, as_of=None):
        row = self.index.iloc[i]
        series = self._series(row.panel_file, row.row_group)
        X, C, Y = tensors(series, row.origin, row.scale_kwh)
        sample = {'X_hist': X, 'C_future': C, 'entity_id': row.entity_id,
                  'role': row.role, 'budget_days': int(row.budget_days), 'origin': row.origin,
                  'scale_kwh': float(row.scale_kwh), 'assumed_available_at': row.assumed_available_at}
        if include_labels:
            required_at = max(row.assumed_available_at, pd.Timestamp(row.get('scaler_frozen_at',row.assumed_available_at)))
            if as_of is None or pd.Timestamp(as_of) < required_at:
                raise ValueError('Labels unavailable under benchmark assumption')
            if not np.isfinite(Y).all():
                raise ValueError('Incomplete labels cannot be used for training/scoring')
            sample['Y'] = Y
        return sample

    def forecast(self, entity_id, budget_days, origin):
        """Build inference inputs even for an origin excluded from scoring.

        No label-completeness gate: future labels must never decide whether to
        forecast. Uses the entity's already locked scale and panel location.
        """
        matches = self.index[(self.index.entity_id == entity_id) & (self.index.budget_days == budget_days)]
        if matches.empty:
            raise KeyError((entity_id, budget_days))
        row = matches.iloc[0]
        origin = pd.Timestamp(origin)
        if row.role == 'source' or origin < pd.Timestamp(row.get('scaler_frozen_at',row.origin)):
            raise ValueError('Online inference requires target origin at/after deployment; warmup is offline at deployment')
        if origin != origin.floor('D'):
            raise ValueError('Origin must be midnight in released clock')
        series = self._series(row.panel_file, row.row_group)
        X, C, _ = tensors(series, origin, row.scale_kwh)
        return {'X_hist':X, 'C_future':C, 'entity_id':entity_id, 'origin':origin,
                'budget_days':int(budget_days), 'scale_kwh':float(row.scale_kwh)}
