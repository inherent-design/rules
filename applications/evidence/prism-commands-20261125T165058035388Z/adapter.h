// Research declarations around unchanged Prism hooks and real LoggedProcess/Qt.
// Instance/environment construction and Task publication are explicit adapters.
#pragma once
#include <QObject>
#include <QProcessEnvironment>
#include <QStringList>
#include <QVariant>
#include "LoggedProcess.h"

QString expandVariables(const QString&, QProcessEnvironment);
struct FixtureInstance {
    QString pre, post, wrapper;
    QProcessEnvironment environment;
    QString getPreLaunchCommand() const { return pre; }
    QString getPostExitCommand() const { return post; }
    QString getWrapperCommand() const { return wrapper; }
    QProcessEnvironment createEnvironment() const { return environment; }
    QProcessEnvironment createLaunchEnvironment() const { return environment; }
};
class LaunchTask : public QObject {
 public:
    FixtureInstance value;
    QString javaPath;
    QStringList gameArgs;
    FixtureInstance* instance() { return &value; }
    const FixtureInstance* instance() const { return &value; }
    QString substituteVariables(QString& cmd, bool isLaunch = false) const;
};
class LaunchStep : public QObject {
    Q_OBJECT
 public:
    explicit LaunchStep(LaunchTask* parent) : QObject(parent), m_parent(parent) {}
    virtual void executeTask() = 0;
    virtual bool abort() { return false; }
    virtual bool canAbort() const { return false; }
    void emitSucceeded() { emit terminal(true, QString()); }
    void emitFailed(QString reason) { emit terminal(false, reason); }
 signals:
    void logLine(QString line, MessageLevel level);
    void terminal(bool successful, QString reason);
 public slots:
    void logLines(QStringList lines, MessageLevel level) {
        for (const auto& line : lines) emit logLine(line, level);
    }
 protected:
    LaunchTask* m_parent;
};
