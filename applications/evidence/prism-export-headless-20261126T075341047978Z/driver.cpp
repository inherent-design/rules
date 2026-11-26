// Fixture interfaces and observations only. Original method bodies are
// inserted privately from checksum-pinned GPL/Apache Prism sources.
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QHash>
#include <archive.h>
#include <archive_entry.h>
#include <sys/stat.h>
#include <clocale>
#include <functional>
#include <iostream>
#include <memory>
#include <optional>

namespace MMCZip {
using FilterFileFunction = std::function<bool(const QFileInfo&)>;
class ArchiveWriter {
public:
    ArchiveWriter(const QString&);
    virtual ~ArchiveWriter();
    bool open();
    bool close();
    bool addFile(const QString&, const QString&);
    bool addFile(const QString&, const QByteArray&);
private:
    struct archive* m_archive = nullptr;
    QString m_filename;
    QString m_format = "zip";
};
// @WRITER@
// @COLLECTOR@
struct FutureWitness {
    bool canceled = false;
    bool isCanceled() const { return canceled; }
};
class ExportHarness {
public:
    using ZipResult = std::optional<QString>;
    ExportHarness(const QJsonObject& r, const QFileInfoList& files)
        : m_output(r["output"].toString()), m_dir(r["root"].toString()), m_files(files),
          m_destinationPrefix(r["prefix"].toString()), m_followSymlinks(r["follow"].toBool())
    {
        m_progressTotal = files.length(); // Supplied by executeTask in the real caller.
        m_buildZipFuture.canceled = r["canceled"].toBool();
        for (auto v : r["excludeAtWrite"].toArray()) m_excludeFiles.append(v.toString());
        const auto extra = r["extra"].toObject();
        for (auto i = extra.begin(); i != extra.end(); ++i) m_extraFiles.insert(i.key(), i.value().toString().toUtf8());
    }
    ZipResult exportZip();
    QJsonArray statuses;
    void setStatus(const QString& s) { statuses.append(s); }
    void setProgress(qint64 value, qint64 total) { m_progress = value; m_progressTotal = total; }
    static QString tr(const char* text) { return QString::fromUtf8(text); } // No localization in fixture.
private:
    ArchiveWriter m_output;
    QDir m_dir;
    QFileInfoList m_files;
    QString m_destinationPrefix;
    bool m_followSymlinks;
    QStringList m_excludeFiles;
    QHash<QString,QByteArray> m_extraFiles;
    FutureWitness m_buildZipFuture; // Controlled branch witness; no QFuture/thread claim.
    qint64 m_progress = 0;
    qint64 m_progressTotal = 0;
};
// @EXPORT@
}

int main(int argc, char** argv) {
    QCoreApplication app(argc,argv);
    if (argc != 2 || !std::setlocale(LC_ALL,"en_US.UTF-8")) return 2;
    QFile input(QString::fromLocal8Bit(argv[1]));
    if (!input.open(QFile::ReadOnly)) return 2;
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(input.readAll(),&error);
    if (error.error != QJsonParseError::NoError || document["schema"].toInt()!=1) return 2;
    std::cout << QJsonDocument(QJsonObject{{"kind","backend"},{"qt",qVersion()},{"archive",archive_version_string()}}).toJson(QJsonDocument::Compact).constData() << '\n';
    for (auto item : document["cases"].toArray()) {
        const auto r=item.toObject(); const QDir root(r["root"].toString());
        QStringList excluded;for (auto p:r["excludeAtCollect"].toArray()) excluded.append(p.toString());
        QJsonArray calls; MMCZip::FilterFileFunction filter;
        if (r["filter"].toBool()) filter=[&](const QFileInfo& f){ const auto relative=root.relativeFilePath(f.absoluteFilePath()); calls.append(relative); return excluded.contains(relative); };
        QFileInfoList files; const bool collected=MMCZip::collectFileListRecursively(root.path(),nullptr,&files,filter);
        QJsonArray listed;for (const auto& file:files) listed.append(root.relativeFilePath(file.absoluteFilePath()));
        if (r.contains("removeAfterCollect")) {
            const auto path=root.filePath(r["removeAfterCollect"].toString());
            if (!QFile::remove(path)) return 3; // Only a named owned fixture file.
        }
        std::optional<QString> result; QJsonArray statuses;
        if (collected) {
            MMCZip::ExportHarness writer(r,files);result=writer.exportZip();statuses=writer.statuses;
        }
        // The original writer destructor has now finalized any partial ZIP.
        QJsonObject row{{"id",r["id"]},{"collected",collected},{"files",listed},{"filterCalls",calls},
                        {"canceledWitness",r["canceled"]},{"methodError",result?QJsonValue(*result):QJsonValue(QJsonValue::Null)},
                        {"methodInvoked",collected},{"statuses",statuses},{"outputExists",QFileInfo::exists(r["output"].toString())}};
        std::cout << QJsonDocument(row).toJson(QJsonDocument::Compact).constData() << '\n';
    }
}
