#include <QApplication>
#include <QComboBox>
#include <QCryptographicHash>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTreeWidget>
#include <iostream>
#include <map>
#include <memory>
#include <vector>

static QStringList errors;
static void reportError(const QString& value) { errors.append(value); }
namespace log {
template<class... T> void error(const char* value, T&&...) { errors.append(QString::fromUtf8(value)); }
}
static std::wstring ToWString(const QString& s) { return s.toStdWString(); }
static QString ToQString(const std::wstring& s) { return QString::fromStdWString(s); }
struct FilesOrigin {
  std::wstring name;
  const std::wstring& getName() const { return name; }
};
struct Alternative {
  int id;
  int originID() const { return id; }
};
struct FileEntry {
  int primary;
  std::vector<Alternative> alternatives;
  int getOrigin(bool& ignored) const { ignored=false; return primary; }
  const auto& getAlternatives() const { return alternatives; }
};
using FileEntryPtr=std::shared_ptr<FileEntry>;
struct DirectoryEntry {
  std::map<std::wstring,std::shared_ptr<DirectoryEntry>> children;
  std::map<std::wstring,FileEntryPtr> files;
  std::map<int,FilesOrigin>* origins;
  DirectoryEntry* findSubDirectory(const std::wstring& name) {
    auto it=children.find(name); return it==children.end()?nullptr:it->second.get();
  }
  FileEntryPtr findFile(const std::wstring& name) {
    auto it=files.find(name);return it==files.end()?nullptr:it->second;
  }
  FilesOrigin& getOriginByID(int id) { return origins->at(id); }
};
struct FixtureUi { QTreeWidget* syncTree; };
class SyncOverwriteDialog {
 public:
  FixtureUi* ui;
  QString m_SourcePath;
  DirectoryEntry* m_DirectoryStructure;
  SyncOverwriteDialog(QString path,DirectoryEntry* root):ui(new FixtureUi{new QTreeWidget}),m_SourcePath(path),m_DirectoryStructure(root) {
    ui->syncTree->setColumnCount(2);
  }
  ~SyncOverwriteDialog() { delete ui->syncTree;delete ui; }
  static QString tr(const char* text) { return QString::fromUtf8(text); }
  void readTree(const QString&,DirectoryEntry*,QTreeWidgetItem*);
  void refresh(const QString&);
  void applyTo(QTreeWidgetItem*,const QString&,const QString&);
  void apply(const QString&);
};
#include "selected_sync.cpp"

static void leaves(QTreeWidget* tree,QTreeWidgetItem* item,QString path,std::map<QString,QComboBox*>& out) {
  for(int i=0;i<item->childCount();++i) {
    auto child=item->child(i);QString p=path.isEmpty()?child->text(0):path+"/"+child->text(0);
    if(child->childCount())leaves(tree,child,p,out);
    else if(auto combo=qobject_cast<QComboBox*>(tree->itemWidget(child,1)))out.emplace(p,combo);
  }
}
static QJsonObject existence(const QString& root,const QJsonArray& files) {
  QJsonObject result;
  for(auto raw:files) {
    auto file=raw.toObject();QString rel=file["relative"].toString();
    QJsonObject entry;
    for(auto base:QStringList{"source","mods/A","mods/B"}) {
      QString path=root+"/"+base+"/"+rel;
      entry[base]=QFileInfo::exists(path)||QFileInfo(path).isSymLink();
    }
    result[rel]=entry;
  }
  return result;
}
int main(int argc,char**argv) {
  QApplication app(argc,argv);
  if(argc!=2)return 2;
  QFile input(QString::fromUtf8(argv[1]));if(!input.open(QIODevice::ReadOnly))return 3;
  auto request=QJsonDocument::fromJson(input.readAll()).object();
  QString root=request["root"].toString();auto files=request["files"].toArray();
  std::map<int,FilesOrigin> origins{{0,{L"overwrite"}},{1,{L"A"}},{2,{L"B"}}};
  DirectoryEntry directory;directory.origins=&origins;
  for(auto raw:files) {
    auto file=raw.toObject();if(!file["entryPresent"].toBool())continue;
    auto parts=file["relative"].toString().split('/');DirectoryEntry* current=&directory;
    for(int i=0;i<parts.size()-1;++i) {
      auto key=ToWString(parts[i]);
      if(!current->children.contains(key)) {
        auto child=std::make_shared<DirectoryEntry>();child->origins=&origins;current->children[key]=child;
      }
      current=current->children[key].get();
    }
    auto entry=std::make_shared<FileEntry>();entry->primary=file["primary"].toInt();
    for(auto alt:file["alternatives"].toArray())entry->alternatives.push_back({alt.toInt()});
    current->files[ToWString(parts.last())]=entry;
  }
  SyncOverwriteDialog dialog(root+"/source",&directory);dialog.refresh(root+"/source");
  std::map<QString,QComboBox*> combos;leaves(dialog.ui->syncTree,dialog.ui->syncTree->topLevelItem(0),"",combos);
  QJsonArray choices;
  for(auto raw:files) {
    auto file=raw.toObject();auto rel=file["relative"].toString();QJsonObject result{{"relative",rel},{"widgetPresent",combos.contains(rel)}};
    if(combos.contains(rel)) {
      auto box=combos.at(rel);QJsonArray options;
      for(int i=0;i<box->count();++i)options.append(box->itemData(i,Qt::UserRole).toInt());
      result["options"]=options;result["default"]=box->currentData().toInt();
      if(!file["choice"].isNull()) {
        int index=box->findData(file["choice"].toInt());if(index<0)return 4;box->setCurrentIndex(index);
      }
      result["selected"]=box->currentData().toInt();
    }
    choices.append(result);
  }
  QJsonArray interventions;
  for(auto raw:request["removeBeforeApply"].toArray()) {
    auto path=raw.toString();if(!path.startsWith("source/")&&!path.startsWith("mods/A/"))return 5;
    interventions.append(QJsonObject{{"relative",path},{"removed",QFile::remove(root+"/"+path)}});
  }
  auto beforeApply=existence(root,files);
  dialog.apply(root+"/mods");
  QJsonArray messages;for(auto e:errors)messages.append(e);
  QJsonObject result{{"schema",1},{"qt",qVersion()},{"platformPlugin",QGuiApplication::platformName()},
    {"choices",choices},{"interventions",interventions},{"beforeApply",beforeApply},
    {"afterApply",existence(root,files)},{"errors",messages}};
  std::cout<<QJsonDocument(result).toJson(QJsonDocument::Compact).constData()<<std::endl;
}
