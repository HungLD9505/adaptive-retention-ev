"""Build versioned indices/scalers/QC. Run: python -m src.inputs.build --dataset urbanev --run-id ID."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
from functools import lru_cache
from .core import ROOT, SEED, HISTORY_FEATURES, FUTURE_FEATURES, split_entities, canonical, origins, fit_scale, InputLoader
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PANELS = {
 'urbanev': 'data/processed/urbanev/urbanev_full_20261002_01',
 'charged': 'data/processed/charged/charged_full_20261002_02',
}
CUTOFFS = {'urbanev': '2022-12-01', 'charged': '2023-07-01'}
RAW = {'urbanev': 'data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip',
       'charged': 'data/raw/charged/zenodo_15814263/Hourly.zip'}
EVIDENCE = {'urbanev': 'reports/data/urbanev_full_20261002_01', 'charged': 'reports/data/charged_full_20261002_02'}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def markdown_table(frame):
    def cell(x): return str(x).replace('|','\\|').replace('\n',' ')
    cols=[cell(c) for c in frame.columns]
    return '\n'.join(['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])

@lru_cache(maxsize=8)
def panel_reader(panel_file):
    return pq.ParquetFile(ROOT / panel_file)

def read_series(record):
    frame = panel_reader(record['panel_file']).read_row_group(record['row_group'], columns=[
        'interval_start_local', 'interval_end_local', 'energy_kwh', 'file_value_valid']).to_pandas()
    return canonical(frame)

def inventory(dataset):
    records = []
    for path in sorted((ROOT / PANELS[dataset]).glob('*_hourly_candidate.parquet')):
        f = pq.ParquetFile(path)
        for i in range(f.num_row_groups):
            ids = f.read_row_group(i, columns=['entity_id', 'native_id', 'city', 'entity_level', 'dataset_version']).to_pandas()
            if ids.entity_id.nunique() != 1:
                raise ValueError('Row group contains multiple entities')
            r = ids.iloc[0].to_dict()
            r.update(panel_file=path.relative_to(ROOT).as_posix(), row_group=i)
            records.append(r)
    return records

def data_contract(dataset):
    evidence = EVIDENCE[dataset]
    return {
      'dataset': dataset, 'accepted_use': 'published processed benchmark' if dataset == 'charged' else 'published raw-derived benchmark',
      'strict_online_claim_allowed': False,
      'shenzhen_independence': {'status': 'unknown', 'claim': 'No reliable cross-release station/site mapping; CHARGED is replication within CHARGED.', 'evidence': evidence + '/handoff.json'},
      'fields': [
        {'field': 'entity_id/native_id', 'status': 'verified', 'meaning': 'station for UrbanEV; site for CHARGED; no zone-level substitution', 'evidence': evidence + '/entity_audit.csv'},
        {'field': 'energy_kwh', 'status': 'verified', 'meaning': 'Released energy estimate in kWh; not independently verified metered energy', 'evidence': evidence + '/audit_report.md'},
        {'field': 'file_value_valid', 'status': 'verified', 'meaning': 'Canonical numerical/coverage validity; not original observation mask', 'evidence': 'src/data/process.py'},
        {'field': 'interval_start_local/end_local', 'status': 'assumed', 'meaning': 'Released naive start label and one-hour end; physical bin convention remains unverified', 'evidence': 'src/data/process.py; ' + evidence + '/handoff.json'},
        {'field': 'timezone/DST', 'status': 'unknown', 'meaning': 'Use released clock; do not localize to UTC or infer physical DST', 'evidence': evidence + '/handoff.json'},
        {'field': 'original_observation_status', 'status': 'unknown', 'meaning': 'Upstream masks unavailable; valid released value is not proof of original observation', 'evidence': evidence + '/handoff.json'},
        {'field': 'publisher_processed', 'status': 'verified', 'meaning': 'CHARGED interpolation/IQR; UrbanEV raw station release already derived from status/power', 'evidence': evidence + '/audit_report.md'},
        {'field': 'label_available_at', 'status': 'unknown', 'meaning': 'Actual publication/arrival time remains unknown and canonical panel is unchanged', 'evidence': evidence + '/handoff.json'},
        {'field': 'assumed_available_at', 'status': 'assumed', 'meaning': 'Next midnight = exclusive horizon end; benchmark labels may be used at this boundary', 'evidence': 'User approved 2026-10-04 protocol'},
        {'field': 'calendar', 'status': 'assumed', 'meaning': 'Released-clock hour/day/weekend; no weather/pricing/future-demand predictors', 'evidence': 'User approved 2026-10-04 protocol'},
      ],
      'strict_online_requirements': ['Verified physical bin/timezone/DST semantics', 'Verified arrival timestamps for all labels', 'Auditable causal upstream processing and original masks'],
      'sources': [evidence + '/handoff.json', evidence + '/audit_report.md', 'src/data/process.py',
                  'data/raw/charged/zenodo_15814263/README.md' if dataset == 'charged' else 'data/raw/urbanev/official_2026_05_11/repository_README.md'],
    }

def build(dataset, run_id, limit=None):
    out = ROOT / 'data/inputs' / dataset / run_id
    report = ROOT / 'reports/inputs' / run_id
    if out.exists() or report.exists():
        raise FileExistsError('Run exists; choose a new run_id')
    out.mkdir(parents=True)
    report.mkdir(parents=True)
    logger = logging.getLogger(run_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(report / 'execution.log', encoding='utf-8'))
    logger.addHandler(logging.StreamHandler())
    cutoff = pd.Timestamp(CUTOFFS[dataset])
    config = {'dataset': dataset, 'run_id': run_id, 'split_seed': SEED, 'split': [60,20,20],
              'rounding': 'Python round for source/development; final remainder, within city',
              'deployment_cutoff': str(cutoff), 'budgets_days': [7,14,28], 'origin': 'released-clock midnight',
              'history_hours': 24, 'horizon_hours': 24, 'scale': 'p95 linear, scale-only',
              'target_eligibility': 'one fully file-valid 48h midnight-aligned window in seven-day warmup',
              'source_eligibility': 'one fully file-valid 48h midnight-aligned window before cutoff',
              'missing_inputs': 'scaled energy=0; file_valid_mask=0', 'missing_labels': 'exclude scoring/training window',
              'availability': 'assumed at exclusive horizon end/next midnight', 'timezone': 'unknown',
              'scope': 'smoke subset' if limit else 'full', 'limit': limit,
              'X_hist': HISTORY_FEATURES, 'C_future': FUTURE_FEATURES}
    write_json(report / 'config.json', config)
    write_json(report / 'data_contract.json', data_contract(dataset))
    records = split_entities(inventory(dataset))
    # Persist every split ID before reading energies/fitting/choosing cohort.
    pd.DataFrame(records).to_csv(report / 'split_manifest.csv', index=False)
    logger.info('Locked %s IDs before scaler/cohort fits', len(records))
    positives = []
    for ri, r in enumerate(records):
        if r['role'] == 'source':
            s = read_series(r)
            v = s[(s.index < cutoff) & (s > 0)].to_numpy()
            if len(v): positives.append(v)
        if (ri+1)%300==0: logger.info('Source-prefix scan %s/%s IDs',ri+1,len(records))
    source_positive_count = sum(len(v) for v in positives)
    fallback = float(np.quantile(np.concatenate(positives), .95)) if positives else 1.
    del positives
    logger.info('Source-only positive fallback %.9g kWh from %s hours', fallback, source_positive_count)
    writer = None
    scalers, cohorts, counts = [], [], []
    chosen = records if limit is None else [r for role in ['source','development','final'] for r in [x for x in records if x['role']==role][:limit]]
    try:
        for ni, r in enumerate(chosen):
            s = read_series(r)
            end = (s.index.max() + pd.Timedelta(hours=1)).floor('D')
            start = s.index.min()
            # Fill absent timestamps on a grid without filling values.
            series = s.reindex(pd.date_range(start, end - pd.Timedelta(hours=1), freq='h'))
            vals = series.to_numpy(float)
            eligible_start = start if r['role'] == 'source' else cutoff - pd.Timedelta(days=7)
            eo = origins(series, eligible_start, cutoff)
            epos = ((eo - start) / pd.Timedelta(hours=1)).to_numpy(dtype=int)
            full48 = sum(np.isfinite(vals[p-24:p+24]).all() and len(vals[p-24:p+24]) == 48 for p in epos if p >= 24 and p+24 <= len(vals))
            eligible = bool(full48)
            cohorts.append({**r, 'eligible': eligible, 'full48_eligibility_windows': full48,
                            'eligibility_start': str(eligible_start), 'eligibility_end_exclusive': str(cutoff),
                            'reason': 'eligible' if eligible else 'no_fully_valid_aligned_48h_window_in_allowed_prefix'})
            if not eligible: continue
            budgets = [0] if r['role'] == 'source' else [7,14,28]
            for budget in budgets:
                fit_start = start if budget == 0 else cutoff - pd.Timedelta(days=budget)
                scale = fit_scale(s, fit_start, cutoff, fallback)
                scalers.append({**r, 'budget_days': budget, **scale, 'fallback_kwh': fallback,
                                'fallback_scope': 'all source-role positive valid energy before cutoff in this dataset',
                                'fallback_reason': 'source_positive_p95' if source_positive_count else 'no_source_positive_1kwh'})
                scopes = [('source_train', fit_start, cutoff)] if budget == 0 else [('warmup', fit_start, cutoff), ('stream', cutoff - pd.Timedelta(hours=24), end)]
                for phase, a, b in scopes:
                    oo = origins(series, a, b)
                    pos = ((oo - start) / pd.Timedelta(hours=1)).to_numpy(dtype=int)
                    rows = []
                    reasons = {'missing_labels': 0, 'all_history_missing': 0, 'outside_panel': 0}
                    for o, p in zip(oo, pos):
                        if p < 24 or p+24 > len(vals):
                            reasons['outside_panel'] += 1; continue
                        x, y = vals[p-24:p], vals[p:p+24]
                        if not np.isfinite(y).all():
                            reasons['missing_labels'] += 1; continue
                        if not np.isfinite(x).any():
                            reasons['all_history_missing'] += 1; continue
                        rows.append({'dataset': dataset, 'dataset_version': r['dataset_version'], 'city': r['city'],
                                     'entity_id': r['entity_id'], 'native_id': r['native_id'], 'entity_level': r['entity_level'],
                                     'role': r['role'], 'budget_days': budget, 'phase': phase, 'origin': o,
                                     'input_start': o-pd.Timedelta(hours=24), 'input_end_exclusive': o,
                                     'label_start': o, 'label_end_exclusive': o+pd.Timedelta(hours=24),
                                     'assumed_available_at': o+pd.Timedelta(hours=24), 'label_available_at_status': 'unknown',
                                     'history_valid_hours': int(np.isfinite(x).sum()), 'label_valid_hours': 24,
                                     'scale_kwh': scale['scale_kwh'], 'panel_file': r['panel_file'], 'row_group': r['row_group'], 'run_id': run_id})
                    counts.append({'entity_id':r['entity_id'], 'city':r['city'], 'role':r['role'], 'budget_days':budget, 'phase':phase,
                                   'candidate_origins':len(oo), 'accepted_windows':len(rows), **reasons})
                    if rows:
                        table = pa.Table.from_pandas(pd.DataFrame(rows), preserve_index=False)
                        if writer is None: writer = pq.ParquetWriter(out / 'window_index.parquet', table.schema, compression='zstd')
                        writer.write_table(table)
            if (ni+1) % 200 == 0: logger.info('Processed %s/%s entities', ni+1, len(chosen))
    finally:
        if writer: writer.close()
    if not writer: raise ValueError('No accepted windows')
    cohort = pd.DataFrame(cohorts)
    cohort.to_csv(report / 'cohort_manifest.csv', index=False)
    scaler = pd.DataFrame(scalers)
    scaler.to_csv(report / 'scalers.csv', index=False)
    pd.DataFrame(counts).to_csv(report / 'window_audit.csv', index=False)
    groups = cohort.groupby(['city','role']).agg(entities=('entity_id','size'), eligible=('eligible','sum')).reset_index()
    groups['excluded'] = groups.entities-groups.eligible
    groups.to_csv(report / 'cohort_counts.csv', index=False)
    wc = pd.DataFrame(counts).groupby(['city','role','budget_days','phase']).sum(numeric_only=True).reset_index()
    wc.to_csv(report / 'window_counts.csv', index=False)
    allowed = scaler.groupby(['city','role','budget_days']).agg(valid_hours=('valid_fit_hours','sum'),zero_hours=('zero_fit_hours','sum'),all_zero_entities=('all_zero_initial','sum'),fallback_entities=('fallback_used','sum')).reset_index()
    allowed.to_csv(report / 'allowed_prefix_counts.csv', index=False)
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/PANELS[dataset]).glob('*.parquet'))}
    hashes[RAW[dataset]] = sha(ROOT/RAW[dataset])
    code = {p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'src/inputs').glob('*.py'))}
    git = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    manifest = {'run_id':run_id, 'dataset':dataset, 'created_at_utc':str(datetime.now(timezone.utc)), 'input_dir':str(out),
                'source_hashes_sha256':hashes, 'code_hashes_sha256':code, 'git_base_commit':git,
                'code_state':'working tree; exact source snapshots and hashes stored', 'config_sha256':sha(report/'config.json'),
                'split_manifest_sha256':sha(report/'split_manifest.csv'), 'source_positive_count':source_positive_count,
                'source_positive_p95_fallback_kwh':fallback, 'index_sha256':sha(out/'window_index.parquet'),
                'scope':config['scope'], 'training_performed':False}
    snap = report/'source_snapshot'
    snap.mkdir()
    for p in (ROOT/'src/inputs').glob('*.py'): shutil.copy2(p,snap/p.name)
    write_json(report/'manifest.json',manifest)
    checks = verify(out, report, cutoff)
    final_n = int(cohort[(cohort.role=='final') & cohort.eligible].shape[0])
    handoff = not limit and checks['passed'] and (dataset != 'urbanev' or final_n >= 100)
    render(report, out, dataset, groups, wc, scaler, handoff)
    write_json(report/'handoff.json', {'accepted':handoff,'scope':config['scope'],'eligible_final_entities':final_n,
               'conclusion':'published-data benchmark inputs ready for model development' if handoff else 'smoke only or acceptance gate failed',
               'strict_online':False, 'model_training_performed':False})
    logger.info('Finished %s; handoff=%s; checks=%s',run_id,handoff,checks)
    return report

def verify(out, report, cutoff):
    loader = InputLoader(out)
    df = loader.index
    checks = {}
    checks['unique_key'] = not df.duplicated(['entity_id','budget_days','origin']).any()
    checks['midnight_origins'] = bool((df.origin == df.origin.dt.floor('D')).all())
    checks['source_boundary'] = bool((df.loc[df.role=='source','label_end_exclusive'] <= cutoff).all())
    checks['label_count_24'] = bool((df.label_valid_hours == 24).all())
    warm = df[df.phase=='warmup']
    checks['warmup_boundary'] = bool(((warm.input_start >= cutoff - pd.to_timedelta(warm.budget_days,unit='D')) & (warm.label_end_exclusive <= cutoff)).all())
    checks['stream_boundary'] = bool((df.loc[df.phase=='stream','origin'] >= cutoff).all())
    checks['availability'] = bool((df.assumed_available_at == df.label_end_exclusive).all())
    sample_n = 0
    sample_records = []
    for key, g in df.groupby(['city','role','budget_days','phase']):
        for i in sorted(set([int(g.index[0]),int(g.index[len(g)//2]),int(g.index[-1])])):
            sample = loader.load(i,include_labels=True,as_of=df.loc[i,'assumed_available_at'])
            assert sample['X_hist'].shape==(24,7) and sample['C_future'].shape==(24,5) and sample['Y'].shape==(24,)
            assert all(sample[k].dtype==np.float32 and np.isfinite(sample[k]).all() for k in ['X_hist','C_future','Y'])
            assert np.isclose(sample['X_hist'][:,1].sum(),df.loc[i,'history_valid_hours'])
            from .core import calendar
            assert np.allclose(sample['C_future'],calendar(pd.date_range(df.loc[i,'origin'],periods=24,freq='h')),atol=1e-6)
            sample_n += 1
            sample_records.append({'index':i,'entity_id':sample['entity_id'],'origin':str(sample['origin']),'role':sample['role'],'budget_days':sample['budget_days']})
    checks['tensor_samples'] = sample_n
    audit = pd.read_csv(report/'window_audit.csv')
    checks['counts_match_audit'] = len(df)==int(audit.accepted_windows.sum())
    split = pd.read_csv(report/'split_manifest.csv')
    checks['split_disjoint'] = not split.entity_id.duplicated().any()
    checks['passed'] = all(v for v in checks.values())
    write_json(report/'readback_checks.json',checks)
    write_json(report/'tensor_samples.json',sample_records)
    if not checks['passed']: raise AssertionError(checks)
    return checks

def render(report, out, dataset, groups, wc, scaler, accepted):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figs = report/'figures'; figs.mkdir()
    fig,ax=plt.subplots(figsize=(12,5))
    labels=groups.city+' / '+groups.role
    ax.bar(labels,groups.eligible,label='Eligible from allowed prefix')
    ax.bar(labels,groups.excluded,bottom=groups.eligible,label='Excluded')
    ax.set(ylabel='Entities',title=f'{dataset}: deterministic split and prefix-only eligibility');ax.tick_params(axis='x',rotation=65);ax.legend()
    fig.tight_layout();fig.savefig(figs/'01_cohort.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    for role,g in scaler.groupby('role'): ax.hist(np.log10(g.scale_kwh),bins=40,alpha=.5,label=role)
    ax.set(xlabel='log10(scale in kWh)',ylabel='Entity-budget scalers',title='Scales fit only before cutoff');ax.legend()
    fig.tight_layout();fig.savefig(figs/'02_scales.png',dpi=140);plt.close(fig)
    loader=InputLoader(out);df=loader.index
    row=df[df.role!='source'].sort_values(['history_valid_hours','entity_id','origin']).iloc[0]
    sample=loader.load(int(row.name),include_labels=True,as_of=row.assumed_available_at)
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
    axes[0].plot(np.arange(-24,0),sample['X_hist'][:,0],label='History (missing encoded 0)')
    axes[0].plot(np.arange(0,24),sample['Y'],label='Horizon labels');axes[0].legend();axes[0].set_ylabel('Scaled energy')
    axes[1].step(np.arange(-24,0),sample['X_hist'][:,1],where='mid');axes[1].set(ylim=(-.1,1.1),ylabel='File-valid mask',xlabel='Hours from origin')
    fig.suptitle(f"{row.entity_id} | {row.origin} | budget {row.budget_days}d\nRule: target window with fewest valid history hours, ties by ID/origin")
    fig.tight_layout();fig.savefig(figs/'03_mask_window.png',dpi=140);plt.close(fig)
    prefix=scaler.groupby(['role','budget_days']).agg(valid=('valid_fit_hours','sum'),zero=('zero_fit_hours','sum')).reset_index()
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(prefix.role+' / '+prefix.budget_days.astype(str),prefix.zero/prefix.valid)
    ax.set(ylabel='Zero fraction among valid prefix values',title='Allowed-prefix zero audit (no stream selection)',ylim=(0,1))
    ax.tick_params(axis='x',rotation=45);fig.tight_layout();fig.savefig(figs/'04_prefix_zero.png',dpi=140);plt.close(fig)
    text=f'''# Báo cáo đầu vào model — {dataset}

Run: `{out.name}`. Nghiệm thu benchmark: **{accepted}**. Không huấn luyện model.

## Protocol và giới hạn

Nguồn chuẩn Report 1; split theo SHA-256 `20261004|entity_id`, 60/20/20, round source/dev và remainder final, riêng từng city. File split được lưu trước khi đọc energy để fit scale/cohort. Cutoff `{CUTOFFS[dataset]}`; calendar dùng giờ naive phát hành, timezone/bin thực chưa xác minh.

Đây là benchmark trên dữ liệu phát hành; không claim strict online. `assumed_available_at` là cuối horizon exclusive/00:00 ngày kế tiếp; thời điểm label thật vẫn unknown trong panel gốc. CHARGED có interpolation/IQR/masks chưa biết; Shenzhen chưa xác minh độc lập với UrbanEV.

Target cohort: có một window full48 căn midnight trong warmup7 ngày; tất cả budgets dùng chung cohort. Source cần một window full48 trước cutoff. Windows dùng cho train/score có đủ24 label, input có ít nhất một giờ hợp lệ; input thiếu mã hóa scaled0/mask0, zero thật mask1. Mask chỉ phản ánh file validity, không chứng minh original observation.

Scale-only p95 linear mỗi entity/budget từ lịch sử trước cutoff; fallback source-positive p95 trong cùng dataset, nếu không có positive dùng1kWh. Giữ scale cố định. Source-role fallback dùng tất cả source IDs trước cutoff, kể cả source không đủ window; không dùng final energy để fit fallback.

## Kết quả thực

{markdown_table(groups)}

{markdown_table(wc)}

Eligibility/exclusions chi tiết: `cohort_manifest.csv`. Counts/rejections: `window_audit.csv`; rejection reason ưu tiên missing_labels rồi all_history_missing. Thống kê zero/missing và scale chỉ trên allowed prefix; không chọn bằng stream. Mỗi row index có input/horizon bounds, scale, nguồn panel và rowgroup; tensors tạo khi đọc.

## Visual và ý nghĩa

- `01_cohort.png`: phân bố role/cohort, giúp thấy exclusion do lịch sử ban đầu.
- `02_scales.png`: độ chênh thang năng lượng trước cutoff; không dùng để tuning final.
- `03_mask_window.png`: window target theo rule số giờ history hợp lệ ít nhất; zero encoding phải đọc cùng mask.
- `04_prefix_zero.png`: zero-rate trong phạm vi được phép, giữ cả trạm toàn zero.

## Loader và tái chạy

`python -m src.inputs.build --dataset {dataset} --run-id NEW_UNIQUE_ID`

`InputLoader(run_dir).load(i)` chỉ trả X/C. Khi lấy Y phải gọi `include_labels=True, as_of=...` và qua assumed availability. Dataset index có role/phase; caller model phase sau phải tách source/train, warmup/update và final/scoring đúng protocol. `Y * scale_kwh` đổi về kWh; loss trên scaled, metrics trên đơn vị gốc.

Manifest lưu SHA256 raw/panel/config/index/code, Git base và source snapshot. Raw/candidate panel/run cũ không sửa. Dữ liệu lớn local trong `{out.relative_to(ROOT)}`. Readback và samples đầu/giữa/cuối từng city/role/budget/phase tại `readback_checks.json`, `tensor_samples.json`.

## Chưa hoàn thành

Model/loss/retention/controller và experiment chưa triển khai. Physical timezone/DST/bin, causal upstream masks và label arrival chưa xác minh. Strict online chỉ được claim khi các gate trong `data_contract.json` đạt.
'''
    (report/'input_report.md').write_text(text,encoding='utf-8')
    imgs=''.join(f'<h2>{p.stem}</h2><img src="figures/{p.name}" style="max-width:100%">' for p in sorted(figs.glob('*.png')))
    (report/'eda.html').write_text(f'<!doctype html><meta charset="utf-8"><title>{dataset} input QC</title><body style="max-width:1200px;margin:auto;font-family:Arial"><h1>{dataset}: input QC</h1><p>Published-data benchmark. Original masks/timezone unknown. Prefix-only QC; no model training.</p>{imgs}{groups.to_html(index=False)}{wc.to_html(index=False)}</body>',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=PANELS,required=True);p.add_argument('--run-id',required=True);p.add_argument('--limit-per-role',type=int)
    a=p.parse_args()
    if not a.run_id or Path(a.run_id).name!=a.run_id: p.error('run-id must be a single directory name')
    if a.limit_per_role is not None and a.limit_per_role<1:p.error('limit must be positive')
    build(a.dataset,a.run_id,a.limit_per_role)

if __name__=='__main__':main()
