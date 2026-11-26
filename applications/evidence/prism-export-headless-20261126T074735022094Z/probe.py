"""Original Prism collector/writer bodies with controlled caller context; no GUI."""
from datetime import datetime,timezone
import hashlib,json,os,shlex,signal,stat,subprocess,sys,tempfile,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'applications/prism'))
from accounts_probe import function
import accounts_probe
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    ledger=json.loads((ROOT/'applications/sources/prism-export-selections.json').read_text());sources={r['path']:r for r in ledger['sources']}
    selected={}
    for path in ['launcher/MMCZip.cpp','launcher/archive/ArchiveWriter.cpp','launcher/archive/ExportToZipTask.cpp']:
        row=sources[path];p=ROOT/row['cache'];assert sha(p)==row['sha256'];selected[path]=p.read_text()
    run=ROOT/'applications/evidence'/('prism-export-headless-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-prism-export-core-',dir='/private/tmp'));(work/'tmp').mkdir();(work/'cases').mkdir()
    (run/'probe.py').write_bytes(Path(__file__).read_bytes());(run/'driver.cpp').write_bytes((Path(__file__).parent/'headless_driver.cpp').read_bytes())
    excerpts=[]
    def take(path,signature,rename=False):
        original=function(selected[path],signature);body=original.replace('ExportToZipTask::exportZip','ExportHarness::exportZip',1)if rename else original
        excerpts.append(dict(path=path,signature=signature,originalSha256=hashlib.sha256(original.encode()).hexdigest(),compiledSha256=hashlib.sha256(body.encode()).hexdigest(),transformation='one class qualifier rename'if rename else'none'));return body
    writer='\n'.join(take('launcher/archive/ArchiveWriter.cpp',s)for s in ['ArchiveWriter::ArchiveWriter(const QString& archiveName)','ArchiveWriter::~ArchiveWriter()','bool ArchiveWriter::open()','bool ArchiveWriter::close()','bool ArchiveWriter::addFile(const QString& fileName, const QString& fileDest)','bool ArchiveWriter::addFile(const QString& fileDest, const QByteArray& data)'])
    collector=take('launcher/MMCZip.cpp','bool collectFileListRecursively(const QString& rootDir, const QString& subDir, QFileInfoList* files, FilterFileFunction excludeFilter)')
    export=take('launcher/archive/ExportToZipTask.cpp','auto ExportToZipTask::exportZip() -> ZipResult',True)
    text=(run/'driver.cpp').read_text()
    for marker,body in [('WRITER',writer),('COLLECTOR',collector),('EXPORT',export)]:
        token='// @'+marker+'@';assert text.count(token)==1;text=text.replace(token,body)
    (work/'main.cpp').write_text(text)
    cases=[]
    for name in ['instance-follow','game-retain-link','game-filter-prefix','missing-root','vanished-input','canceled-witness','directory-output','empty-selection']:
        base=work/'cases'/name;instance=base/'instance';game=instance/'.minecraft';game.mkdir(parents=True);(base/'external').mkdir();(base/'external/linked.txt').write_text('Own outside-instance bytes.\n')
        files={'instance.cfg':'Generated instance metadata.\n','.hidden-root':'Hidden root bytes.\n','.minecraft/config/visible.txt':'Visible Ω 日本.\n','.minecraft/config/.hidden-file':'Hidden bytes.\n','.minecraft/config/.hidden-dir/inside.txt':'Ordinary bytes in hidden directory.\n','.minecraft/logs/latest.log':'Generated log.\n','.minecraft/saves/world/README.txt':'Generated world-like bytes.\n'}
        for path,body in files.items():p=instance/path;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(body)
        (game/'config/linked.txt').symlink_to(base/'external/linked.txt')
        root=instance if name=='instance-follow'else game;output=base/'output.zip';output.write_bytes(b'PREVIOUS OUTPUT\n')
        row=dict(id=name,root=str(root),output=str(output),prefix='overrides/'if name=='game-filter-prefix'else'',follow=name!='game-retain-link',filter=name in ['game-filter-prefix','empty-selection'],excludeAtCollect=['config/visible.txt']if name=='game-filter-prefix'else[],excludeAtWrite=[],canceled=name=='canceled-witness',extra={'metadata.json':'Generated metadata\n'}if name=='game-filter-prefix'else{})
        if name=='missing-root':row['root']=str(base/'missing')
        if name=='vanished-input':row['removeAfterCollect']='config/visible.txt'
        if name=='directory-output':output.unlink();output.mkdir()
        if name=='empty-selection':row['excludeAtCollect']=['config/visible.txt','config/linked.txt','config/.hidden-dir/inside.txt','logs/latest.log','saves/world/README.txt']
        cases.append(row)
    write(run/'input.json',dict(schema=1,cases=cases));commands=[]
    def snapshot():
        result={}
        for p in sorted((work/'cases').rglob('*')):
            s=p.lstat();v=dict(mode=stat.S_IMODE(s.st_mode))
            if stat.S_ISLNK(s.st_mode):v.update(kind='link',target=os.readlink(p))
            elif stat.S_ISDIR(s.st_mode):v.update(kind='directory')
            else:v.update(kind='file',bytes=s.st_size,sha256=sha(p))
            result[p.relative_to(work/'cases').as_posix()]=v
        return result
    write(run/'before.json',snapshot());env=dict(os.environ,LANG='en_US.UTF-8',LC_ALL='en_US.UTF-8',TMPDIR=str(work/'tmp'))
    def command(label,argv,timeout):
        with(run/(label+'.stdout')).open('wb')as out,(run/(label+'.stderr')).open('wb')as err:
            p=subprocess.Popen(argv,cwd=work,env=env,stdout=out,stderr=err,start_new_session=True);write(run/'current-process.json',dict(pid=p.pid,label=label,status='running',argv=argv));timedout=False
            try:code=p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timedout=True;os.killpg(p.pid,signal.SIGTERM)
                try:code=p.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=10)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        commands.append(dict(label=label,argv=argv,pid=p.pid,exitCode=code,timedOut=timedout,groupAbsent=absent,stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr'))));write(run/'commands.json',commands);write(run/'current-process.json',dict(pid=p.pid,label=label,status='terminal',exitCode=code,groupAbsent=absent));assert not timedout and code==0 and absent
    pkg='/opt/homebrew/bin/pkg-config';flags=shlex.split(subprocess.check_output([pkg,'--cflags','--libs','Qt6Core'],text=True));lib=Path(subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip());compiler=Path(subprocess.check_output(['/usr/bin/xcrun','--find','clang++'],text=True).strip());sdk=Path(subprocess.check_output(['/usr/bin/xcrun','--show-sdk-path'],text=True).strip())
    write(run/'setup.json',dict(work=str(work),sourceRevision=ledger['revision'],producerSha256=sha(run/'probe.py'),templateSha256=sha(run/'driver.cpp'),extractorSha256=sha(Path(accounts_probe.__file__)),generatedSourceSha256=sha(work/'main.cpp'),compiler=dict(path=str(compiler),sha256=sha(compiler),version=subprocess.check_output([str(compiler),'--version'],text=True)),sdk=dict(path=str(sdk),settingsSha256=sha(sdk/'SDKSettings.json')),qtVersion=subprocess.check_output([pkg,'--modversion','Qt6Core'],text=True).strip(),qtCoreSha256=sha(lib/'QtCore.framework/Versions/A/QtCore'),excerpts=excerpts,sourceIdentities=[sources[k]for k in selected],limits=['Original selected bodies;only export class qualifier renamed. Interface context omits unused ArchiveReader methods.','Collector callback is controlled exact-file exclusion,not FileIgnoreProxy/GUI conformance. Future cancellation is supplied Boolean witness;no QFuture,threads,Task::finish/abort/signals or actual termination claim.','Real QtCore6.12 and system libarchive;not installed Prism bundledQt6.9.3 or product export.','No GUI,game,account,network,personal profile or HOME override. All source/binary/private fixtures retained.']))
    command('compile',[str(compiler),'-std=c++20','-O0',str(work/'main.cpp'),'-o',str(work/'probe'),*flags,'-larchive','-Wl,-rpath,'+str(lib)],90)
    binary=sha(work/'probe');command('observe',[str(work/'probe'),str(run/'input.json')],30);assert sha(work/'probe')==binary
    write(run/'after.json',snapshot());rows=[json.loads(line)for line in(run/'observe.stdout').read_text().splitlines()];assert rows[0]['kind']=='backend'and len(rows)==len(cases)+1
    artifacts=[];(run/'outputs').mkdir()
    for row in cases:
        p=Path(row['output']);item=dict(id=row['id'],exists=p.exists(),isFile=p.is_file())
        if p.is_file():
            target=run/'outputs'/(row['id']+'.zip');target.write_bytes(p.read_bytes());item.update(sha256=sha(p),bytes=p.stat().st_size)
            try:
                with zipfile.ZipFile(p)as z:
                    item['members']=[dict(name=i.filename,mode=i.external_attr>>16,bytes=i.file_size,sha256=hashlib.sha256(z.read(i)).hexdigest())for i in z.infolist()]
            except zipfile.BadZipFile:item['notZip']=True
        artifacts.append(item)
    write(run/'artifacts.json',artifacts);write(run/'receipt.json',dict(schema=1,cases=len(cases),sourceComponentOnly=True,binarySha256=binary,generatedSourceSha256=sha(work/'main.cpp'),allGroupsAbsent=all(c['groupAbsent']for c in commands),backend=rows[0],work=str(work)))
    print(json.dumps(dict(capture=str(run),cases=len(cases),backend=rows[0],allGroupsAbsent=True)))


if __name__=='__main__':main()
