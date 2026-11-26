"""Owned regular-file Prism install/drop method probe;no launcher,GUI,or game."""
from datetime import datetime,timezone
import hashlib,json,os,shlex,stat,subprocess,tempfile
from pathlib import Path
from accounts_probe import function
import accounts_probe

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    acquired=json.loads((ROOT/'.build/prism-content-preread/sources.json').read_text());sources={s['path']:s for s in acquired if 'error' not in s}
    old=json.loads((ROOT/'applications/sources/prism-update-selections.json').read_text());old=old if isinstance(old,list) else old['sources'];fsrow=dict(next(s for s in old if s['path']=='launcher/FileSystem.cpp'));sources[fsrow['path']]=fsrow
    selected={}
    for name in ['launcher/FileSystem.cpp','launcher/minecraft/mod/Resource.cpp','launcher/minecraft/mod/Resource.h','launcher/minecraft/mod/ResourceFolderModel.cpp']:
        p=ROOT/sources[name]['cache'];assert sha(p)==sources[name]['sha256'];selected[name]=p.read_text()
    work=Path(tempfile.mkdtemp(prefix='rules-prism-content-',dir='/private/tmp'));cap=ROOT/'applications/evidence'/('prism-content-install-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    for n in ['home','tmp','cases']:(work/n).mkdir()
    (cap/'probe.py').write_bytes(Path(__file__).read_bytes());(cap/'driver.cpp').write_bytes((HERE/'content_install_driver.cpp').read_bytes())
    excerpts=[]
    def take(path,signature,rename=False):
        body=function(selected[path],signature);compiled=body
        if rename:compiled=body.replace('ResourceFolderModel::installResource(','ResourceFolderModel::installResourceOriginal(',1)
        excerpts.append(dict(path=path,signature=signature,originalSha256=hashlib.sha256(body.encode()).hexdigest(),compiledSha256=hashlib.sha256(compiled.encode()).hexdigest(),transformation='one method-symbol rename for observational wrapper' if rename else 'none'))
        return compiled
    fsbody='\n'.join(take('launcher/FileSystem.cpp',sig)for sig in ['bool deletePath(QString path)','QString NormalizePath(QString path)','uintmax_t hardLinkCount(const QString& path)','bool updateTimestamp(const QString& filename)'])
    resource='\n'.join(take('launcher/minecraft/mod/Resource.cpp',sig)for sig in ['Resource::Resource(QFileInfo file_info)','void Resource::setFile(QFileInfo file_info)','static std::tuple<QString, qint64> calculateFileSize(const QFileInfo& file)','void Resource::parseFile()'])
    inline=take('launcher/minecraft/mod/Resource.h','bool valid() const')
    install=take('launcher/minecraft/mod/ResourceFolderModel.cpp','bool ResourceFolderModel::installResource(QString original_path)',True)
    drop=take('launcher/minecraft/mod/ResourceFolderModel.cpp','bool ResourceFolderModel::dropMimeData(const QMimeData* data, Qt::DropAction action, int, int, const QModelIndex&)')
    text=(cap/'driver.cpp').read_text()
    for marker,body in [('FS_EXCERPTS',fsbody),('RESOURCE_INLINE',inline),('RESOURCE_EXCERPTS',resource),('INSTALL_EXCERPT',install),('DROP_EXCERPT',drop)]:
        token='// @'+marker+'@';assert text.count(token)==1;text=text.replace(token,body)
    (work/'main.cpp').write_text(text)
    cases=[]
    for name in ['fresh-copy','overwrite-copy','same-path','symlink-self-overwrite','disabled-sibling','drop-mixed','drop-alias','refresh-refuses']:
        base=work/'cases'/name;incoming=base/'incoming';installed=base/'installed';incoming.mkdir(parents=True);installed.mkdir()
        src=incoming/'item.jar';dst=installed/'item.jar';observed=[str(src),str(dst),str(dst)+'.disabled',str(incoming/'missing.jar')]
        if name in ['overwrite-copy','same-path','symlink-self-overwrite','drop-alias']:dst.write_text('OLD\n')
        if name=='same-path':src=dst
        elif name in ['symlink-self-overwrite','drop-alias']:src.symlink_to(dst)
        else:src.write_text('NEW\n')
        if name=='disabled-sibling':Path(str(dst)+'.disabled').write_text('DISABLED-OLD\n')
        row=dict(id=name,operation='drop' if name.startswith('drop-') else 'install',source=str(src),destination=str(installed),observe=observed,watching=name!='refresh-refuses',updateResult=name!='refresh-refuses')
        if row['operation']=='drop':row['urls']=[src.as_uri()]+([(incoming/'missing.jar').as_uri()] if name=='drop-mixed' else [])
        cases.append(row)
    request=dict(schema=1,work=str(work),cases=cases);write(cap/'input.json',request)
    def snapshot():
        result={}
        for p in sorted((work/'cases').rglob('*')):
            s=p.lstat();info=dict(mode=s.st_mode&0o777,mtimeNs=s.st_mtime_ns)
            if stat.S_ISLNK(s.st_mode):info.update(kind='symlink',target=os.readlink(p),targetExists=p.exists())
            elif stat.S_ISREG(s.st_mode):info.update(kind='file',bytes=s.st_size,sha256=sha(p),text=p.read_text())
            elif stat.S_ISDIR(s.st_mode):info.update(kind='directory')
            else:raise RuntimeError('Unadmitted fixture entry')
            result[str(p.relative_to(work/'cases'))]=info
        return result
    write(cap/'before.json',snapshot());commands=[]
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
    def command(label,argv,timeout):
        out=cap/(label+'.stdout');err=cap/(label+'.stderr')
        with out.open('xb') as stdout,err.open('xb') as stderr:
            child=subprocess.Popen(argv,cwd=work,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(cap/'current-process.json',dict(label=label,pid=child.pid,status='running',argv=argv))
            try:code=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                write(cap/'current-process.json',dict(label=label,pid=child.pid,status='observation-timeout;not-declared-terminal',argv=argv));raise RuntimeError('Preserve and reconcile the same PID;do not restart.')
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        commands.append(dict(label=label,argv=argv,pid=child.pid,exitCode=code,groupAbsent=absent,stdout=dict(path=out.name,sha256=sha(out)),stderr=dict(path=err.name,sha256=sha(err))));write(cap/'commands.json',commands);write(cap/'current-process.json',dict(label=label,pid=child.pid,status='terminal',exitCode=code,groupAbsent=absent));assert absent and code==0,(label,code)
    pkg='/opt/homebrew/bin/pkg-config';flags=shlex.split(subprocess.check_output([pkg,'--cflags','--libs','Qt6Core'],text=True));lib=Path(subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip())
    setup=dict(schema=1,work=str(work),sourceRevision='7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4',producerSha256=sha(cap/'probe.py'),driverTemplateSha256=sha(cap/'driver.cpp'),extractorSha256=sha(Path(accounts_probe.__file__)),generatedSha256=sha(work/'main.cpp'),excerpts=excerpts,sources=[sources[k] for k in selected],compiler=subprocess.check_output(['/usr/bin/clang++','--version'],text=True),qtVersion=subprocess.check_output([pkg,'--modversion','Qt6Core'],text=True).strip(),qtCoreSha256=sha(lib/'QtCore.framework/Versions/A/QtCore'),environment=env,limits=['Original selected methods with one install-symbol rename for a result wrapper. Context class omits QObject reflection/lifetime and model-view/controller behavior.','ASCII path/display-size adapters;folder-copy branch throws if reached;watcher refresh callback is explicitly controlled.','Real QtCore file IO in owned fixtures;no installed launcher,bundled Qt,GUI,game,provider,network,metadata-index,or full filesystem qualification.','No production fix or candidate variant included. Source GPL/Apache notices remain in upstream files;private generated excerpts are not staged as project-owned source.'])
    write(cap/'setup.json',setup)
    print(json.dumps(dict(capture=str(cap),work=str(work))),flush=True)
    command('compile',['/usr/bin/clang++','-std=c++20','-O0','-DQT_NO_DEBUG',str(work/'main.cpp'),'-o',str(work/'probe'),*flags,'-Wl,-rpath,'+str(lib)],90)
    binary=sha(work/'probe');command('observe',[str(work/'probe'),str(cap/'input.json')],20)
    rows=[json.loads(line) for line in(cap/'observe.stdout').read_text().splitlines()];assert len(rows)==8 and [r['id']for r in rows]==[c['id']for c in cases];assert all(r['unsupportedFolderCopies']==0 for r in rows);assert sha(work/'probe')==binary
    write(cap/'after.json',snapshot());write(cap/'receipt.json',dict(schema=1,binarySha256=binary,generatedSourceSha256=sha(work/'main.cpp'),cases=8,allGroupsAbsent=all(c['groupAbsent']for c in commands),scope='Selected original methods plus declared adapters. Not the full launcher or a product-wide result.'))
    print(json.dumps(dict(capture=str(cap),cases=8,allGroupsAbsent=True)),flush=True)


if __name__=='__main__':main()
