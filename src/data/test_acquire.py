import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from acquire import download,ROOT

class Response:
    def __init__(self,status,data,headers=None):self.status_code=status;self.data=data;self.headers=headers or {}
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def raise_for_status(self):pass
    def iter_content(self,*a):yield self.data

class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        base=ROOT/'reports/data/test_artifacts';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base);self.dest=Path(self.tmp.name)/'data.bin';self.check='sha256:'+hashlib.sha256(b'abcdef').hexdigest()
    def tearDown(self):self.tmp.cleanup()
    def test_existing_immutable(self):
        self.dest.write_bytes(b'abcdef')
        with patch('acquire.requests.get') as get:download('https://example.invalid',self.dest,6,self.check);get.assert_not_called()
        with self.assertRaises(ValueError):download('https://example.invalid',self.dest,7,self.check)
    def test_resume(self):
        self.dest.with_suffix('.bin.part').write_bytes(b'abc')
        with patch('acquire.requests.get',return_value=Response(206,b'def',{'Content-Range':'bytes 3-5/6'})) as get:
            download('https://example.invalid',self.dest,6,self.check)
            self.assertEqual(get.call_args.kwargs['headers'],{'Range':'bytes=3-'})
        self.assertEqual(self.dest.read_bytes(),b'abcdef')
    def test_resume_ignored_restarts(self):
        self.dest.with_suffix('.bin.part').write_bytes(b'abc')
        with patch('acquire.requests.get',return_value=Response(200,b'abcdef')):download('https://example.invalid',self.dest,6,self.check)
        self.assertEqual(self.dest.read_bytes(),b'abcdef')
    def test_oversized_partial_quarantined(self):
        self.dest.with_suffix('.bin.part').write_bytes(b'corrupted-long')
        with patch('acquire.requests.get',return_value=Response(200,b'abcdef')):download('https://example.invalid',self.dest,6,self.check)
        self.assertEqual(len(list(self.dest.parent.glob('*.rejected_*'))),1)
    def test_checksum_failure_not_promoted(self):
        with patch('acquire.requests.get',return_value=Response(200,b'badbad')),patch('acquire.time.sleep'):
            with self.assertRaises(ValueError):download('https://example.invalid',self.dest,6,self.check)
        self.assertFalse(self.dest.exists())

if __name__=='__main__':unittest.main()
