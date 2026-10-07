"""Independent readback, prefix scaler audit and full rerun comparison."""
import argparse
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from .core import ROOT, InputLoader, split_entities, fit_scale, tensors, full_window_exists, pd, np
from .build import sha, write_json, read_series

def check(primary, repeat):
    p=ROOT/'reports/inputs'/primary;r=ROOT/'reports/inputs'/repeat
    pm=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
    rm=json.loads((r/'manifest.json').read_text(encoding='utf-8'))
    checks={}
    checks['raw_panel_hashes_unchanged']=pm['source_hashes_sha256']==rm['source_hashes_sha256']
    for name in ['src/inputs/core.py','src/inputs/build.py','src/inputs/test_inputs.py']:
        assert pm['code_hashes_sha256'][name]==rm['code_hashes_sha256'][name]
    checks['preprocessing_code_same']=True
    configs=[]
    for directory in [p,r]:
        c=json.loads((directory/'config.json').read_text(encoding='utf-8'));c.pop('run_id');configs.append(c)
    checks['protocol_same']=configs[0]==configs[1]
    for name in ['split_manifest','cohort_manifest','scalers','window_audit','cohort_counts','window_counts','allowed_prefix_counts']:
        a=pd.read_csv(p/f'{name}.csv');b=pd.read_csv(r/f'{name}.csv')
        pd.testing.assert_frame_equal(a,b)
        checks[f'{name}_reproducible']=True
    l=InputLoader(pm['input_dir']);rr=InputLoader(rm['input_dir'])
    pd.testing.assert_frame_equal(l.index.drop(columns='run_id'),rr.index.drop(columns='run_id'))
    checks['index_values_reproducible']=True
    split=pd.read_csv(p/'split_manifest.csv')
    rebuilt=split_entities(split.drop(columns=['split_hash','role']).to_dict('records'))
    pd.testing.assert_frame_equal(split,pd.DataFrame(rebuilt),check_dtype=False)
    checks['hash_split_recomputed']=True
    scaler=pd.read_csv(p/'scalers.csv');cohort=pd.read_csv(p/'cohort_manifest.csv')
    dataset=pm['dataset'];cutoff=pd.Timestamp(configs[0]['deployment_cutoff'])
    positive=[]
    for row in split[split.role=='source'].to_dict('records'):
        s=read_series(row);v=s[(s.index<cutoff)&(s>0)].to_numpy()
        if len(v):positive.append(v)
    fallback=float(np.quantile(np.concatenate(positive),.95)) if positive else 1.
    assert np.isclose(fallback,pm['source_positive_p95_fallback_kwh'],rtol=1e-12)
    assert sum(map(len,positive))==pm['source_positive_count']
    del positive
    for entity,g in scaler.groupby('entity_id'):
        s=read_series(g.iloc[0].to_dict())
        for row in g.itertuples():
            fit=fit_scale(s,pd.Timestamp(row.fit_start),pd.Timestamp(row.fit_end_exclusive),fallback)
            assert np.isclose(fit['scale_kwh'],row.scale_kwh,rtol=1e-12)
            assert fit['valid_fit_hours']==row.valid_fit_hours and fit['zero_fit_hours']==row.zero_fit_hours
    checks['all_scalers_recomputed_from_allowed_prefix']=True
    samples=json.loads((p/'tensor_samples.json').read_text(encoding='utf-8'))
    causal_n=0
    for sample in samples:
        i=sample['index'];row=l.index.iloc[i]
        as_of=max(row.assumed_available_at,row.scaler_frozen_at)
        a=l.load(i,include_labels=True,as_of=as_of);b=rr.load(i,include_labels=True,as_of=as_of)
        for k in ['X_hist','C_future','Y']:np.testing.assert_array_equal(a[k],b[k])
        if row.phase=='stream':
            series=l._series(row.panel_file,row.row_group).copy()
            series.loc[series.index>=row.origin]=np.nan
            X,C,_=tensors(series,row.origin,row.scale_kwh)
            np.testing.assert_array_equal(a['X_hist'],X);np.testing.assert_array_equal(a['C_future'],C)
            sc=scaler[(scaler.entity_id==row.entity_id)&(scaler.budget_days==row.budget_days)].iloc[0]
            fit=fit_scale(series,pd.Timestamp(sc.fit_start),pd.Timestamp(sc.fit_end_exclusive),fallback)
            assert np.isclose(fit['scale_kwh'],sc.scale_kwh,rtol=1e-12)
            assert full_window_exists(series,cutoff-pd.Timedelta(days=7),cutoff)
            causal_n+=1
    checks['tensor_repeat_samples']=len(samples)
    checks['real_stream_future_perturbation_samples']=causal_n
    checks['canonical_actual_availability_not_overwritten']=bool((l.index.label_available_at_status=='unknown').all())
    # Verify all persisted references/manifest hashes without rewriting source panels.
    for filename,expected in pm['artifact_hashes_sha256'].items():assert sha(p/filename)==expected
    assert sha(Path(pm['input_dir'])/'window_index.parquet')==pm['index_sha256']
    checks['artifact_hash_readback']=True
    ranges=l.index.groupby(['city','role','budget_days','phase']).agg(windows=('origin','size'),first_origin=('origin','min'),last_origin=('origin','max')).reset_index()
    ranges.to_csv(p/'window_ranges.csv',index=False)
    scaler['expected_prefix_hours']=((pd.to_datetime(scaler.fit_end_exclusive)-pd.to_datetime(scaler.fit_start))/pd.Timedelta(hours=1)).astype(int)
    scaler['missing_prefix_hours']=scaler.expected_prefix_hours-scaler.valid_fit_hours
    assert (scaler.missing_prefix_hours>=0).all()
    scaler['missing_fraction']=scaler.missing_prefix_hours/scaler.expected_prefix_hours
    scaler['zero_fraction_valid']=scaler.zero_fit_hours/scaler.valid_fit_hours
    scaler[['city','role','entity_id','budget_days','expected_prefix_hours','valid_fit_hours','missing_prefix_hours','zero_fit_hours','missing_fraction','zero_fraction_valid']].to_csv(p/'prefix_quality.csv',index=False)
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for role,g in scaler.groupby('role'):
        axes[0].hist(g.missing_fraction,bins=np.linspace(0,1,21),alpha=.5,label=role)
        axes[1].hist(g.zero_fraction_valid,bins=np.linspace(0,1,21),alpha=.5,label=role)
    axes[0].set(title='Missing fraction in permitted prefix',xlabel='Fraction');axes[1].set(title='Zero fraction among valid prefix values',xlabel='Fraction')
    for ax in axes:ax.set_ylabel('Entity-budget count');ax.legend()
    fig.tight_layout();fig.savefig(p/'figures/05_prefix_quality.png',dpi=140);plt.close(fig)
    checks['html_and_figures_readback']=html_check(p)
    checks['passed']=all(checks.values())
    write_json(p/'reproducibility_checks.json',{'primary_run':primary,'repeat_run':repeat,'qa_code_sha256':sha(__file__),**checks})
    supplement=f'''# QC bổ sung và tái lập — {dataset}

Primary `{primary}`; rebuild `{repeat}` giữ nguyên raw/config/preprocessing code. So sánh tất cả split/cohort/scalers/audit và index values sau khi bỏ run_id. Tensor samples lặp lại bit-exact; scaler được tính lại từ prefix cho mọi entity-budget. Raw/panel hashes không đổi giữa hai lần dựng.

Checks: `{checks}`.

`prefix_quality.csv` chỉ dùng lịch sử được phép, phân biệt missing/zero; `05_prefix_quality.png` minh họa phân phối. CHARGED missing=0 trong release không chứng minh original observation. `window_ranges.csv` ghi origin đầu/cuối theo city/role/budget/phase.

Future perturbation chỉ bảo vệ X/calendar/scale/cohort đã quyết định trước origin stream. Y và scoring eligibility có thể thay đổi nếu sửa nhãn tương lai; đó là lý do forecast schedule tách khỏi retrospective scoring index. Không claim kiểm tra này loại leakage upstream.

Tái chạy QC: `python -m src.inputs.qa --primary {primary} --repeat {repeat}`. QC từ chối ghi đè artifacts cùng tên; dùng run mới khi thay thiết kế. Model/controller/experiment vẫn chưa thực hiện.
'''
    (p/'qc_supplement.md').write_text(supplement,encoding='utf-8')
    (p/'qc.html').write_text('<!doctype html><meta charset="utf-8"><title>Prefix QC</title><h1>Prefix-only QC and reproducibility</h1><p>See qc_supplement.md and reproducibility_checks.json. No strict-online claim.</p><img style="max-width:100%" src="figures/05_prefix_quality.png">'+ranges.to_html(index=False),encoding='utf-8')
    assert html_check(p,'qc.html')
    if not checks['passed']:raise AssertionError(checks)
    print(json.dumps(checks,indent=2))

def html_check(directory,name='eda.html'):
    class Images(HTMLParser):
        def __init__(self):super().__init__();self.images=[]
        def handle_starttag(self,tag,attrs):
            if tag=='img':self.images.append(dict(attrs)['src'])
    parser=Images();parser.feed((directory/name).read_text(encoding='utf-8'))
    assert parser.images
    from PIL import Image
    for src in parser.images:
        with Image.open(directory/src) as img:img.verify()
    return True

def main():
    a=argparse.ArgumentParser();a.add_argument('--primary',required=True);a.add_argument('--repeat',required=True);args=a.parse_args()
    for value in [args.primary,args.repeat]:
        if Path(value).name!=value:a.error('Run names must be single directory names')
    if (ROOT/'reports/inputs'/args.primary/'reproducibility_checks.json').exists():raise FileExistsError('QA already exists; preserve it')
    check(args.primary,args.repeat)

if __name__=='__main__':main()
