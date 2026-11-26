# Notification definitions and timer ownership

Periodic notifications connect resource definitions to selection, host timers, queued UI work, and client lifetime. The [source ledger](notification-timer-sources.json) follows selected Java Edition 1.21.1 and 26.3 consumer edges. The [separate host study](../java/TIMERS.md) observes authored JDK Timer calls on Java 17, 21, and 25. No Minecraft notification manager, selector, codec, callback, toast, or game reload is executed by that fixture.

## Definition and operational boundaries

The earlier [breadth linework](BREADTH-LINEWORK.md) records group-to-list definitions with delay, period, title, and message fields. In the two source views inspected here, delay defaults to zero, period is a required long, and title/message are required strings. Those codec declarations are not yet native invalid-input comparisons or a complete definition-language proof.

The reviewed manager selects matching groups and flattens their lists. An empty selected list stops the existing timer. A selected zero period logs through the consumer's helper and stops it. Other preparations compute a minimum initial delay and a GCD-based period, then attempt fixed-rate scheduling. Negative values, arithmetic, argument exceptions, and actual selector eligibility remain distinct obligations; a nonzero period is not a complete host scheduling precondition.

Each inspected original client constructs a retained final manager field, registers that same object as a resource reload listener, and calls its close during client close. Original bytecode confirms those edges in both clients. The manager's selected `stopTimer` body cancels a present timer without nulling its field. Its apply body creates a timer only when that field is null, and otherwise retains that timer while replacing/resetting its task. The [source checker](notification_timer_sources_check.py) binds eight original class identities, the two reviewed source views, and private disassembly receipts. Ordinary CI checks attribution only; its owner-only `--private` mode rechecks the retained inputs without running Java.

The JDK host witness establishes that a canceled timer refuses a fresh task. Combined with these source clauses, a later scheduling attempt on a retained canceled timer is a **conditional consistency concern**. Actual selection changes, resource contents, application sequencing, and failure handling have not been exercised through this manager, so this is not a demonstrated Minecraft defect. The original notification task accesses the client during initialization and queues a toast action when run; those dependencies prevent treating its body as a pure timer example.

## Preserve semantics; qualify changes independently

Keep group selection, definition admission, scheduling admission, callback execution, queued UI publication, and client closure separate. An empty result after a read/decode failure can have a scheduling effect; it should not be labeled a harmless absence without the consuming contract. Task reset, timer cancellation, and queued toast retirement require different evidence.

One possible design is to make terminal timer state explicit and create a fresh timer when a later admitted preparation needs it. Another is to document a manager as single-use and recreate the owning manager at the appropriate resource boundary. Both change lifetime behavior and require review of listener registration, callback ownership, stale queued actions, and error reporting. Simply nulling a field does not retire an already-running callback or a queued UI action. No option is adopted here.

Diagnostics should name the affected notification resource/group, whether decoding or scheduling failed, which prior schedule remains or was canceled, and whether follow-up UI work can still publish. Human and machine reports should preserve partial state and the original cause. Retry guidance must not assume a canceled Timer or TimerTask object can be reused.

The component remains source inspection plus an independently qualified host API witness. Full codecs, malformed values, selection/user-region policy, preparation failure, repeated reloads, task timing, saturation/overflow, real callbacks, toast lifetime, accessibility, provider coexistence, other client versions, and native Windows/Linux qualification remain pending. No production fix, mod, provider installation, pack pin, account read, or rollout is selected.
