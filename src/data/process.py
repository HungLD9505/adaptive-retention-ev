"""Released timestamp-hour panels; unknown time semantics are explicit, never guessed."""
from __future__ import annotations
import argparse, html, io, json, logging, os, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.deps'))
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from acquire import digest

TRANSFORM='hourly_audit_v1'
def json_write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def hourly(frame,frequency_minutes):
    """Sum interval energies assigned to released timestamp bins (semantics unverified).

    Conflicting timestamp duplicates invalidate the affected hour; exact duplicates
    are removed. No label fill, outlier clipping or missing-to-zero conversion.
    """
    x=frame.copy(); x['time']=pd.to_datetime(x['time'],errors='coerce')
    malformed=int(x['time'].isna().sum()); x=x.dropna(subset=['time'])
    x['volume']=pd.to_numeric(x['volume'],errors='coerce')
    exact=int(x.duplicated().sum()); x=x.drop_duplicates()
    conflicts=x.loc[x.duplicated('time',keep=False),'time'].dt.floor('h').unique()
    x=x.drop_duplicates('time',keep='first').sort_values('time').set_index('time')
    if x.empty:raise ValueError('No parseable timestamps')
    offgrid=(x.index.minute%frequency_minutes!=0)|(x.index.second!=0)
    bad_hours=set(conflicts)|set(x.index[offgrid].floor('h'))
    x=x.loc[~offgrid]
    expected=60//frequency_minutes
    full=pd.date_range(x.index.min().floor('h'),x.index.max().floor('h')+pd.Timedelta(minutes=60-frequency_minutes),freq=f'{frequency_minutes}min')
    y=x['volume'].reindex(full); valid=y.notna()&np.isfinite(y)&(y>=0)
    grouped=y.where(valid).resample('h')
    sums=grouped.sum(min_count=1);counts=valid.resample('h').sum()
    good=(counts==expected)&(~sums.index.isin(bad_hours))
    out=pd.DataFrame({'interval_start_local':sums.index,'interval_end_local':sums.index+pd.Timedelta(hours=1),
      'energy_kwh':sums.where(good).to_numpy(),'partial_energy_kwh':sums.to_numpy(),
      'coverage_fraction':(counts/expected).to_numpy(),'file_value_valid':good.to_numpy(),
      'invalid_reason':np.where(sums.index.isin(bad_hours),'conflicting_duplicate_or_offgrid',np.where(good,'','incomplete_or_invalid_interval'))})
    audit={'input_rows':len(frame),'exact_duplicates':exact,'conflicting_timestamps':len(conflicts),'malformed_timestamps':malformed,
      'offgrid_rows':int(offgrid.sum()),'negative_values':int((y<0).sum()),'nonfinite_values':int((y.notna()&~np.isfinite(y)).sum()),
      'expected_intervals':len(full),'valid_intervals':int(valid.sum()),'missing_intervals':int(y.isna().sum()),
      'zero_intervals':int((y==0).sum()),'output_hours':len(out),'valid_hours':int(good.sum()),
      'invalid_hours':int((~good).sum()),'zero_hours':int((out.energy_kwh==0).sum()),'start':str(full.min()),'end':str(full.max())}
    # Compare only complete accepted hours; partial intervals are not discarded from audit.
    included=valid & full.floor('h').isin(out.loc[good.to_numpy(),'interval_start_local'])
    source_total=float(y.where(included).sum());target_total=float(out.energy_kwh.sum())
    audit.update(energy_kwh=target_total,reconciliation_source_kwh=source_total,reconciliation_pass=bool(np.isclose(source_total,target_total,rtol=1e-8,atol=1e-6)))
    return out,audit

def enrich(out,dataset,city,native_id,source,run_id,processed):
    values={'dataset':dataset,'dataset_version':'official_2026_05_11' if dataset=='urbanev' else 'zenodo_15814263',
      'city':city,'entity_level':'station' if dataset=='urbanev' else 'site','entity_id':f'{dataset}:{city}:{native_id}','native_id':str(native_id),
      'timezone':'unknown','timestamp_status':'released_naive_timestamp; timezone_and_bin_semantics_unverified',
      'availability_status':'unknown','target_semantics':'estimated_from_status_and_power; not_metered',
      'original_observation_status':'unknown','publisher_processed':processed,'strict_online_ready':False,
      'source_file':source,'source_record_rule':'released timestamp in displayed hour; immutable archive member',
      'transform_version':TRANSFORM,'run_id':run_id}
    for k,v in values.items():out[k]=v
    out['label_available_at']=pd.NaT
    return out

def inventory(z):
    rows=[]
    for i in z.infolist():
        if not i.file_size:continue
        row={'member':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'extension':Path(i.filename).suffix}
        if i.filename.endswith('.csv'):
            with z.open(i) as f:
                line=f.readline().decode('utf-8-sig',errors='replace').strip()
            row['header']=line[:20000]
        rows.append(row)
    return rows

def run(dataset,run_id,limit=None):
    report=ROOT/'reports/data'/run_id;report.mkdir(parents=True,exist_ok=False)
    processed=ROOT/'data/processed'/dataset/run_id;processed.mkdir(parents=True,exist_ok=False)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(report/'processing.log',encoding='utf-8'),logging.StreamHandler()])
    archive=ROOT/('data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip' if dataset=='urbanev' else 'data/raw/charged/zenodo_15814263/Hourly.zip')
    audits=[];daily=[];samples=[];writers={};failures=[];dictionary=[];coordinates=[];charged_ids={}
    with zipfile.ZipFile(archive) as z:
        inv=inventory(z);pd.DataFrame(inv).to_csv(report/'file_inventory.csv',index=False)
        json_write(report/'run_config.json',{'dataset':dataset,'run_id':run_id,'transform':TRANSFORM,'limit':limit,'raw_sha256':digest(archive),
          'timestamp_bin_mapping':'released displayed hour; NOT confirmed event interval','timezone':'unknown','availability':'unknown',
          'imputation':None,'scaling':None,'split':None,'seed':20261002})
        if dataset=='urbanev':
            members=sorted(n for n in z.namelist() if 'station-raw/charge_5min/' in n and n.endswith('.csv'))
            metadata=[n for n in z.namelist() if n.endswith('station-raw/station_information.csv')][0]
            meta=pd.read_csv(z.open(metadata));meta.to_csv(report/'entity_metadata.csv',index=False)
            coordinates=[meta]
            tasks=[('SZH',Path(n).stem,n) for n in members]
        else:
            members=sorted(n for n in z.namelist() if n.endswith('/volume.csv') and 'remove_zero' not in n.lower())
            tasks=[]
            for n in members:
                matrix=pd.read_csv(z.open(n));timecol=matrix.columns[0]
                city=next((part.upper() for part in n.split('/') if part.upper() in ['AMS','JHB','LOA','MEL','SPO','SZH']),None)
                if city is None:raise ValueError('Unknown city path: '+n)
                for col in matrix.columns[1:]:tasks.append((city,str(col),(n,pd.DataFrame({'time':matrix[timecol],'volume':matrix[col]}))))
            for n in z.namelist():
                if n.endswith('/sites.csv') and 'remove_zero' not in n:
                    md=pd.read_csv(z.open(n));md['source_file']=n;md.to_csv(report/(n.replace('/','_')),index=False)
                    if n.split('/')[0] in ['MEL','SPO']:
                        if 'site' not in md:raise ValueError('Expected released site column in '+n)
                        md=md.rename(columns={'site':'site_id'})
                    charged_ids[n.split('/')[0]]=set(md.site_id.astype(str))
            city_meta=[]
            for city,ids in charged_ids.items():
                source=next(n for n in members if n.startswith(city+'/'))
                cols=set(pd.read_csv(z.open(source),nrows=0).columns[1:])
                info=pd.read_csv(z.open(city+'/info.csv'))
                site=pd.read_csv(z.open(city+'/sites.csv'))
                id_col='site' if city in ['MEL','SPO'] else 'site_id'
                city_meta.append({'city':city,'sites_rows':len(site),'unique_site_ids':len(ids),'duplicate_site_ids':int(site[id_col].duplicated().sum()),'released_site_id_column':id_col,
                  'volume_columns':len(cols),'volume_ids_without_metadata':sorted(cols-ids),'metadata_ids_without_volume':sorted(ids-cols),
                  'info_headers':list(info.columns),'metadata_coordinate_system':'unverified','static_aggregate_features':'not used as predictors'})
            json_write(report/'city_metadata_audit.json',city_meta)
        if limit:tasks=tasks[:limit]
        for i,(city,native,task) in enumerate(tasks):
            try:
                if isinstance(task,tuple):source,frame=task
                else:source=task;frame=pd.read_csv(z.open(source))
                if i==0:
                    dictionary=[{'field':c,'dtype':str(frame[c].dtype),'role':'target estimated kWh' if c=='volume' else 'released timestamp (semantics pending)' if c=='time' else 'auxiliary, not predictor in this phase'} for c in frame.columns]
                    json_write(report/'data_dictionary.json',dictionary)
                if not {'time','volume'}.issubset(frame.columns):raise ValueError('Unexpected target schema')
                out,a=hourly(frame,5 if dataset=='urbanev' else 60)
                out=enrich(out,dataset,city,native,source,run_id,dataset=='charged')
                a.update(entity_id=f'{dataset}:{city}:{native}',city=city,native_id=native)
                if dataset=='urbanev':
                    a['metadata_id_match']=bool(int(native) in set(meta.station_id))
                    a['raw_missing_cells']=int(frame.isna().sum().sum())
                    compare=source.replace('station-raw/charge_5min/','station-processed/')
                    if compare in z.namelist():
                        comp=pd.read_csv(z.open(compare),usecols=['time','volume'])
                        joined=frame[['time','volume']].merge(comp,on='time',suffixes=('_raw','_processed'))
                        a['publisher_filled_volume_rows']=int((joined.volume_raw.isna()&joined.volume_processed.notna()).sum())
                        a['publisher_changed_volume_rows']=int((joined.volume_raw.notna()&joined.volume_processed.notna()&~np.isclose(joined.volume_raw,joined.volume_processed,rtol=1e-8,atol=1e-6)).sum())
                    else:a['publisher_processed_counterpart']=False
                else:a['metadata_id_match']=native in charged_ids.get(city,set())
                audits.append(a)
                table=pa.Table.from_pandas(out,preserve_index=False)
                if city not in writers:writers[city]=pq.ParquetWriter(processed/f'{city}_hourly_candidate.parquet',table.schema,compression='zstd')
                writers[city].write_table(table)
                d=out.set_index('interval_start_local').resample('D').agg({'energy_kwh':lambda s:s.sum(min_count=1),'file_value_valid':'mean','coverage_fraction':'mean'})
                d['entity_id']=a['entity_id'];d['city']=city;daily.append(d.reset_index())
                # Deterministic evenly spaced descriptive sample; never a training cohort.
                vals=out.energy_kwh.dropna().to_numpy(); samples.extend(vals[np.linspace(0,len(vals)-1,min(256,len(vals)),dtype=int)].tolist() if len(vals) else [])
                if i%50==0:logging.info('%s %d/%d (%s)',dataset,i+1,len(tasks),native)
                if i%100==0:pd.DataFrame(audits).to_csv(report/'entity_audit.csv',index=False)
            except Exception as e:
                failures.append({'entity':native,'source':str(task)[:300],'error':str(e)});logging.exception('Entity failed %s',native)
        for w in writers.values():w.close()
    audit=pd.DataFrame(audits);audit.to_csv(report/'entity_audit.csv',index=False)
    if daily:pd.concat(daily,ignore_index=True).to_parquet(report/'daily_audit.parquet',index=False)
    json_write(report/'failures.json',failures)
    summary={'dataset':dataset,'run_id':run_id,'entities_succeeded':len(audits),'entities_failed':len(failures),'scope':'smoke' if limit else 'full released standard scope',
      'panel_status':'candidate only: released timezone/bin/availability require verification','strict_online_ready':False,
      'upstream_status':'publisher processed, masks unknown' if dataset=='charged' else 'structured station-raw release, already derived volume; original pile events unavailable',
      'independence_status':'Shenzhen overlap not established; no cross-release native-ID mapping',
      'source_sha256':digest(archive),'code_sha256':digest(__file__),'runtime':{'pandas':pd.__version__,'numpy':np.__version__,'pyarrow':pa.__version__},
      'totals':{c:int(audit[c].sum()) for c in ['input_rows','exact_duplicates','conflicting_timestamps','malformed_timestamps','negative_values','nonfinite_values','valid_hours','invalid_hours','zero_hours']} if len(audit) else {}}
    summary['reconciliation_pass']=bool(len(audit) and audit.reconciliation_pass.all())
    summary['panels']=[str(p.relative_to(ROOT)) for p in processed.glob('*.parquet')]
    json_write(report/'qc_summary.json',summary)
    if len(audit):visuals(report,processed,audit,pd.concat(daily,ignore_index=True),samples,coordinates,summary)
    print(json.dumps(summary,ensure_ascii=False))

def visuals(report,processed,audit,daily,samples,coordinates,summary):
    figs=report/'figures';figs.mkdir(exist_ok=True);notes=[]
    def save(name,title,note):
        plt.title(title);plt.tight_layout();plt.savefig(figs/(name+'.png'),dpi=140);plt.close();notes.append((name,title,note))
    plt.figure(figsize=(12,7));pivot=daily.pivot(index='entity_id',columns='interval_start_local',values='file_value_valid').sort_index()
    plt.imshow(pivot.to_numpy(),aspect='auto',vmin=0,vmax=1,cmap='viridis');plt.colorbar(label='Fraction valid released-hour bins');plt.xlabel('Days, chronological');plt.ylabel('All entities, sorted ID')
    save('coverage_heatmap','Daily coverage — released timestamps',f'{len(pivot)} entities; coverage is file validity, not original-observation proof.')
    plt.figure(figsize=(10,4));plt.hist(audit.invalid_hours/audit.output_hours,bins=30,alpha=.7,label='invalid/missing hours');plt.hist(audit.zero_hours/audit.output_hours,bins=30,alpha=.6,label='valid zero hours');plt.legend();plt.xlabel('Fraction of released-hour grid')
    save('zero_missing','Zero and missing are separate',f'Invalid hours: {int(audit.invalid_hours.sum()):,}; valid zero hours: {int(audit.zero_hours.sum()):,}.')
    plt.figure(figsize=(10,4));plt.hist(np.log1p(samples),bins=60);plt.xlabel('log(1 + estimated energy kWh)')
    save('energy_distribution','Estimated hourly energy — descriptive sample','Up to256 evenly spaced valid bins per entity, fixed deterministic rule; not full-distribution quantiles.')
    plt.figure(figsize=(10,4));series=daily.groupby('interval_start_local').energy_kwh.sum(min_count=1);plt.plot(series.index,series.values);plt.ylabel('Sum of available estimated kWh');plt.xticks(rotation=25)
    save('daily_energy','Daily totals over available valid bins','Coverage changes can drive totals; not a complete metered demand series.')
    chosen=[]
    for criterion,col,asc in [('coverage','valid_hours',False),('sparse','zero_hours',False),('gaps','invalid_hours',False)]:
        for _,r in audit.sort_values([col,'entity_id'],ascending=[asc,True]).iterrows():
            if r.entity_id not in [x[0] for x in chosen]:chosen.append((r.entity_id,criterion,r.city));break
    json_write(report/'representative_entities.json',[{'entity_id':e,'reason':r} for e,r,c in chosen])
    pattern=[];gaps=[]
    fig,axes=plt.subplots(len(chosen),1,figsize=(12,3*len(chosen)),squeeze=False)
    for i,(entity,reason,city) in enumerate(chosen):
        p=processed/f'{city}_hourly_candidate.parquet';df=pd.read_parquet(p,filters=[('entity_id','==',entity)])
        axes[i,0].plot(df.interval_start_local,df.partial_energy_kwh,alpha=.45,label='partial released sum');axes[i,0].plot(df.interval_start_local,df.energy_kwh,label='complete accepted sum');axes[i,0].set_title(entity+' — '+reason);axes[i,0].legend();axes[i,0].set_ylabel('estimated kWh')
    plt.tight_layout();plt.savefig(figs/'before_after_examples.png',dpi=140);plt.close();notes.append(('before_after_examples','Before/after examples','Only validity masking/aggregation; no imputation, scaling or outlier removal.'))
    # Read one city at a time, retaining only low-dimensional EDA aggregates.
    for p in processed.glob('*.parquet'):
        df=pd.read_parquet(p,columns=['entity_id','interval_start_local','energy_kwh','file_value_valid'])
        t=pd.to_datetime(df.interval_start_local);df['hour']=t.dt.hour;df['weekday']=t.dt.dayofweek
        pattern.append(df.groupby(['hour','weekday']).energy_kwh.agg(['sum','count']))
        for _,g in df.groupby('entity_id',sort=False):
            miss=~g.file_value_valid.to_numpy();edges=np.diff(np.r_[False,miss,False].astype(int));gaps.extend((np.where(edges==-1)[0]-np.where(edges==1)[0]).tolist())
    agg=pd.concat(pattern).groupby(level=[0,1]).sum();mean=(agg['sum']/agg['count']).unstack()
    plt.figure(figsize=(10,4));plt.imshow(mean.T,aspect='auto',cmap='magma');plt.colorbar(label='Mean estimated kWh / valid bin');plt.xlabel('Released clock hour');plt.ylabel('Weekday (0=Mon)')
    save('hour_weekday','Hour × weekday pattern','Released clock only; timezone and DST semantics unverified. Weighted across valid entity-hour bins.')
    plt.figure(figsize=(10,4));plt.hist(np.log1p(gaps),bins=35);plt.xlabel('log(1 + consecutive invalid hours)')
    save('gap_lengths','Invalid/missing run lengths',f'{len(gaps):,} invalid runs; file missingness only, not hidden upstream imputation.')
    if coordinates:
        md=coordinates[0];plt.figure(figsize=(8,6));plt.scatter(md.longitude,md.latitude,s=4,alpha=.6);plt.xlabel('Longitude (GCJ-02)');plt.ylabel('Latitude (GCJ-02)')
        save('station_map','UrbanEV station metadata — GCJ-02','Coordinates from official station_information; no basemap mixing or coordinate conversion.')
    audit_notes=['Full-period EDA is descriptive only; not used for split/model/threshold selection.',summary['upstream_status'],summary['panel_status'],'No scaler/imputed label/split/features/windows were created.']
    md='# Data audit — '+summary['dataset']+'\n\n'+ '\n'.join('- '+n for n in audit_notes)+'\n\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n'
    body='<h1>Data audit — '+summary['dataset']+'</h1><p>'+'</p><p>'.join(html.escape(n) for n in audit_notes)+'</p><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre>'
    for name,title,note in notes:
        md+='\n## '+title+'\n\n'+note+'\n\n!['+title+'](figures/'+name+'.png)\n'
        body+='<h2>'+html.escape(title)+'</h2><p>'+html.escape(note)+'</p><img src="figures/'+name+'.png" alt="'+html.escape(title)+'">'
    (report/'audit_report.md').write_text(md,encoding='utf-8')
    (report/'eda.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>EV Data Audit</title><style>body{font:16px Arial;max-width:1200px;margin:32px auto;padding:20px;background:#f7fafc;color:#203744}img{width:100%;height:auto}pre{white-space:pre-wrap;background:white;padding:20px}</style>'+body+'</html>',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['urbanev','charged'],required=True);p.add_argument('--run-id',required=True);p.add_argument('--limit',type=int);a=p.parse_args();run(a.dataset,a.run_id,a.limit)
