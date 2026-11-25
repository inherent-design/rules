# Path spelling, object identity, and protected trees

A preflight check can reject a known conflict without authorizing a later mutation. This contract separates application policy, current object/ancestry evidence, protected scope coverage, authority, and the protocol that binds those facts to the actual effect. It is a proposed host guard for operations that must preserve selected trees, not an implementation of a race-safe writer or a universal policy for in-place editing.

## The application counterexample

The application owner retained a pnpm 12.21.0 macOS comparison in [the deployment study](../../applications/pnpm-deploy/README.md). Exact source spelling refuses; a case-only spelling names the same device/inode, is admitted under force, and exits zero after removing the fixture's program and author-only file. The retained preimages and raw channels were independently checked here, along with nine pinned source files' SHA-256 and Git blob identities. No pnpm invocation was repeated by the host study.

The selected Unix comparison retains spelling while its target guard protects source/ancestor paths through component comparisons. Native identity, lexical path relations, destructive preparation, payload presence, and command outcome are different facts. This finding does not establish a defect in another program or all pnpm versions/filesystems.

## Rule inputs and decisions

[FilesystemGuard.lean](../../common/FilesystemGuard.lean) has 14 laws. [FilesystemGuard.bend](../../common/FilesystemGuard.bend) has nine kernel-checked laws. Their version-one input has:

| Input | Required meaning |
| --- | --- |
| `policyAllows` | The selected operation's existing policy does not already refuse. This does not claim that path spelling proves safety. |
| `relation` | 0 unknown; 1 an overlap is established; 2 separation is established for the protected scope. Different IDs alone do not prove tree separation. |
| `complete` | Evidence covers every protected tree relevant to the proposed effect. A known conflict does not need a complete scan to refuse. |
| `identityCurrent` | The relevant binding remains current for the selected preflight observation. A stored ID is not a permanent identity or freshness guarantee. |
| `scopeMatches` | The evidence belongs to the intended operation, target, and protected set. Matching a display name is insufficient. |
| `authority` | The effect owner has the required current operation authority. |
| `boundaryBound` | An independently established native protocol binds that authority and relevant identities to the actual mutation boundary. A prior stat/resolve call does not establish this premise. |

Preflight returns 0 for policy refusal, 1 for unresolved evidence, 2 for conflict, and 3 for a candidate. A known current conflict refuses even with incomplete coverage; an incomplete claim of separation stays unresolved. A candidate becomes a modeled mutation admission only with both authority and boundary binding. The native fixtures supply neither, so they authorize no mutation.

Protected-tree overlap deliberately includes a target inside the protected tree as well as a target containing it. The operation owner must select the actual preservation scope. Legitimate output inside a mutable author tree, approved exceptions, missing-target creation, and in-place updates need their own contracts; this rule must not silently prohibit those operations or invent their authority.

[compare.py](compare.py) compares all **192** finite combinations through Lean and Bend and rejects eight malformed research requests. [The committed table](vectors.json) binds the exact model, decoder, and projection source hashes. The proof lane rechecks the table; host lanes use it without installing either proof tool. This is rule-input completeness, not a proof of the Python projection, filesystem implementation, or production integration. Both models receive the same supplied premises.

## Native observations and API boundaries

[native.py](native.py) performs standard-library filesystem operations only in one owned temporary tree. It records spelling, `os.stat` identity, `os.path.samefile`, resolved ancestor walks, missing identity, and a controlled rename/rebind. It restores both moved directories and checks their sentinel bytes before retiring the scratch tree. No application, account, live project, hardlink, network service, or graphical desktop is involved.

The retained [Darwin/Python observation](evidence/native-macos-20261125T155103537084Z/observed.json) has nine raw cases and ten guard projections. Case and Unicode-normalization aliases identify the same object on that selected fixture volume. Distinct endpoint IDs still overlap for ancestor/descendant cases. After preflight, an owned directory rename makes the same target spelling identify the captured protected object; the old separated binding must be revalidated. The witness does not generalize case/normalization behavior to every volume or host.

[protocol.py](protocol.py) derives typed evidence from those raw observations. It uses complete endpoint ancestry only within the quiescent owned fixture, preserves unavailable identity, and withholds later mutation authority. [verify.py](verify.py) checks rule agreement and six altered raw observations, including contradictory same-object results, incomplete ancestry, invalid identity, a forged fresh binding, lost source preservation, and an unsupported schema. Its ancestor walk is an inspected fixture adapter, not an attacker-safe production algorithm.

Python 3.13 documents `samefile` using device/inode observations and raising when the stat calls fail. Lexical normalization is a different API. [Python path contracts](https://docs.python.org/3.13/library/os.path.html#os.path.samefile). This fixture requires meaningful positive identity values; filesystems/providers without them need an explicit unavailable adapter rather than fabricated separation. `stat` snapshots, symlink resolution, and repeated comparisons do not close a check/use race or prove durable storage.

Native Windows handle identity has a separate representation and API contract; Microsoft's FILE_ID_INFO documentation describes volume and file identifiers for comparing open handles. This fixture does not call that API directly or establish its availability on an untested Windows target. [Win32 handle identity](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info). The current Python adapter, native backend, directory/reparse semantics, object lifetime, and mutation synchronization still need explicit qualification.

## Java 17 with 21 and 25 overlays

The owner-run [standard-library probe](SameFileProbe.java) performs five `Files.isSameFile` calls and independent basic-attribute reads on each explicit JDK. [Collection](java_probe.py) uses Java 17 class output, bounded heaps, two processors, no daemon, and separate private roots. [Export](export_java.py) checks actual tool/program/raw-channel hashes and process-group retirement. The [pure comparison](java_compare.py) checks all **15** calls, 15 conservative guard projections, and six changed observations without starting Java.

All three selected Darwin JDKs return true for two equal missing paths while attribute reads report NoSuchFileException. The [Java 17 API](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/file/Files.html#isSameFile(java.nio.file.Path,java.nio.file.Path)) explicitly permits that equal-Path shortcut without checking existence. This is documented library behavior, not a JVM or application defect. A Boolean with the name “same file” therefore cannot be substituted for another adapter's current-object witness.

The Java adapter withholds tree separation and mutation-boundary authority. A false result on existing objects is insufficient to prove absence of ancestry. A true result on equal missing paths remains unknown object evidence. The receipt in [java-conformance.json](evidence/java-conformance.json) keeps these interpretations separate from raw API results. Custom providers, permissions, cross-provider calls, races, symlinks, Windows/Linux JDKs, and every Java file-identity API remain unqualified. Java 18 is not a reference target.

The separate [Minecraft linked-filesystem witness](../minecraft/LINKED-FILESYSTEM.md) now qualifies selected original provider operations on macOS/JDK 21 and 25. Distinct logical nodes backed by the same physical file compare as different; virtual existence can survive backing deletion. That witness supplies no physical tree-separation or mutation authority. Other custom providers and backing hosts remain open.

## Relative targets and consuming context

Path context is another independent input. The Java 17 contract for [`Files.readSymbolicLink`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/file/Files.html#readSymbolicLink(java.nio.file.Path)) returns a target path without guaranteeing that target exists. [`Path.toAbsolutePath`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/file/Path.html#toAbsolutePath()) resolves relative paths according to the implementation's context, typically a filesystem default directory. Neither operation alone binds a relative link target to its link's parent or establishes object authority.

The [original Minecraft detector comparison](../minecraft/PACK-DETECTION.md) supplies a concrete macOS/APFS witness on selected Java 21 and 25 installations. After a real validator accepts an authored relative link target, the original detector reads that raw target from its working-directory context. An existing parent-relative target can therefore accompany a missing lookup, or a successful factory callback can receive a different owned working-directory path. The fixture opens no archive and uses an authored all/none matcher; production allowlist policy and full application reachability remain separate. This is not native Java 17, Windows, Linux, recursive-link, reparse-point, race, or mutation qualification.

An operation must retain the relevant raw path, intended anchor/provider, current binding evidence, validation policy, and consuming context as distinct facts. The consumer must use the context its validation actually covered. The detector models compare current behavior with a proposed parent anchor on quiescent fixtures; that proposal does not implement a general safe resolver or close a check/use race. String normalization, a callback's success, and a same-name or same-file Boolean cannot replace the missing context/boundary evidence. Existing protected-tree mutation rules still apply separately.

## CI and operational use

After compiling tracked models, run:

```sh
python3 host/filesystem/compare.py
python3 host/filesystem/verify.py host/filesystem/evidence/native-macos-20261125T155103537084Z/observed.json --controls
python3 host/filesystem/java_compare.py
```

The proof lane uses only retained data and models. `python3 host/filesystem/run.py` is the bounded native host fixture for macOS, Linux, and Windows CI; it preserves the raw record in `.build/filesystem/current.json` and emits a `filesystem-native-v1=` log record after verification. It starts no studied application or JVM. Selected runner results do not qualify Windows 11 LTSC, every Linux/macOS filesystem, or native race-safe mutation. New CI results must be inspected before advancing those evidence cells.

The completed [4e22c66 CI run](https://github.com/inherent-design/rules/actions/runs/45651889866) supplied three exact raw log records. [qualification.json](evidence/ci-45651889866/qualification.json) binds their hashes, actual profiles, job identities, and independent six-control replays. All four jobs passed; the proof job checked 210 Lean modules and 96 Bend files. No application or JVM was launched by these host fixtures.

| Runner and actual recorded system | Raw cases / guard projections | First case-only lookup | First Unicode-normalization lookup |
| --- | --- | --- | --- |
| [Windows Server 2025, AMD64, Python 3.13.17](evidence/ci-45651889866/windows-2025.json) | 10 / 11 | Same object | Unavailable; subsequent owned distinct-name control recorded |
| [Ubuntu runner, Linux 7.0.0-1020-azure, x86-64, Python 3.13.18](evidence/ci-45651889866/ubuntu-24.04.json) | 11 / 12 | Unavailable; subsequent owned distinct-name control recorded | Unavailable; subsequent owned distinct-name control recorded |
| [macOS runner, Darwin 24.6.0, arm64, Python 3.13.17](evidence/ci-45651889866/macos-15.json) | 9 / 10 | Same object | Same object |

The filesystem type was not measured in those records. An unavailable first lookup is not proof of physical separation, and a runner label does not qualify every volume or the selected Windows 11 LTSC baseline. These retained records are replayed without new filesystem collection in the proof lane; the three host lanes still perform their one bounded current fixture.

Before a destructive preparation, distinguish policy refusal, unresolved identity, a current overlap, a candidate, and owner-bound admission. Report the target and retained state in the operation's actual terms. Preserve source and partial outputs, and reconcile uncertain writes before retrying. Globally lowercasing names, obtaining a canonical string, displaying a warning, or receiving exit zero does not implement the missing native protocol.

No pnpm/empack fix, new generic transaction engine, installer, pack change, platform upgrade, or rollout is selected. The wider host and Minecraft consumer/native/rendering scopes remain unfinished.
