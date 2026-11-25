# Virtual asset entries and physical backing files

The selected Minecraft linked filesystem gives resource names a virtual tree backed by ordinary paths. Its equality, existence, attributes, reads, and close behavior answer different questions. Across five original clients, two logical names backed by the same file compare as different, a registered entry remains present after its backing file is deleted, and later reads see changed backing bytes. These are bounded provider observations, not a Minecraft defect or a physical protection boundary.

This band follows the [host filesystem guard](../filesystem/README.md) into an actual resource-host implementation. It adds [17 Lean laws](LinkedFilesystem.lean), [nine Bend laws](LinkedFilesystem.bend), and a [nullable research decoder](LinkedFilesystemCase.lean). Resource identifiers, virtual nodes, backing objects, verified content, operation authority, and consumer lifetime retain separate contracts.

## Selected implementations and actual consumers

[linkfs-sources.json](linkfs-sources.json) records **105 original/named class pairings and 45 private decompiler views** across Java Edition 1.21.1, 1.21.4, 1.21.5, 1.21.11, and 26.3. Each profile binds its client, metadata, mappings where applicable, original class members, named inspection classes, source views, decompiler, inspection JDK, frozen producer, and private receipt. Locators identify selected methods or calls; a matching method name is not execution evidence. The original binaries and source views stay private.

| Surface | Inspected contract | Qualification boundary |
| --- | --- | --- |
| `LinkFileSystem.Builder` | Builds a virtual tree from logical path components and backing paths. Registration does not itself read or verify those bytes. | The native fixture uses three file registrations and two filesystem instances. Arbitrary builders, collisions, and path grammar remain open. |
| `LinkFSPath.equals` and provider `isSameFile` | Require the same filesystem object; real nodes compare their contents objects, while missing/relative nodes compare parent and name. The provider checks both path types before equality. | Canonical fixture nodes only. Neither matching store labels nor shared backing paths merge distinct logical nodes. |
| `checkAccess` and `readAttributes` | Existence is virtual contents presence; basic attributes are dummy file/directory values. Attribute reads resolve an absolute virtual path, while the selected existence check uses the supplied path directly. | Permissions, arbitrary attributes, links, and general access-mode combinations are not modeled. |
| `newByteChannel` | Resolves a mapped file and delegates its read to the backing provider. The selected write/create/append options refuse. | One-byte A/B/absent states only; other IO errors and concurrent changes remain open. |
| Filesystem lifecycle | `close` has no body, `isOpen` returns true, and `isReadOnly` returns true. | This provider's close call does not revoke its paths or freeze backing bytes. It is not a Java arena or generic resource-scope contract. |
| `IndexedAssetSource.createIndexFs` | Reads an index, maps each logical filename to an object path derived from its hash text, and builds the linked root. Selected JSON/IO catches log errors and still reach the final build. | Source-only. Index parsing, malformed hashes, downloads, hash verification, partial-index behavior, and an actual asset index were not exercised. The path derivation is not a content-verification proof. |
| `ClientPackSource` | Passes the external asset root into the vanilla resource builder; development-only exploded-pack discovery separately checks the default filesystem. The selected 26.3 builder also introduces an explicit layer step. | Source-only. Builder ordering and full pack selection need their own consumer comparisons. |
| `FolderRepositorySource.FolderPackDetector` | Its selected ZIP supplier accepts the default filesystem or `LinkFileSystem`, while directory suppliers have a separate construction path. | Source-only. Supplier acceptance does not qualify archive opening, validation, reload, or rendering. |

The dummy-attribute class moved packages between these selected implementations. The source collector initially selected only its newer package and refused the older source selection before launching a decompiler. That failed selection, frozen input, and disposition remain private; the corrected collector selects both package locations. No original API outcome was changed to accommodate it.

## Original API observations

[LinkFSProbe.java](LinkFSProbe.java) constructs one fixed authored plan through original builders and public Java filesystem interfaces. Official name bindings locate the original filesystem and builder; the observer does not substitute a reimplemented provider. Each exported receipt identifies 15 loaded original classes, actual JDK/tools/libraries, compiler output, separate raw channels, and retired process groups.

| Selected client | Runtime used for the original API fixture | Captured snapshots |
| --- | --- | --- |
| 1.21.1 | Recorded Temurin 21, macOS arm64 | [23 snapshots](evidence/linkfs-native-1.21.1-20261125T163537038277Z/observed.json) |
| 1.21.4 | Recorded Temurin 21, macOS arm64 | [23 snapshots](evidence/linkfs-native-1.21.4-20261125T163538338427Z/observed.json) |
| 1.21.5 | Recorded Temurin 21, macOS arm64 | [23 snapshots](evidence/linkfs-native-1.21.5-20261125T163539600229Z/observed.json) |
| 1.21.11 | Recorded Temurin 21, macOS arm64 | [23 snapshots](evidence/linkfs-native-1.21.11-20261125T163540951708Z/observed.json) |
| 26.3 | Recorded Temurin 25, macOS arm64 | [23 snapshots](evidence/linkfs-native-26.3-20261125T163340102803Z/observed.json) |

The observer compiles for Java 21. The Java 25 source-inspection tool is separate from the fixture runtime. This does not extend Java 17 native qualification or establish another host's backing-provider behavior.

All five profiles agree on the fixed plan:

| Operation | Observed result | Consequence |
| --- | --- | --- |
| Same path object, including an unmapped path | Same-file result true. | Logical equality does not establish backing existence. Independently reconstructed equal missing paths were not a separate native case. |
| Distinct logical paths sharing the same backing file | Provider and `Files.isSameFile` return false. | Logical inequality does not establish physical separation. |
| Two filesystem objects with the same display label | Same-file result false. | Display labels are not namespace identity. |
| Registered file with absent backing | Virtual existence true; read throws `NoSuchFileException`. | Entry presence is not readable content. |
| Selected relative path to a registered file | Existence false; read returns A. | These two APIs resolve the virtual path differently. |
| File attributes | Size zero while a read returns A. | Dummy metadata is not measured backing size. |
| External owned write A→B, then deletion | Existing link reads B, then throws `NoSuchFileException`; virtual existence remains true. | A read-only namespace does not make backing storage immutable or retained. |
| Write-open request | `UnsupportedOperationException`. | This selected provider route refuses the write; other owners can still change the backing. |
| Close, restore owned backing, read again | Filesystem still open; read returns A. | Close is not a revocation or retirement receipt here. |

The root listing is independently checked against the three registered heads. The optional backing-file-key observation is retained separately; it is not a theorem about inode lifetime. The helper restores the original **bytes** after deletion and recreation, not the original inode or timestamps. These are 115 captured API/control snapshots, not a count of every setup or method invocation. No game, real asset index, user pack, GUI, world, renderer, or device was started.

## Model and adapter limits

[linkfs_conformance.py](linkfs_conformance.py) compares **105 selected results** with both models and checks five root listings plus five optional file-key facts separately. It rejects 13 malformed or unresolved requests and eight changed observations. Four examples admit an unused unknown input only after an earlier fact determines the result. [The receipt](evidence/linkfs-conformance.json) binds the exact inputs and programs.

The decoder keeps filesystem identity, node identity, absolute-path status, registered-entry presence, backing-file mapping, and backing state separate. Missing required evidence refuses; a known different filesystem does not need node identity, and a known unmapped file does not need backing-byte evidence. Selected backing states are absent, A, and B. Boolean, byte, zero-size, and exception outcomes have distinct codes.

Both models receive the same manually inspected Python projection of the frozen Java plan. The frozen Java program's hash is checked against the maintained plan, but adapter fidelity, Java semantics, decompiler translation, all path shapes, and arbitrary byte IO are not formally proved. The constant open/read-only/close observations share one selected model operation; this is not a general lifecycle interpreter.

After compiling the tracked modules, the ordinary proof lane can run:

```sh
python3 host/minecraft/linkfs_conformance.py
```

This command replays retained data and proof models without launching Java or Minecraft. `linkfs_sources.py --check` additionally verifies the owner-local private source inputs. `native_linkfs.py`, `inspect_linkfs_sources.py`, and `export_linkfs.py` are explicit local collection/audit procedures, not ordinary CI actions. Earlier draft proof/typechecking errors were corrected without changing the observations or relaxing a negative control.

## Host contracts and selectable design

The common guard already requires evidence whose scope matches the intended protected set. A logical provider equality result cannot fill a physical-object or ancestry field merely because both use “file” terminology. The additional Lean law composes this case with the existing wrong-scope refusal. It does not introduce a new generic writer or pretend to supply its missing mutation-boundary protocol.

A possible resource-host adapter should report the logical resource ID and provider incarnation, selected pack/source, backing location when available, observed read/verification result, and relevant retained ownership independently. Diagnostics should distinguish a missing virtual entry, unavailable backing, and failed content verification, while preserving any earlier usable state. A zero dummy size must not be presented as the actual download or memory cost. These are design requirements to evaluate against the actual consumer, not adopted Minecraft/mod API changes.

For a future combined provider, choose explicitly between sharing mutable backing paths, taking an immutable verified snapshot, or holding an established retention lease. Each has different storage, update, and retirement obligations. A `close` method name, cached path, successful builder call, or content-looking pathname cannot supply those guarantees. Selected resource reloads, open-channel lifetime, provider coexistence, native replacement/ancestry protocols, full ZIP suppliers, and renderer retirement still need their own evidence. Nothing in this band selects a backport, installation, pack change, or production patch.
