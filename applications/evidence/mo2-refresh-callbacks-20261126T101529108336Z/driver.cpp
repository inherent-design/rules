#include <boost/signals2.hpp>
#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>

class OrganizerCore {
public:
  enum class RefreshCallbackMode { RUN_NOW_IF_POSSIBLE = 0, FORCE_WAIT_FOR_REFRESH = 1 };
  enum class RefreshCallbackGroup { CORE = 0, INTERNAL = 1, EXTERNAL = 2 };
  bool m_DirectoryUpdate = false;
  boost::signals2::signal<void()> m_OnNextRefreshCallbacks;
  boost::signals2::connection onNextRefresh(std::function<void()> const& func,
                                          RefreshCallbackGroup group,
                                          RefreshCallbackMode mode);
  void finishCurrent() {
    // Exact three source statements, with other work/logging omitted explicitly.
    /*SOURCE_CURRENT_DRAIN*/
  }
  void finishProposed() {
    m_DirectoryUpdate = false;
    boost::signals2::signal<void()> batch;
    batch.swap(m_OnNextRefreshCallbacks);
    batch();
  }
};

/*SOURCE_REGISTRATION*/

using Group = OrganizerCore::RefreshCallbackGroup;
using Mode = OrganizerCore::RefreshCallbackMode;

void numbers(const std::vector<int>& values) {
  std::cout << '[';
  for (std::size_t i = 0; i < values.size(); ++i) {
    if (i) std::cout << ',';
    std::cout << values[i];
  }
  std::cout << ']';
}

void state(OrganizerCore& core, const std::vector<int>& trace,
           const std::map<int, boost::signals2::connection>& connections) {
  std::cout << "{\"trace\":";
  numbers(trace);
  std::vector<int> connected;
  for (const auto& [event, connection] : connections)
    if (connection.connected()) connected.push_back(event);
  std::cout << ",\"connected\":";
  numbers(connected);
  std::cout << ",\"pending\":" << core.m_OnNextRefreshCallbacks.num_slots() << '}';
}

void run(const std::string& name, bool proposed) {
  OrganizerCore core;
  std::vector<int> trace;
  std::map<int, boost::signals2::connection> connections;
  core.m_DirectoryUpdate = name != "immediate";
  auto record = [&](int event, Group group, bool force, std::function<void()> action) {
    connections[event] = core.onNextRefresh(
        action, group, force ? Mode::FORCE_WAIT_FOR_REFRESH : Mode::RUN_NOW_IF_POSSIBLE);
  };
  if (name == "groups") {
    record(3, Group::EXTERNAL, true, [&] { trace.push_back(3); });
    record(1, Group::CORE, true, [&] { trace.push_back(1); });
    record(2, Group::INTERNAL, true, [&] { trace.push_back(2); });
  } else {
    record(1, Group::CORE, name != "immediate", [&] {
      trace.push_back(1);
      if (name == "reentrant-forced" || name == "reentrant-immediate") {
        record(2, Group::EXTERNAL, name == "reentrant-forced", [&] { trace.push_back(2); });
      }
    });
  }
  std::cout << "{\"case\":\"" << name << "\",\"policy\":\""
            << (proposed ? "detached-batch" : "current") << "\",\"before\":";
  state(core, trace, connections);
  if (proposed) core.finishProposed(); else core.finishCurrent();
  std::cout << ",\"first\":";
  state(core, trace, connections);
  if (proposed) core.finishProposed(); else core.finishCurrent();
  std::cout << ",\"second\":";
  state(core, trace, connections);
  std::cout << "}\n";
}

int main() {
  for (const std::string name : {"queued", "immediate", "reentrant-forced", "reentrant-immediate", "groups"}) {
    run(name, false);
    run(name, true);
  }
}
