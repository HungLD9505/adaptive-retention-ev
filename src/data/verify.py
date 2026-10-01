"""Read back deliverables and independently reconcile one full raw station."""
import argparse,csv,io,json,math,sys,zipfile
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'.deps'))
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from process import hourly

def verify(run_id):
    report=ROOT/'reports/data'/run_id;j=json.loads((report/'qc_summary.json').read_text())
    checks={'panels':{},'aggregate_reconciliation':j['reconciliation_pass'],'no_entity_failures':j['entities_failed']==0}
    rows=valid=zero=0;seen=set();last={}
    for p in j['panels']:
        pf=pq.ParquetFile(ROOT/p);n=0
        for b in pf.iter_batches(batch_size=100000,columns=['entity_id','interval_start_local','energy_kwh','file_value_valid','coverage_fraction','strict_online_ready']):
            df=b.to_pandas();n+=len(df)
            assert not df.duplicated(['entity_id','interval_start_local']).any()
            assert not df.strict_online_ready.any()
            assert df.loc[~df.file_value_valid,'energy_kwh'].isna().all()
            assert df.loc[df.file_value_valid,'energy_kwh'].notna().all()
            assert (df.loc[df.file_value_valid,'coverage_fraction']==1).all()
            valid+=int(df.file_value_valid.sum());zero+=int((df.energy_kwh==0).sum())
            for entity,g in df.groupby('entity_id',sort=False):
                assert g.interval_start_local.is_monotonic_increasing
                if entity in last:assert g.interval_start_local.iloc[0]>last[entity]
                last[entity]=g.interval_start_local.iloc[-1];seen.add(entity)
        rows+=n;checks['panels'][p]={'rows':n,'unique_keys_order_check':True}
    assert len(seen)==j['entities_succeeded']
    assert valid==j['totals']['valid_hours'] and zero==j['totals']['zero_hours']
    assert rows==j['totals']['valid_hours']+j['totals']['invalid_hours']
    if j['dataset']=='urbanev':
        source='UrbanEVDataset/20220901-20230228_station-raw/charge_5min/1001.csv'
        with zipfile.ZipFile(ROOT/'data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip') as z:
            raw=z.read(source).decode();records=defaultdict(list)
            for r in csv.DictReader(io.StringIO(raw)):
                try:v=float(r['volume'])
                except ValueError:v=float('nan')
                records[r['time'][:13]].append(v)
            expected={k:math.fsum(v) if len(v)==12 and all(math.isfinite(x) and x>=0 for x in v) else float('nan') for k,v in records.items()}
            actual=pd.read_parquet(ROOT/j['panels'][0],filters=[('entity_id','==','urbanev:SZH:1001')],columns=['interval_start_local','energy_kwh'])
            comparison=np.array([expected.get(str(t)[:13],np.nan) for t in actual.interval_start_local])
            assert np.allclose(comparison,actual.energy_kwh.to_numpy(),equal_nan=True,rtol=1e-8,atol=1e-6)
            f=pd.read_csv(io.StringIO(raw));a,_=hourly(f,5);f.loc[pd.to_datetime(f.time)>='2022-10-01','volume']=999
            b,_=hourly(f,5);cut=a.interval_end_local<=pd.Timestamp('2022-10-01')
            pd.testing.assert_frame_equal(a.loc[cut],b.loc[cut])
            checks.update(independent_csv_math_reconciliation=True,future_perturbation_transform_only=True)
    checks.update(rows=rows,entities=len(seen),valid_hours=valid,zero_hours=zero,status='PASS',
      limits='Time semantics/label arrival/upstream causality NOT certified; no split/features/scaler/windows.')
    (report/'readback_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);verify(p.parse_args().run_id)
