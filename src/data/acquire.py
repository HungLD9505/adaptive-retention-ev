"""Acquire public releases with immutable manifests, retries and checksums."""
from __future__ import annotations
import argparse, hashlib, json, logging, shutil, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.deps'))
import requests
from filelock import FileLock

def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()

def download(url, destination, expected_size=None, checksum=None):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    # Serialize writers for each raw path, including independent CLI invocations.
    with FileLock(str(destination)+'.lock',timeout=600):
        return _download(url,destination,expected_size,checksum)

def _download(url, destination, expected_size=None, checksum=None):
    dest = Path(destination); dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if checksum:
            algorithm, value = checksum.split(':', 1)
            if digest(dest, algorithm) != value: raise ValueError('Existing raw checksum mismatch: '+str(dest))
        if expected_size and dest.stat().st_size != expected_size: raise ValueError('Existing raw size mismatch')
        return dest
    if expected_size and shutil.disk_usage(dest.parent).free < expected_size*4:
        raise OSError('Insufficient disk space for archive and processing')
    part = dest.with_suffix(dest.suffix+'.part')
    if expected_size and part.exists() and part.stat().st_size>=expected_size:
        good=part.stat().st_size==expected_size
        if checksum:
            algorithm,value=checksum.split(':',1);good=good and digest(part,algorithm)==value
        if good:part.rename(dest);return dest
        quarantine=part.with_name(part.name+'.rejected_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S'))
        part.rename(quarantine)
        logging.warning('Preserved invalid partial file: %s',quarantine)
    for attempt in range(3):
        try:
            offset = part.stat().st_size if part.exists() else 0
            headers = {'Range':f'bytes={offset}-'} if offset else {}
            with requests.get(url, headers=headers, stream=True, timeout=(20,90)) as r:
                r.raise_for_status()
                resume = offset and r.status_code == 206
                if resume and not r.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                    raise ValueError('Invalid resume response')
                with part.open('ab' if resume else 'wb') as f:
                    for block in r.iter_content(1024*1024):
                        if block: f.write(block)
            if expected_size and part.stat().st_size != expected_size: raise ValueError('Incomplete download')
            if checksum:
                algorithm, value = checksum.split(':',1)
                if digest(part,algorithm) != value: raise ValueError('Publisher checksum mismatch')
            part.rename(dest); return dest
        except Exception:
            logging.exception('Download attempt %d failed: %s', attempt+1,url)
            if attempt == 2: raise
            time.sleep(2*(attempt+1))

def acquire(run_id):
    report = ROOT/'reports/data'/run_id; report.mkdir(parents=True,exist_ok=False)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(report/'download.log',encoding='utf-8'),logging.StreamHandler()])
    manifest={'run_id':run_id,'acquired_at':datetime.now(timezone.utc).isoformat(),'files':[],'failures':[]}
    def record(url,path,size=None,checksum=None,**meta):
        try:
            p=download(url,path,size,checksum)
            entry=dict(meta,url=url,path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p),publisher_checksum=checksum,status='downloaded')
            if p.suffix=='.zip':
                with zipfile.ZipFile(p) as z:
                    entry['uncompressed_bytes']=sum(i.file_size for i in z.infolist())
                    entry['archive_members']=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size} for i in z.infolist()]
                    bad=z.testzip()
                    if bad:raise ValueError('Bad archive CRC '+bad)
            manifest['files'].append(entry)
            logging.info('Verified %s (%d bytes)',p.name,p.stat().st_size)
        except Exception as e:manifest['failures'].append({'url':url,'error':str(e)});logging.exception('Acquisition blocked')
        (report/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    urban=ROOT/'data/raw/urbanev/official_2026_05_11'
    record('https://raw.githubusercontent.com/IntelligentSystemsLab/UrbanEV/main/readme.md',urban/'repository_README.md',dataset='UrbanEV',role='source_documentation')
    record('https://raw.githubusercontent.com/IntelligentSystemsLab/UrbanEV/main/LICENSE',urban/'repository_LICENSE',dataset='UrbanEV',license='CC0-1.0')
    # Public Drive URLs are linked directly by the official repository. No private cookies.
    for file_id,name,size in [('1OEpo-XDocd33aK3MbgDt9S5bcqwiAFPQ','UrbanEVDataset.zip',647305188),('1ojGWoQ13w2o59DjEAuUk2-CPzG08NRIT','UrbanEVSupplemental.zip',6052188)]:
        record('https://drive.usercontent.google.com/download?id='+file_id+'&export=download&confirm=t',urban/name,size,dataset='UrbanEV',release='official Drive 2026-05-11',role='release_archive_scope_pending_inventory')
    # Dryad immutable file listing retained as independent release evidence.
    record('https://datadryad.org/api/v2/versions/423269/files',urban/'dryad_files.json',dataset='UrbanEV',role='mirror_inventory')
    record('https://datadryad.org/api/v2/files/4587831/download',urban/'dryad_README.md',14914,'sha256:ec2aba0a893d2b310b12ddfd006679ae92a85149aa7a767e1734e82d175ac177',dataset='UrbanEV',role='mirror_documentation')
    charged=ROOT/'data/raw/charged/zenodo_15814263'
    api='https://zenodo.org/api/records/15814263'
    record(api,charged/'record.json',dataset='CHARGED',role='release_metadata')
    if (charged/'record.json').exists():
        metadata=json.loads((charged/'record.json').read_text())
        for f in metadata['files']:
            if f['key'] in ['README.md','Hourly.zip']:
                record(f['links']['self'],charged/f['key'],f['size'],f['checksum'],dataset='CHARGED',release='15814263',license=metadata['metadata']['license']['id'])
    print(json.dumps({'manifest':str(report/'source_manifest.json'),'files':len(manifest['files']),'failures':manifest['failures']},ensure_ascii=False))
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args();acquire(args.run_id)
