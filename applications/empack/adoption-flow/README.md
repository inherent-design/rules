# empack: observed files through native adoption

The installed 0.8.8 CLI records deliberate existing bytes without rewriting the selected payloads in these fixtures. URL adoption updates its accepted observation; local adoption also requires the installed bytes to match the separately declared local source. Missing or mismatched destinations are refused rather than repaired.

This fills the native observed-file gap left by the [source review](../AUTHOR-TRANSITIONS.md) and [supplied-value core admission study](../author-transitions/README.md). It does not qualify provider identification, all file roles, or an entire authoring workflow.

## Native workflow and effects

The [initial receipt](../../evidence/empack-adoption-flow-20261126T081334217208Z/receipt.json) covers eleven commands in three owned projects with separate state/cache roots. A [two-command continuation](../../evidence/empack-adoption-matching-local-20261126T081545037258Z/receipt.json) tests a discriminating local-source change on that same owned fixture. Its setup binds the prior receipt, command log, and complete terminal image before author edits. Neither original producer nor completed receipt was extended or rewritten.

The fixtures declare vanilla 1.21.1, one ordinary resource-pack placement, and two generated ZIP payloads of equal size but different content. URL roots explicitly accept observed bytes and use the reserved `example.invalid` origin. Local roots name a separate `vendor/observed.zip` source. No independent publisher digest or provider selection is declared. No engine build, game, consumer export, desktop, host installation, or live pack is involved. The pinned CLI checksum and [source identities/ranges](../../sources/empack-adoption-flow-selections.json) are separate evidence; no reproducible source-to-binary build is claimed.

| Requested operation | Observed outcome |
| --- | --- |
| First lock, only one of two declared roots selected | Refused before project/state/cache changes. |
| First lock, repeated logical key | Refused, with every measured scope unchanged. |
| URL first preview and apply | Preview proposes the observed digest; apply creates only `empack.lock` in the project. |
| URL unchanged preview | Succeeds with no measured effects and no detailed candidate rows. |
| URL bytes changed by the author | Preview shows a new accepted digest; apply changes only the lock. The authored URL and acceptance policy remain. |
| Local first apply | Creates the lock from matching source and destination bytes. |
| Local installed bytes differ from the separate source | Refused; neither copy is repaired or replaced. |
| Local unchanged preview | Succeeds with no measured effects and no detailed candidate rows. |
| Local destination removed by the author | Refused; adoption does not install the missing file. |
| Local source and destination both deliberately changed to matching new bytes | Preview and apply succeed; the new observation is recorded without rewriting either file. |

All thirteen command groups retired. Every preview and refusal leaves the captured project, explicit durable-state root, and cache unchanged. Successful applies change only the project's lock document and add durable operation records; cache images remain unchanged. Payload hashes, device/inode identity, mode, mtime, and ctime are equal before/after each command. The between-command author mutations are recorded separately. These are scoped observations, not a claim about every host effect or arbitrary descendants.

The lock retains the declared acquisition role, null provider selection, unknown dependency coverage, and an accepted content observation. The observation identifies the accepted bytes; it does not authenticate a publisher or prove Minecraft compatibility. The full lock bytes remain in the captures, including provenance for accepting changed tracked bytes.

## Model and independent readback

[Lean](Adoption.lean) expresses the selected admission order, proposed observation, preview/publication distinction, lock transition, and payload/source preservation, with twelve laws. [Bend](Adoption.bend) supplies nine laws. The [DTO decoder](AdoptionCase.lean) rejects unrepresented byte identities and inconsistent source/first-lock premises. The model has only two generated content identities plus absence; it is not a generic digest, filesystem, resolver, or authorization implementation.

The [reader](observations.py) derives requests from actual arguments, authored JSON, and before-state files. It reads results independently from exit/error text, reported after-digests, raw lock bytes, and scoped after-images. A deliberately narrow regular expression reads one controlled lock field; this is not a general YAML parser. It verifies document byte hashes and the captured image/mutation/continuation chain. [Replay](conformance.py) compares thirteen Lean outcomes and fifty Bend scalar values, with four changed-result, five DTO, three changed-input, and four raw-evidence controls.

Two unchanged previews print only a proposal heading and `Dry run complete - no changes applied`. Their candidate digests are **unreported** and excluded from that field comparison. The first reader incorrectly expected detailed rows after every successful command; it was corrected to preserve this visibility boundary. No native output was changed. Likewise, payload-preservation laws describe the model; only the independent native inode/time/hash observations support this bounded implementation behavior.

The isolated standard proof gate checks two Lean modules and one Bend file. Retained replay never invokes empack or a compiler. `ADOPTION_FORMAL` may name an isolated compiled-module directory; `ADOPTION_PRIVATE=0` excludes current CLI/helper and private Git-source revalidation explicitly. Ordinary CI may typecheck these models but must not run either native producer.

## Design and UX consequences

Keep adoption distinct from installation and deliberate selection update. An operator can review existing URL bytes and accept their new observation; for a local source/destination pair, selecting only one side's bytes is insufficient. Missing content needs a separate installation or restoration choice. The current refusal is correct for these cases, and no weaker content checks are proposed.

The local mismatch diagnostic, `Source differs from accepted lock observation`, omits the logical dependency, actual destination, source role, and expected/observed identity. A focused reporting improvement should preserve that typed cause while naming which installed path disagrees with which source evidence. Offer review of the two copies, an explicit source-install/update path, or adoption after intentionally aligning source and destination. Do not silently download, replace bytes, reinterpret a provider pin, or encourage blind retry. The missing-file error already names the installed path; it can additionally explain that adoption records existing files and will not install them.

Keep concise unchanged-preview feedback. If more detail is requested later, distinguish inspected current files from proposed document changes; zero changes is not evidence that no verification happened. There is no new adoption JSON contract in this study, and no CLI or API implementation was changed.

For the portable empack target, saved intent, declared source, installed observation, proposed lock, approval, and document publication retain separate owners. A portable draft may retain an unavailable local source, but it cannot create native adoption authority. Keep the current source-identity and placement checks when improving reporting.

## Remaining verification

The selected profile omits independently asserted digests, provider hash identification, exact authored provider pins, first-lock provider worlds, multiple members/placements, new `--from` declarations, no-op apply, symlinks, permission changes, stale approval, concurrency, and interruption/recovery. URL request absence was not instrumented; the reserved origin and local-observation source path do not prove general network isolation. Source/runtime validity and whole-project health retain their separate admission obligations. Public-only replay cannot revalidate unavailable private binaries or source objects.

The next authoring/release join should use these records rather than rerun this grid. Production diagnostic changes remain a separate implementation decision, and the full nine-application analysis remains active.
