# Prism Java settings and launch checks

Prism 11.1.1 separates the configured Java path, inherited or instance settings, saved probe fields, and the later compatibility decision. This band executes selected source methods with Qt 6.12 and explicit adapters. It does not launch installed Prism, Java, or Minecraft.

The [source selections](../sources/prism-java-selections.json) pin commit `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. The [retained receipt](../evidence/prism-java-20261125T054951238691Z/receipt.json) records five completed fixture process groups and 37 cases: ten setting traces and 27 check/verification components. The source classes and seven selected method bodies are unchanged. An in-memory settings backend, injected checker result, parent/profile/context objects, and identity path resolver are fixture adapters. Supported Qt 6.12 differs from the installed launcher's Qt 6.9.3.

## Settings have separate read and write rules

[`MinecraftInstance`](https://github.com/PrismLauncher/PrismLauncher/blob/7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4/launcher/minecraft/MinecraftInstance.cpp) registers independent gates for Java location, arguments, and memory. Java path and compatibility bypass use `OverrideSetting`; saved version, vendor, architectures, and signature use `PassthroughSetting` behind the location gate.

| Setting operation | Override setting | Passthrough setting |
| --- | --- | --- |
| Read with gate off | Read global. | Read global. |
| Read with gate on | Read local if present, otherwise current global. | Read local if present, otherwise current global. |
| Set | Write local when different from the effective value, even if the gate is off. | Write local when gated on and different; always pass the write to global. |
| Reset | Remove local. | Remove local only when gated on; always reset global. |

An equal write does not create an explicit local value. In the fixture, setting an enabled override to the inherited global value leaves it absent; a later global change becomes effective. A passthrough reset with its gate off retains the dormant local value. Re-enabling the gate exposes it again. These follow the selected source classes with synchronous signal delivery; they do not establish concrete backend persistence or concurrent observer behavior.

The [Java settings widget](https://github.com/PrismLauncher/PrismLauncher/blob/7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4/launcher/ui/widgets/JavaSettingsWidget.cpp) saves each override group separately. Disabled path, memory, and argument groups reset their corresponding local values. Saving memory orders the entered minimum and maximum; saving arguments replaces newlines with spaces. Those widget operations were read, not executed. The generic setting fixture does not qualify full UI editing, notifications, or save/reopen.

## A successful check has several meanings

The inspected launch caller orders automatic Java selection, `CheckJava`, and `VerifyJavaInstall`. The fixture joins the last two selected methods after an explicitly supplied effective path/profile; it does not execute the automatic selector or complete task controller.

`CheckJava` first requires a discoverable executable and the checker library. Those guards still run when saved probe fields look reusable. Its cache signature is SHA-1 of the executable's modification time in milliseconds followed by the resolved path spelling. A signature change or an empty version, architecture, real architecture, or vendor requests another probe. This is a cache heuristic, not a content digest or process identity.

| Input or result | Observed selected-method outcome |
| --- | --- |
| Matching signature and four nonempty fields | Use saved fields, update runtime context, and succeed. |
| Probe cannot start | Fail before compatibility verification. |
| Probe returns invalid data | Report invalid output, retain saved fields and signature, update context, and succeed. |
| Probe returns valid fields | Write those fields and the signature through the settings objects, update context, and succeed. |

A valid instance probe can therefore update global saved probe fields as well as local fields. The subsequent path/signature check normally requires the appropriate probe again when another configured path is used. This band establishes the write behavior; it does not demonstrate a cross-instance launch failure or require replacing that cache.

`VerifyJavaInstall` reads the resulting saved version and architecture. An empty allowed-major list permits continuation. Otherwise it requires a listed major or the explicit compatibility bypass. A 32-bit runtime configured above 2,048 MiB produces an error-level diagnostic and continues to that major-version decision; the memory warning itself is not refusal. These are current policies, independent of whether an actual JVM will accept the eventual invocation.

The bitness cases deliberately inject the `32` field while retaining `aarch64` as the real-architecture field. They isolate the verifier's predicate and do not establish that Prism's actual Java checker can produce that pair. General discovery and cross-field consistency remain outside this fixture.

The retained invalid-output case has saved Java 21, a changed signature, and allowed major 21. The check warns, retains Java 21, and the later compatibility predicate succeeds. With no saved version, the source parser supplies major `0`; a nonempty requirement refuses it, while an empty list permits continuation. Successful verification alone consequently does not prove that the currently selected executable was identified successfully. These are controlled source-method observations, not reproduced full-launcher incidents or a claim that every invalid probe occurs in ordinary use.

## Reporting proposal and preservation decisions

Keep configured input, effective input and its origin, saved observation, current probe outcome, compatibility decision, and final process result separate. For Prism, an instance summary could show which settings inherit globally and which are explicit. After invalid output, retain useful historical fields but label them as saved evidence; avoid presenting the later predicate's success as fresh runtime verification. Preserve the existing warning-and-continue alternative unless a separately reviewed policy changes it.

The [Lean model](Java.lean) has 19 laws covering setting ownership, cache prerequisites, failed-check sequencing, historical evidence, memory warnings, and explicit bypass. Its proposed `evidence` classification distinguishes cached, current, unknown-with-saved-fields, and unavailable observations. That classification is a reporting proposal. It neither authenticates an executable nor changes launch admission. The [Bend model](Java.bend) has eight laws and independently executes the setting traces and runtime decision projection.

The keep-current alternative retains Prism's permissive invalid-output path and cache/write-through behavior, with clearer summaries and diagnostics. A structural alternative would bind saved probe fields to an explicit executable observation and origin rather than a group of independent settings. That affects global and instance readers, automatic selection, UI tests, saved configuration, and compatibility migration. This study does not approve that change or invent a new storage framework.

For empack, preserve the same distinction between pack requirements, selected host executable, observed Java properties, and actual invocation. Reuse the existing runtime evidence and typed outcomes. Prism's accumulated major list, download preferences, cache signature, and bypass are its own policies; they are not substitutes for empack's constraint rules.

## Checks and remaining qualification

The [independent observer](java_observations.py) verifies source Git blobs, copied classes, unchanged method excerpts, generated adapter, retained commands and streams, executable witness, framework/tool identities, field placement, and scoped diagnostics. The [pure comparison](java_conformance.py) matches both models to all 37 retained outcomes, refuses 19 unsupported or contradictory research inputs, and rejects four changed premises and four changed observation projections. Its line codec and version profile are deliberately bounded; they are not Prism's public schema or general Java parser.

```sh
python3 applications/prism/java_observations.py
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/prism/java_conformance.py
```

The original owner-run collection command was `python3 applications/prism/java_probe.py`. It uses disposable files and no JVM. A real discovery, automatic download/selection, current process protocol, filesystem resolver, settings backend and UI, multi-instance/concurrent writers, missing/stale metadata, architecture eligibility, cancellation, and supported-platform launch remain unqualified. Fresh GUI checks must use an isolated profile and coordinated desktop access. All nine complete Java/settings operations remain pending; these bounded component records do not replace them.
