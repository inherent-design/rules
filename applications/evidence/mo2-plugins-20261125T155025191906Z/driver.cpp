// Research field/callback adapters. The collector inserts selected unchanged methods.
#include <QCoreApplication>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStringList>
#include <iostream>
#include <functional>
#include <map>
#include <set>
#include <vector>

static int errors=0,warnings=0;
namespace fixture_log {
template<class... T> void error(const char*, const T&...) { ++errors; }
template<class... T> void warn(const char*, const T&...) { ++warnings; }
}
#define log fixture_log
#define emit
using FileNameComparator=std::less<QString>; // Canonical exact-name corpus only.
struct IPluginList {
  enum PluginState {STATE_MISSING,STATE_INACTIVE,STATE_ACTIVE};
  using PluginStates=PluginState;
};
void reportError(const QString&) { ++errors; }
QString state_text(IPluginList::PluginStates value) {
  return value==IPluginList::STATE_ACTIVE?"active":value==IPluginList::STATE_INACTIVE?"inactive":"missing";
}
struct PluginList {
  using PluginStates=IPluginList::PluginStates;
  struct ESPInfo {
    QString name;bool enabled=false,forceLoaded=false,forceEnabled=false,forceDisabled=false;
    int priority=0,loadOrder=-1;
    std::set<QString,FileNameComparator> masters,masterUnset;
  };
  std::vector<ESPInfo> m_ESPs;
  std::map<QString,int> m_ESPsByName;
  std::vector<int> m_ESPsByPriority;
  int writes=0,generated=0;
  QJsonArray events;
  std::function<void(const std::map<QString,PluginStates>&)> m_PluginStateChanged;
  PluginList() {
    m_PluginStateChanged=[this](const auto& names) {
      QJsonObject values;
      for(const auto& [name,value]:names)values[name]=state_text(value);
      events.append(QJsonObject{{"kind","state"},{"values",values}});
    };
  }
  static QString tr(const char* value){return QString::fromUtf8(value);}
  void writePluginsList(){++writes;events.append(QJsonObject{{"kind","write"}});}
  void generatePluginIndexes(){++generated;} // No game feature,Qt slot,or plugin-index allocation.
  PluginStates state(const QString& name)const;
  void setState(const QString& name,PluginStates value);
  void enableESP(const QString& name,bool enable);
  void setEnabledAll(bool enable);
  void setLoadOrder(const QStringList& names);
  void updateIndices();
  void syncLoadOrder();
  void testMasters();
  void pluginStatesChanged(const QStringList& names,PluginStates value)const;
};

/*METHODS*/

QJsonObject observe(const PluginList& value) {
  QJsonArray plugins,byPriority;QJsonObject indexed;
  for(const auto& p:value.m_ESPs){
    QJsonArray missing;for(const auto& name:p.masterUnset)missing.append(name);
    plugins.append(QJsonObject{{"name",p.name},{"enabled",p.enabled},{"priority",p.priority},
      {"loadOrder",p.loadOrder},{"missing",missing},{"queriedState",state_text(value.state(p.name))}});
  }
  for(int index:value.m_ESPsByPriority)byPriority.append(index);
  for(const auto&[name,index]:value.m_ESPsByName)indexed[name]=index;
  return {{"plugins",plugins},{"byPriority",byPriority},{"byName",indexed},
    {"writes",value.writes},{"generated",value.generated},{"events",value.events},
    {"errors",errors},{"warnings",warnings}};
}
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);
  if(argc!=2)return 2;
  QFile file(QString::fromUtf8(argv[1]));if(!file.open(QIODevice::ReadOnly))return 2;
  auto packet=QJsonDocument::fromJson(file.readAll()).object();if(packet["schema"].toInt()!=1)return 2;
  QJsonArray rows;
  for(const auto& entry:packet["cases"].toArray()){
    auto input=entry.toObject();PluginList value;errors=warnings=0;
    for(const auto& item:input["plugins"].toArray()){
      auto p=item.toObject();PluginList::ESPInfo info;
      info.name=p["name"].toString();info.enabled=p["enabled"].toBool();info.priority=p["priority"].toInt();info.loadOrder=p["loadOrder"].toInt();
      info.forceLoaded=p["forceLoaded"].toBool();info.forceEnabled=p["forceEnabled"].toBool();info.forceDisabled=p["forceDisabled"].toBool();
      for(const auto& master:p["masters"].toArray())info.masters.insert(master.toString());
      for(const auto& master:p["missing"].toArray())info.masterUnset.insert(master.toString());
      value.m_ESPs.push_back(info);
    }
    // Admitted initial indices; constructor/refresh/file parsing are not executed.
    value.m_ESPsByPriority.resize(value.m_ESPs.size());
    for(int i=0;i<static_cast<int>(value.m_ESPs.size());++i){
      const auto&p=value.m_ESPs[i];if(p.priority<0||p.priority>=static_cast<int>(value.m_ESPs.size()))return 3;
      value.m_ESPsByName[p.name]=i;value.m_ESPsByPriority.at(p.priority)=i;
    }
    QJsonArray steps;auto before=observe(value);
    for(const auto& item:input["actions"].toArray()){
      auto action=item.toObject();auto kind=action["kind"].toString();
      if(kind=="set-state")value.setState(action["name"].toString(),action["active"].toBool()?IPluginList::STATE_ACTIVE:IPluginList::STATE_INACTIVE);
      else if(kind=="enable")value.enableESP(action["name"].toString(),action["active"].toBool());
      else if(kind=="all")value.setEnabledAll(action["active"].toBool());
      else if(kind=="order") {QStringList names;for(const auto& name:action["names"].toArray())names.append(name.toString());value.setLoadOrder(names);}
      else if(kind=="sync")value.syncLoadOrder();
      else if(kind=="masters")value.testMasters();
      else return 4;
      steps.append(observe(value));
    }
    rows.append(QJsonObject{{"id",input["id"]},{"before",before},{"steps",steps}});
  }
  std::cout<<QJsonDocument(rows).toJson(QJsonDocument::Compact).constData()<<'\n';
}
