#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse,hashlib,json,subprocess,shutil,tarfile,re
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--monado-repo',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--head',type=Path,default=r.parent/'qiyu-head-tracking');p.add_argument('--controller',type=Path,default=r.parent/'qiyu-controller-tracking');p.add_argument('--prepare-only',action='store_true');p.add_argument('--cmake-option',action='append',default=[]);a=p.parse_args();out=a.output.resolve()
if out.exists():p.error('Choose a new output directory')
meta=json.loads((r/'upstream.json').read_text());out.mkdir(parents=True);src=out/'source';src.mkdir();archive=out/'upstream.tar'
subprocess.run(['git','-C',str(a.monado_repo),'archive','--format=tar','--output='+str(archive),meta['commit']],check=True)
subprocess.run(['tar','-xf',str(archive),'-C',str(src)],check=True)
subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(src),'-i',str(r/'patches/monado-a081.patch')],check=True)
owners={'qiyu-head-tracking':a.head,'qiyu-controller-tracking':a.controller}
for dest,(owner,path) in meta['external_headers'].items():
 q=src/dest;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(re.sub(r'#include <qiyu/(?:head|controller)/([^>]+)>',r'#include "\1"',(owners[owner]/path).read_text()))
for path,digest in meta['changed_files_sha256'].items():
 q=src/path
 if digest is None:assert not q.exists(),path
 else:assert hashlib.sha256(q.read_bytes()).hexdigest()==digest,path
result={'upstream':meta['commit'],'patch_sha256':hashlib.sha256((r/'patches/monado-a081.patch').read_bytes()).hexdigest(),'all_downstream_files_match_frozen_source':True,'device_tested':False}
if not a.prepare_only:
 options=json.loads((r/'cmake-options.json').read_text());subprocess.run(['cmake','-S',str(src),'-B',str(out/'build'),'-G','Ninja',*options,*a.cmake_option],check=True);subprocess.run(['cmake','--build',str(out/'build'),'--target','driver_monado','-j4'],check=True);shutil.copytree(out/'build/steamvr-monado',out/'monado');result['driver_sha256']=hashlib.sha256((out/'monado/bin/linuxarm64/driver_monado.so').read_bytes()).hexdigest()
(out/'build-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
