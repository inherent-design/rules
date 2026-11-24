# Cache verification and installed content

This intermediate band investigates npm 11.20.0 and its shipped cacache 20.0.4 on one generated local project. It separates selected cached bytes, cache cleanup, installed files, clean-install admission, and acquisition. **Formal models and replay remain pending.** The fixture does not establish a clean-install correctness defect.

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

## Interpretation and remaining work

Successful cache repair can leave a requested payload unavailable. A count of verified metadata/content objects is not proof that a particular package can be installed offline. Conversely, cache verification does not detect or revert an edit in an installed module. Cache integrity, availability of a requested representation, and installed integrity are different facts.

The clean-install failure preserves authored inputs but has consequential installation effects. This is consistent with a clean rebuild: the source clears the existing installation before later acquisition. Do not report it as corruption or promise rollback. Recovery here is a successful reacquisition/reinstallation, not restoration of arbitrary user edits. No general failure ordering or recovery guarantee follows from this one case.

Next, compare the captured sequence with scoped Lean/Bend models. Keep target-byte evidence separate from a semantic cache-index decoder: the snapshots retain file/hash views, not a complete index interpretation. A valid file alone does not establish a reusable index entry or a retained lease. If an availability-first alternative is modeled, require captured inputs to remain owned through the destructive boundary rather than trusting a prior global cache verification.

Further obligations include shared writers/garbage collection, metadata expiry, multiple dependencies, different sources, interrupted cleanup/reification, failing storage, arbitrary package scripts, remote services, and other hosts. The cache is intended to be replaceable; a portable project's only retained local source has stronger retention obligations. No production behavior or broad host rule changes here.
