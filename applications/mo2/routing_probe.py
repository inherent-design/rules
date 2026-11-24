#!/usr/bin/env python3
"""Owner-run mapping source fragment; no USVFS, process launch, or mapped writes."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'applications/restic'))
from locks_probe import redact
PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=ROOT/'applications/tools/source-cache/launchers/mo2__src__organizercore.cpp';data=source.read_text()
    start='std::vector<Mapping> OrganizerCore::fileMapping(const QString& profileName,'
    stop='std::vector<Mapping> OrganizerCore::fileMapping(const QString& dataPath,'
    assert data.count(start)==data.count(stop)==1
    selected=data[data.index(start):data.index(stop)]
    run=ROOT/'applications/evidence'/('mo2-routing-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for n in ['home','tmp','cache','runtime','private']:(work/n).mkdir(parents=True)
    (work/'runtime').chmod(0o700)
    (run/'probe.py').write_bytes(PRODUCER);(run/'driver.cpp').write_bytes((HERE/'routing_driver.cpp').read_bytes());(run/'helper.py').write_bytes((ROOT/'applications/restic/locks_probe.py').read_bytes())
    (work/'selected_mapping.cpp').write_text(selected)
    active=[dict(name='overwrite',regular=False,priority=99),dict(name='A',regular=True,priority=1),dict(name='B',regular=False,priority=2)]
    cases=[]
    def row(name,**values):
        r=dict(case=name,active=active,dataPaths=1,custom='',profile='A',currentProfile='A',localByProfile={'A':False,'B':False},localFeature=True,plugin=False,pluginEnabled=False)
        r.update(values);cases.append(r)
    for count in [1,2]:
        for title,custom in [('default',''),('regular','A'),('inactive','missing'),('case-sensitive','a'),('nonregular','B'),('reserved','overwrite')]:
            row(title+'-'+str(count),dataPaths=count,custom=custom)
    row('empty-active',active=[])
    row('local-same-profile',localByProfile={'A':True,'B':False})
    row('local-different-profile-current-enabled',profile='B',localByProfile={'A':True,'B':False})
    row('local-different-profile-selected-enabled',profile='B',localByProfile={'A':False,'B':True})
    row('local-feature-absent',localFeature=False,localByProfile={'A':True,'B':False})
    row('plugin-enabled',plugin=True,pluginEnabled=True)
    row('plugin-disabled',plugin=True,pluginEnabled=False)
    (run/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    compiler=Path(subprocess.check_output(['xcrun','--find','clang++'],text=True).strip());sdk=Path(subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip())
    flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','Qt6Widgets'],text=True));qt=subprocess.check_output(['pkg-config','--modversion','Qt6Widgets'],text=True).strip()
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),XDG_CACHE_HOME=str(work/'cache'),XDG_RUNTIME_DIR=str(work/'runtime'),QT_QPA_PLATFORM='offscreen',LANG='en_US.UTF-8')
    commands=[];owned=[];binary=work/'routing-oracle'
    def command(label,args):
        begin=time.monotonic()
        with (work/'private'/(label+'.stdout')).open('wb') as out,(work/'private'/(label+'.stderr')).open('wb') as err:
            p=subprocess.Popen(args,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(p);timed_out=False
            try:p.wait(timeout=40)
            except subprocess.TimeoutExpired:timed_out=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        streams={}
        for stream in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+stream);public=run/(label+'.'+stream);public.write_bytes(redact(raw.read_bytes()));streams[stream]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(run)))
        commands.append(dict(case=label,argv=args,pid=p.pid,seconds=time.monotonic()-begin,streams=streams,outcome=dict(exitCode=p.returncode,timedOut=timed_out)))
        (run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(label,p.returncode,flush=True);assert not timed_out and p.returncode==0
    try:
        command('compile',[str(compiler),'-std=c++20','-isysroot',str(sdk),'-O0','-g0','-I',str(work),str(run/'driver.cpp'),'-o',str(binary),*flags])
        command('observe',[str(binary),str(run/'cases.json')])
        rows=[json.loads(line) for line in (run/'observe.stdout').read_text().splitlines()]
        assert len(rows)==len(cases)==19
        assert all(row['qt']==qt and row['platformPlugin']=='offscreen' for row in rows)
        receipt=dict(schema=1,sourcePath=str(source.relative_to(ROOT)),sourceSha256=sha(source),sourceSelection=dict(start=start,stop=stop,sha256=sha(work/'selected_mapping.cpp')),
            producerSha256=hashlib.sha256(PRODUCER).hexdigest(),driverSha256=sha(run/'driver.cpp'),helperSha256=sha(run/'helper.py'),casesSha256=sha(run/'cases.json'),observedSha256=sha(run/'observe.stdout'),
            binarySha256=sha(binary),compiler=dict(path=str(compiler),sha256=sha(compiler),version=subprocess.check_output([str(compiler),'--version'],text=True)),sdk=dict(path=str(sdk),settingsSha256=sha(sdk/'SDKSettings.json')),
            qt=dict(pkgConfigVersion=qt,flags=flags),platform=platform.platform(),architecture=platform.machine(),records=len(rows),allOwnedProcessesRetired=all(p.poll() is not None for p in owned),
            limits=['Unchanged fileMapping method with actual Qt strings/paths and controlled game/profile/mod/plugin/local-save adapters. No real profile parser, directory refresh, or game plugin.',
                'Ready wait is held false; fake connect refuses execution. No USVFS mapping installation, tool/game process, or physical mapped read/write.',
                'Nonregular custom target and differing selected/current profile are explicit API-boundary inputs; normal caller reachability and Windows product outcomes are not established.',
                'Mapping list order/flags are observations, not proof of effective-file precedence, new/existing write behavior or complete process isolation.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        print('capture',run,flush=True)


if __name__=='__main__':main()
