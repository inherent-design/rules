# Generated Java command paths

The installed empack 0.8.8 reference exporter and the selected Prism 11.1.1 command parsers disagree on a Windows-style Java program path. The preparation parser preserves `C:\Program Files\Java\bin\javaw.exe`; the wrapper parser produces `C:Program FilesJavabinjavaw.exe`. POSIX and forward-slash controls preserve their program text in both roles. This is a reproduced producer/consumer token mismatch on macOS, not a completed Windows Prism launch test.

## Producer and consumer

The [source selections](../sources/prism-command-paths-selections.json) pin empack `0b4462e3032b4f09230b15329722eabefb7f574c` and Prism `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. The [preceding command study](COMMANDS.md) identifies the unchanged Prism variable-expansion and parser functions and their real Qt 6.12 build. Its protected parser executable is reused here; the collector's `parse` mode returns before any process launch.

One new, dependency-free vanilla author fixture runs the unchanged installed binary with private state and cache directories:

```sh
empack --state-dir <private>/state --cache-dir <private>/cache \
  --workdir <private>/project --yes --color never check --json
empack --state-dir <private>/state --cache-dir <private>/cache \
  --workdir <private>/project --yes --color never build --ad-hoc prism \
  --delivery references --environment client --updates snapshot --format zip
```

The [receipt](../evidence/prism-command-paths-20261125T173349259410Z/receipt.json) binds that actual export, its eleven members, the installed executable, native reader, parser, inputs, and original streams. This is an artifact build, not an engine compilation. The original archive and its bootstrap JAR remain owner-local; the exact [instance.cfg](../evidence/prism-command-paths-20261125T173349259410Z/instance.cfg) and member hashes are retained publicly. No game, bootstrap JAR, Java runtime, Windows executable, account, or personal instance is launched. Source agreement with the emitter is inspected separately; this is not a reproducible-build proof for the installed engine.

The native configuration reader uses the original Prism `INIFile` and `Json` implementations with empack's pinned consumer-probe source and real Qt Core/Network. It loads the exported ConfigVersion 1.2 file as effective version 1.3 without rewriting its bytes. Both command values survive that stage. Preparation and wrapper then expand the same injected `INST_JAVA` value, but consume different grammars:

- Preparation uses Qt `QProcess::splitCommand`.
- Wrapper selection uses Prism `Commandline::splitArgs`, where a backslash inside quotes consumes the following character as an escape.

Passing an INI readback therefore establishes the command value at one boundary. It does not establish the program token after expansion and command parsing.

## Retained observations

| Injected Java path | Preparation program | Wrapper program |
| --- | --- | --- |
| `/opt/Java Runtime/bin/java` | Preserved | Preserved |
| `C:\Program Files\Java\bin\javaw.exe` | Preserved | `C:Program FilesJavabinjavaw.exe` |
| `C:/Program Files/Java/bin/javaw.exe` | Preserved | Preserved |

These six observations come from the actual generated command strings, not reconstructed template literals. The raw input contains four single backslash code units; the mismatch is not a doubled-escape fixture mistake. All nonprogram arguments, including the invocation-file path and wrapper's terminal `--`, retain their expected values.

Prism's pinned `MinecraftInstance::getVariables` constructs `INST_JAVA` using `QDir::toNativeSeparators` on an absolute Java path. Qt documents [Windows separator conversion](https://doc.qt.io/qt-6.12/qdir.html#toNativeSeparators). That source supports investigating the normal Windows path, while a custom environment override can change the value. The study injects that value on Mac; it does not execute Windows path conversion, establish physical path equivalence, or qualify an installed Windows Prism process. Released 11.1.1 is the inspected target; unreleased upstream changes remain unreviewed.

## Rules and proposed correction

The [Lean model](CommandPaths.lean), [decoder](CommandPathsCase.lean), and [Bend model](CommandPaths.bend) describe only the inner payload of a quoted Java program token. Their correspondence profile excludes quotes and a trailing backslash. Eleven Lean theorems and six Bend laws distinguish preparation identity, wrapper escape consumption, separator loss, and a candidate round trip. The candidate doubles backslashes **after expansion at the wrapper consumer boundary**. It is a model-only transformation, not a production correction or complete parser proof.

The [pure replay](command_paths_conformance.py) reconstructs inputs from the captured requests and expected results independently from native parser output. Both models match all six program lists. Two changed-result controls must fail comparison, and five invalid schema/profile inputs must be refused. Original streams, source identities, retained config, and available archive/artifact bytes are checked without rerunning the programs.

A safe implementation decision must review the actual current wrapper contract and its callers before changing escaping or parser behavior. The static exporter cannot quote a future expanded Java path by knowing only the literal `$INST_JAVA`. The forward-slash control demonstrates a representable input; it is not approval to persist a stale Java path, normalize every argument, or add a new launcher. Keep hook and wrapper grammars distinct. A later Windows fixture should verify the actual executable selected through Prism, including paths with spaces, native separators, and supported custom environment values. No product fix or broader launcher redesign is selected here.

## Harness and availability limits

The first private fixture precreated state with mode 0755. The engine correctly refused it before a build; the [excluded run](../evidence/prism-command-paths-20261125T173202810392Z/failure.json) remains intact. A fresh fixture uses mode 0700. Its initial collector then stopped after successful check and export because an authored two-MiB archive limit was too small for the generated bootstrap JAR. The original failure remains, and a frozen continuation reads the same archive with the emitter's eight-MiB JAR bound and separate small-member bounds. Check and build were not repeated, and no functional assertion was weakened.

Twelve command groups in the completed capture and the excluded refusal group were observed absent after completion. Proxies refused outbound acquisition; they are not an OS network sandbox. Owner-local compiler, framework, helper, and archive availability is reported separately from portable retained-data comparisons. Cleanup or future reruns must preserve that distinction and the failed collectors' original evidence.
