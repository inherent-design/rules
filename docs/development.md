# Development and verification

Use Python 3.11 or newer and Node 26. Bend 2.0.40 and Lean 4.34.0 are pinned in toolchain.json. The installer verifies release archive SHA-256 values and installs only under ignored .tools/. macOS and Linux can compile proofs. Native Windows verification consumes source-bound JavaScript emitted by the proof lane.

From a fresh clone:

```sh
python3 scripts/setup-tools.py
export PATH="$PWD/.tools/bend/bin:$PWD/.tools/lean-4.34.0-linux/bin:$PATH"
python3 scripts/check-rules.py
```

On macOS, use lean-4.34.0-darwin or lean-4.34.0-darwin_aarch64 in PATH according to the selected archive. Linux arm64 uses lean-4.34.0-linux_aarch64. Extracting the Lean archive requires tar with Zstandard support. The toolchain installer supports an explicit read-only archive cache.

scripts/check-rules.py compiles tracked Lean files with warnings as errors and checks tracked Bend files through the independent kernel. It never calls a package manager, browser, GUI, or sibling application.

The proof lane also runs the Minecraft codec, resource-selection, and artifact-version comparisons, the Java arena comparison, and the retained static host/API census check. These use pure models or retained facts; they do not execute Java or Minecraft. Owner-run collectors and private game inputs remain outside CI.

## Local checks

Install the development tools in mise.toml, then use:

```sh
mise run format:check
mise run check:ci
python3 scripts/check-meta.py
```

For changes to the host classifiers, run scripts/check-host or scripts/check-lifecycles with the qualified local adapters described in their documentation. Those commands have larger local evidence scopes. Shared examples that need sibling checkouts remain optional source comparisons. Their historical source pins can fail independently of the pure rules check.

## CI scope and cost

CI compiles and proves once on Ubuntu, emits two small JavaScript modules and their Lean vectors, and binds the handoff to source and output hashes. macOS, Linux, and Windows compare those rules and replay retained observations. POSIX runners execute small loopback, private PTY, filesystem, SQLite, process, and archive fixtures. Windows runs an isolated Win32 file/thread/handle fixture.

The host lane records the runner's actual environment. Windows Server 2025 runner evidence does not qualify a Windows 11 LTSC profile. macOS 15 evidence does not qualify the macOS 26 Metal profile. GUI, browser, external application, live registry, model inference, and sibling-project workflows are outside automatic CI.

The proof toolchain is cached by its pins. Superseded branch runs are cancelled. Documentation-only pushes skip the host matrix. Use local checks while developing and coordinate one reviewed push with other writers. Additional Java, browser, application, or desktop evidence belongs to a separately selected run.

## Delivery

This repository distributes source, models, and attributable research. The release workflow packages a selected tag's source and the small generated rule modules after the exact source passed the rules/host gate. It creates a checksum manifest and includes the license and notices. A release records its executed qualification scope. A new tag does not establish support for an untested application or profile.

Create releases manually from a reviewed tag. Ordinary pushes perform verification only. The repository has no application installer, npm publication, or deployment target.
