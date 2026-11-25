#!/usr/bin/env python3
"""Synthetic Qt account/session method chains; no accounts store,GUI or auth IO."""
from datetime import datetime,timezone
import hashlib,json,os,re,shlex,signal,subprocess,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def function(text,signature):
    assert text.count(signature)==1,signature
    start=text.index(signature)
    # Preserve offsets while excluding comments/quoted braces from matching.
    mask=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),text,flags=re.S)
    first=mask.index('{',start);depth=0
    for end in range(first,len(mask)):
        if mask[end]=='{':depth+=1
        if mask[end]=='}':
            depth-=1
            if depth==0:return text[start:end+1]
    raise AssertionError(signature)


def actor(id='B',name='Alex',profile='2'*32,type=0,owns=True,validity=2,**kw):
    return dict(id=id,name=name,profileId=profile,type=type,owns=owns,validity=validity,state=3,tokenPresent=True,
                hasIssue=True,issuedAgo=0,hasExpiry=True,expiresIn=21600,**kw)


def main():
    ledger=json.loads((ROOT/'applications/sources/prism-accounts-selections.json').read_text());selected={}
    for s in ledger['sources']:
        p=ROOT/s['cache'];assert sha(p)==s['sha256'];selected[s['path']]=p.read_text()
    run=ROOT/'applications/evidence'/('prism-accounts-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for d in ['home','tmp']:(work/d).mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER)
    copied={}
    for path in ['launcher/minecraft/auth/AccountData.h','launcher/minecraft/auth/AuthSession.h','launcher/minecraft/auth/AuthSession.cpp','launcher/LaunchMode.h','launcher/Usable.h']:
        target=work/Path(path).name;target.write_text(selected[path]);copied[path]=sha(target)
    (work/'QObjectPtr.h').write_text('#pragma once\n// Fixture include shim only: retained actors use std::shared_ptr;no QObject lifetime claim.\n')
    excerpts=[]
    def take(path,signature,clock=False):
        original=function(selected[path],signature);adapted=original
        if clock:
            assert original.count('QDateTime::currentDateTimeUtc()')==1
            adapted=original.replace('QDateTime::currentDateTimeUtc()','fixtureNow()')
        excerpts.append(dict(path=path,signature=signature,originalSha256=hashlib.sha256(original.encode()).hexdigest(),adaptedSha256=hashlib.sha256(adapted.encode()).hexdigest(),
                             transformation='one fixed-clock call replacement'if clock else'none'))
        return adapted
    data='\n'.join(take('launcher/minecraft/auth/AccountData.cpp',s)for s in ['QString AccountData::accessToken() const','QString AccountData::profileId() const','QString AccountData::profileName() const','QString AccountData::lastError() const'])
    account='\n'.join(take('launcher/minecraft/auth/MinecraftAccount.cpp',s,clock=s.startswith('bool MinecraftAccount::shouldRefresh'))for s in
        ['bool MinecraftAccount::shouldRefresh() const','void MinecraftAccount::fillSession(AuthSessionPtr session)','QUuid MinecraftAccount::uuidFromUsername(QString username)'])
    inline='\n'.join(take('launcher/minecraft/auth/MinecraftAccount.h',s)for s in ['bool ownsMinecraft() const','bool hasProfile() const','QString typeString() const'])
    lookup='\n'.join(take('launcher/minecraft/auth/AccountList.cpp',s)for s in ['int AccountList::findAccountByProfileId(const QString& profileId) const','MinecraftAccountPtr AccountList::getAccountByProfileName(const QString& profileName) const','const MinecraftAccountPtr AccountList::at(int i) const'])
    claim='\n'.join(take('launcher/minecraft/launch/ClaimAccount.cpp',s)for s in ['ClaimAccount::ClaimAccount(LaunchTask* parent, AuthSessionPtr session)','void ClaimAccount::executeTask()','void ClaimAccount::finalize()'])
    login=take('launcher/LaunchController.cpp','void LaunchController::login()')
    profile=take('launcher/ui/dialogs/ProfileSetupDialog.cpp','void ProfileSetupDialog::setupProfileFinished(QByteArray* response)')
    needle='''            if (ProfileSetupDialog dialog(m_accountToUse, m_parentWidget); dialog.exec() != QDialog::Accepted) {
                emitAborted();
                return;
            }'''
    assert login.count(needle)==1
    refill=login.replace('LaunchController::login','RefillController::login').replace(needle,needle+'\n            m_accountToUse->fillSession(m_session);')
    adopted=login.replace('LaunchController::login','AdoptController::login').replace(needle,needle+'''
            if (!admitFixtureProfile(m_accountToUse)) { emitFailed("Fixture profile admission failed");return; }
            m_accountToUse->fillSession(m_session);''')
    source=r'''
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDebug>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QRegularExpression>
#include <QUuid>
#include <iostream>
#include <memory>
#include <stdexcept>
#include "AccountData.h"
#include "AuthSession.h"
#include "Usable.h"
QDateTime fixtureNow(){return QDateTime::fromSecsSinceEpoch(1800000000,Qt::UTC);}
__DATA__
class MinecraftAccount:public Usable {
public:
 AccountData data;
 QString profileName()const{return data.profileName();}
 QString profileId()const{return data.profileId();}
 AccountType accountType()const{return data.type;}
 __INLINE__
 bool shouldRefresh()const;void fillSession(AuthSessionPtr);
 static QUuid uuidFromUsername(QString);
};
using MinecraftAccountPtr=std::shared_ptr<MinecraftAccount>;
__ACCOUNT__
class AccountList {
public:
 QList<MinecraftAccountPtr> m_accounts;
 int count()const{return m_accounts.size();}
 const MinecraftAccountPtr at(int i)const;
 int findAccountByProfileId(const QString&)const;
 MinecraftAccountPtr getAccountByProfileName(const QString&)const;
};
__LOOKUP__
struct FixtureApplication{AccountList list;AccountList*accounts(){return &list;}} fixtureApplication;
#define APPLICATION (&fixtureApplication)
class LaunchTask{};
class LaunchStep{public:explicit LaunchStep(LaunchTask*){}bool succeeded=false;void emitSucceeded(){succeeded=true;}};
class ClaimAccount:public LaunchStep {
public:ClaimAccount(LaunchTask*,AuthSessionPtr);void executeTask();void finalize();
 QString claimed()const{return m_account?m_account->data.internalId:QString();}
private:std::unique_ptr<UseLock> lock;MinecraftAccountPtr m_account;
};
__CLAIM__
class CapturedClaim {
 std::unique_ptr<UseLock> lock;MinecraftAccountPtr account;
public:CapturedClaim(MinecraftAccountPtr a,LaunchMode mode):account(mode==LaunchMode::Normal?a:nullptr){}
 void executeTask(){if(account)lock.reset(new UseLock(account.get()));}
 void finalize(){lock.reset();}
 QString claimed()const{return account?account->data.internalId:QString();}
};
// UI/network-result adapters below never instantiate a widget or send a request.
struct QDialog{enum{Rejected=0,Accepted=1};};
struct QDialogButtonBox{enum{Cancel=0};};
struct FixtureLabel{void setVisible(bool){}void setText(QString){}};
struct FixtureButton{void setEnabled(bool){}};
struct FixtureButtons{FixtureButton b;FixtureButton*button(int){return &b;}};
struct FixtureUi{FixtureLabel label;FixtureButtons buttons;FixtureLabel*errorLabel=&label;FixtureButtons*buttonBox=&buttons;};
struct FixtureReply{auto error(){return QNetworkReply::NoError;}QString errorString(){return{};}int replyStatusCode(){return 200;}};
struct MojangError{
 bool fullyParsed=false;QString path,error,errorMessage,rawError;QJsonParseError parseError;
 static MojangError fromJSON(QByteArray){return{};}
};
QJsonObject fixtureProfile;bool fixtureAccept=true;int dialogCalls=0;
class ProfileSetupDialog{
 bool accepted=false;FixtureUi uiStorage;FixtureUi*ui=&uiStorage;
 std::shared_ptr<FixtureReply>m_profile_task=std::make_shared<FixtureReply>();
public:bool isWorking=true;
 ProfileSetupDialog(MinecraftAccountPtr,void*){}
 static QString tr(const char*s){return QString::fromUtf8(s);}
 void accept(){accepted=true;}
 void setupProfileFinished(QByteArray*);
 int exec(){dialogCalls++;if(!fixtureAccept)return QDialog::Rejected;auto bytes=QJsonDocument(fixtureProfile).toJson();setupProfileFinished(&bytes);return accepted?QDialog::Accepted:QDialog::Rejected;}
};
__PROFILE__
bool admitFixtureProfile(MinecraftAccountPtr account){
 auto id=fixtureProfile["id"].toString(),name=fixtureProfile["name"].toString();
 // Private candidate premise: a fresh profile has been independently admitted.
 // These closed-fixture checks do not replace Prism's provider parsers/auth.
 if(!QRegularExpression("^[0-9a-f]{32}$").match(id).hasMatch()||!QRegularExpression("^[A-Za-z0-9_]{3,16}$").match(name).hasMatch())return false;
 account->data.minecraftProfile.id=id;account->data.minecraftProfile.name=name;account->data.minecraftProfile.validity=Validity::Certain;return true;
}
enum class LaunchDecision{Continue,Undecided,Abort};
class LaunchController{
public:
 MinecraftAccountPtr m_accountToUse;AuthSessionPtr m_session;
 LaunchMode m_actualLaunchMode=LaunchMode::Normal,m_wantedLaunchMode=LaunchMode::Normal;
 void*m_parentWidget=nullptr;QString m_offlineName="Offline_Alias";
 bool aborted=false;int launches=0;QString error;
 void decideAccount(){}LaunchDecision decideLaunchMode(){return LaunchDecision::Continue;}
 bool askPlayDemo(){return true;}QString askOfflineName(QString,bool*ok){*ok=true;return "Demo_Player";}
 void launchInstance(){launches++;}void emitAborted(){aborted=true;}void emitFailed(QString s){error=s;}
 static QString tr(const char*s){return QString::fromUtf8(s);}
 void login();
};
__LOGIN__
class RefillController:public LaunchController{public:void login();};
__REFILL__
class AdoptController:public LaunchController{public:void login();};
__ADOPT__
QJsonObject sessionJson(AuthSessionPtr s){
 if(!s)return{};
 return{{"session",s->session},{"access_token",s->access_token},{"name",s->player_name},{"uuid",s->uuid},{"user_type",s->user_type},{"mode",int(s->launchMode)}};
}
int integer(QJsonObject o,QString k,int low,int high){auto v=o[k];if(!v.isDouble()||v.toDouble()!=v.toInt()||v.toInt()<low||v.toInt()>high)throw std::runtime_error("integer admission");return v.toInt();}
bool boolean(QJsonObject o,QString k){if(!o[k].isBool())throw std::runtime_error("boolean admission");return o[k].toBool();}
MinecraftAccountPtr account(QJsonObject o){
 for(auto k:{"id","name","profileId"})if(!o[k].isString())throw std::runtime_error("string admission");
 auto a=std::make_shared<MinecraftAccount>();auto&d=a->data;
 d.internalId=o["id"].toString();d.minecraftProfile.name=o["name"].toString();d.minecraftProfile.id=o["profileId"].toString();
 d.type=AccountType(integer(o,"type",0,1));d.minecraftEntitlement.ownsMinecraft=boolean(o,"owns");d.validity_=Validity(integer(o,"validity",0,2));d.accountState=AccountState(integer(o,"state",0,7));
 d.yggdrasilToken.token=boolean(o,"tokenPresent")?(d.type==AccountType::Offline?"0":"fixture"):"";
 int age=integer(o,"issuedAgo",-200000,200000),expiry=integer(o,"expiresIn",-200000,200000);
 if(boolean(o,"hasIssue"))d.yggdrasilToken.issueInstant=fixtureNow().addSecs(-age);
 if(boolean(o,"hasExpiry"))d.yggdrasilToken.notAfter=fixtureNow().addSecs(expiry);
 return a;
}
QJsonObject accountJson(MinecraftAccountPtr a){return{{"id",a->data.internalId},{"rawName",a->data.minecraftProfile.name},{"profileName",a->profileName()},{"profileId",a->profileId()},{"owns",a->ownsMinecraft()},{"hasProfile",a->hasProfile()},{"uses",int(a->useCount())}};}
QJsonArray counts(const QList<MinecraftAccountPtr>&as){QJsonArray out;for(auto a:as)out.append(QJsonObject{{"id",a->data.internalId},{"uses",int(a->useCount())},{"refresh",a->shouldRefresh()}});return out;}
template<class C>QJsonObject loginCase(QJsonObject input){
 C c;c.m_accountToUse=account(input["account"].toObject());c.m_actualLaunchMode=LaunchMode(integer(input,"mode",0,2));c.m_wantedLaunchMode=c.m_actualLaunchMode;
 auto before=accountJson(c.m_accountToUse);dialogCalls=0;c.login();
 return{{"before",before},{"account",accountJson(c.m_accountToUse)},{"session",sessionJson(c.m_session)},{"dialogs",dialogCalls},{"launches",c.launches},{"aborted",c.aborted},{"error",c.error}};
}
int main(int argc,char**argv){
 QCoreApplication app(argc,argv);if(argc!=2)return 2;QFile f(QString::fromLocal8Bit(argv[1]));if(!f.open(QIODevice::ReadOnly))return 2;
 QJsonParseError e;auto doc=QJsonDocument::fromJson(f.readAll(),&e);auto root=doc.object();if(e.error!=QJsonParseError::NoError||root["schema"].toInt()!=1||!root["cases"].isArray()||root["cases"].toArray().size()>128)return 2;
 try{for(auto raw:root["cases"].toArray()){
  auto input=raw.toObject();auto kind=input["kind"].toString();QJsonObject result{{"id",input["id"]},{"kind",kind}};
  if(kind=="identity"){
   auto a=account(input["account"].toObject());auto s=std::make_shared<AuthSession>();s->launchMode=LaunchMode(integer(input,"mode",0,2));
   if(boolean(input,"fill"))a->fillSession(s);auto before=sessionJson(s);auto mutation=input["mutation"].toString();
   if(mutation=="offline")s->MakeOffline("Offline_Alias");else if(mutation=="demo")s->MakeDemo("Demo_Player",QString(32,'3'));else if(mutation!="none")return 2;
   result["account"]=accountJson(a);result["before"]=before;result["after"]=sessionJson(s);
  }else if(kind=="refresh"){
   auto a=account(input["account"].toObject());std::unique_ptr<UseLock>held;if(boolean(input,"inUse"))held=std::make_unique<UseLock>(a.get());
   auto expires=a->data.yggdrasilToken.notAfter;if(!expires.isValid())expires=a->data.yggdrasilToken.issueInstant.addSecs(24*3600);
   result["uses"]=int(a->useCount());result["remaining"]=expires.isValid()?QJsonValue(double(fixtureNow().secsTo(expires))):QJsonValue(QJsonValue::Null);result["refresh"]=a->shouldRefresh();
  }else if(kind=="claim"){
   auto&list=fixtureApplication.list;list.m_accounts.clear();MinecraftAccountPtr selected;
   for(auto value:input["accounts"].toArray()){auto a=account(value.toObject());list.m_accounts.append(a);if(a->data.internalId==input["selected"].toString())selected=a;}
   if(!selected)return 2;auto s=std::make_shared<AuthSession>();s->launchMode=LaunchMode(integer(input,"mode",0,2));selected->fillSession(s);
   ClaimAccount first(nullptr,s),second(nullptr,s);result["before"]=counts(list.m_accounts);first.executeTask();second.executeTask();result["claimed"]=first.claimed();result["held"]=counts(list.m_accounts);first.finalize();result["oneFinalized"]=counts(list.m_accounts);second.finalize();result["finalized"]=counts(list.m_accounts);
   CapturedClaim c1(selected,s->launchMode),c2(selected,s->launchMode);c1.executeTask();c2.executeTask();result["candidateClaimed"]=c1.claimed();result["candidateHeld"]=counts(list.m_accounts);c1.finalize();c2.finalize();result["candidateFinalized"]=counts(list.m_accounts);
  }else if(kind=="login"){
   fixtureAccept=boolean(input,"accept");fixtureProfile=input["profileResponse"].toObject();
   result["current"]=loginCase<LaunchController>(input);result["refillOnly"]=loginCase<RefillController>(input);result["admittedThenRefill"]=loginCase<AdoptController>(input);
  }else return 2;
  std::cout<<QJsonDocument(result).toJson(QJsonDocument::Compact).constData()<<"\n";
 }}catch(const std::exception&){return 2;}return 0;
}
'''
    for name,value in [('DATA',data),('INLINE',inline),('ACCOUNT',account),('LOOKUP',lookup),('CLAIM',claim),('PROFILE',profile),('LOGIN',login),('REFILL',refill),('ADOPT',adopted)]:
        assert source.count('__'+name+'__')==1;source=source.replace('__'+name+'__',value)
    (work/'main.cpp').write_text(source)
    cases=[]
    def add(kind,id,**fields):cases.append(dict(kind=kind,id=id,**fields))
    for id,a,mode,mutation,fill in [
        ('msa-normal',actor(),0,'none',True),('offline-conversion',actor(),1,'offline',True),
        ('demo-reuse',actor(),0,'demo',True),('demo-fresh',actor(),0,'demo',False),
        ('missing-profile',actor(name='',profile=''),0,'none',True),
        ('offline-entitlement-flag',actor(type=1,owns=True),1,'none',True),
        ('no-token',dict(actor(),tokenPresent=False),0,'none',True)]:add('identity',id,account=a,mode=mode,mutation=mutation,fill=fill)
    for id,validity,expires,issue,hasExpiry,hasIssue,inUse in [
        ('none',0,86400,0,True,True,False),('assumed',1,86400,0,True,True,False),
        ('fresh',2,86400,0,True,True,False),('inside-12h',2,43199,0,True,True,False),
        ('exact-12h',2,43200,0,True,True,False),('outside-12h',2,43201,0,True,True,False),
        ('expired',2,-1,0,True,True,False),('fallback-exact',2,0,43200,False,True,False),
        ('fallback-inside',2,0,43201,False,True,False),('missing-timestamps',2,0,0,False,False,False),
        ('in-use-assumed',1,0,0,False,False,True),('in-use-certain',2,0,0,True,True,True)]:
        a=actor(validity=validity);a.update(expiresIn=expires,issuedAgo=issue,hasExpiry=hasExpiry,hasIssue=hasIssue);add('refresh',id,account=a,inUse=inUse)
    a=actor(id='A',type=1,owns=False,validity=0,profile='1'*32);b=actor()
    for id,entries,mode in [('name-collision',[a,b],0),('name-collision-reversed',[b,a],0),('unique-names',[dict(a,name='Other'),b],0),('offline-constructor-control',[a,b],1),('demo-constructor-control',[a,b],2)]:add('claim',id,accounts=entries,selected='B',mode=mode)
    fresh=actor(name='',profile='');response=dict(name='Fresh_Player',id='2'*32)
    for id,a,mode,accept,responseValue in [('new-profile-accepted',fresh,0,True,response),('new-profile-rejected',fresh,0,False,response),('invalid-success-body',fresh,0,True,dict(name='',id='')),('existing-profile',actor(),0,True,response),('offline-existing',actor(),1,True,response),('demo',actor(),2,True,response)]:add('login',id,account=a,mode=mode,accept=accept,profileResponse=responseValue)
    (run/'input.json').write_text(json.dumps(dict(schema=1,cases=cases),indent=2)+'\n')
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8');owned=[];commands=[]
    def command(label,argv,timeout):
        with(run/(label+'.stdout')).open('xb')as out,(run/(label+'.stderr')).open('xb')as err:
            p=subprocess.Popen(argv,env=env,cwd=work,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(p)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
            timed=False;start=time.monotonic()
            try:p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        row=dict(case=label,argv=argv,exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent,seconds=time.monotonic()-start,streams={s:sha(run/(label+'.'+s))for s in ['stdout','stderr']});commands.append(row)
        (run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert not timed and absent and p.returncode==0,(label,p.returncode)
    try:
        pkg='/opt/homebrew/bin/pkg-config';flags=shlex.split(subprocess.check_output([pkg,'--cflags','--libs','Qt6Core','Qt6Network'],text=True));lib=subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip()
        command('compile',['/usr/bin/clang++','-std=c++20','-O0','-DQT_NO_DEBUG','-I'+str(work),str(work/'main.cpp'),str(work/'AuthSession.cpp'),'-o',str(work/'probe'),*flags,'-Wl,-rpath,'+lib],90)
        command('observe',[str(work/'probe'),str(run/'input.json')],20)
        rows=[json.loads(line)for line in(run/'observe.stdout').read_text().splitlines()];assert len(rows)==len(cases)==30 and [r['id']for r in rows]==[c['id']for c in cases]
        receipt=dict(schema=1,producerSha256=sha(run/'probe.py'),generatedSourceSha256=sha(work/'main.cpp'),binarySha256=sha(work/'probe'),copiedSources=copied,excerpts=excerpts,
            candidates=dict(refillOnlySha256=hashlib.sha256(refill.encode()).hexdigest(),admittedThenRefillSha256=hashlib.sha256(adopted.encode()).hexdigest()),
            compiler=subprocess.check_output(['/usr/bin/clang++','--version'],text=True),qtVersion=subprocess.check_output([pkg,'--modversion','Qt6Core'],text=True).strip(),
            frameworkSha256={n:sha(Path(lib)/(n+'.framework')/'Versions/A'/n)for n in ['QtCore','QtNetwork']},
            cases=len(cases),allOwnedGroupsAbsent=all(c['ownedGroupAbsent']for c in commands),workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            limits=['Synthetic DTO/UI/network-result/APP/pointer adapters;NO actual account store,network requests,widgets,game or installed-Prism launch.',
                'Unchanged selected method bodies except one explicit refresh clock call replacement;candidate login bodies and captured-actor claim are private proposals.',
                'All accounts retained through each case;std::shared_ptr adapter does NOT qualify actual QObject/shared_qobject_ptr destruction or concurrent lifetime.',
                'Profile-success uses actual handler with controlled NoError;it accepts WITHOUT updating AccountData. Candidate consumes admitted fixture profile,not real provider/parser/refresh proof.',
                'Current installed Qt profile recorded;not the launcher bundled-Qt or all-platform binary. Constructor-only non-Normal claim controls are not full launch routes.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(capture=str(run),cases=len(cases),qt=receipt['qtVersion']),indent=2))
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
