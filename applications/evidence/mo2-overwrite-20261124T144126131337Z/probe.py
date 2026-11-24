#!/usr/bin/env python3
"""Owner-run unchanged sync methods with real Qt widgets/QFile on owned paths.

Offscreen source-fragment execution, not MO2/USVFS/Windows qualification.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import signal
import stat
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'applications/restic'))
from locks_probe import redact
PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def image(root):
    result={}
    for p in sorted(root.rglob('*')):
        s=p.lstat();row=dict(mode=stat.S_IMODE(s.st_mode))
        if p.is_symlink():row.update(kind='symlink',target=os.readlink(p))
        elif p.is_file():row.update(kind='file',bytes=s.st_size,sha256=sha(p))
        elif p.is_dir():row.update(kind='directory')
        else:raise AssertionError('Unexpected fixture node.')
        result[str(p.relative_to(root))]=row
    return result


def main():
    source=ROOT/'applications/tools/source-cache/mo2-output/src__syncoverwritedialog.cpp'
    data=source.read_text()
    run=ROOT/'applications/evidence'/('mo2-overwrite-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work'
    for n in ['home','tmp','cache','runtime','private','cases']:(work/n).mkdir(parents=True)
    (work/'runtime').chmod(0o700)
    (run/'probe.py').write_bytes(PRODUCER);(run/'driver.cpp').write_bytes((HERE/'overwrite_driver.cpp').read_bytes())
    (run/'helper.py').write_bytes((ROOT/'applications/restic/locks_probe.py').read_bytes())
    start=data.index('static void addToComboBox(')
    selected=data[start:];(work/'selected_sync.cpp').write_text(selected)
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),
        XDG_CACHE_HOME=str(work/'cache'),XDG_RUNTIME_DIR=str(work/'runtime'),QT_QPA_PLATFORM='offscreen',LANG='en_US.UTF-8')
    flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','Qt6Widgets'],text=True))
    version=subprocess.check_output(['pkg-config','--modversion','Qt6Widgets'],text=True).strip()
    compiler=Path(subprocess.check_output(['xcrun','--find','clang++'],text=True).strip())
    sdk=Path(subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip())
    binary=work/'sync-oracle';rows=[];owned=[]

    def command(label,args,cwd=None):
        began=time.monotonic()
        with (work/'private'/(label+'.stdout')).open('wb') as out,(work/'private'/(label+'.stderr')).open('wb') as err:
            p=subprocess.Popen(args,cwd=cwd or work,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            owned.append(p);timed_out=False
            try:p.wait(timeout=40)
            except subprocess.TimeoutExpired:timed_out=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        streams={}
        for stream in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+stream);public=run/(label+'.'+stream);public.write_bytes(redact(raw.read_bytes()))
            streams[stream]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(run)))
        row=dict(case=label,argv=args,pid=p.pid,seconds=time.monotonic()-began,streams=streams,
            outcome=dict(exitCode=p.returncode,timedOut=timed_out));rows.append(row)
        (run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(label,p.returncode,flush=True);assert not timed_out and p.returncode==0

    try:
        command('compile',[str(compiler),'-std=c++20','-isysroot',str(sdk),'-O0','-g0','-I',str(work),str(run/'driver.cpp'),'-o',str(binary),*flags])
        observations=[]
        cases=['move','dont-sync','missing-destination','readonly-target','readonly-source','source-gone-after-preview',
            'destination-gone-after-preview','nested','unknown-entry','metadata-file','default-alternative','only-overwrite',
            'partial-batch','source-link','destination-link']
        for label in cases:
            root=work/'cases'/label
            for p in ['source','mods/A','mods/B']:(root/p).mkdir(parents=True)
            rel='sub/café Ω.txt' if label=='nested' else 'meta.ini' if label=='metadata-file' else 'a.txt'
            source_path=root/'source'/rel;source_path.parent.mkdir(parents=True,exist_ok=True);source_path.write_bytes(b'incoming\n')
            dest=root/'mods/A'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            if label!='missing-destination':dest.write_bytes(b'old A\n')
            files=[dict(relative=rel,entryPresent=label!='unknown-entry',primary=0,
                alternatives=[] if label=='only-overwrite' else [1,2] if label=='default-alternative' else [1],
                choice=-1 if label=='dont-sync' else None if label in ['unknown-entry','metadata-file','default-alternative','only-overwrite'] else 1)]
            if label=='default-alternative':(root/'mods/B'/rel).write_bytes(b'old B\n')
            if label=='partial-batch':
                dest.unlink();(root/'source/b.txt').write_bytes(b'incoming B\n');(root/'mods/A/b.txt').write_bytes(b'old B\n')
                files.append(dict(relative='b.txt',entryPresent=True,primary=0,alternatives=[1],choice=1))
            if label in ['source-link','destination-link']:
                canary=root/'canary.txt';canary.write_bytes(b'owned canary\n')
                link=source_path if label=='source-link' else dest
                link.unlink();link.symlink_to(canary)
            if label=='readonly-target':dest.parent.chmod(0o555)
            if label=='readonly-source':source_path.parent.chmod(0o555)
            removed=['source/'+rel] if label=='source-gone-after-preview' else ['mods/A/'+rel] if label=='destination-gone-after-preview' else []
            request=dict(root=str(root),files=files,removeBeforeApply=removed)
            request_path=work/(label+'.json');request_path.write_text(json.dumps(request)+'\n')
            before=image(root)
            try:
                command(label,[str(binary),str(request_path)])
                result=json.loads((work/'private'/(label+'.stdout')).read_text())
                assert result['qt']==version and result['platformPlugin']=='offscreen'
                after=image(root)
                observations.append(dict(case=label,request=request,before=before,after=after,result=result))
                raw=work/'private/observations.json';raw.write_text(json.dumps(observations,indent=2)+'\n')
                (run/'observations.json').write_bytes(redact(raw.read_bytes()))
            finally:
                for p in [source_path.parent,dest.parent]:
                    if p.exists():p.chmod(0o755)
        receipt=dict(schema=1,sourceSha256=sha(source),sourcePath=str(source.relative_to(ROOT)),
            sourceSelection=dict(start='static void addToComboBox(',sha256=sha(work/'selected_sync.cpp'),
                firstLine=data[:start].count('\n')+1,lastLine=len(data.splitlines())+1),
            producerSha256=hashlib.sha256(PRODUCER).hexdigest(),driverSha256=sha(run/'driver.cpp'),helperSha256=sha(run/'helper.py'),
            binarySha256=sha(binary),compiler=dict(path=str(compiler),sha256=sha(compiler),version=subprocess.check_output([str(compiler),'--version'],text=True)),
            sdk=dict(path=str(sdk),settingsSha256=sha(sdk/'SDKSettings.json'),typeTraitsSha256=sha(sdk/'usr/include/c++/v1/type_traits')),
            qt=dict(pkgConfigVersion=version,modules=['Qt6Widgets','Qt6Gui','Qt6Core'],flags=flags),platform=platform.platform(),
            architecture=platform.machine(),commands=len(rows),cases=len(observations),
            rawObservationSha256=sha(work/'private/observations.json'),publicObservationSha256=sha(run/'observations.json'),
            allOwnedProcessesRetired=all(p.poll() is not None for p in owned),
            limits=['Actual unchanged sync readTree/refresh/applyTo/apply and combo helper; constructor/UI shell, origin tree and error collector are adapters.',
                'Real Qt6Widgets offscreen and QFile on macOS; not native MO2, Windows/USVFS injection, game/file-origin discovery, or full GUI acceptance.',
                'Only owned generated paths. Two explicit pre-apply removals are harness interventions, not attributed to sync.',
                'No claim of atomic replacement, full path security, process output capture, or complete mod adoption workflow.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        print('capture',run,flush=True)


if __name__=='__main__':main()
