# pnpm: command admission and script namespaces

A command name does not identify one operation in pnpm. The selected interface distinguishes registered handlers, registered placeholders, explicit package scripts, script fallback, and parser help. Some built-ins yield to a same-named script; others do not. The existing explicit entry points are useful and should be preserved.

The pinned pnpm 12.21.0 interface really includes task, pipeline, runtime, and permission commands. Their presence is not a claim that this study has executed those entire features. Conversely, a registered `edit` or `xmas` entry is not an implemented editing or holiday-display operation: its handler refuses execution and suggests npm. A separately authored package script with that name remains a different operation.

## Profile and observed routes

The [capture](../evidence/pnpm-admission-20261126T031327788019Z/receipt.json) uses the pinned pnpm 12.21.0 native binary and Node 26.13.1 on macOS arm64. Setup records their exact hashes, an isolated home/config/state environment, and the controlled marker program. Both binaries match their selected pins before and after the run. Eleven [source selections](../sources/pnpm-admission-selections.json) refer to pnpm revision `b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600`; a reproducible source-to-binary build is not established.

There are 21 CLI calls: fifteen namespace cases, four help-only admission queries, and two version reads. Seven real script-child events independently record label, arguments, working directory, and `npm_command`. No dependency installation, registry operation, global setup, runtime installation, or pipeline execution is performed. Offline settings and CI mode are selected, but are not a network-denial sandbox.

The new workspace root declares controlled scripts named `tasks`, `edit`, `xmas`, `pm`, and `fixture-inventory-script`. Its member has no scripts. One explicit author edit later empties the root's `tasks` body.

| Request/context | Actual route and outcome |
| --- | --- |
| Root `pnpm tasks status` | Runs the local `tasks` script with argument `status`. |
| Root/member `pnpm pm tasks status` | Runs the built-in status query; no marker child. |
| Member `pnpm tasks status`, with root script present | Refuses with `ERR_PNPM_SCRIPT_OVERRIDE_IN_WORKSPACE_ROOT`; directs the user to the root script entry point. |
| Root `pnpm run tasks status` | Explicitly runs that package script. |
| Root `pnpm edit` | Refuses with `ERR_PNPM_NOT_IMPLEMENTED`, despite an `edit` script. |
| Root `pnpm run edit` | Runs the authored `edit` script, not an npm editing operation. |
| Root `pnpm xmas --fixture-option` | Reaches the unsupported-handler diagnostic; the trailing flag is absorbed rather than rejected as an unknown option. |
| `pnpm fixture-inventory-script --literal` | Runs the declared fallback script, preserving its argument. |
| Root `pnpm --dir . pm tasks status` | Runs the declared `pm` script with arguments `tasks`, `status`. |
| `pnpm pm run tasks status` | Selects the built-in `run` command, which intentionally executes the requested script. |
| `pnpm tasks --help` | Displays parser help before script override. |
| `pnpm run tasks --help` | Passes `--help` to the script. |
| Root/member `pnpm tasks status` after the empty-body edit | Uses the built-in; an empty root script no longer shadows it. |

The four additional help queries admit `pipeline`, `runtime`, `permissions`, and `with` at the parser/interface boundary. They establish no installation, cache, scheduler, permission, or alternate-runtime behavior. Root help and source declarations also admit the other inventoried runtime commands. Their operational qualification remains separate.

## Existing policy and types

`CliCommand` provides distinct registered variants and an external-name fallback. The selected routing arms send `Edit` and `Xmas` directly to the typed unsupported diagnostic. They do not use the script-override resolver. This is an advertised capability boundary, not a missing package script or failed executable search.

For `tasks`, the maintenance dispatcher calls `script_override::resolve`. It keeps a forced built-in request, otherwise selects a nonempty local script, otherwise refuses a member invocation when the workspace root owns that name. Empty bodies are treated as absent for this purpose. The native empty-body edit exercises that change without assuming all falsey, whitespace, or malformed script values behave alike.

The `pm` prefix is removed only when it is the first argument after the program name. It is not an independently registered command. The observed leading-option case follows that documented source rule; it is not classified as a parser defect. Reordering global options across `pm` changes the request namespace. Automation must preserve this ordering rather than normalize the tokens as interchangeable flags.

The prefix is also not a “never execute scripts” security policy. The measured `pm run` reaches the built-in script runner. Unknown-program fallback and arbitrary shell/script execution are outside the native profile. Do not infer a sandbox, trust grant, or built-ins-only execution guarantee from the word “force.”

Script dispatch already carries useful context: `RunCtx` has `builtin_command_forced` and `builtin_replaced_by_script`, and script children observe `npm_command=run-script`. Reuse these distinctions in any operator trace. A no-child observation is encoded as null label/environment evidence; it does not assert that the built-in process has an empty or unset environment variable.

The generic `not_implemented` source comment uses `token` as an example. The selected current registry and routing instead give `Token` its own handler. That stale comment cannot establish token-operation support or refusal. Inspect the actual route and selected version, then qualify its behavior separately. Correcting the example is a documentation candidate, not a reproduced token-service defect.

## Preservation and interface decisions

Keep explicit `pnpm run <script>` and leading `pnpm pm <built-in>`. They let a caller name the intended namespace without renaming existing scripts or weakening workspace-root guards. Do not make every registered command overridable: the placeholder control demonstrates that registration and override eligibility are separate policies. Do not remove the conservative root-shadow refusal merely because this particular built-in query is read-only; the existing explicit choice resolves the ambiguity.

For automation, put the forcing prefix first and the built-in's global options afterward. Use explicit `run` when a package script is intended. These are invocation choices supported by the current interface, not proposed flags. A compact help/documentation note about prefix position would make this requirement easier to find. Preserve parser help as an inspection route; a help query should not be presented as successful execution of the named feature.

An optional selected-handler trace could report the requested namespace, typed command, project/root basis, selected script or built-in, and actual child/result separately. First reuse the current typed command and dispatch context; a new command-resolution framework is not justified by this band. The current human script output and explicit entry points are a reasonable keep-current alternative when no trace consumer needs more detail.

Preserve the first-token rule for compatibility. Changing it could redirect the real `pm` package script observed here. Any broader rewrite needs an explicit decision about package-script collisions and global-option handling, with argument/cwd controls. No such production change is selected. Existing package manifests, lockfiles, and saved states need no migration for these preservation decisions or a clearer help note.

For empack's current/portable design, an operation's meaning may depend on its namespace, arguments, project image, and entry point, not just a command string and tool version. The before/after authored-body cases are a concrete reason to preserve that input basis. This is a comparative design constraint, not a reproduced empack bug or evidence of a pnpm cache defect.

## Verification and scope

[Lean](Admission.lean) and [Bend](Admission.bend) each state ten laws. They separate task-script precedence, forced selection, root shadowing, unsupported placeholders, help, explicit script argument forwarding, empty-body policy, and the leading-prefix rule. The [gate](../evidence/pnpm-admission-20261126T031327788019Z/proof-gate.json) checks two Lean modules and one Bend file.

The [observer](observations.py) derives requests from actual argv and saved input images. It derives outcomes from diagnostics/help/status and actual marker events in both stdout and the event file. The original collector stored author-file digests rather than the initial manifest's full text. The additive [input images](../evidence/pnpm-admission-20261126T031327788019Z/manifest-images.json) reconstruct only the known initial body and verify its exact recorded SHA-256 and length. Final root/member/workspace readbacks also match. No original record is rewritten, and no arbitrary historical text is inferred from a hash.

Owner checks bind private project/event/marker bytes and both native tools. Source caches are checked against retained SHA-256 and Git blob IDs. The selected setup snapshot supplies the tool basis; unrelated edits to the shared tool catalog are not added to this comparison's read set.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/pnpm-admission/conformance.py
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/pnpm-admission/conformance.py --public-only
```

The [replay](conformance.py) compares fifteen native namespace outcomes against both models, checks fifteen additional pure prefix inputs, and rejects sixteen unsupported DTOs, seven changed premises, and eight changed raw observations. Prefix comparisons are not additional native cases. Public mode checks the five recorded artifacts with explicit private-check exclusions. [Control record](../evidence/pnpm-admission-comparison/controls.json).

Neither replay runs pnpm, Node, package scripts, installers, or source acquisition. Controlled script success, supported JSON/argument shapes, and empty private group state are premises. Other shell bodies, child failure, registry/runtime dispatch, populated concurrency groups, aliases, arbitrary manifests, other hosts, and general CLI parsing remain open. All recorded command groups retired; the later exact-work scan found no remaining fixture process, without claiming a universal descendant census. Private fixtures, marker events, caches, and sources remain retained. Only the two selected built-in placeholders acquire an explicit unsupported-profile disposition; broader feature/workflow statuses remain unqualified.
