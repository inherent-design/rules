# MO2: ranked origins and the effective file view

This first band studies Mod Organizer 2 v2.5.2 at `9c130cbf2fc7225fb2916e46419af50671772aa0`. It models the sorted origin selection for one virtual file. It does not qualify profile loading, the complete directory builder, Windows VFS injection, game archives, or native launching.

The later [profile activation band](PROFILES.md) examines scalar/bulk enabled-state changes and the boundary between notifications, effective-view refresh, and persistence. Its source-method cases retain their fixture-adapter scope.

## Domain and source

An installed mod, an enabled profile entry, an origin contributing a file, and the winning file backing are different objects. Reordering a mod changes the profile's priority; it does not move every physical file into the game directory. The selected source stores a primary origin and alternatives for a file.

The pinned [`FileEntry::sortOrigins`](https://github.com/ModOrganizer2/modorganizer/blob/9c130cbf2fc7225fb2916e46419af50671772aa0/src/shared/fileentry.cpp) compares loose files by origin priority, archived files by archive order, and loose versus archived files by backing kind. Negative comparison values are mapped to `INT_MAX`. The final sorted entry becomes the primary origin. This is richer than a universal “highest mod priority wins” rule.

[`OrganizerCore::modPrioritiesChanged`](https://github.com/ModOrganizer2/modorganizer/blob/9c130cbf2fc7225fb2916e46419af50671772aa0/src/organizercore.cpp) updates enabled origins, writes the profile list, and asks the file register to sort origins. The inspected profile writer persists enabled/disabled status and reverses the internal priority order for its list format. These observations identify relationships; they do not establish every refresh path or archive discovery rule.

## Model and comparison

[Lean](Overlay.lean) models a candidate origin, loose/archive rank, finite order or a sentinel, and winner selection. Five laws cover loose-versus-archive precedence, sentinel ordering, same-class order, and empty/singleton selection. [Bend](Overlay.bend) implements the winner projection and two checked laws.

The [source-fragment probe](../launcher_fragments_probe.py) extracts the pinned sort method without changing its body. A small C++ fixture supplies the fields and methods that body accesses. It executes 56 ordered pairs covering loose/archive candidates, values 0/1/2, and the negative sentinel. Both executable models agree with the [retained fragment results](../evidence/launcher-fragments-20261124T012218677503Z/conformance.json). A priority-only selection rule is contradicted by the results.

This is execution of a source fragment with fixture adapters, **not execution of MO2 on macOS**. Native MO2 requires a supported Windows environment. The abstract sentinel is above finite ranks; the native codec reserves `INT_MAX`, and the tested finite values are below it. Equal ranks, arbitrary integer boundaries, case/Unicode path lookup, hidden files, archive contents, and process injection remain unqualified. Eligibility is an input premise, not a claim that the model implements profile activation.

Compile `Overlay.lean` and Prism's `Update.lean` to their matching module paths under `.build`, then use the [shared replay](../launchers/conformance.py):

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/launchers/conformance.py applications/evidence/launcher-fragments-20261124T012218677503Z
```

The replay uses retained observations and the model tools. It does not build or launch MO2, Prism, or the source-fragment C++ probe. Source collection and fragment compilation remain owner-run procedures outside ordinary CI.

## Preservation decision and candidate interface

Preserve backing-kind and archive-order distinctions. A replacement model based only on mod priority would lose observed behavior. No implementation defect was established in this band.

A useful inspection result would identify the virtual path, winning origin, alternatives, backing kind, comparison rule, and profile/origin-set basis. Much of that information already exists in `FileEntry` and its surrounding types. Review the existing conflict UI and plugin APIs before proposing another interface. A tagged rank such as loose-file priority versus archive order could make a future projection harder to misuse, but it must preserve the current native sentinel and ordering semantics.

The keep-current alternative is appropriate if the existing views already explain those distinctions consistently. A change should not reorder saved profiles or reinterpret archive order. Its verification must exercise supported Windows MO2 with disposable loose/archived conflicts, reorder and disable operations, hidden files, profile switching, and an injected process reading the resulting view. Capture the winning physical bytes and original mod files, rather than relying solely on conflict icons.

The shared host contracts can describe origin identity, observed effective-view provenance, and process ownership. They do not determine the game's archive rules or MO2's precedence policy. The remaining MO2 inventory, including installation, external writes and overwrite adoption, plugin load order, saves, tools, recovery, and maintenance, stays open.

The later [output and sync band](OUTPUTS.md) separates custom write routing and shell-move adoption from the sync dialog's per-file remove/move sequence. Real Qt/macOS source-method evidence exposes partial destination loss; supported Windows/USVFS qualification and any correction remain separate.
