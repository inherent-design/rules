#!/usr/bin/env python3
"""Execute pinned MO2 activation bodies with explicit fixture adapters, not MO2."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    selections = json.loads((ROOT / 'applications/sources/launcher-selections.json').read_text())
    row = next(r for r in selections if r['application'] == 'mo2' and r['path'] == 'src/profile.cpp')
    source = (ROOT / row['cache']).read_bytes()
    assert sha(source) == row['sha256']
    text = source.decode()
    start, middle, end = [text.index(s) for s in ['void Profile::setModEnabled(', 'void Profile::setModsEnabled(', 'bool Profile::modEnabled(']]
    single, batch = text[start:middle], text[middle:end]
    cases = []
    for policy, old, request in itertools.product(['free', 'on', 'off'], [False, True], [False, True]):
        cases.append(dict(id=f'single-{policy}-{int(old)}-{int(request)}', mode='single', policies=[policy], before=[old], target=0, request=request))
    cases.append(dict(id='single-invalid-index', mode='single', policies=['free'], before=[False], target=9, request=True))
    def add(identity, enabled, disabled, policies=None, before=None):
        cases.append(dict(id=identity, mode='batch', policies=policies or ['free','on','off'],
            before=[False,True,False] if before is None else before, enable=enabled, disable=disabled))
    add('batch-empty', [], [])
    add('batch-enable-free', [0], [])
    add('batch-disable-free', [], [0], before=[True,True,False])
    add('batch-enable-all', [0,1,2], [])
    add('batch-disable-all', [], [0,1,2])
    add('batch-duplicate-enable', [0,0], [])
    add('batch-overlapping-requests', [0], [0])
    add('batch-invalid-then-valid', [9,0], [])
    add('batch-ordered-changes', [1,0], [], ['free','free','on','off'], [False,False,True,False])
    add('batch-invalid-on-prestate', [], [0], ['on'], [False])
    add('batch-invalid-off-prestate', [0], [], ['off'], [True])
    body = r'''#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#define emit
int loggedErrors=0;
namespace fixtureLog { template<class... T> void error(const char*,T...) {++loggedErrors;} }
namespace log=fixtureLog;
struct Message { std::string text; Message arg(unsigned) const {return *this;} };
Message tr(const char* text) {return {text};}
struct MyException:std::runtime_error {MyException(Message m):std::runtime_error(m.text){}};
template<class T> struct QList:std::vector<T> {using std::vector<T>::vector; void append(T t){this->push_back(t);} bool isEmpty()const{return this->empty();}};
struct ModInfo {
  using Ptr=std::shared_ptr<ModInfo>;
  bool on,off;
  bool alwaysEnabled()const{return on;} bool alwaysDisabled()const{return off;}
  static std::vector<Ptr> catalog;
  static Ptr getByIndex(unsigned i){return catalog.at(i);}
};
std::vector<ModInfo::Ptr> ModInfo::catalog;
struct Status { bool m_Enabled; };
struct Profile {
  std::vector<Status> m_ModStatus;
  std::vector<std::vector<unsigned>> notifications;
  void setModEnabled(unsigned,bool);
  void setModsEnabled(const QList<unsigned>&,const QList<unsigned>&);
  void modStatusChanged(unsigned i){notifications.push_back({i});}
  void modStatusChanged(QList<unsigned> ids){notifications.push_back(ids);}
};
SINGLE_BODY
BATCH_BODY
void state(const Profile& p) {std::cout<<"[";bool first=true;for(auto s:p.m_ModStatus){if(!first)std::cout<<",";first=false;std::cout<<(s.m_Enabled?"true":"false");}std::cout<<"]";}
void run(const char* id, Profile p, bool batch, unsigned target, bool request, QList<unsigned> enable, QList<unsigned> disable) {
  Profile independent=p;loggedErrors=0;bool threw=false;
  try {if(batch)p.setModsEnabled(enable,disable);else p.setModEnabled(target,request);}catch(const MyException&){threw=true;}
  std::cout<<"{\"id\":\""<<id<<"\",\"state\":";state(p);std::cout<<",\"independent\":";state(independent);
  std::cout<<",\"signals\":[";bool first=true;for(auto ids:p.notifications){if(!first)std::cout<<",";first=false;std::cout<<"[";bool a=true;for(auto i:ids){if(!a)std::cout<<",";a=false;std::cout<<i;}std::cout<<"]";}
  std::cout<<"],\"loggedErrors\":"<<loggedErrors<<",\"threw\":"<<(threw?"true":"false")<<",\"catalogFlags\":[";
  first=true;for(auto m:ModInfo::catalog){if(!first)std::cout<<",";first=false;std::cout<<"["<<(m->on?"true":"false")<<","<<(m->off?"true":"false")<<"]";}std::cout<<"]}"<<std::endl;
}
int main(){
CASES
}
'''.replace('SINGLE_BODY',single).replace('BATCH_BODY',batch)
    calls=[]
    bit=lambda b:'true' if b else 'false'
    for c in cases:
        flags=[('true','false') if p=='on' else ('false','true') if p=='off' else ('false','false') for p in c['policies']]
        catalog=','.join('std::make_shared<ModInfo>(ModInfo{'+a+','+b+'})' for a,b in flags)
        statuses=','.join('{'+bit(b)+'}' for b in c['before'])
        ids=lambda name:','.join(str(i) for i in c.get(name,[]))
        calls.append('ModInfo::catalog={'+catalog+'};run("'+c['id']+'",Profile{{'+statuses+'},{}},'+bit(c['mode']=='batch')+','+str(c.get('target',0))+','+bit(c.get('request',False))+',{'+ids('enable')+'},{'+ids('disable')+'});')
    cpp=body.replace('CASES','\n'.join(calls))
    run=ROOT/'applications/evidence'/('mo2-profile-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work';(work/'home').mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER);(run/'input.json').write_text(json.dumps({'schema':1,'cases':cases},indent=2)+'\n')
    (work/'probe.cpp').write_text(cpp)
    env={'PATH':'/usr/bin:/bin','HOME':str(work/'home'),'LANG':'en_US.UTF-8'}
    argv=['/usr/bin/clang++','-std=c++20','-O0',str(work/'probe.cpp'),'-o',str(work/'probe')]
    compiled=subprocess.run(argv,env=env,capture_output=True,timeout=60)
    (run/'compile.stdout').write_bytes(compiled.stdout);(run/'compile.stderr').write_bytes(compiled.stderr)
    assert compiled.returncode==0,compiled.stderr.decode(errors='replace')
    executed=subprocess.run([str(work/'probe')],env=env,capture_output=True,timeout=10)
    (run/'observed.stdout').write_bytes(executed.stdout);(run/'observed.stderr').write_bytes(executed.stderr)
    assert executed.returncode==0
    observed=[json.loads(line) for line in executed.stdout.splitlines()]
    assert len(observed)==len(cases)
    receipt={'schema':1,'kind':'Executed unmodified source method bodies with fixture adapters; not MO2 or Qt execution',
        'producerSha256':sha(PRODUCER),'source':row,'sourceUnchanged':sha((ROOT/row['cache']).read_bytes())==row['sha256'],
        'singleBodySha256':sha(single.encode()),'batchBodySha256':sha(batch.encode()),'generatedCppSha256':sha(cpp.encode()),
        'inputSha256':sha((run/'input.json').read_bytes()),'stdoutSha256':sha(executed.stdout),'stderrSha256':sha(executed.stderr),
        'compileCommand':argv,'compileExit':compiled.returncode,'executeExit':executed.returncode,'cases':len(cases),
        'compiler':subprocess.check_output(['/usr/bin/clang++','--version'],text=True),'platform':platform.platform(),
        'limits':['QList, logging, translation, ModInfo metadata, signal delivery and Profile construction are explicit fixture adapters.',
            'No profile parsing/writing, QObject event delivery, complete refresh, effective VFS, Windows application, or game execution.',
            'Inconsistent forced-policy prestates are constructed controls, not evidence that normal MO2 loading produces them.']}
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'run':str(run),'cases':len(cases),'compiler':receipt['compiler'].splitlines()[0]},indent=2))


if __name__=='__main__':main()
