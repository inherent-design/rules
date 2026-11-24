# Lifecycle profiles

The November 23, 2026 study extends the [baseline profiles](README.md). It reuses the same physical macOS host and the retained Ubuntu guest. Application versions are separate from their supporting host APIs.

| Profile | Executed surface | Qualification and open boundary |
| --- | --- | --- |
| macOS 26.7.1, build 25G241, Darwin 25.6.0, arm64 M4 Pro, APFS | Native Python 3.15.2 SQLite/process/namespace and archive fixtures | Real native file descriptors, transaction ordering, bounded reads, and private children. No physical crash, malicious kernel, all-descendant containment, or filesystem-wide GC claim. |
| Ubuntu 24.04.5 LTS, Linux 6.8.0-147-generic, glibc 2.39, arm64, ext4 | Same fixtures in the existing Lima 2.3.0 VZ guest | Actual Linux APIs in the guest. The guest has no host mounts or GPU node. No new image or package installation was needed for this pass. |
| Java 17, 21, and 25 on both hosts | Compile with each pinned javac and run the capture/save/retirement and exact-revision fixture | The exact JDK builds remain in the baseline profile. This new fixture uses the common baseline. Virtual threads and Java 25 scoped values have their separate prior tests. Windows JVM execution remains open. |
| Chromium 156.0.8078.4, Playwright 1.64.1, macOS arm64 | OPFS async writes and worker sync access, IndexedDB, Web Locks, and cross-origin fetch | Fresh isolated persistent contexts under loopback origins. A transient OPFS failure occurred in an ephemeral WebKit context despite API presence; persistent contexts worked. Presence and operation success remain separate observations. |
| WebKit 27.2, Playwright 1.64.1, macOS arm64 | Same browser-candidate sequence | This is the tested Playwright engine build. It does not qualify every Safari installation, browser setting, storage backend, or private mode. |
| VS Code 1.147.0, commit 8a14f0cc1b08d531eb83255ea3764ae22aa932b5, macOS arm64 | Native desktop editor, extension API, private filesystem provider backed by a local file | Executed under re:desktop with an owned user-data root. The observed save/dirty mismatch is provider-specific. It persists in the quiet-provider control after a 100 ms settle. No broad product defect or normal-file-provider conformance claim. |
| Windows 11 Enterprise LTSC 2024 | Proposed Win32/CRT host mappings and baseline cross-compiled probe | Native LTSC lifecycle and Java qualification remain unavailable locally. GitHub runner results must identify their actual Windows Server build and cannot be relabeled LTSC evidence. |
| Mobile or embedded | Extension point | Identify storage, task suspension, input, background lifetime, and unavailable capabilities before reusing a model. No native observation exists here. |

## Specification and implementation owners

OPFS access handles, writable streams, and entry operations have a [File System Standard](https://fs.spec.whatwg.org/) owner. Metadata transaction completion belongs to [IndexedDB](https://w3c.github.io/IndexedDB/). The tested origin-scoped serialization mechanism is [Web Locks](https://w3c.github.io/web-locks/). Response opacity and cross-origin behavior belong to [Fetch](https://fetch.spec.whatwg.org/). Their separate scopes explain why one transaction cannot automatically commit every participating store.

VS Code distinguishes native and virtual workspace capabilities in its [virtual workspace](https://code.visualstudio.com/api/extension-guides/virtual-workspaces) and [web extension](https://code.visualstudio.com/api/extension-guides/web-extensions) contracts. The prototype provider and native experiment exercise one particular adapter. A proposed portable editor must identify capabilities actually available for the requested effect.

The browser prototype does not implement a full archive codec, provider authentication, a native companion, signing, a real permission picker interaction, or a portable empack project format. Its import/retain/save/reopen/export boundary uses tiny controlled text assets to qualify the host sequence. The application owner separately qualifies local JAR/config interpretation and semantic Prism inventories.
