# Coverage and boundaries

The native profile is macOS 26.7.1 arm64. Tool identities are npm 11.20.0, pnpm 12.21.0, Yarn Berry 4.19.0, empack 0.8.8-beta, and Node 26.13.1. The empirical scope is a small local dependency graph, not an online modpack solver or gameplay test.

## Journeys

| Journey | npm | pnpm | Yarn Berry | empack |
| --- | --- | --- | --- | --- |
| Help and discovery | Top help exits 1 and prints usage | Help exits 0 | Help exits 0 | Help exits 0; author/install/publish groups |
| Inspect | `pkg get --json` | `list --json` | `info --json` needs a valid lock | Document/recorded `check --json`, `status --json` |
| Preview or resolution | Install dry run preserves project files, writes logs/caches | Dry run after default gate-created install preserves project files | `update-lockfile` writes lock/cache and skips link | `sync` and local-add dry runs preserve project/durable state |
| Apply and repeat | Local install; repeat preserves project snapshot | Local install; repeat updates install metadata | Local install; repeat preserves project snapshot | Empty sync; repeat preserves project but updates operation records |
| Add/remove | Local add and uninstall | Local add and remove | Local add and remove | Local resource-pack add and remove, with previews |
| Refusal | Unknown command; `ci` lock disagreement | Unknown-name fallback installs before refusal; frozen lock mismatch | Unknown command; immutable mismatch; CI defaults immutable | Invalid command, malformed lock, missing supplied file, outside-root supplied path |
| Required input | Explicit fixture script: pipe EOF vs supplied TTY input | Same; configured pre-run prompt additionally tested | Same | Confirmation declined, unavailable input, and cancellation at confirmation |
| Failure with effects | Explicit script writes, then exits 7 | Same, plus installed-before-refusal example | Same | Save-phase cancellation completed the operation; missing-source independent-add refused before any partial apply |
| Interruption | SIGINT after marker; marker remains | SIGINT after marker; marker remains | Script runner returns 129 after signal; marker remains | Early cancellation returns 130 without publication; late cancellation returns actual completed status 0 |
| Recovery/retry | Inspect snapshots, then reconcile install; script markers remain | Same | Same | Inspect status/recover/pending after cancellation; restore a deliberately malformed lock's exact saved bytes, then check |

For the three package managers, the fixture scripts are **explicit `run` requests**, not dependency install hooks. These observations establish that an external script can complete effects before failure/interruption; they do not qualify install-hook approval policy. Package managers' normal install reconciliation does not roll back arbitrary script effects.

For empack, `recover` inspection reported no interrupted publication in the observed cancellation cases. A genuine crash during a partially applied native journal, `recover finish/restore`, process-retirement uncertainty, signed updates, live publication, and Minecraft launches were not exercised here. Restoring saved fixture bytes is not a claim that native journal recovery was tested. The missing-input independent-add case does not establish partial-success behavior.

## Stream and environment profiles

| Profile | stdin / stdout / stderr | What it establishes |
| --- | --- | --- |
| Parent fixture, both input modes | pipe or TTY / pipe / TTY | Stream capabilities are independent; diagnostics/progress need not contaminate result stdout |
| Lifecycle, both input modes | pipe or TTY / pipe / TTY | EOF vs supplied input, explicit script failure and interruption effects |
| Narrow | TTY / pipe / TTY; 28 columns | Fixed narrow rendering surface and usable empack confirmation with result redirection |
| CI | pipe / pipe / pipe; `CI=1`, `NO_COLOR=1`, `TERM=dumb` | Noninteractive refusal, structured output, and Yarn's cold immutable refusal |
| Input-only TTY | TTY / pipe / pipe | empack refuses approval without a stderr terminal; pnpm prompt gate exits 1 without captured explanation in this non-controlling profile |
| C locale, terminal | TTY / TTY / TTY; 28 columns | Local Unicode source values under this runtime; channels deliberately merged, not a JSON-stdout test |
| Explicit styling | pipe / pipe / TTY; color enabled/disabled by tool-supported config | Structured result bytes inspected separately from display styling |

The private PTY is not a controlling terminal, shell job-control environment, human operator, or screen reader. Tests verify its width and independent descriptors against child-observed values. Input injection is fixture action, not human consent. Full-terminal merged output containing progress does not imply stdout contamination.

File effects are sampled net changes in regular-file bytes/modes and symlink targets under the isolated work root. Directory metadata, timestamps, inode changes, transient writes, and external paths are not measured. “Unchanged” below those premises is not proof that no write syscall occurred.

Unrun: Windows/Linux application journeys, real terminal resizing, live human keyboard navigation, screen-reader acceptance, network interruption, concurrent project writers, malicious lifecycle scripts, and a full package/version update graph. The parent host study's platform observations do not qualify these application behaviors on another platform.

## Run index

| Run | Role |
| --- | --- |
| `20261123T224431994122Z` | First breadth; qualification exclusions retained |
| `20261123T224740171810Z`, `20261123T224805512573Z` | Corrected breadth, pipe and TTY input |
| `20261123T225119949338Z-journeys` | Lifecycle discovery; cold offline/self-management and invalid-form limits retained |
| `20261123T225211680511Z-journeys` | Corrected piped-input package lifecycles and empack local addition |
| `20261123T225322018614Z-journeys` | TTY-input lifecycles, empack removal, late cancellation, and inspection |
| `20261123T225424382629Z-journeys` | Narrow profile |
| `20261123T225425406843Z-journeys` | Fully piped CI profile |
| `20261123T225426550365Z-journeys` | Input-only TTY profile |
| `20261123T225427626218Z-journeys` | C-locale, fully terminal profile |
| `20261123T230015174972Z-journeys` | empack early cancellation and missing-source independent-add refusal |

The explicit styling run is named in `claims.json`. Run receipts retain exact arguments, configured profile, tool pins, outcomes, and source hashes. Do not combine earlier successful cases with later changes and call them one tested binary/source tree.
