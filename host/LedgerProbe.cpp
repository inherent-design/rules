#include "runtime/ResourceLedger.hpp"
#include <iostream>
using namespace playground::runtime;

int main() {
    ResourceLedger ledger({8, 8, 6, 6});
    auto recording = ledger.reserve(MemoryClass::GPU, ResourceKind::Target, 6, "recording");
    auto published = recording;
    recording.reset();  // The one operation retired. A second owner can keep it charged.
    for (const bool release : {false, true}) {
        if (release) published.reset();
        const auto charged = ledger.snapshot().memory[1].bytes;
        bool fits = false;
        try {
            auto candidate = ledger.reserve(MemoryClass::GPU, ResourceKind::Target, 6, "next");
            fits = true;
        } catch (const ResourcePressure&) {}
        if (charged != (release ? 0u : 6u)) return 1;
        std::cout << R"({"v":1,"surface":"reuse","case":")" << (release ? "released" : "retained")
                  << R"(","observed":{"retired":true,"sole_pool_owner":)" << (release ? "true" : "false")
                  << R"(,"no_more_uses":true},"outcome":{"decision":)" << fits
                  << R"(,"charged_bytes":)" << charged << "}}\n";
    }
}
