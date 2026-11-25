// All real children are this same disposable executable; no game/Java/shell runs.
#include "commands_adapter.h"
#include "PreLaunchCommand.h"
#include "PostLaunchCommand.h"
#include "Commandline.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QTextStream>
#include <QThread>
#include <QTimer>

// @@VARIABLE_FUNCTIONS@@

class WrapperProbe : public LaunchStep {
 public:
    explicit WrapperProbe(LaunchTask* parent) : LaunchStep(parent) {
        m_process.setProcessEnvironment(parent->instance()->createLaunchEnvironment());
        QObject::connect(&m_process, &LoggedProcess::log, this, &LaunchStep::logLines);
        // Completion is a research adapter, not LauncherPartLaunch's game protocol.
        QObject::connect(&m_process, &LoggedProcess::stateChanged, this, [this](LoggedProcess::State state) {
            if (state == LoggedProcess::Finished) {
                if (m_process.exitCode() == 0) emitSucceeded();
                else emitFailed("adapter child exit");
            } else if (state == LoggedProcess::FailedToStart || state == LoggedProcess::Aborted || state == LoggedProcess::Crashed) {
                emitFailed("adapter child failure");
            }
        });
    }
    void setWorkingDirectory(const QString& wd) { m_process.setWorkingDirectory(wd); }
    void executeTask() override {
        auto instance = m_parent->instance();
        auto javaPath = m_parent->javaPath;
        auto args = m_parent->gameArgs;
        // @@WRAPPER_BLOCK@@
    }
    LoggedProcess m_process;
};

void output(const QJsonObject& row) {
    QTextStream out(stdout);
    out << QJsonDocument(row).toJson(QJsonDocument::Compact) << '\n';
    out.flush();
}
int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    const auto values = app.arguments();
    if (values.size() > 1 && (values[1] == "child" || values[1] == "wrapper-child")) {
        // Own-file witness is independent of LoggedProcess's line decoder.
        const QString witness = qEnvironmentVariable("RULES_WITNESS");
        QJsonObject row{{"pid", qint64(QCoreApplication::applicationPid())}, {"cwd", QDir::currentPath()},
            {"argv", QJsonArray::fromStringList(values.mid(1))}, {"value", qEnvironmentVariable("RULES_VALUE")}};
        QFile file(witness);
        if (!file.open(QIODevice::WriteOnly)) return 88;
        file.write(QJsonDocument(row).toJson(QJsonDocument::Compact));
        file.close();
        QTextStream(stdout) << "child-output Ω 日本\n" << Qt::flush;
        if (values.contains("hold")) {
            // Parent aborts the real process after observing the witness.
            for (int i = 0; i < 500; ++i) QThread::msleep(10);
            return 89;
        }
        return values.contains("exit7") ? 7 : 0;
    }
    if (values.size() != 2) return 90;
    QFile input(values[1]);
    if (!input.open(QIODevice::ReadOnly)) return 91;
    const auto request = QJsonDocument::fromJson(input.readAll()).object();
    const auto mode = request["mode"].toString();
    const auto cwd = request["cwd"].toString();
    const auto witness = request["witness"].toString();
    const auto command = request["command"].toString();
    LaunchTask task;
    task.value.pre = command; task.value.post = command; task.value.wrapper = command;
    task.javaPath = QCoreApplication::applicationFilePath();
    task.gameArgs = {"child", "success", "original game argument", "Ω 日本"};
    const auto environment = request["environment"].toObject();
    for (auto it = environment.begin(); it != environment.end(); ++it) task.value.environment.insert(it.key(), it.value().toString());
    task.value.environment.insert("RULES_WITNESS", witness);
    task.value.environment.insert("PROBE", QCoreApplication::applicationFilePath());
    QString expanded = task.substituteVariables(task.value.pre);
    const QStringList hookArgs = QProcess::splitCommand(expanded);
    const QStringList wrapperArgs = Commandline::splitArgs(expanded);
    const bool noDebug =
#ifdef QT_NO_DEBUG
        true;
#else
        false;
#endif
    output({{"phase", "before"}, {"mode", mode}, {"raw", command}, {"expanded", expanded},
            {"qtVersion", qVersion()}, {"qtNoDebug", noDebug},
            {"hookArgs", QJsonArray::fromStringList(hookArgs)}, {"wrapperArgs", QJsonArray::fromStringList(wrapperArgs)}});
    if (mode == "parse") return 0;
    LaunchStep* step;
    if (mode == "pre") {
        auto p = new PreLaunchCommand(&task); p->setWorkingDirectory(cwd); step = p;
    } else if (mode == "post") {
        auto p = new PostLaunchCommand(&task); p->setWorkingDirectory(cwd); step = p;
    } else {
        auto p = new WrapperProbe(&task); p->setWorkingDirectory(cwd); step = p;
    }
    QJsonArray logs;
    bool terminal = false, success = false, timedOut = false, abortCalled = false, abortAccepted = false;
    QString reason;
    QObject::connect(step, &LaunchStep::logLine, &app, [&](QString text, MessageLevel level) {
        logs.append(QJsonObject{{"text", text}, {"level", int(level)}});
    });
    QObject::connect(step, &LaunchStep::terminal, &app, [&](bool good, QString why) {
        terminal = true; success = good; reason = why;
        QTimer::singleShot(0, &app, &QCoreApplication::quit);
    });
    QTimer abortPoll;
    if (request["abort"].toBool()) {
        QObject::connect(&abortPoll, &QTimer::timeout, &app, [&] {
            if (!QFile::exists(witness)) return;
            abortPoll.stop(); abortCalled = true; abortAccepted = step->abort();
        });
        abortPoll.start(5);
    }
    QTimer::singleShot(6000, &app, [&] {
        timedOut = true; step->abort(); app.quit();
    });
    QTimer::singleShot(0, step, [step] { step->executeTask(); });
    app.exec();
    output({{"phase", "after"}, {"mode", mode}, {"terminal", terminal}, {"successful", success},
            {"reason", reason}, {"logs", logs}, {"timedOut", timedOut},
            {"abortCalled", abortCalled}, {"abortAccepted", abortAccepted}});
    return timedOut ? 92 : 0;
}
