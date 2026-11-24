# Package publication, acknowledgement, and later failures

A failed publication command does not prove that a version is absent from the registry. A successful upload does not prove that subsequent hooks succeeded. This band compares npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 with Node 26.13.1 on the pinned macOS arm64 profile. It complements the [lock-mode](LOCK-MODES.md) and [script-policy](../js-scripts/README.md) studies without treating their unrelated state as publication evidence.

## Domain and selected flow

The publisher owns a package directory, its declared name/version, selected archive bytes, and local hooks. The registry owns whether a version was accepted and what bytes that record names. The network response is the client's evidence about the exchange. The command's final status also includes work after that exchange. These facts need separate identities and owners.

The fixture creates one dependency-free package per manager with five selected versions, a `files: [index.js]` list, and a generated excluded file. A private loopback HTTP server accepts npm-style publication documents and refuses overwriting existing versions. Its own acceptance record, received archive, completed or deliberately lost response, and the client's output are retained separately. It is a controlled registry adapter, not a real npm deployment or proof of authentication, durable storage, replication, or availability to another consumer.

All tool entrypoints are hash-checked before collection. The publisher has private HOME, configuration, cache, and temporary directories. Registry settings point to the owned `127.0.0.1` endpoint; the literal authentication marker works only in this fixture and is not a real credential. No public registry, account, package, or user project is involved. The selected profile disables configured request retries. The received requests confirm at most one PUT per command. This does not characterize default retry policies.

| Purpose                                 | npm                                                    | pnpm                             | Yarn Berry                                                              |
| --------------------------------------- | ------------------------------------------------------ | -------------------------------- | ----------------------------------------------------------------------- |
| Publish the current directory           | `publish --json`                                       | `publish --no-git-checks --json` | `npm publish --json`                                                    |
| Prepare without uploading               | Add `--dry-run`                                        | Add `--dry-run`                  | Add `--dry-run`                                                         |
| Check an existing version before upload | Current ordinary command performs its version precheck | Not observed in this profile     | Available separately through `--tolerate-republish`; not exercised here |

The collector also supplies private registry/configuration arguments. pnpm's Git checks are explicitly disabled for this disposable, non-Git project. Yarn receives one dependency-free `install` to initialize its workspace state. Neither preparation is a test of author Git policy, dependency resolution, or a real registry's permission model.

## Native observations

The [primary receipt](../evidence/js-publication-20261124T122142272675Z/receipt.json) and [trace](../evidence/js-publication-20261124T122142272675Z/trace.json) contain 28 invocations. A separately frozen [boundary follow-up](../evidence/js-publication-20261124T122243777223Z/receipt.json) adds 10. These include six help calls and two Yarn initialization calls, leaving 30 publication outcomes. The original primary producer predates the optional boundary-only flag; both exact producer files and their hashes remain intact.

| Operation                                                | Server observation                                                | Command observation                                                                                                      |
| -------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Dry run, no hooks                                        | No PUT and no version added                                       | All exit 0. npm makes registry reads; pnpm and Yarn make no requests to this fixture.                                    |
| Ordinary publication                                     | Version and archive accepted; HTTP 201 sent                       | All exit 0.                                                                                                              |
| Publish the same version again                           | Existing record retained                                          | npm refuses after a GET without PUT; pnpm and Yarn receive 409 from their PUT and exit 1.                                |
| Explicit fixture rejection                               | PUT receives 403; no new version                                  | All exit 1.                                                                                                              |
| Accept version, then close connection without a response | New version and bytes retained; no acknowledgement reaches client | All exit 1 with transport errors. A separate owner GET confirms version 3 exists.                                        |
| Retry that lost-response publication                     | Existing version retained                                         | npm's precheck refuses; pnpm and Yarn receive 409. Their retry archives have the same digests as the accepted originals. |
| Dry run with generated hooks                             | No PUT and no version added                                       | All exit 0 and append the selected local hook log.                                                                       |
| Acknowledge upload, then fail a selected later hook      | New version and archive remain accepted                           | npm exits 7; pnpm and Yarn exit 1.                                                                                       |
| Close connection before acceptance, separate follow-up   | No version added                                                  | All exit 1 with transport errors.                                                                                        |
| Fail generated `prepack`, separate follow-up             | No PUT                                                            | npm exits 7; pnpm and Yarn exit 1. Local hook effects remain.                                                            |

The two loss cases establish the ambiguity directly: the same transport-failure status occurs with and without a server-side record. The owner knows the injected boundary; the client does not acquire that knowledge from its socket error. No inference about an arbitrary server's durable acceptance follows from a TCP write or this fixture's in-memory record.

The nine accepted archives are retained with their exact publication documents. The replay independently recomputes SHA-1, SHA-512 SRI, archive SHA-256, and member hashes. Every selected archive contains exactly `package/package.json` and `package/index.js`; the generated excluded file is absent. No tarball is extracted onto the host. This qualifies these fixed generated inputs, not general packlist rules, traversal defense, symlink policy, or arbitrary manifests.

The generated hooks append their names before an optional exit 7. They intentionally have effects; the model's `hooks` bit refers to these scripts, not the proposition that every declared hook necessarily writes a file. Their observed order is:

- npm: `prepublishOnly`, `prepack`, `postpack`, `publish`, `postpublish`.
- pnpm: `prepublishOnly`, `prepublish`, `prepack`, `postpack`, `publish`, `postpublish`.
- Yarn: `prepublish`, `prepack`, `postpack`.

The selected failing later hook is `postpublish` for npm/pnpm and `postpack` for Yarn. Yarn's `postpack` runs after the publication callback through `finally`; npm and pnpm finish packing before upload and run their separate publication hooks afterward. These are different boundaries, not renamed equivalents. All three execute the selected hooks during their publication dry run. The before-upload control stops at the generated `prepack` failure.

## Source comparison and executable laws

[Twelve pinned source identities](../sources/js-publication-selections.json) record inspected ranges and exclusions. npm's command and `libnpmpublish` implementation match the installed distribution byte-for-byte. Entrypoint hashes and upstream pins for pnpm/Yarn do not establish reproducible source-to-binary correspondence.

npm's command creates its tarball in memory, performs the selected registry version check, calls `libpub`, and then runs `publish`/`postpublish`. A `dryRun` gate surrounds the upload, not the entire workflow. Its completed JSON artifact summary is emitted before those later hooks. In the native late-hook failure, stdout contains that summary followed by a separate error object, and stderr identifies `postpublish`. That is not one valid JSON document; consumers need the actual output contract rather than assuming a whole-stdout object.

pnpm already has `PublishFailure { published, error }`. Its directory path retains the accepted summary when a later hook fails. The single-package caller then uses `.map_err(|failure| failure.error)`, dropping that recorded publication fact before rendering the error-only JSON observed here. Its optional availability wait also retains a published summary on wait failure in source; that wait is disabled by default and was not executed in this band. Preserve acceptance, later availability, and local hooks as different facts. The pnpr-specific conflict confirmation checks release identity through a separate route and is deliberately outside this ordinary npm-style fixture. A plain 409 is not evidence that arbitrary submitted bytes are the existing release.

Yarn emits a structured `published: true` record after the successful PUT and before the `postpack` finalizer. The late failure retains that record alongside its named postpack error and final status 1. Its dry-run record explicitly says `published: false`. Preserve those useful distinctions. The source's `--tolerate-republish` precheck skips when the version key exists; that alone is not an archive-equivalence proof. The option was inspected but not run.

[Lean](Publication.lean) proves 16 laws, and [Bend](Publication.bend) checks seven. The models project this admitted single-package ordering, with separate sent, accepted-here, existing-remote, acknowledged, local-effect, and final-status fields. They do not implement an archiver, registry, HTTP client, script runner, or authorization mechanism. The two loss points have different server facts but the same proposed client claim, `unknown`. Rejected means this request was refused; it does not mean the version is absent. A post-upload hook failure preserves acknowledgement and the accepted version. A pre-upload failure prevents the PUT while retaining its local effects.

The [pure replay](publication_conformance.py) matches both models against all 30 retained publication outcomes and checks the nine archive inventories, hook sequences, response boundaries, independent owner reads, and immutable retry evidence. Seven invalid research inputs are refused, including unsupported profiles, unknown loss/hook boundaries, impossible selected hook settings, and loss controls combined with an already existing version. Those are decoder boundaries, not claims about what the products reject. `Claim` is a proposed reporting projection; it is not a current CLI field measured by the replay.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-peers/publication_conformance.py \
  applications/evidence/js-publication-20261124T122142272675Z \
  applications/evidence/js-publication-20261124T122243777223Z
```

Compile `Publication.lean` into `.build/formal/applications/js-peers/Publication.olean` first. The native collector is `applications/js-publication-probe.py`, optionally with `--loss-boundaries`; it is owner-run evidence collection and never ordinary CI. Both server threads were joined and listening sockets closed. Their private configuration, caches, and generated packages remain under ignored capture `work/`, with frozen producers, streams, receipts, and archives preserved separately. Moving retained work after execution does not promise that its former absolute paths remain usable.

## Application-specific proposals and preservation decisions

**npm:** preserve publication hooks, numeric failure status, archive identity, and existing private/version checks. Add a completed-publication fact to the final error presentation when `libpub` returned successfully but a later hook failed: “Published name@version; postpublish failed.” For a lost upload response, say publication is unconfirmed and suggest checking the target registry's version and integrity before retrying or choosing a new version. A version key alone cannot prove byte equality. Reuse the existing publication metadata and reporter rather than another resolver, publishing engine, or error hierarchy. Any JSON adjustment needs an explicit stream/object compatibility decision and tests for current consumers; do not silently replace established fields. Keeping current behavior is defensible for callers that already interpret the complete stream, but its generic network/proxy advice does not explain this publication-specific uncertainty.

**pnpm:** carry the already-existing `PublishFailure.published` information across the single-package CLI boundary and include it beside the hook cause in human/machine output. This is a retention and presentation candidate, not a request to mark the whole command successful or roll back a published immutable version. Preserve dry-run hook semantics and `--ignore-scripts`; make their scope clear. Keep ordinary npm registries separate from pnpr's stronger release-confirmation mechanism and from an optional availability wait. A keep-current alternative is explicit operator documentation, but that leaves automation unable to recover an accepted summary from the observed single-package error JSON. Verify both single and recursive callers, wait failures, and JSON consumers before adoption.

**Yarn:** preserve its acknowledged `published` event and explicit dry-run `published: false` event. Improve the final headline to connect the already-published version to the later postpack failure. Keep `postpack` finalization semantics unless a separately reviewed design changes their compatibility contract; moving hooks casually could change artifact preparation or cleanup. A lost-response error should identify uncertain publication without asserting absence or recommending destructive cleanup. Keep-current remains reasonable for structured stream consumers. Verify hook failures while another error is active, tolerate-republish identity expectations, staged publication, and text output before a broader change.

For empack, these observations support retaining selected artifact identity, local operation outcome, remote acceptance evidence, and later pointer/channel publication as separate records. They do not qualify empack's live publication flow or authorize a publishing service or URL redesign. Reuse existing typed receipts and host finalization witnesses when the corresponding feature is modeled; do not manufacture remote evidence from a local command exit code.

## Remaining qualification

Real registry policy, credentials and token custody, TLS, redirects, authentication challenges, provenance, stage approval/rejection, tags, availability polling, workspace batches, registry replication, process interruption, durable server state, concurrent writers, default retries, and other platforms remain pending. Dry-run file effects are measured only through the generated hook log and selected project inputs; global nonmutation is not claimed. No package was published to a public service, no production source changed, and no entire feature family is qualified by this band.
