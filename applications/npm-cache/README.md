# Cache verification and installed content

This band investigates npm 11.20.0 and its shipped cacache 20.0.4 on one generated local project. It separates selected cached bytes, cache cleanup, installed files, clean-install admission, and acquisition. Scoped formal comparisons preserve the observed effects; broader cache/index behavior remains open. The fixture does not establish a clean-install correctness defect.

The [source ledger](../sources/npm-cache-selections.json) identifies actual shipped modules by package version, path, hash, and retained source copy. It is not a reproducible upstream-build claim. `cache verify` delegates to cacache's verification, garbage collection, index rebuilding, temporary cleanup, and marker update. It does not inspect installed package files. `ci` admits the lock and ideal tree before clearing `node_modules`; acquisition during reification remains a later stage.

## Observed local sequence

The [collector](probe.py) reuses pinned npm/Node and creates one private project/cache and an owned loopback registry. Its archive contains only a generated manifest and a tiny JavaScript module. User/global configuration, home, temporary paths, and logs are private; scripts, audit, funding, notifications, and mise reshimming are disabled. No existing cache or project is opened.

The [receipt](../evidence/npm-cache-20261124T235228248707Z/receipt.json) records 14 commands: seven npm operations and seven independent Node availability observations. There are three loopback GETs: metadata and archive for installation, then one archive for recovery. All other steps make no request to that origin. Every owned process group retired, and the server closed. Generated work occupies 2,708 KiB, excluding the reused tools.

| Boundary                                     | Measured result                                                                                                                                                                    |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Install and verify the valid cache           | Both commands succeed; the module exports its original value.                                                                                                                      |
| Corrupt the exact cached archive             | The owned regular file matches the expected SHA-512 before mutation and has one link. Its original is retained. Installed execution still returns the original value.              |
| Verify that corrupted cache                  | Exit 0; one corrupt content object is removed, one missing object is reported, and one metadata object remains verified. Installed files are unchanged.                            |
| Clean install offline with missing archive   | Exit 1, `ENOTCACHED`, and no registry request. The old installed tree has been removed; manifests and lock remain unchanged. The availability observer reports `MODULE_NOT_FOUND`. |
| Clean install from the owned origin          | One archive request; installation succeeds and restores the original module.                                                                                                       |
| Edit the installed module, then verify cache | Verification succeeds and preserves the installed edit. Execution returns the edited value.                                                                                        |
| Clean install offline with valid cache       | No registry request; installation succeeds and replaces the edit with the original package bytes.                                                                                  |

The [read-only observation checker](observations.py) binds command streams, requests, file images, the deliberate mutations, and observed values. Its Node helper returns success for a captured availability report even when that report says the module is missing. That is the harness protocol, not a claim that ordinary Node execution succeeds when a required module is absent.

## Models and interpretation

Successful cache repair can leave a requested payload unavailable. A count of verified metadata/content objects is not proof that a particular package can be installed offline. Conversely, cache verification does not detect or revert an edit in an installed module. Cache integrity, availability of a requested representation, and installed integrity are different facts.

The clean-install failure preserves authored inputs but has consequential installation effects. This is consistent with a clean rebuild: the source clears the existing installation before later acquisition. Do not report it as corruption or promise rollback. Recovery here is a successful reacquisition/reinstallation, not restoration of arbitrary user edits. No general failure ordering or recovery guarantee follows from this one case.

The [Lean](Cache.lean) and [Bend](Cache.bend) models separate selected backing, installed content, and authored inputs. Thirteen Lean and eight Bend laws preserve cache verification's scope, clear-before-acquisition effects, cache lookup admission, and origin versus cache recovery. Invalid lock admission and unreferenced-content eviction are source/model branches, not native controls from this fixture.

The [pure replay](conformance.py) compares 15 captured boundaries: six npm operations after the initial installation baseline, two explicitly labeled owned interventions, and seven availability observations. Interventions and observers compare state fields, not fabricated npm exit codes. Both models match the five measured fields for npm operations and the seven observed availability fields. Eight malformed research inputs refuse; six changed outcome/availability expectations are detected. The [receipt](../evidence/npm-cache-20261124T235228248707Z/conformance.json) retains inputs, outputs, measurement masks, source premises, and hashes. No npm, Node, or server runs during replay.

Two [retained index records](../evidence/npm-cache-20261124T235228248707Z/cache-index-witness.json), read after the run, match exact file hashes in the before/after offline-success boundary. Their checked record checksums, request key, integrity, and lock selection support that selected cached representation. This is not a general index decoder or current lookup grant. The earlier verification rows retain a source-informed referenced-object/history premise; they do not claim recovered index bytes at every historical point. Unknown backing/installed hashes refuse interpretation instead of becoming absence.

A valid file alone does not establish a reusable index entry or retained lease. Cache snapshots cover selected file/hash views and two closed-format index witnesses, not complete permissions, freshness, concurrency, or retention authority.

## Decisions and verification plan

Keep cache verification's current cleanup scope and its verified, removed, missing, and index counts. It can succeed at repairing a cache while a package remains unavailable. A useful reporting/API distinction is cache-repair statistics versus availability of a requested representation versus installation verification. Reuse existing cacache statistics and typed request identities; a new generic transaction system is not justified here. If a caller needs a runnable installation, it must separately check that installation or finish a qualified materialization.

Keep the clean-install command's explicit rebuild meaning. An optional availability-first alternative could reduce avoidable disruption, but it needs retained, verified acquisition before clearing the old installation. A prior global cache check supplies neither ownership nor a stable lookup. The models preserve the old installation on a known preflight miss only under those conditional premises; no patched npm path was executed. Additional storage, staging, failure/recovery, and script semantics are real costs. Keeping today's behavior and explaining its phase/effects is a credible alternative.

For empack's portable design, distinguish an evictable cache hint from the retained backing of a user's only local authoring asset. Recoverable cache misses do not justify collecting project/history/plan inputs. Conversely, a durable-asset retention protocol need not become a universal promise that every replaceable package cache entry survives. Qualify each operation's required roots and captured inputs before sharing host mechanisms.

Further obligations include shared writers/garbage collection, metadata expiry, multiple dependencies, different sources, interrupted cleanup/reification, failing storage, arbitrary package scripts, remote services, and other hosts. The cache is intended to be replaceable; a portable project's only retained local source has stronger retention obligations. No production behavior or broad host rule changes here.
