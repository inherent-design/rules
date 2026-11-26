# Released runtime migration and exact-pin policy

The released empack 0.8.8-beta executable preserves a target-compatible authored exact pin, refuses an incompatible one in preview and application, and reselects only after explicit unpinning in this fixture. This adds an actual CLI/engine boundary to the earlier [supplied-core comparison](../author-transitions/README.md). It is provider-metadata compatibility, not proof that Minecraft or the mod starts successfully.

The [collector](probe.py) ran twelve operations across two disposable projects, each with its own state and cache. The [receipt](../../evidence/empack-migration-flow-20261126T054446879342Z/receipt.json), [commands and entry images](../../evidence/empack-migration-flow-20261126T054446879342Z/commands.json), and independently sampled [metadata](../../evidence/empack-migration-flow-20261126T054446879342Z/metadata.json) retain the observations. The native executable's SHA256 is `99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f`. No engine build, artifact export, channel, Java process, personal pack, or host installation change was requested.

## Two target-validation branches

Both projects start at Minecraft 1.21.1, Fabric 0.16.0, and preferred Java 21, with one explicit FerriteCore root (`uXXizFIs`). The requested target is **Minecraft 1.21**, deliberately an older game release. This tests an explicit runtime change; it does not test chronological upgrade policy or world downgrading.

The independently sampled Modrinth record `wmIZ4wP4` / 7.0.0-fabric lists both game versions. Record `sOzRw3CG` / 7.0.3-fabric lists only 1.21.1. Both sampled records list Fabric and no required mod dependencies. The Fabric service separately lists loader 0.16.0 for target 1.21. Samples were taken before the native run; they are not intercepted native responses or a guarantee of provider correctness.

| Branch and action | Observed result |
| --- | --- |
| Compatible pin: sync | First lock records `wmIZ4wP4`; no mod payload is materialized. |
| Compatible pin: structured preview | Ready document changes for target 1.21; the exact selection remains `wmIZ4wP4`. The report retains its reference and says no materialization or native publication occurred. |
| Compatible pin: application | Author and lock documents change to the target runtime. The authored pin remains, and changed document bytes/lengths match the earlier preview. |
| Incompatible pin: sync | Source-runtime lock records `sOzRw3CG`, with its authored exact pin. |
| Incompatible pin: preview and application | Both exit 4: “No provider file satisfies the requested compatibility and release policy.” The captured project, state, and cache entries remain equal. No replacement selection is silently accepted. |
| Explicit unpin | Author policy changes to automatic; exact saved selection `sOzRw3CG` and source runtime remain. Relaxing policy is not a migration. |
| Automatic preview and application | Target-compatible `wmIZ4wP4` is proposed and then saved for runtime 1.21. The author policy remains automatic. Actual changed document bytes/lengths match preview. |
| Both final recorded checks | Complete, zero verified payload files, one reference. Author/lock binding and runtime checks pass. No game or online compatibility check runs here. |

These are two small workflow branches, not twelve independent end-to-end tests. The [retained-data observer](observations.py) checks project-specific continuity, exact command modes, recorded exit codes, before/after document digests, author versus locked policy, runtime, references, and preview-versus-application bytes. It reuses the bounded author/lock decoder from the earlier [update join](../update-flow/README.md); it is not a general YAML implementation. The writer uses both single- and double-quoted game values, which the observer admits without changing original captures.

Project, selected durable state, and cache are observed separately. In this run, previews, refusals, and checks leave every captured entry unchanged. Sync, unpin, and successful migration change project documents and the selected durable operation history; cache images remain equal. The snapshot includes file bytes/digests, modes, and modification times, plus directory shape/modes. It does not measure directory timestamps, every OS effect, network transfers, or private stores outside the selected roots.

## Global preview-flag ordering

The same compatible source project produces different parser outcomes:

```sh
empack --dry-run migrate --minecraft 1.21 --loader fabric --loader-version 0.16.0 --json
# Exit 2: parser says --dry-run is required.

empack migrate --minecraft 1.21 --loader fabric --loader-version 0.16.0 --dry-run --json
# Exit 0: structured ready preview; captured entries unchanged.
```

The [three source selections](../../sources/empack-migration-flow-selections.json) show `dry_run` declared global, `MigrationArgs::json` requiring it, and a separate application-mode check that also refuses structured migration outside preview. The native prefix/suffix pair confirms a released interface inconsistency at this boundary. It does not identify an upstream parser-library defect or qualify other commands, environment variables, flag positions, or parser versions.

A candidate fix should admit equivalent global flag placement while keeping the non-mutating JSON-preview requirement. Review whether the existing application-mode check can own that combined condition after parsing, and add a parser-level regression for both positions and missing preview mode. This is a proposal only; no production parser or permission check changed.

## Failure reporting and API consequences

The incompatible-pin refusal agrees with the independently sampled target declarations. Its native error does not name `ferrite`, its pinned identity, or the requested game/loader context. Even with `--json`, stdout is empty and the error is human text on stderr. Progress also says “Downloading content: 0 bytes received” and “Verifying content”; no mod payload appears in the observed projects. These facts can leave a caller unsure whether discovery, policy, acquisition, or publication failed.

Carry the failing logical key, exact selection, target context, and useful evidence through the existing error/report path. Define the machine-readable failure contract explicitly, including output channel and exit code; keep progress outside JSON stdout. Prefer operation-specific progress such as checking target versions when that is the actual work. Do not add an independent status database or another resolver to produce this information.

Do not automatically prescribe unpinning or widening accepted game versions. The author's pin can express a deliberate content decision or a metadata workaround. This fixture explicitly authorized unpinning and then verified the result. A general diagnostic should explain the blocking selection and let the author review that policy, keep the old runtime, or choose an appropriate explicit replacement.

For the current/0.9 interface proposal, preserve authored constraints, provider eligibility observations, retained exact selections, materialization obligations, prepared native effects, and actual publication as distinct values. A ready preview does not bind a later command's approval object, and matching preview/application bytes here does not qualify stale approval or mutable-provider races.

## Preserved attempts and remaining verification

The [first attempt](../../evidence/empack-migration-flow-20261126T054252648792Z/disposition.json) created its selected state subdirectory with default permissions; the engine correctly refused non-private journal storage. All captured scopes stayed unchanged. A fresh fixture uses explicit `0700`. The [second attempt](../../evidence/empack-migration-flow-20261126T054326094647Z/disposition.json) completed sync, then exposed the global-prefix parser refusal. Both originals remain unchanged. The final run includes the prefix refusal as an explicit control beside the successful suffix preview, rather than treating it as target validation.

The [Lean model](MigrationFlow.lean) has seventeen laws and the [Bend model](MigrationFlow.bend) has sixteen. Both predict the twelve-step observation stream from the two initial fixture requests and command actions. They do not consume native after-state as model input. The sampled target eligibility is an admitted premise, not a proven catalog implementation. The decoder admits this exact two-project collection profile; its strict sequence check does not qualify arbitrary migration ordering.

The [retained-data replay](conformance.py) matches all twelve observations in each model. Six reason-specific decoder controls, nine changed-output controls, and four raw-observer controls exercise wrong mode/order, lost pin/runtime/selection, hidden refusal, false materialization, changed state, and corrupted document bytes or continuity. The focused standard gate checked two Lean modules and one Bend file. The proposed global-flag equivalence and preview-mode guard are acceptance criteria in the models, not executed production fixes.

Owner-local replay also reads the identified native executable, three source caches, independently sampled metadata bodies, and final private project/state/cache images. A fresh public-only copy explicitly excludes those private inputs and matches the same model results, basis, and controls. It cannot replace those original artifact and latest-fixture checks. Ordinary CI must not run the native collector or reacquire live metadata. Native source/compiler/build correspondence, YAML interpretation, transport, cryptography, and low-level publication are not proved by these workflow models.

The scoped migration component and joined scenario remain partial; all existing operation statuses and prior scenario records are preserved. Existing migration/source reviews remain applicable at their own boundaries.

Multiple roots and required edges, alternative loaders/Java changes, project replacements, local/URL/world content, materialization, stale source/approval, interrupted publication, source binding failures, other platforms, and actual consumer/game execution remain unqualified. A public-provider service response is not a complete inter-mod or implementation-level compatibility result. The broader nine-application study and production implementation decisions remain separate.
