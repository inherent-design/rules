// Runs the upstream header directly. Sizes are synthetic bytes.
#include "runtime/ResourceLedger.hpp"
#include <cassert>
using namespace playground::runtime;
int main() {
    ResourceLedger ledger({8, 8, 6, 5});
    auto held = ledger.reserve(MemoryClass::GPU, ResourceKind::Target, 6, "target");
    try {
        ledger.reserve(MemoryClass::GPU, ResourceKind::Target, 1, "overflow");
        return 1;
    } catch (const ResourcePressure& pressure) {
        assert(pressure.used == 6 && pressure.limit == 6);
    }
    auto child = ledger.splitReservation(held, 2);
    assert(child->bytes() == 2 && held->bytes() == 4);
    assert(ledger.snapshot().memory[1].bytes == 6);
    child.reset();
    assert(ledger.snapshot().memory[1].bytes == 4);
    held.reset();
    assert(ledger.snapshot().memory[1].bytes == 0);
}
