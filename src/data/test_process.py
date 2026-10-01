import unittest
import pandas as pd
import numpy as np
from process import hourly

class HourlyTests(unittest.TestCase):
    def fixture(self):return pd.DataFrame({'time':pd.date_range('2022-09-01',periods=24,freq='5min'),'volume':np.ones(24)})
    def test_sum_boundaries(self):
        out,a=hourly(self.fixture(),5)
        self.assertEqual(out.energy_kwh.tolist(),[12.,12.]);self.assertTrue(a['reconciliation_pass'])
    def test_zero_missing_partial(self):
        f=self.fixture();f.loc[:11,'volume']=0;f.loc[13,'volume']=np.nan
        out,a=hourly(f,5);self.assertEqual(out.energy_kwh.iloc[0],0);self.assertTrue(pd.isna(out.energy_kwh.iloc[1]));self.assertEqual(out.partial_energy_kwh.iloc[1],11)
    def test_duplicate_conflict(self):
        f=self.fixture();out,a=hourly(pd.concat([f,f.iloc[:1]]),5);self.assertEqual(a['exact_duplicates'],1);self.assertEqual(out.energy_kwh.iloc[0],12)
        c=f.iloc[:1].copy();c.volume=3;out,a=hourly(pd.concat([f,c]),5);self.assertTrue(pd.isna(out.energy_kwh.iloc[0]));self.assertEqual(a['conflicting_timestamps'],1)
    def test_negative_inf_and_gap(self):
        f=self.fixture();f.loc[1,'volume']=-1;f.loc[13,'volume']=np.inf;out,a=hourly(f,5);self.assertTrue(out.energy_kwh.isna().all())
        f=self.fixture().drop(2);out,a=hourly(f,5);self.assertTrue(pd.isna(out.energy_kwh.iloc[0]));self.assertEqual(out.energy_kwh.iloc[1],12)
    def test_future_perturbation(self):
        f=self.fixture();before,_=hourly(f,5);f.loc[12:,'volume']=123;after,_=hourly(f,5)
        pd.testing.assert_frame_equal(before.iloc[:1],after.iloc[:1])
    def test_dst_unresolved_no_localization(self):
        f=pd.DataFrame({'time':['2023-10-29 02:00','2023-10-29 02:00','2023-10-29 03:00'],'volume':[1,2,3]})
        out,a=hourly(f,60);self.assertTrue(pd.isna(out.energy_kwh.iloc[0]));self.assertEqual(a['conflicting_timestamps'],1)
    def test_interval_cross_boundary_not_guessed(self):
        f=self.fixture();f.loc[11,'time']=pd.Timestamp('2022-09-01 00:57')
        out,a=hourly(f,5);self.assertTrue(pd.isna(out.energy_kwh.iloc[0]));self.assertEqual(a['offgrid_rows'],1)
        self.assertEqual(out.energy_kwh.iloc[1],12)
    def test_malformed_timestamp(self):
        f=self.fixture();f['time']=f.time.astype(str);f.loc[0,'time']='invalid'
        out,a=hourly(f,5);self.assertEqual(a['malformed_timestamps'],1);self.assertTrue(pd.isna(out.energy_kwh.iloc[0]))

if __name__=='__main__':unittest.main()
