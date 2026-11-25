// Research adapters around two unchanged ProcessRunner policy methods.
// No Windows API, Qt event loop, real child, lock UI, refresh, or writer runs.
#include <iostream>
#include <string>
#include <vector>

struct Observed {
  int waitCalls = 0, lockCalls = 0, afterCalls = 0, connectCalls = 0, eventCalls = 0;
  bool nullSession = false;
} observed;
namespace log { template<class... T> void debug(const char*, T...) {} }
namespace Qt { enum class ConnectionType { QueuedConnection }; }
struct QObject {
  template<class... T> static void connect(T...) { ++observed.connectCalls; }
};
struct QEventLoop {
  void quit() {}
  void exec() { ++observed.eventCalls; }
};
struct UILocker {
  enum Reasons { NoReason, LockUI, OutputRequired, PreventExit };
  struct Session {};
};
struct Settings {
  bool enabled = true;
  Settings& interface() { return *this; }
  bool lockGUI() const { return enabled; }
};
struct OrganizerCore {
  Settings value;
  Settings& settings() { return value; }
  void directoryStructureReady() {}
  void afterRun(int, int) { ++observed.afterCalls; }
};
struct Flags {
  unsigned value;
  bool testFlag(unsigned bit) const { return (value & bit) == bit; }
  unsigned operator&(unsigned bit) const { return value & bit; }
};
struct Handle { int get() const { return 42; } };
class ProcessRunner {
 public:
  enum Results { Running = 1, Completed, Error, Cancelled, ForceUnlocked };
  enum WaitFlag { NoFlags = 0, TriggerRefresh = 1, ForceWait = 2, WaitForRefresh = 4 };
  OrganizerCore m_core;
  struct { bool hooked; int binary = 0; } m_sp;
  Flags m_waitFlags;
  UILocker::Reasons m_lockReason;
  Handle m_handle;
  int m_exitCode = -1;
  Results fixtureWaitResult;
  template<class F> void withLock(F fn) {
    ++observed.lockCalls;
    UILocker::Session session;
    fn(session);
  }
  bool shouldRefresh(Results r) const;
  Results postRun();
};
ProcessRunner::Results fixtureResult;
ProcessRunner::Results waitForProcess(int, int*, UILocker::Session* session) {
  ++observed.waitCalls;
  observed.nullSession = session == nullptr;
  return fixtureResult;
}

// @@SELECTED_METHODS@@

int main() {
  std::string id;
  unsigned flags;
  int hooked, reason, lockEnabled, result;
  while (std::cin >> id >> hooked >> flags >> reason >> lockEnabled >> result) {
    observed = {};
    ProcessRunner runner;
    runner.m_sp.hooked = hooked;
    runner.m_waitFlags.value = flags;
    runner.m_lockReason = static_cast<UILocker::Reasons>(reason);
    runner.m_core.value.enabled = lockEnabled;
    fixtureResult = static_cast<ProcessRunner::Results>(result);
    const bool admittedRefresh = runner.shouldRefresh(fixtureResult);
    const auto returned = runner.postRun();
    std::cout << id << ' ' << returned << ' ' << runner.m_lockReason << ' '
              << observed.waitCalls << ' ' << observed.lockCalls << ' '
              << observed.nullSession << ' ' << observed.afterCalls << ' '
              << observed.connectCalls << ' ' << observed.eventCalls << ' '
              << admittedRefresh << '\n';
  }
}
