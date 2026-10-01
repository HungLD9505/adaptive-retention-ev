"""Add handoff visualizations and Vietnamese conclusions after successful runs."""
import argparse,html,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'.deps'))
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pyarrow.parquet as pq

def run(run_id):
    report=ROOT/'reports/data'/run_id;q=json.loads((report/'qc_summary.json').read_text());d=pd.read_parquet(report/'daily_audit.parquet');a=pd.read_csv(report/'entity_audit.csv')
    extra=[]
    def save(name,title,note):
        plt.title(title);plt.tight_layout();plt.savefig(report/'figures'/(name+'.png'),dpi=140);plt.close();extra.append((name,title,note))
    plt.figure(figsize=(10,4));plt.hist(np.log1p(d.energy_kwh.dropna()),bins=60);plt.xlabel('log(1 + available estimated entity-day kWh)')
    save('daily_distribution','Daily energy distribution','Tổng ngày trên các giờ có giá trị; chưa phải tổng energy ngày đủ coverage. Không dùng để chọn cohort final.')
    sums=np.zeros(2);counts=np.zeros(2)
    for p in q['panels']:
        for b in pq.ParquetFile(ROOT/p).iter_batches(batch_size=100000,columns=['interval_start_local','energy_kwh']):
            f=b.to_pandas();weekday=pd.to_datetime(f.interval_start_local).dt.dayofweek
            for i,flag in enumerate([weekday<5,weekday>=5]):
                vals=f.loc[flag,'energy_kwh'].dropna();sums[i]+=vals.sum();counts[i]+=len(vals)
    plt.figure(figsize=(8,4));plt.bar(['Weekday','Weekend'],np.divide(sums,counts,out=np.full(2,np.nan),where=counts>0));plt.ylabel('Mean estimated kWh / valid released-hour bin')
    save('weekday_weekend','Weekday vs weekend','Calendar theo timestamp phát hành, timezone chưa xác minh; weighted theo valid entity-hour, không phải so sánh nhân quả.')
    if 'publisher_filled_volume_rows' in a:
        plt.figure(figsize=(9,4));plt.bar(['Filled raw missing','Changed observed values'],[a.publisher_filled_volume_rows.sum(),a.publisher_changed_volume_rows.sum()]);plt.ylabel('5-minute records')
        save('publisher_before_after','Publisher processed vs structured raw','Đối chiếu trực tiếp volume theo cùng station và timestamp; không dùng bản filled làm ground truth. Counterparts không tồn tại được ghi riêng.')
    total=q['totals']['valid_hours']+q['totals']['invalid_hours'];rate=q['totals']['invalid_hours']/total
    lines=[f'Đã xử lý {q["entities_succeeded"]:,} entities; {total:,} bin giờ; missing/invalid theo file {rate:.2%}.',
      f'{q["totals"]["zero_hours"]:,} bin giờ zero hợp lệ số học được giữ nguyên; thiếu label không được điền.',
      'Energy là estimate từ trạng thái/công suất, không phải số đo công tơ. Original-observation status và label availability chưa xác minh.',
      'Panel là candidate theo giờ hiển thị; không chứng nhận strict online, timezone/DST/bin semantics hoặc upstream causality.',
      'EDA toàn kỳ chỉ mô tả. Split/cohort/dates, imputation/scaling, features và windows chuyển development.',
      'Nghiệm thu: đủ để tiếp tục audit/development trên published-data candidate, chưa đạt gate strict causal experiment.']
    if q['dataset']=='urbanev':
        m=json.loads((report/'metadata_audit.json').read_text());lines.append(f'Metadata local: {m["unique_station_ids"]:,} station IDs, {m["unique_pile_ids"]:,} pile IDs; {m["nonpositive_or_missing_rated_power"]} rated-power records thiếu/không dương. Không dùng số paper thay số local.')
        aux=pd.read_csv(report/'auxiliary_audit.csv');lines.append('Auxiliary QC được lưu riêng; static inventory không được mặc định known-at-origin. '+str(aux[['busy_balance_mismatch_rows','idle_balance_mismatch_rows','negative_fee_rows']].sum().to_dict()))
    else:
        lines.append('CHARGED license CC BY4.0 theo record; upstream IQR correction/zero interpolation, original masks không xác nhận. Shenzhen independence chưa xác minh.')
        lines.append('MEL/SPO metadata dùng cột site, các city khác site_id; alias đã ghi city_metadata_audit. Một số info headers malformed, không dùng làm predictors.')
    md=(report/'audit_report.md').read_text(encoding='utf-8');body=(report/'eda.html').read_text(encoding='utf-8')
    md+='\n## Nhận xét và bàn giao\n\n'+'\n'.join('- '+x for x in lines)+'\n'
    fragment='<h2>Nhận xét và bàn giao</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in lines)+'</ul>'
    for name,title,note in extra:
        md+='\n## '+title+'\n\n'+note+'\n\n!['+title+'](figures/'+name+'.png)\n'
        fragment+='<h2>'+html.escape(title)+'</h2><p>'+html.escape(note)+'</p><img src="figures/'+name+'.png">'
    (report/'audit_report.md').write_text(md,encoding='utf-8');(report/'eda.html').write_text(body.replace('</html>',fragment+'</html>'),encoding='utf-8')
    (report/'handoff.json').write_text(json.dumps({'conclusions':lines,'pending':['time semantics','label availability','upstream masks','Shenzhen independence','development decisions'],'accepted':'published-data candidate; strict causal gate not met'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(run_id,'handoff visuals complete',len(list((report/'figures').glob('*.png'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
