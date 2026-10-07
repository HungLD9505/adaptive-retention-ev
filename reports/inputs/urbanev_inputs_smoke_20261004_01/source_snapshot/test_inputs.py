"""Protocol fixtures independent of release sizes."""
import unittest
import tempfile
from pathlib import Path
from .core import ROOT, split_entities, canonical, grid, origins, full_window_exists, fit_scale, tensors, InputLoader, pd, np, pq
import pyarrow as pa

class InputTests(unittest.TestCase):
    def series(self, days=40):
        return pd.Series(np.arange(days*24,dtype=float)%11,index=pd.date_range('2022-10-22',periods=days*24,freq='h'))

    def test_split_repeat_disjoint_city_small(self):
        rec=[{'entity_id':f'{c}:{i}','city':c} for c,n in [('A',21),('B',1),('C',3)] for i in range(n)]
        a=split_entities(rec);b=split_entities(list(reversed(rec)))
        self.assertEqual(a,b)
        self.assertEqual(len(set(r['entity_id'] for r in a)),len(rec))
        self.assertEqual(sum(r['role']=='source' and r['city']=='A' for r in a),13)
        self.assertEqual(sum(r['role']=='development' and r['city']=='A' for r in a),4)

    def test_budget_boundaries(self):
        s=self.series(70);cut=pd.Timestamp('2022-12-01')
        for b in [7,14,28]:
            oo=origins(s,cut-pd.Timedelta(days=b),cut)
            self.assertEqual(len(oo),b-1)
            self.assertEqual(oo[0]-pd.Timedelta(hours=24),cut-pd.Timedelta(days=b))
            self.assertEqual(oo[-1]+pd.Timedelta(hours=24),cut)
        source=origins(s,s.index.min(),cut)
        self.assertTrue(all(o+pd.Timedelta(hours=24)<=cut for o in source))
        stream=origins(s,cut-pd.Timedelta(hours=24),pd.Timestamp('2022-12-31'))
        self.assertEqual(stream[0],cut)
        self.assertEqual(stream[-1]+pd.Timedelta(hours=24),pd.Timestamp('2022-12-31'))

    def test_shapes_missing_zero(self):
        s=self.series();o=s.index[48];s.iloc[24]=0;s.iloc[25]=np.nan
        x,c,y=tensors(s,o,2)
        self.assertEqual(x.shape,(24,7));self.assertEqual(c.shape,(24,5));self.assertEqual(y.shape,(24,))
        self.assertEqual(x.dtype,np.float32)
        self.assertEqual(tuple(x[0,:2]),(0,1));self.assertEqual(tuple(x[1,:2]),(0,0))
        self.assertTrue(np.isfinite(x).all())

    def test_missing_labels_not_filled(self):
        s=self.series();o=s.index[48];s.iloc[49]=np.nan
        self.assertTrue(np.isnan(tensors(s,o,1)[2][1]))
        s.iloc[24:48]=np.nan
        with self.assertRaises(ValueError):tensors(s,o,1)

    def test_scale_scope_and_fallback(self):
        s=self.series();cut=s.index[24*10]
        a=fit_scale(s,s.index[0],cut,7)
        s.loc[s.index>=cut]=1e9
        self.assertEqual(a,fit_scale(s,s.index[0],cut,7))
        s.loc[s.index<cut]=0
        b=fit_scale(s,s.index[0],cut,7)
        self.assertEqual(b['scale_kwh'],7);self.assertTrue(b['all_zero_initial'])
        self.assertEqual(fit_scale(s,cut-pd.Timedelta(days=7),cut,1)['scale_kwh'],1)

    def test_causality_eligibility_history_scale(self):
        s=self.series();o=s.index[24*10]
        eligibility=full_window_exists(s,o-pd.Timedelta(days=7),o)
        scale=fit_scale(s,o-pd.Timedelta(days=7),o,3)
        x,c,_=tensors(s,o,scale['scale_kwh'])
        s.loc[s.index>=o]=np.nan
        self.assertEqual(eligibility,full_window_exists(s,o-pd.Timedelta(days=7),o))
        self.assertEqual(scale,fit_scale(s,o-pd.Timedelta(days=7),o,3))
        xx,cc,_=tensors(s,o,scale['scale_kwh'])
        np.testing.assert_array_equal(x,xx);np.testing.assert_array_equal(c,cc)
        # Completed and assumed-available window is unchanged by modifications after its horizon.
        s=self.series();y=tensors(s,o,2)[2];s.loc[s.index>=o+pd.Timedelta(hours=24)]=1e8
        np.testing.assert_array_equal(y,tensors(s,o,2)[2])

    def test_gaps_and_invalid_timestamp(self):
        s=self.series().drop(self.series().index[27]);self.assertTrue(np.isnan(grid(s,s.index[24])[3]))
        t=pd.date_range('2022-01-01',periods=3,freq='h')
        f=pd.DataFrame({'interval_start_local':t,'interval_end_local':t+pd.Timedelta(hours=1),'energy_kwh':[0,-1,2],'file_value_valid':[True,True,False]})
        v=canonical(f);self.assertEqual(v.iloc[0],0);self.assertTrue(v.iloc[1:].isna().all())
        with self.assertRaises(ValueError):canonical(pd.concat([f,f.iloc[:1]]))
        f.loc[0,'interval_start_local']=t[0]+pd.Timedelta(minutes=1)
        with self.assertRaises(ValueError):canonical(f)

    def test_long_gap_eligibility(self):
        s=self.series();cut=s.index[24*10];s.loc[(s.index>=cut-pd.Timedelta(days=7))&(s.index<cut)]=np.nan
        self.assertFalse(full_window_exists(s,cut-pd.Timedelta(days=7),cut))

    def test_scale_nonpositive(self):
        for sc in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):tensors(self.series(),pd.Timestamp('2022-10-24'),sc)

    def test_loader_label_gate(self):
        (ROOT/'.cache').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as temp:
            temp=Path(temp);s=self.series();o=s.index[48]
            panel=temp/'panel.parquet'
            pq.write_table(pa.Table.from_pandas(pd.DataFrame({'interval_start_local':s.index,'interval_end_local':s.index+pd.Timedelta(hours=1),'energy_kwh':s.values,'file_value_valid':True})),panel)
            row={'panel_file':str(panel),'row_group':0,'origin':o,'scale_kwh':2,'entity_id':'fixture','role':'final','budget_days':7,'assumed_available_at':o+pd.Timedelta(hours=24)}
            pq.write_table(pa.Table.from_pandas(pd.DataFrame([row])),temp/'window_index.parquet')
            loader=InputLoader(temp)
            self.assertNotIn('Y',loader.load(0))
            with self.assertRaises(ValueError):loader.load(0,include_labels=True,as_of=o)
            self.assertEqual(loader.load(0,include_labels=True,as_of=o+pd.Timedelta(hours=24))['Y'].shape,(24,))
            # Forecast API does not need the origin to be in the scoring index.
            self.assertEqual(loader.forecast('fixture',7,o+pd.Timedelta(days=1))['X_hist'].shape,(24,7))

if __name__=='__main__':unittest.main()
