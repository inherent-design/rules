#include <QApplication>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QVariant>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <tuple>
#include <vector>

struct Mapping { QString source,destination;bool isDirectory,createTarget; };
using MappingType=std::vector<Mapping>;
static QStringList warnings;
namespace log {template<class... T>void warn(const char* s,T&&...){warnings.append(QString::fromUtf8(s));}}
struct MyException:std::runtime_error { explicit MyException(QString s):std::runtime_error(s.toStdString()){} };
struct IPlugin {virtual ~IPlugin()=default;};
namespace MOBase {
struct IPluginFileMapper: IPlugin {
  MappingType rows;bool enabled;
  MappingType mappings(){return rows;}
};
}
struct IPluginGame {
  int paths=1;
  QDir dataDirectory()const{return QDir("/fixture/Data");}
  QList<QDir> secondaryDataDirectories()const{return paths==2?QList<QDir>{QDir("/fixture/Extra")}:QList<QDir>{};}
};
Q_DECLARE_METATYPE(IPluginGame*)
struct LocalSavegames {
  MappingType mappings(QString p){return {{p,"/fixture/Saves",true,true}};}
};
struct Features {
  LocalSavegames* saves=nullptr;
  template<class T>T* gameFeature(){return static_cast<T*>(saves);}
};
struct ModInfo {
  using Ptr=std::shared_ptr<ModInfo>;
  bool regular;
  static std::vector<Ptr> values;
  static std::map<QString,unsigned> indices;
  static unsigned getIndex(const QString& name){return indices.at(name);}
  static Ptr getByIndex(unsigned index){return values.at(index);}
  bool isRegular()const{return regular;}
};
std::vector<ModInfo::Ptr> ModInfo::values;
std::map<QString,unsigned> ModInfo::indices;
using Mods=std::vector<std::tuple<QString,QString,int>>;
static std::map<QString,Mods> profileMods;
static std::map<QString,bool> saveFlags;
static QString constructed;
struct Profile {
  QString path,name;
  Profile(QDir dir,IPluginGame*,Features):path(dir.absolutePath()),name(dir.dirName()){constructed=path;}
  Mods getActiveMods()const{return profileMods.at(name);}
  bool localSavesEnabled()const{return saveFlags.at(name);}
  QString absolutePath()const{return path;}
};
struct Paths {
  QString profiles()const{return "/fixture/profiles";}
  QString overwrite()const{return "/fixture/overwrite";}
};
struct Settings {Paths paths()const{return {};}};
struct Container {
  std::vector<std::unique_ptr<MOBase::IPluginFileMapper>> values;
  template<class T>std::vector<T*> plugins(){std::vector<T*>result;for(auto& v:values)result.push_back(static_cast<T*>(v.get()));return result;}
  bool isEnabled(IPlugin* p){for(auto& v:values)if(v.get()==p)return v->enabled;return false;}
};
class OrganizerCore {
 public:
  bool m_DirectoryUpdate=false;
  Settings m_Settings;
  Profile* m_CurrentProfile=nullptr;
  Container* m_PluginContainer=nullptr;
  Features features;
  Features gameFeatures(){return features;}
  Profile* currentProfile(){return m_CurrentProfile;}
  static QString tr(const char* s){return QString::fromUtf8(s);}
  void directoryStructureReady(){}
  template<class... T>void connect(T&&...){throw std::runtime_error("Ready-wait adapter must remain unexecuted");}
  std::vector<Mapping> fileMapping(const QString&,const QString&);
};
#include "selected_mapping.cpp"

int main(int argc,char**argv){
  QApplication app(argc,argv);if(argc!=2)return 2;
  QFile file(QString::fromUtf8(argv[1]));if(!file.open(QIODevice::ReadOnly))return 3;
  auto requests=QJsonDocument::fromJson(file.readAll()).array();
  for(auto raw:requests){
    auto r=raw.toObject();QString id=r["case"].toString();warnings.clear();ModInfo::values.clear();ModInfo::indices.clear();profileMods.clear();saveFlags.clear();
    IPluginGame game;game.paths=r["dataPaths"].toInt();qApp->setProperty("managed_game",QVariant::fromValue(&game));
    Mods mods;
    for(auto item:r["active"].toArray()){
      auto m=item.toObject();QString name=m["name"].toString();
      ModInfo::indices[name]=ModInfo::values.size();ModInfo::values.push_back(std::make_shared<ModInfo>(ModInfo{m["regular"].toBool()}));
      mods.emplace_back(name,"/fixture/mods/"+name,m["priority"].toInt());
    }
    QString requested=r["profile"].toString(),current=r["currentProfile"].toString();
    profileMods[requested]=mods;profileMods[current]=mods;
    auto flags=r["localByProfile"].toObject();for(auto it=flags.begin();it!=flags.end();++it)saveFlags[it.key()]=it.value().toBool();
    LocalSavegames saves;Features features{r["localFeature"].toBool()?&saves:nullptr};
    Profile currentProfile(QDir("/fixture/profiles/"+current),&game,features);Container plugins;
    if(r["plugin"].toBool()){
      auto p=std::make_unique<MOBase::IPluginFileMapper>();p->enabled=r["pluginEnabled"].toBool();
      p->rows={{"/fixture/plugin","/fixture/Data",true,true}};plugins.values.push_back(std::move(p));
    }
    OrganizerCore core;core.m_CurrentProfile=&currentProfile;core.m_PluginContainer=&plugins;core.features=features;
    QJsonObject outcome;
    try{
      auto mappings=core.fileMapping(requested,r["custom"].toString());QJsonArray rows;
      for(auto& m:mappings)rows.append(QJsonObject{{"source",m.source},{"destination",m.destination},{"directory",m.isDirectory},{"createTarget",m.createTarget}});
      outcome=QJsonObject{{"accepted",true},{"mappings",rows}};
    }catch(const std::exception& e){outcome=QJsonObject{{"accepted",false},{"error",QString::fromUtf8(e.what())}};}
    QJsonArray ws;for(auto s:warnings)ws.append(s);
    QJsonObject record{{"case",id},{"request",r},{"observed",outcome},{"constructedProfile",constructed},
      {"warnings",ws},{"qt",qVersion()},{"platformPlugin",QGuiApplication::platformName()}};
    std::cout<<QJsonDocument(record).toJson(QJsonDocument::Compact).constData()<<std::endl;
  }
}
