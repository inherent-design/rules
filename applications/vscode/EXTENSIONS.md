# VS Code: extension membership, host placement, and execution

Installing an extension, admitting it to a profile, choosing an extension host, and activating it are separate operations. An uninstall can remove profile membership while leaving version directories on disk. A successful CLI exit can also mean that a requested downgrade was skipped. These distinctions matter to operators and automation; they do not establish a product defect.

## Selected versions and boundaries

The [native collection](../evidence/vscode-extensions-20261126T040016341935Z/receipt.json) uses the installed VS Code **1.148.0**, commit `661626d0e72f97806550790a98fb87116c9db825`, on macOS arm64. The executable and product commit are checked before any application call and again after the run. The prior 1.147.0 executable guard failed before creating a profile or running Code. Historical studies keep their original pins.

Sixteen commit-addressed [source files](../sources/vscode-extensions-selections.json) were retrieved for this version. Their bytes match the corresponding earlier 1.147.0 selections, including the host pickers, caller, CLI/environment handling, and selected management files. This does not establish whole-version equivalence or a reproducible build of the installed application. The selected source and installed bundles have separate hashes and attribution.

There are two evidence classes:

| Collection | What actually ran | What it does not establish |
| --- | --- | --- |
| Native CLI | Thirteen calls through the installed Electron executable with `ELECTRON_RUN_AS_NODE=1` and the bundled `out/cli.js`; twelve management outcomes plus one version read. Three owned local VSIXs; no Marketplace ID. | No GUI, extension host, activation, browser worker, remote service, account, or trust enforcement. |
| Source caller and pickers | Thirty selected calls through `determineExtensionHostKinds` and the desktop/browser picker bodies under Node 26.13.1. | No manifest deduction, scanner, actual remote connection, worker creation, full enablement, or runtime support. |

The [existing trust study](TRUST.md) covers selected support and trust-disable predicates. This band reuses those limits and does not repeat its large finite matrix or promote it to native enforcement.

## Native lifecycle and retained state

The generated extension has `main`, `browser`, ordered kinds `[workspace, web]`, and an activation event. Its three versions are 0.0.1 and 0.0.2 with engine range `^1.100.0`, and 0.0.3 with the incompatible range `^999.0.0`. No force flag, dependency installation, extension pack, or publisher allowlist is involved.

| Request | Exit | Registered version afterward | Independent effects/readback |
| --- | --- | --- | --- |
| List empty profile | 0 | Absent | No fixture directory. |
| Install 0.0.1; list | 0 | 0.0.1 | Package and entry-point bytes captured. |
| Install incompatible 0.0.3; list | 1, then 0 | 0.0.1 | Old membership and package hashes preserved. No installed 0.0.3. This is not a general failure-rollback guarantee. |
| Install 0.0.2; list | 0 | 0.0.2 | Both 0.0.1 and 0.0.2 directories remain. |
| Request 0.0.1 without force; list | 0 | 0.0.2 | CLI says a newer version is installed and suggests `--force` for a downgrade. It does not claim installation success. |
| Uninstall; list | 0 | Absent | Both version directories still exist. `.obsolete` marks 0.0.1; absence of a 0.0.2 obsolete marker does not restore its profile membership. |
| Uninstall again | 1 | Absent | Diagnostic names the missing full extension ID. |

Each list is a new process, rather than a cached in-process query. The index and directory observations are captured independently of console interpretation. The [retained readback](../evidence/vscode-extensions-20261126T040016341935Z/installed-manifest-readback.json) also shows that installed `package.json` has added `__metadata`. Original declarative fields match the VSIX semantically; installed manifest bytes are not falsely asserted equal to archive bytes. Entry-point byte hashes do match their owned inputs.

No activation beacon appeared. That is a bounded observation of this CLI route, not proof that installing arbitrary extensions can never execute code or that an extension host was safely retired. All thirteen owned processes were waited for; a final process-table read found no command referencing the private fixture root. No GUI lease was needed or acquired.

## Source placement policies

The unchanged caller merges scanned local and remote descriptions by extension identity. When both descriptions exist, the **local effective kind list wins**, even if the remote description declares another list. Kind lists are ordered. Development on only one side supplies a preference for that side; development on both or neither side supplies no preference. This is not a general trust or user-preference flag.

The fixture admits one lowercase/uppercase identifier pair through an explicit normalization adapter. It does not qualify all Unicode identifiers, scanners, duplicate-description rules, or manifest parsing. Two helper-record constructors are explicit field-assignment adapters. Original caller, picker, and getter bodies are retained in the [fragment](../evidence/vscode-host-selection-20261126T040253545Z/fragment.ts); [adapter input](../evidence/vscode-host-selection-20261126T040253545Z/adapter.ts) and type-stripped JavaScript have separate hashes. Node's strip-only compiler rejected upstream parameter-property syntax; its API also rejected transform mode. Both failed attempts are retained privately and excluded from measured results.

| Situation | Desktop picker | Browser picker |
| --- | --- | --- |
| Local workspace-kind extension, no remote | Local process. | No local Node host. |
| Local workspace-kind extension in a remote window, not installed remotely | Unavailable, unless another admitted kind supplies a local host. | Unavailable without a remotely installed eligible kind. |
| Remotely installed workspace-kind extension | Remote host. | Remote host. |
| Local web-kind extension | Local worker only if the constructor's worker-availability fact permits it. | Local worker candidate. Actual creation is not tested. |
| Remote-only web-kind extension | No local worker candidate from this picker. | Local worker candidate. |
| Remote UI-kind extension | No local UI process without local installation. | Remote host as a last resort, unless remote development makes it preferred. |
| Eligible kinds in another order | Can change the selected host. | Can change the selected host; ordinary candidates precede the UI last resort. |

The models express these rules as ranked eligible candidates, rather than copying the original early-return loops. A kind declaration alone supplies neither an installed copy nor a host. Conversely, a selected host supplies neither enablement nor activation. The desktop source constructor uses remote authority and worker configuration/development facts; this band supplies those facts explicitly instead of inventing a live remote server.

## Isolation and diagnostic scope

All named user data, extension, download, shared data, agent-plugin, agents-user-data, and agents-extension directories point inside one short disposable fixture root. HOME, TMPDIR, and XDG configuration/cache paths are private. No inherited remote CLI hook or personal account environment is supplied. Telemetry and update settings are disabled, but this is not a network-denial sandbox or a trace of every OS write. A device ID file was observed in the **private** home. Shared-data files were absent in the captured tree.

The explicit `--shared-data-dir` path avoids silently using the personal shared store identified by the earlier [configuration study](CONFIGURATION.md). That earlier study's unmeasured shared writes remain unmeasured; they are not retroactively repaired. Secret storage is in-memory, and this path did not open a keychain dialog. System policy reads and incidental OS state are not claimed fully isolated.

Successful native installs also emitted a Node `url.parse()` deprecation warning on stderr. The installed version and requested action remain available in stdout and captured state. That warning alone is not a proven vulnerability, failed installation, or proof of an observed network request.

## Preserved behavior and design candidates

Preserve explicit engine refusal, downgrade explanation, full extension IDs, profile-aware membership, development-placement precedence, ordered kinds, and the browser's distinct host capabilities. Preserve retained versions until their actual collection policy is qualified. Do not make uninstall diagnostics promise physical erasure or immediate process retirement.

For VS Code, a compact operation report could expose `installed`, `skipped`, `refused`, or `removed from profile`, the selected version/profile, and an optional host/enablement explanation. Keep physical files and running hosts as separately observed facts. Detailed provenance should name the effective kind list, which copy supplied it, why a placement preference exists, and which host is unavailable. This is a proposed reporting improvement; the measured downgrade text already correctly explains its skip.

For empack, keep declaration/selection, installed membership, retained content, and runtime execution distinct in human and machine reports. Existing package-manager observations already show why an exit code cannot carry every effect. Apply the lesson at actual operation boundaries rather than adding a universal extension-host abstraction to programs with different purposes. No production or deferred UX implementation is activated by this study.

## Verification and remaining work

[Lean](Extensions.lean) and [Bend](Extensions.bend) each contain twelve laws. The bounded [Lean codec](ExtensionsCase.lean) rejects unsupported study profiles and caller premises. The [retained-data checker](extensions_conformance.py) compares thirty source-host outcomes and twelve native management outcomes with both models. Sixteen DTO refusals, seven changed premises, and nine changed raw observations check that relevant evidence affects the result. Original raw results remain unchanged.

The public-only replay excludes sixteen source caches and four private categories. It uses retained observations, owned archive inputs, source excerpts, and public hashes; it does not rerun the studied application or claim private tool/source revalidation. Owner checks additionally read available pinned sources, tool readbacks, and the private installed fixture. The [comparison report](../evidence/vscode-extensions-comparison/conformance.json) freezes every public evidence input and model hash; [admitted inputs](../evidence/vscode-extensions-comparison/input.json) and [measured outcomes](../evidence/vscode-extensions-comparison/measured.json) remain separately inspectable. Fresh public-only and owner results match apart from explicitly excluded private checks.

Run `python3 applications/vscode/extensions_conformance.py --public` with the pinned Lean and Bend binaries. Actual collection requires the separately selected `extensions_probe.py` or `extensions_source_probe.mjs` procedure and stays outside ordinary CI.

Full enable/disable UI, trust grant/revoke persistence, actual process/web-worker activation, remote authority/installation, extension dependency/pack handling, platform-specific installation, arbitrary engine/version policy, interruption/repair, and eventual file collection remain open. The parent extension and web-extension operation statuses stay pending; only these scoped components are linked.

The subsequent [activation follow-up](ACTIVATION.md) adds one local native four-window policy/runtime flow with independent execution, storage, and shutdown observations. It leaves full enable/disable UI, trust enforcement, remote/browser hosts, and interruption behavior unqualified.
