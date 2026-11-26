// Study adapter only. Upstream GPL/Apache-noticed method excerpts are inserted
// into the private generated translation unit from checksum-pinned sources.
#include <QCoreApplication>
#include <QAbstractItemModel>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMimeData>
#include <QUrl>
#include <filesystem>
#include <tuple>
#include <utime.h>
#include <stdexcept>

namespace fs=std::filesystem;
namespace StringUtils {
// ASCII fixture path conversion and unused display-size label only.
std::string toStdString(const QString& value){return value.toStdString();}
QString humanReadableFileSize(qint64 size,bool){return QString::number(size);}
}
namespace FS {
// @FS_EXCERPTS@
int unsupportedFolderCopies=0;
struct CopyBoundary {bool operator()(){++unsupportedFolderCopies;throw std::runtime_error("Unadmitted folder-copy branch");}};
CopyBoundary copy(const QString&,const QString&){return {};}
}

enum class ResourceType {UNKNOWN,ZIPFILE,SINGLEFILE,FOLDER,LITEMOD};
class Resource:public QObject {
 public:
  Resource(QFileInfo);
  void setFile(QFileInfo);
  void parseFile();
  // @RESOURCE_INLINE@
  QFileInfo m_file_info;
  ResourceType m_type=ResourceType::UNKNOWN;
  QString m_internal_id,m_name,m_size_str;
  qint64 m_size_info=0;
  uintmax_t m_hardLinkCount=0;
  bool m_enabled=true;
  QDateTime m_changed_date_time;
};
// @RESOURCE_EXCERPTS@

class ResourceFolderModel:public QObject {
 public:
  explicit ResourceFolderModel(QDir dir,bool watching=true,bool updateResult=true):m_dir(dir),m_is_watching(watching),updateResult(updateResult){}
  bool installResourceOriginal(QString);
  bool installResource(QString path){bool result=installResourceOriginal(path);calls.append(QJsonObject{{"path",path},{"returned",result}});return result;}
  bool dropMimeData(const QMimeData*,Qt::DropAction,int,int,const QModelIndex&);
  Qt::DropActions supportedDropActions()const{return Qt::CopyAction;}
  bool update(){++updateCalls;return updateResult;}
  QDir m_dir;
  bool m_is_watching,updateResult;
  int updateCalls=0;
  QJsonArray calls;
};
// @INSTALL_EXCERPT@
// @DROP_EXCERPT@

QJsonObject entry(QString path){
  QFileInfo info(path);
  QJsonObject value{{"exists",info.exists()},{"isFile",info.isFile()},{"isDir",info.isDir()},{"isSymLink",info.isSymLink()}};
  if(info.isSymLink())value.insert("linkTarget",info.symLinkTarget());
  if(info.isFile()&&!info.isSymLink()){
    QFile file(path);if(!file.open(QIODevice::ReadOnly))throw std::runtime_error("Owned read failed");
    value.insert("text",QString::fromUtf8(file.readAll()));
  }
  return value;
}
QJsonObject snapshot(const QJsonObject& row){
  QJsonObject result;
  for(auto p:row["observe"].toArray())result.insert(p.toString(),entry(p.toString()));
  return result;
}
int main(int argc,char**argv){
  QCoreApplication app(argc,argv);
  if(argc!=2)return 2;
  QFile input(QString::fromUtf8(argv[1]));if(!input.open(QIODevice::ReadOnly))return 2;
  auto request=QJsonDocument::fromJson(input.readAll()).object();
  if(request["schema"].toInt()!=1||!QDir::setCurrent(request["work"].toString()))return 2;
  for(auto item:request["cases"].toArray()){
    auto row=item.toObject();ResourceFolderModel model(QDir(row["destination"].toString()),row["watching"].toBool(),row["updateResult"].toBool());
    auto before=snapshot(row);bool result=false;
    if(row["operation"]=="install")result=model.installResource(row["source"].toString());
    else if(row["operation"]=="drop"){
      QMimeData data;QList<QUrl> urls;
      for(auto u:row["urls"].toArray())urls.append(QUrl(u.toString()));
      data.setUrls(urls);result=model.dropMimeData(&data,Qt::CopyAction,0,0,QModelIndex());
    }else return 2;
    QJsonObject record{{"id",row["id"]},{"returned",result},{"before",before},{"after",snapshot(row)},
                       {"installCalls",model.calls},{"updateCalls",model.updateCalls},{"unsupportedFolderCopies",FS::unsupportedFolderCopies}};
    auto line=QJsonDocument(record).toJson(QJsonDocument::Compact);fwrite(line.data(),1,size_t(line.size()),stdout);fputc('\n',stdout);fflush(stdout);
  }
}
