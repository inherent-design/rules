# Restricted downloads: ambiguity and bounded discovery

This follow-up to [saved builds](PENDING.md) exercises installed empack 0.8.8-beta on this macOS arm64 host without changing product code or compiling the engine. The [setup](../evidence/empack-discovery-cli-20261125T163044602818Z/setup.json) pins the installed executable separately from six current-source files at `0b4462e3032b4f09230b15329722eabefb7f574c`. Source/binary equivalence is not established.

Four private fictional packs each have one manual input. The independent authored-wire fixture is admitted by the real CLI before testing. These are inert 128-byte resource-pack payloads, not usable packs or provider records. The [test vectors](../sources/md5-collision-inputs.json) retain the two public blocks from [Peter Selinger's MD5 collision demonstration](https://www.mscs.dal.ca/~selinger/md5collision/). Python independently verifies their equal MD5 and different SHA-256 values. No collision generator or executable example is used.

## Observed outcomes

| Request | Native result |
| --- | --- |
| Discover two different payloads matching the same MD5 and size | Warns that different candidate bytes match; saves the unresolved build and publishes nothing |
| Explicitly select the second payload afterward | Verifies the declared weak assertions and publishes those selected bytes |
| Discover two copies of the first payload | Collapses identical content to one candidate and publishes it |
| Add the first payload's SHA-256 assertion while keeping MD5 | Rejects the other collision payload as a match and publishes the intended bytes |
| Scan 10,001 direct entries, including one matching payload | Refuses the entry limit and returns no published subset |
| Supply that matching file explicitly afterward | Verifies it without requiring a complete directory scan and publishes it |

The [capture](../evidence/empack-discovery-cli-20261125T163044602818Z/results.json) retains 18 fresh CLI commands: four check/suspend/list setups and six discovery/association decisions. All four resulting mrpacks were independently opened and their member bytes compared. Every owned command group retired; the final exact-work-path process scan was empty. Inputs, private state/cache, and the 10,001-entry directory remain retained. Their measured allocation was 172 KiB, excluding filesystem metadata not reported by `du`.

The ambiguity path's nonzero exit is not a zero-effect promise. Its saved recipe retained the same bytes while its file identity and timestamps changed. The entry-limit refusal changed none of the captured scopes. Successful publication changed project, state, and cache. Compressed before/after images preserve regular-file digests, links, modes, selected identities, and timestamps; they do not establish durability, absence of unmeasured OS effects, or race freedom. Proxies refused ordinary outbound acquisition; this was not an OS network sandbox.

The collector initially stopped after command four because it expected the literal word “ambiguous.” The actual build path used actionable different-bytes wording and saved its continuation. The original producer, diagnostic streams, and failed assertion remain. A separately frozen correction continued without repeating any native command. That was a harness expectation error, not a product failure.

## Contract and model boundary

Current source separates bounded scan results from verified acquisition. Matching uses every declared assertion; distinct privately computed content addresses keep different weak-digest matches separate. Duplicate bytes collapse. Candidates are suggestions, and explicit or discovered files are verified again during resume. A completed scan may still have ambiguous obligations; an incomplete scan must not return a successful subset. An explicit association is a different operation and can avoid scanning unrelated files without weakening its own content checks.

The build host retains an unresolved preparation when there are no unique candidates, warns on ambiguity, and saves the build. A scanner error propagates before that continuation finish path. These source paths explain the bounded observations; they do not qualify all import, sync, or instance callers.

[Lean](Discovery.lean) has fifteen laws, including explicit-association and incomplete-scan premises. [Bend](Discovery.bend) has seven laws and independent selection kernels. The [replay](discovery_conformance.py) matches six native decisions and 24 scalar fields, checks retained streams/images/source pins and available products, and rejects eight changed-observation/decoder controls. It never launches empack. The observation adapter derives matching IDs from captured author assertions and known bytes; it derives explicit choice from the requested path, while native selection comes independently from exported member bytes.

The closed model does not implement hashing, enumerate files, grant execution authority, or prove a cryptographic property. Its interpreted matching list and completed-scan boundary omit traversal timing and candidate ordering. Content labels are fixture identities, and the decoder's fixed limits are research-profile admission rather than a new production codec.

## API and UX direction

Keep candidate discovery, content verification, explicit choice, saved continuation, and publication distinct. Preserve different matching byte identities and tell the user which exact obligation needs a choice. The existing ambiguity guidance is useful; adding candidate paths and assertion strength through existing views could make the next action easier without automatically choosing a filename or silently strengthening policy.

Keep the entry-limit refusal bounded and offer explicit `KEY=PATH` selection as an alternative when the user already knows the file. Do not suggest that raising limits is always necessary. Report completed publication and saved unresolved work differently, and preserve visible partial effects on a nonzero result. This supports the existing continuation model; no second scanner, new migration system, or generic recovery framework is proposed.

Byte, deadline, root, requirement, and association limits; unreadable files; link/race controls; automatic waiting; browser assistance; other continuation kinds; interrupted saving; Windows/Linux parity; and real provider integration remain open. Recheck the pinned scanner, assertion validation, build finish behavior, test-vector provenance, and fixture codec when updating dependencies or schemas. The parent operations remain pending.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/discovery_conformance.py
```

Compile the model modules first. Do not rerun the one-shot producer over the completed capture.
