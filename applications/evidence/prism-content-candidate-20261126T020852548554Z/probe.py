"""Compare private alias-refusal/staged-copy proposals;no launcher or GUI."""
from datetime import datetime,timezone
import hashlib,json,os,stat,subprocess,tempfile
from pathlib import Path
from accounts_probe import function
import accounts_probe

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'applications/evidence/prism-content-install-20261126T015852314941Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')

GUARD='''    const auto source_identity = file_info.canonicalFilePath();
    const auto destination_identity = QFileInfo(new_path).canonicalFilePath();
    if (!source_identity.isEmpty() && source_identity == destination_identity)
        return false;
'''
STAGED='''            QFile source(original_path);
            if (!source.open(QIODevice::ReadOnly))
                return false;
            QSaveFile staged(new_path);
            staged.setDirectWriteFallback(false);
            if (!staged.open(QIODevice::WriteOnly))
                return false;
            while (!source.atEnd()) {
                const auto chunk = source.read(65536);
                if ((chunk.isEmpty() && source.error() != QFileDevice::NoError)
                    || staged.write(chunk) != chunk.size())
                    return false;
            }
            if (source.error() != QFileDevice::NoError)
                return false;
            source.close();
            if (fixtureCancelBeforeCommit)
                return false;
            if (!staged.commit())
                return false;

'''


def main():
    setup=json.loads((BASE/'setup.json').read_text());original=Path(setup['work'])/'main.cpp';assert sha(original)==setup['generatedSha256']
    for p,h in json.loads((BASE/'collection-basis.json').read_text()).items():assert sha(BASE/p)==h
    template=original.read_text();body=function(template,'bool ResourceFolderModel::installResourceOriginal(QString original_path)')
    anchor='    if (original_path == new_path) {';assert body.count(anchor)==1
    guarded=body.replace('ResourceFolderModel::installResourceOriginal(','ResourceFolderModel::installResourceGuarded(',1).replace(anchor,GUARD+anchor,1)
    first=body.index('            if (QFile::exists(new_path) || QFile::exists(new_path + QString(".disabled"))) {')
    last=body.index('            FS::updateTimestamp(new_path);',first)
    staged=body[:first]+STAGED+body[last:];staged=staged.replace('ResourceFolderModel::installResourceOriginal(','ResourceFolderModel::installResourceStaged(',1)
    wrapper='bool result=installResourceOriginal(path);';assert template.count(wrapper)==1
    template=template.replace(wrapper,'bool result; if(policy=="guarded")result=installResourceGuarded(path);else if(policy=="staged")result=installResourceStaged(path);else throw std::runtime_error("Unknown proposal");',1)
    template=template.replace('  bool installResourceOriginal(QString);','  bool installResourceGuarded(QString);\n  bool installResourceStaged(QString);\n  QString policy;',1)
    template=template.replace(body,guarded+'\n'+staged,1).replace('#include <QFile>','#include <QFile>\n#include <QSaveFile>',1)
    template=template.replace('namespace fs=std::filesystem;','namespace fs=std::filesystem;\nstatic bool fixtureCancelBeforeCommit=false;',1)
    token='    auto row=item.toObject();ResourceFolderModel model';assert template.count(token)==1
    template=template.replace(token,'    auto row=item.toObject();fixtureCancelBeforeCommit=row["cancelBeforeCommit"].toBool(false);ResourceFolderModel model',1)
    token='    auto before=snapshot(row);';assert template.count(token)==1;template=template.replace(token,'    model.policy=row["policy"].toString();\n'+token,1)
    work=Path(tempfile.mkdtemp(prefix='rules-prism-content-candidate-',dir='/private/tmp'));cap=ROOT/'applications/evidence'/('prism-content-candidate-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    for n in ['home','tmp','cases']:(work/n).mkdir()
    (work/'main.cpp').write_text(template);(cap/'probe.py').write_bytes(Path(__file__).read_bytes())
    original_cases={r['id']:r for r in json.loads((BASE/'input.json').read_text())['cases']}
    cases=[]
    for policy in ['guarded','staged']:
        names=['fresh-copy','overwrite-copy','same-path','symlink-self-overwrite','drop-alias','equal-bytes-distinct-files']
        if policy=='staged':names+=['cancel-before-publish']
        for name in names:
            baseid=name if name in original_cases else 'overwrite-copy';old=original_cases[baseid];base=work/'cases'/(policy+'--'+name);incoming=base/'incoming';installed=base/'installed';incoming.mkdir(parents=True);installed.mkdir()
            row=json.loads(json.dumps(old).replace(setup['work']+'/cases/'+baseid,str(base)))
            row.update(id=policy+':'+name,baseId=name,policy=policy,cancelBeforeCommit=name=='cancel-before-publish')
            src=Path(row['source']);dst=installed/'item.jar'
            if name not in ['fresh-copy']:dst.write_text('NEW\n' if name=='equal-bytes-distinct-files' else 'OLD\n')
            if name in ['symlink-self-overwrite','drop-alias']:src.symlink_to(dst)
            elif name!='same-path':src.write_text('NEW\n')
            cases.append(row)
    write(cap/'input.json',dict(schema=1,work=str(work),cases=cases))
    def snapshot():
        result={}
        for p in sorted((work/'cases').rglob('*')):
            s=p.lstat();v=dict(mode=s.st_mode&0o777,mtimeNs=s.st_mtime_ns)
            if stat.S_ISLNK(s.st_mode):v.update(kind='symlink',target=os.readlink(p),targetExists=p.exists())
            elif stat.S_ISREG(s.st_mode):v.update(kind='file',bytes=s.st_size,sha256=sha(p),text=p.read_text())
            elif stat.S_ISDIR(s.st_mode):v.update(kind='directory')
            else:raise RuntimeError('Unadmitted entry')
            result[str(p.relative_to(work/'cases'))]=v
        return result
    write(cap/'before.json',snapshot());commands=[];env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
    def command(label,argv,timeout):
        out=cap/(label+'.stdout');err=cap/(label+'.stderr')
        with out.open('xb') as stdout,err.open('xb') as stderr:
            child=subprocess.Popen(argv,cwd=work,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(cap/'current-process.json',dict(label=label,pid=child.pid,status='running',argv=argv))
            try:code=child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                write(cap/'current-process.json',dict(label=label,pid=child.pid,status='observation-timeout;not-terminal',argv=argv));raise RuntimeError('Reconcile this PID;do not restart from timeout.')
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        commands.append(dict(label=label,argv=argv,pid=child.pid,exitCode=code,groupAbsent=absent,stdout=dict(path=out.name,sha256=sha(out)),stderr=dict(path=err.name,sha256=sha(err))));write(cap/'commands.json',commands);write(cap/'current-process.json',dict(label=label,pid=child.pid,status='terminal',exitCode=code,groupAbsent=absent));assert absent and code==0,(label,code)
    compile_cmd=json.loads((BASE/'commands.json').read_text())[0]['argv'];compile_cmd=[a.replace(setup['work'],str(work)) for a in compile_cmd]
    pkg='/opt/homebrew/bin/pkg-config';lib=Path(subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip());assert sha(lib/'QtCore.framework/Versions/A/QtCore')==setup['qtCoreSha256']
    assert subprocess.check_output(['/usr/bin/clang++','--version'],text=True)==setup['compiler']
    record=dict(schema=1,base=str(BASE.relative_to(ROOT)),baseGeneratedSha256=setup['generatedSha256'],baseMethodSha256=hashlib.sha256(body.encode()).hexdigest(),replacedCopyBlockSha256=hashlib.sha256(body[first:last].encode()).hexdigest(),guardedMethodSha256=hashlib.sha256(guarded.encode()).hexdigest(),stagedMethodSha256=hashlib.sha256(staged.encode()).hexdigest(),generatedSha256=sha(work/'main.cpp'),producerSha256=sha(cap/'probe.py'),extractorSha256=sha(Path(accounts_probe.__file__)),work=str(work),qtVersion=setup['qtVersion'],qtCoreSha256=setup['qtCoreSha256'],compiler=setup['compiler'],guard=GUARD,stagedBlock=STAGED,scope='Two private proposals,not production patches. Canonical guard rejects known aliases;staged copy captures chunks before QSaveFile commit with direct-write fallback disabled. Cancellation is an authored precommit hook. No crash,durability,concurrency,all-alias,full-launcher,bundled-Qt or platform qualification.')
    write(cap/'setup.json',record);print(json.dumps(dict(capture=str(cap),work=str(work))),flush=True)
    command('compile',compile_cmd,90);binary=sha(work/'probe');command('observe',[str(work/'probe'),str(cap/'input.json')],20)
    rows=[json.loads(l)for l in(cap/'observe.stdout').read_text().splitlines()];assert len(rows)==13 and [r['id']for r in rows]==[r['id']for r in cases];assert all(r['unsupportedFolderCopies']==0 for r in rows) and sha(work/'probe')==binary
    write(cap/'after.json',snapshot());write(cap/'receipt.json',dict(schema=1,cases=13,binarySha256=binary,allGroupsAbsent=all(c['groupAbsent']for c in commands),generatedSha256=sha(work/'main.cpp')));print(json.dumps(dict(capture=str(cap),cases=13,allGroupsAbsent=True)),flush=True)


if __name__=='__main__':main()
