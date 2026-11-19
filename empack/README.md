# empack

This projection follows the primary `empack` checkout's Rust engine. The author schema, lock schema and native release schema carry distinct identities. An authored requirement can have several provider candidates; only a resolved lock binds an exact selection. Preserve the distinction between accepted content, an artifact built from it, the installed baseline and bytes currently observed on disk.

| Boundary | Decision and effect |
| --- | --- |
| Terminal → capability snapshot | Observe stderr TTY, console library color policy, COLORTERM, locale and width. Never disables color, Always chooses truecolor or ANSI256, Auto follows the console decision. Non-TTY forces ASCII independently of color. The first present locale wins even when empty. A non-UTF locale can still use an OS charset fallback. |
| Request → permit | Check closure, then all dimensions for impossible requests, then all for current pressure. Only Busy can wait for capacity. Cancellation while waiting creates no permit. Jobs, estimated memory, scratch and open files are independently charged. A retained output can receive part of an existing permit without another charge. |
| Author intent → lock → content | Import adapters normalize external IDs, sides, loader policy and paths. Sync reconciles the lock; update deliberately reselects. Acquired content needs exact integrity verification and bounded extraction. A successful capacity estimate cannot prove that delivered bytes fit adapter limits. |
| Verified plan → publication | Stage outside the visible result, check expected file identities, acquire publication ownership and journal the transition. Unfinished publication constrains subsequent operations until recovery. A newly planned rollback is distinct from finishing an interrupted commit. |
| Signed channel → selected release → instance | Verify channel trust, sequence, target and exact release. Compare installed baseline, observed path and incoming policy. Preserve player state, surface managed conflicts, and bind explicit resolutions to observations. A rollback can change managed content while leaving gameplay history intact. |
| Process plan → host runtime | Captured jobs and inherited foreground terminals have distinct ownership. On Unix, capture controlling group/settings, transfer before child exec, restore when done. Terminal display capability alone cannot authorize process-group transfer. |

[Model.lean](Model.lean) runs color/Unicode decisions and a four-resource classifier, proves refusal cannot partially charge an envelope and proves identical normalized observations yield identical display traces. Its single-file update example expresses a conservative ownership policy. Actual instance decisions also distinguish directories, file policies, platform permissions, explicit overrides and missing paths. [Source pins](../sources.json) identify the engine code.

After `scripts/check`, use the same Lean installation and `LEAN_PATH=.build` from the repository root:

```sh
python3 empack/TerminalProbe.py --fixture empack/redirected.json | LEAN_PATH=.build lean --run empack/Run.lean always
python3 empack/TerminalProbe.py --colors-enabled no | LEAN_PATH=.build lean --run empack/Run.lean auto
```

The example interpreter samples Python's preferred encoding and uses width 80 when terminal size is unavailable. For exact empack equivalence, feed the Rust console library's decision and effective OS charset probe into the normalized fixture. Replaying the redirected fixture with Always produces truecolor and ASCII. The distinction is observable even on a host with no terminal.
