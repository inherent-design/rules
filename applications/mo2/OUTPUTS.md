# MO2: tool output, overwrite choices, and partial file moves

This band distinguishes a tool's write destination, the overwrite directory, existing mod backings, and deliberate adoption. It studies MO2 v2.5.2 source at `9c130cbf2fc7225fb2916e46419af50671772aa0`. Selected methods run with real Qt 6.12.0 widgets and file operations on macOS, using the offscreen platform. This is supplemental source-method evidence, not native MO2, supported Windows, USVFS, or game qualification.

## The workflows are separate

The [source ledger](../sources/mo2-overwrite-selections.json) identifies six files and inspected ranges. `OrganizerCore::fileMapping` builds mappings from enabled profile entries. A custom write target must be active; regular mod mappings carry its create-target flag, while the default overwrite mapping carries that flag when no custom target is selected. Local saves and plugin mappings add separate destinations. The executable dialog filters several special mod classes, and the connector passes the flag to directory VFS linking. These paths were inspected, not executed here. They do not establish where a particular injected write actually lands or qualify every mod/plugin combination.

After tools run, several adoption paths remain distinct. Creating a new mod or moving overwrite contents to an existing mod uses the shell-move helper. The sync dialog instead offers per-file existing origins and uses its own remove-then-rename sequence. Testing that dialog does not qualify the create-mod workflow, process retirement, or automatic output routing.

## Source-method fixture

The [collector](overwrite_probe.py) and [driver](overwrite_driver.cpp) retain the unchanged combo helper, `readTree`, `refresh`, `applyTo`, and `apply` bodies from `syncoverwritedialog.cpp`. Qt's tree items, combo boxes, directory iteration, and `QFile` operations are real. The surrounding constructor/UI shell, virtual origin directory, translation, and error reporter are controlled adapters. Error calls are collected immediately; this does not test production modal dialogs or user acknowledgement.

The [receipt](../evidence/mo2-overwrite-20261124T144126131337Z/receipt.json) records one compilation and 15 cases, producing 16 file transitions because one case contains two files. Its [environment readback](../evidence/mo2-overwrite-20261124T144126131337Z/environment.json) identifies current framework files and load commands. Those dependency hashes were inspected after the run; runtime Qt version and offscreen platform are measured in each original result. There is no supported-consumer dependency or reproducible-build claim.

The [first compile attempt](../evidence/mo2-overwrite-20261124T144005823922Z/disposition.json) remains excluded. Directly invoking the resolved compiler without the SDK failed to find a C++ header. An explicit SDK header control passed; the successful collector supplies the selected SDK. No method ran in the failed attempt, and it is not an MO2 failure.

All paths belong to newly generated cases. Before/after images identify file bytes, node kind, symlink target, and mode. Two deliberate removals happen between preview and apply; their separate intervention and before-apply records prevent attributing those fixture changes to the method. No user mods, game files, desktop windows, or existing runtime processes are involved.

| Case                                         | Observed result                                                                   |
| -------------------------------------------- | --------------------------------------------------------------------------------- |
| Selected writable destination                | Old destination replaced; source removed; incoming object retained at destination |
| Explicit don't-sync choice                   | Both backings preserved                                                           |
| Missing destination                          | Remove error; source retained; no new destination                                 |
| Read-only destination directory              | Remove error; both backings preserved                                             |
| Read-only source directory                   | Destination removed; move error; source retained; **old destination absent**      |
| Source removed after preview                 | Destination removed; move error; **both paths absent**                            |
| Destination removed after preview            | Remove error; source retained                                                     |
| Nested accented/Greek filename               | Move succeeds; empty source subtree and its empty parent are removed              |
| Unknown virtual file entry                   | Only don't-sync offered; no move                                                  |
| `meta.ini`                                   | No widget offered; file retained                                                  |
| Overwrite primary with alternatives A then B | Default choice is the last supplied eligible alternative, B                       |
| Only overwrite origin                        | Only don't-sync offered                                                           |
| Two files, one missing destination           | One remove error and one successful move; partial batch result retained           |
| Source symlink                               | Link object moved; owned canary bytes unchanged                                   |
| Destination symlink                          | Old link removed, incoming regular file installed; owned canary bytes unchanged   |

The methods filter the overwrite origin from destinations and preserve the supplied alternative order. They do not compute origin priority themselves. Real origin discovery, archives, hidden files, and default eligibility must be qualified with the surrounding view before interpreting that choice as the correct highest-priority mod.

The symlink and Unicode cases are bounded controls. They do not prove general path safety, Windows link behavior, normalization equivalence, or sandboxing. The replay uses a unique NFC path projection to connect this Mac's directory names with the requested nested name; it does not make that a production identity policy.

## Failure after a destructive step

The critical source order is destination removal followed by source rename. A rename failure cannot restore the already removed destination. The read-only-source case reproduces that consequence using actual Qt operations without a missing source. The controlled source-removal case separately exposes the preview/apply gap. A preliminary existence check alone would not close either the later failure or the race.

This is a source-confirmed destructive failure path with supplemental macOS evidence. It is not a reproduced supported-Windows MO2 workflow or a claim about the shell-move path. Keep the source file that survived, the missing destination fact, the failed phase, and any other completed rows visible. An error does not mean the whole sync was unapplied.

A candidate correction must preserve the prior destination until replacement is confirmed, or retain verified recovery bytes before destructive work. Inspect existing filesystem helpers and Windows replacement guarantees before selecting an implementation. Reusing an appropriate checked move helper may suffice; its mere presence in a different workflow proves neither atomicity nor recovery. Do not add a broad filesystem transaction framework by default, weaken destination permissions, or retry blindly after the old path has disappeared.

The current error calls identify remove versus move failure. A focused per-file result could also retain which prior backing was removed, where the incoming object remains, and which rows completed or were skipped. That supports accurate refresh and recovery guidance. The selected `apply` returns no such aggregate result; this fixture's structured result is research instrumentation, not an existing public MO2 API.

## Models and comparison

[Lean](Overwrite.lean) checks 15 laws; [Bend](Overwrite.bend) checks eight. Choice construction, default selection, physical source/destination roles, failure phase, and optional recovery retention remain separate. Remove/move primitive outcomes are admitted host witnesses cross-checked against the filesystem images, not a portable permission or Qt rename simulator.

The [pure replay](overwrite_conformance.py) matches both models to all [16 retained transitions](../evidence/mo2-overwrite-20261124T144126131337Z/conformance.json). It verifies offered/default/selected choices, final object identity and kind, selected file modes, untouched other mod backings, and canary preservation. Seven malformed research inputs are refused. The proposed prior-backing retention is a model-only requirement with an explicit verified-retention premise; no native recovery copy or corrected replacement implementation is claimed. Current destination loss stays in the comparison.

Before any correction is adopted, use a supported Windows MO2/Qt build with disposable real loose and archived origins. Exercise default and custom output routing, disabled or stale targets, source/destination replacement after preview, permission and cross-volume failures, multiple-row acknowledgement, links, metadata/attributes, partial shell moves, restart, and restoration from actual retained bytes. An active tool must retire before its output is treated as a stable captured set. No complete inventory feature or joined scenario is qualified here.

For empack, preserve the distinction between externally written bytes, a chosen editable source, retained exact content, and permission to replace an installed backing. A tool output directory is not automatically a mod declaration or verified project image. The native ownership/publication and proposed portable capture boundaries should carry their existing basis and partial-effect facts through reporting rather than letting a generic failure headline erase them. This study does not select a new tool runner or production change.
