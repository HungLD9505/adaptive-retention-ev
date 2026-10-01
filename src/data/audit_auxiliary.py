"""Full raw auxiliary-field audit without silently changing target values."""
import argparse,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'.deps'))
import pandas as pd
import numpy as np

def run(run_id):
    report=ROOT/'reports/data'/run_id
    rows=[]
    with zipfile.ZipFile(ROOT/'data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip') as z:
        names=sorted(n for n in z.namelist() if 'station-raw/charge_5min/' in n and n.endswith('.csv'))
        meta=pd.read_csv(z.open('UrbanEVDataset/20220901-20230228_station-raw/station_information.csv'))
        powers=pd.read_csv(z.open('UrbanEVDataset/20220901-20230228_station-raw/pile_rated_power.csv'))
        mapping=meta.set_index('station_id').charge_count.to_dict()
        inventory={'metadata_rows':len(meta),'unique_station_ids':int(meta.station_id.nunique()),'duplicate_station_ids':int(meta.station_id.duplicated().sum()),
          'pile_rows':len(powers),'unique_pile_ids':int(powers.pile_id.nunique()),'duplicate_pile_ids':int(powers.pile_id.duplicated().sum()),
          'nonpositive_or_missing_rated_power':int((powers.power.isna()|(powers.power<=0)).sum()),
          'raw_entities_without_metadata':sorted(set(int(Path(n).stem) for n in names)-set(meta.station_id)),
          'metadata_inventory_temporal_validity':'unknown: release static inventory must not be assumed historically available',
          'coordinate_system':'GCJ-02 per official repository'}
        (report/'metadata_audit.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
        for i,n in enumerate(names):
            f=pd.read_csv(z.open(n));numeric=f.select_dtypes('number');sid=int(Path(n).stem)
            observed=f[['busy','idle','fast_busy','fast_idle','slow_busy','slow_idle']].notna().all(axis=1)
            r={'native_id':sid,'rows':len(f),'aux_missing_cells':int(numeric.isna().sum().sum()),'aux_negative_cells':int((numeric<0).sum().sum()),
              'aux_nonfinite_cells':int((numeric.notna()&~np.isfinite(numeric)).sum().sum()),
              'busy_balance_mismatch_rows':int((observed&(f.busy!=f.fast_busy+f.slow_busy)).sum()),
              'idle_balance_mismatch_rows':int((observed&(f.idle!=f.fast_idle+f.slow_idle)).sum()),
              'static_inventory_mismatch_rows':int((observed&(f.busy+f.idle!=mapping.get(sid))).sum()),
              'noninteger_pile_counts_rows':int((observed&((f[['busy','idle','fast_busy','fast_idle','slow_busy','slow_idle']]%1)!=0).any(axis=1)).sum()),
              'negative_fee_rows':int(((f.e_price<0)|(f.s_price<0)).sum()),'negative_duration_rows':int((f.duration<0).sum())}
            rows.append(r)
            if i%200==0:print('auxiliary',i+1,len(names),flush=True)
    pd.DataFrame(rows).to_csv(report/'auxiliary_audit.csv',index=False)
    print('Auxiliary audit complete:',len(rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
