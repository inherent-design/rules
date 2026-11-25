# Template interpretation and generated configuration

Templates transform captured author inputs into a consumer-specific candidate. They do not grant publication permission or certify that a launcher, shell, or game interprets arbitrary output correctly. This band keeps current source, installed CLI builds, scalar encoders, and Java consumers separate. It changes no empack implementation or project schema.

## Evidence and source scope

The [source selections](../sources/empack-template-selections.json) pin empack `0b4462e3032b4f09230b15329722eabefb7f574c`. The [source collector](template_encoding_probe.py) executes the unchanged `template_address` body against retained real core path types and the complete standard-library encoding module. Its standalone error `Result` alias and address visibility are explicitly adapted; it does not compile `WorkspaceSnapshot`, Handlebars, or the engine. The [receipt](../evidence/empack-template-encoding-20261125T150106975825Z/receipt.json) identifies the compiler, reused library, source ranges, generated driver, binary, and original streams. Eighteen address inputs and sixteen UTF-8 scalar inputs completed.

The [installed-CLI collector](template_probe.py) creates one dependency-free vanilla author project, synchronizes it normally, and builds eleven standalone bundled Prism snapshot ZIPs. The [native receipt](../evidence/empack-templates-20261125T145924167329Z/receipt.json) binds the unchanged installed 0.8.8 binary, inputs, commands, original output, source snapshots, archive members, attributes, and process-group observations. These binary observations are not a reproducible-build proof for the inspected source commit. No launcher, game, bootstrap, installer, or live project was selected. Every recorded command returned and its process group was absent afterward.

An [earlier fixture](../evidence/empack-templates-20261125T145859236192Z/disposition.json) used a pack name containing double quotation marks. Artifact-name validation refused every build before template rendering. Its original producer and eleven refusals remain retained, contribute zero template cases, and were not rewritten. The corrected name keeps an apostrophe and Unicode while satisfying artifact naming.

## Addressing, selection, and rendering are different decisions

Only `common/`, `client/`, and `server/` address template layers. Addressing removes one terminal, case-sensitive `.template` suffix and validates the resulting portable destination. A suffix in a parent directory is not removed. Unknown top-level names and inputs without a layer separator are ignored. Recognized invalid destinations fail; an ignored layer does not obtain a destination merely because its filename is portable.

The suffix selects an initial rendering mode. `.template` requires UTF-8 and renders through Handlebars. An ordinary file uses `TextOrBinary`: valid UTF-8 is rendered, and invalid UTF-8 is copied exactly. Consequently, a `.txt` extension does not promise literal content. API callers can override a captured input's mode to `Copy`, which preserves even template-looking UTF-8 bytes. That override does not change destination addressing, and unknown mode-map paths fail. The CLI cohort uses default modes; it does not exercise an explicit API override.

For the selected client, common files provide the base and exact client destinations replace them. Same-layer duplicates and aliases fail before rendering. Final cross-layer aliases and file/ancestor conflicts also fail. A replacement chooses the whole side file; it does not render or merge the displaced common body. Required semantic validation and selected-byte acquisition remain separate from that optimization.

| Native input | Observed outcome |
| --- | --- |
| Common, client, and server copies of one destination | Client bytes selected; common and server bodies absent from that output |
| Ordinary UTF-8 `{{NAME}}` and invalid-UTF-8 binary | Text rendered; binary bytes copied |
| Unknown variable in a selected ordinary or `.template` file | Refused with the source template path |
| Invalid UTF-8 in a selected `.template` file | Refused |
| Duplicate destination, file ancestor, or cross-layer case alias | Refused |
| Invalid common body shadowed by a valid client file | Selected client bytes published |
| Invalid binary body on the unselected server side | Ignored for this client build |
| Unknown top-level template layer | Ignored |
| Template destination already supplied by selected game content | Refused |

Four builds succeeded, and seven were refused. All eleven preserved authored file bytes, modes, and modification times. Every refused build preserved the preceding `dist/` entries and file snapshots. These are scoped author/artifact effects, not a claim of no host-state or cache activity. The successful baseline preserved its generated script's `0555` mode and exact binary bytes. Running that one controlled generated `printf` under `/bin/sh` recovered the original apostrophe/Unicode pack name. It is not arbitrary author-script safety or Windows shell qualification.

## Output-language helpers are explicit

The renderer uses strict lookup and disables HTML escaping. A filename does not infer a quoting language. Plain `{{NAME}}` inserts text; authors must use the helper appropriate to the output position. `shell_quote` produces one POSIX shell argument, `ini_quote` produces a QSettings-style scalar, and `properties_value` produces a Java-properties value fragment. None is a general HTML, JavaScript, command-line, key-name, or whole-document sanitizer.

The scalar corpus covers leading variant markers, NUL/control characters, adjacent hexadecimal characters, spaces, separators, quotes, backslashes, composed/decomposed Unicode, and supplementary code points. Independent Python byte projections match the sixteen actual Rust INI and properties outputs. This checks the selected values, not arbitrary Unicode-table equivalence or a formal proof of the encoders.

The [properties consumer](TemplatePropertiesProbe.java) reads those exact retained encoder bytes with both `Properties.load(InputStream)` and `Properties.load(Reader)` on installed Java 17, 21, and 25. All [96 readbacks](../evidence/empack-template-properties-20261125T150217339816Z/receipt.json) recover the original UTF-8 value and exactly one key. The source is compiled once for Java 17; runtime, compiler, class, and input identities are recorded. This is Java-properties interpretation, not a server archive, game launch, Java 8 test, or cross-platform matrix. INI outputs were not passed through Prism or Qt in this band; the existing product consumer-probe obligations remain separate.

## Models and replay

[Lean](Templates.lean) defines address/mode decisions, side precedence, ordered preparation guards, and explicit needed-unknown refusal through fifteen laws. [Bend](Templates.bend) provides six corresponding laws. The [decoder](TemplatesCase.lean) refuses unsupported schemas and modes and missing required evidence. The stage numbers are study tags, not CLI exit codes.

The [replay](template_conformance.py) checks eighteen measured address outcomes and eleven measured preparation stages against both models. Sixteen selected-body decisions are separately labeled source-fact projections: a small literal/`NAME`/`shell_quote NAME` interpreter supplies them. It is not a replacement Handlebars parser or another native API stream. Actual successful archive bytes are independently compared with the selected fixture interpretation. The replay also checks scalar bytes, Java readbacks, source/artifact hashes, unchanged author/previous-artifact snapshots, the excluded fixture, and changed-observation/decoder controls.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/template_conformance.py
```

Compile the formal modules first. Replay executes only the formal adapters and reads retained evidence; it never reruns empack, Rust compilation, Java, a shell script, or an importer. Available owner-local binaries are hash-checked, with generated source independently reconstructed from Git objects. Their absence in a public checkout does not create a fresh native observation.

## Interface and extraction decisions

Retain one template service shared by native and portable builds. A virtual source must carry its exact captured bytes and attributes, address, layer, explicit mode override, selected/displaced provenance, metadata basis, and required operation capabilities. Recipe composition still owns generated hooks and final consumer validation. The native writer, mutable source tree, and cache lease do not move into a browser merely because rendering is pure enough to extract.

Show the effective mode and destination together in a detailed build or editor view. Distinguish a selected literal copy, selected rendered text, automatic binary copy, displaced fallback, and unrelated layer. Make the existing UTF-8-dependent default visible before suggesting a new literal-file policy. No default-mode or schema change is selected here.

Keep the useful source-path context already present for missing variables and explicit binary failures. The duplicate-output error names neither source, and the alias error names only the destination. A reporting improvement should retain the colliding source pair and destination through existing contextual diagnostics, with escaped untrusted labels, without weakening refusal or adding routine warnings for intentional side precedence. Unknown top-level directories may deserve an author-facing explanation in detailed output; changing them into universal errors is not justified by this fixture alone.

## Dependency updates and remaining work

The source lock selects Handlebars 6.4.4. An upgrade must exercise actual registered helpers, strict missing-value behavior, no-escape output, expression syntax, and bounded writes through the candidate engine or CLI. Passing the standard-library source adapter alone cannot qualify that dependency. Encoder or Qt/JDK updates also need original-value consumer readbacks, including scalar types and adjacent escape behavior; preserving exact encoded strings alone is insufficient when consumer grammar changes.

Keep per-input, per-output, total-output, entry-count, cancellation, source revalidation, and final publication limits distinct. The current source checks and bounded writer were inspected; this cohort does not qualify their boundary values or interruption windows. Handlebars input/output limits do not establish a whole-process memory or CPU quota. Server composition, managed Prism hooks, API mode/value overrides, arbitrary expressions and syntax errors, template-copy fallback attributes, stale captured files, browser rendering, and other hosts remain open. No new product correctness defect is established by this band.
