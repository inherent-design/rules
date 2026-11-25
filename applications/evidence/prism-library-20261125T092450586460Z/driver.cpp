// Owned adapter for selected unchanged InstanceList/BaseInstance bodies.
// QCoreApplication only; no launcher constructor, watcher, account or OS trash.
#include <QtCore>
#include <QAbstractListModel>
#include <QSaveFile>
#include <memory>
#include <vector>
#include <iostream>
using GroupId=QString;using InstanceId=QString;
struct ShortcutData{QString name,filePath,target;};
struct TrashShortcutItem{ShortcutData data;QString trashPath;};
struct TrashHistoryItem{QString id,path,trashPath,groupName;QList<TrashShortcutItem>shortcuts;};
namespace FS{
QString root;bool failTrash=false,failDelete=false,failWrite=false;int serial=0;
class FileSystemException{QString why;public:FileSystemException(QString w):why(w){}QString cause()const{return why;}};
void bound(QString p){if(!QFileInfo(p).absoluteFilePath().startsWith(root+"/"))qFatal("Fixture escaped owned root");}
QString PathCombine(QString a,QString b){return QDir(a).filePath(b);}
QByteArray read(QString p){bound(p);QFile f(p);if(!f.open(QIODevice::ReadOnly))throw FileSystemException("fixture read");return f.readAll();}
void write(QString p,QByteArray data){bound(p);if(failWrite)throw FileSystemException("injected write refusal");QSaveFile f(p);if(!f.open(QIODevice::WriteOnly)||f.write(data)!=data.size()||!f.commit())throw FileSystemException("fixture write");}
bool trash(QString p,QString*out){bound(p);if(failTrash)return false;auto target=root+"/trash-"+QString::number(++serial);bound(target);if(!QFile::rename(p,target))return false;*out=target;return true;}
bool deletePath(QString p){bound(p);if(failDelete)return false;QFileInfo i(p);return i.isDir()&&!i.isSymLink()?QDir(p).removeRecursively():QFile::remove(p);}
}
struct SettingsObject{QMap<QString,QVariant>values;QVariant get(QString k)const{return values.value(k);}void set(QString k,QVariant v){values[k]=v;}};
class BaseInstance{
public:QString m_rootDir,m_uuid;std::unique_ptr<SettingsObject>m_settings=std::make_unique<SettingsObject>();QList<ShortcutData>links;int propertyNotices=0;
BaseInstance(QString root,QString uuid):m_rootDir(root),m_uuid(uuid){m_settings->set("name",QFileInfo(root).fileName());}
QString instanceRoot()const{return m_rootDir;}QString uuid()const{return m_uuid;}QString name()const{return m_settings->get("name").toString();}QString iconKey()const{return "fixture";}
void propertiesChanged(BaseInstance*){++propertyNotices;}
QList<ShortcutData>shortcuts()const{return links;}
QString id()const;void setName(QString);bool syncInstanceDirName(const QString&)const;
};
struct WatchLock{WatchLock(QFileSystemWatcher*,QString){}};
const static int GROUP_FILE_FORMAT_VERSION=1;
class InstanceList:public QAbstractListModel{
public:
std::vector<std::unique_ptr<BaseInstance>>m_instances;QMap<QString,int>m_groupNameCache;QSet<QString>m_collapsedGroups;QMap<InstanceId,GroupId>m_instanceGroupIndex;QSet<QString>instanceSet;QString m_instDir;QFileSystemWatcher*m_watcher=nullptr;bool m_instancesProbed=true,m_groupsLoaded=false;QStack<TrashHistoryItem>m_trashHistory;int changes=0;
InstanceList(QString d):m_instDir(d){}
int count()const{return int(m_instances.size());}int rowCount(const QModelIndex&parent=QModelIndex())const override;QModelIndex index(int row,int column=0,const QModelIndex&parent=QModelIndex())const override;
QVariant data(const QModelIndex&,int role=Qt::DisplayRole)const override;bool setData(const QModelIndex&,const QVariant&,int role=Qt::EditRole)override;
enum AdditionalRoles{GroupRole=Qt::UserRole,InstancePointerRole=0x34B1CB48,InstanceIDRole=0x34B1CB49};
BaseInstance*getInstanceById(QString)const;int getInstIndex(BaseInstance*)const;
GroupId getInstanceGroup(const InstanceId&)const;void setInstanceGroup(const InstanceId&,GroupId);void setInstanceGroupCanonical(const InstanceId&,GroupId);
QStringList getGroups();void deleteGroup(const GroupId&);void renameGroup(const QString&,const QString&);bool isGroupCollapsed(const QString&);
void increaseGroupCount(const QString&);void decreaseGroupCount(const QString&);void saveGroupList();void loadGroupList();
bool trashInstance(const InstanceId&);bool trashedSomething()const;bool undoTrashInstance();void deleteInstance(const InstanceId&);QList<InstanceId>discoverInstances();
void instancesChanged(){++changes;}
};
__BODIES__
QJsonArray strings(QStringList xs){xs.sort();QJsonArray a;for(auto x:xs)a.append(x);return a;}
QJsonObject textMap(const QMap<QString,QString>&m){QJsonObject o;for(auto i=m.begin();i!=m.end();++i)o[i.key()]=i.value();return o;}
QJsonObject state(InstanceList&l){QJsonObject counts;for(auto i=l.m_groupNameCache.begin();i!=l.m_groupNameCache.end();++i)counts[i.key()]=i.value();QJsonObject roots,names,live;for(auto&i:l.m_instances){roots[i->id()]=QFileInfo(i->instanceRoot()).exists();names[i->id()]=i->name();live[i->id()]=l.getInstanceGroup(i->id());}QJsonObject out{{"index",textMap(l.m_instanceGroupIndex)},{"counts",counts},{"collapsed",strings(l.m_collapsedGroups.values())},{"roots",roots},{"names",names},{"live",live},{"history",l.m_trashHistory.size()},{"notices",l.changes}};QString p=l.m_instDir+"/instgroups.json";out["saved"]=QFileInfo(p).exists()?QJsonValue(QJsonDocument::fromJson(FS::read(p)).object()):QJsonValue();return out;}
void seed(InstanceList&l,QString group){if(!group.isEmpty()){l.m_instanceGroupIndex["a"]=group;l.increaseGroupCount(group);}l.saveGroupList();}
void emitCase(QString id,QJsonObject result){result["id"]=id;std::cout<<QJsonDocument(result).toJson(QJsonDocument::Compact).toStdString()<<"\n";}
int main(int argc,char**argv){QCoreApplication app(argc,argv);FS::root=QString::fromLocal8Bit(argv[1]);
QStringList cases={"rename-label","rename-wrong-role","duplicate-label","group-directory","group-uuid-first","group-uuid-existing","group-uuid-candidate","lookup-collision","rename-group-merge","delete-group","trash-failure","delete-failure","undo-success","undo-directory-collision","undo-file-collision","undo-shortcut-collision","reload-collapse","load-duplicate","load-missing","load-unsupported","save-refused","save-unprobed","discover","rename-path"};
for(auto id:cases){FS::failTrash=FS::failDelete=FS::failWrite=false;QString area=FS::root+"/"+id,dir=area+"/instances";QDir().mkpath(dir);InstanceList l(dir);
for(auto name:QStringList{"a","b"}){QString p=dir+"/"+name;QDir().mkpath(p);FS::write(p+"/instance.cfg","InstanceType=OneSix\n");FS::write(p+"/data",name.toUtf8());auto i=std::make_unique<BaseInstance>(p,name=="a"?QString(32,'1'):QString(32,'2'));l.instanceSet.insert(name);l.m_instances.push_back(std::move(i));}
QJsonObject out;auto before=[&](){out["before"]=state(l);};auto after=[&](){out["after"]=state(l);};
if(id=="rename-label"||id=="rename-wrong-role"||id=="duplicate-label"){before();out["ok"]=l.setData(l.index(0),id=="duplicate-label"?"b":"Renamed",id=="rename-wrong-role"?Qt::DisplayRole:Qt::EditRole);out["uuid"]=l.m_instances[0]->uuid();after();}
else if(id.startsWith("group-")){if(id=="group-uuid-existing")seed(l,"Old");before();QString selector=id=="group-directory"?"a":QString(32,'1');if(id=="group-uuid-candidate")l.setInstanceGroupCanonical(selector,"New");else l.setInstanceGroup(selector,"New");out["resolvedId"]=l.getInstanceById(selector)->id();after();}
else if(id=="lookup-collision"){QString alias=dir+"/"+QString(32,'1');QDir().mkpath(alias);l.m_instances.push_back(std::make_unique<BaseInstance>(alias,QString(32,'3')));before();out["resolvedId"]=l.getInstanceById(QString(32,'1'))->id();after();}
else if(id=="rename-group-merge"){seed(l,"Old");l.setInstanceGroup("b","New");l.m_collapsedGroups.insert("Old");before();l.renameGroup("Old","New");after();}
else if(id=="delete-group"){seed(l,"Old");l.setInstanceGroup("b","Old");before();l.deleteGroup("Old");after();}
else if(id=="trash-failure"||id=="delete-failure"){seed(l,"Old");before();FS::failTrash=id=="trash-failure";FS::failDelete=id=="delete-failure";if(FS::failTrash)out["ok"]=l.trashInstance("a");else l.deleteInstance("a");after();out["bytes"]=QString::fromUtf8(FS::read(dir+"/a/data"));}
else if(id.startsWith("undo-")){seed(l,"Old");QString shortcut=area+"/shortcut";if(id=="undo-shortcut-collision"){FS::write(shortcut,"shortcut");l.m_instances[0]->links.append({"fixture",shortcut,"target"});}before();out["trashOk"]=l.trashInstance("a");QString trashed=l.m_trashHistory.top().trashPath;out["trashed"]=state(l);if(id=="undo-directory-collision")QDir().mkpath(dir+"/a");if(id=="undo-file-collision")FS::write(dir+"/a","occupied");if(id=="undo-shortcut-collision")FS::write(shortcut,"occupied");out["ok"]=l.undoTrashInstance();after();out["trashPayloadRemains"]=QFileInfo(trashed).exists();out["restoredPath"]=QDir(dir+"/a").exists()?"a":QDir(dir+"/a1").exists()?"a1":"";out["secondOk"]=l.undoTrashInstance();out["second"]=state(l);out["originalTrash"]=trashed;if(id=="undo-shortcut-collision")out["shortcutBytes"]=QString::fromUtf8(FS::read(shortcut));}
else if(id=="reload-collapse"||id.startsWith("load-")){seed(l,"Old");if(id=="reload-collapse"){l.m_collapsedGroups.insert("New");l.m_collapsedGroups.insert("");}before();QJsonObject data{{"formatVersion","1"},{"groups",QJsonObject{{"New",QJsonObject{{"hidden",false},{"instances",QJsonArray{"a"}}}}}}};if(id=="load-duplicate")data["groups"]=QJsonObject{{"New",QJsonObject{{"instances",QJsonArray{"a","a"}}}}};if(id=="load-missing")data["groups"]=QJsonObject{{"New",QJsonObject{{"instances",QJsonArray{"ghost"}}}}};if(id=="load-unsupported")data["formatVersion"]="2";FS::write(dir+"/instgroups.json",QJsonDocument(data).toJson());out["input"]=data;l.loadGroupList();after();l.saveGroupList();out["resaved"]=state(l);}
else if(id=="save-refused"||id=="save-unprobed"){seed(l,"Old");before();if(id=="save-refused")FS::failWrite=true;else l.m_instancesProbed=false;l.setInstanceGroup("a","New");after();}
else if(id=="discover"){QString other=area+"/outside/x";QDir().mkpath(other);FS::write(other+"/instance.cfg","InstanceType=OneSix\n");QFile::link(dir+"/a",dir+"/internal");QFile::link(other,dir+"/external");QDir().mkpath(dir+"/.hidden");FS::write(dir+"/.hidden/instance.cfg","InstanceType=OneSix\n");QDir().mkpath(dir+"/no-config");before();out["found"]=strings(l.discoverInstances());after();}
else if(id=="rename-path"){before();auto*i=l.m_instances[0].get();out["ok"]=i->syncInstanceDirName(dir+"/renamed");after();out["newExists"]=QFileInfo(dir+"/renamed/data").exists();out["objectRoot"]=i->instanceRoot();}
emitCase(id,out);
}
}
