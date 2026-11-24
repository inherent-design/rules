# Application extension of lifecycle traces

The host and application owners agreed to preserve the existing trace envelope and add versioned application identity. The host owns shared schema admission; this document records the application mapping requirements while that schema is being implemented.

| Field or relation                 | Application requirement                                                                                                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Producer and artifact             | Exact tool/extension/adapter identity, version, source or binary digest, and profile receipt                                                          |
| Application / feature / operation | Stable inventory IDs plus the actual interface invoked; semantic operation names are not silently treated as CLI names                                |
| Operation identity                | One invocation/lifecycle identity, with child events linked rather than merged into an unrelated request                                              |
| Target                            | Exact logical resource and relevant current backing; a URI, filename, digest, and deletion authority are different values                             |
| Basis                             | Captured inputs, raw/semantic revisions, effective configuration, evidence completeness, and permissions                                              |
| Revision                          | Monotonic host revision counters are exact decimal strings; application Git IDs, etags, versions, and content digests retain their own types          |
| Request and approval              | Requested effects and any current principal/target/revision-bound approval; TTY, focus, or a displayed plan is not a grant                            |
| Observations                      | Actual communications and independent state facts, including scoped project/install/runtime/cache/log/user/external net effects and explicit unknowns |
| Outcome                           | Actual return/status/receipt and observed publication/finalization; do not insert proposed behavior or proof status here                              |
| Interpretation                    | Separate source/model/law/native/simulation/proposal status, expectation basis, UX finding, and safe next action                                      |

No universal package/instance/document/snapshot enum is imposed. Adapters must explain how their own domain maps to common witnesses. A native file path is not a portable asset handle; a successful API return is not automatically a saved revision; a visible clean marker is not independently verified persisted content.

UI adapters must retain the selected action and target, not only the search text they intended to invoke. A substring match can select a different command. Keep that observation under its actual scope and exclude it from the intended flow's acceptance. Check the active view when several editor containers exist, and keep input-method buffers, rendered text, working-copy identity, and backing evidence separate. A marker surviving reload does not establish a complete document snapshot, file save, or durable project receipt.

Freeze the producer source and relevant inputs when collection starts, and identify those same bytes in its terminal record. Reading a live edited file only at finalization can attribute an earlier execution to newer code. Do not edit an active run's inputs; wait for its terminal result or explicitly end and classify that run. Preserve original native observations and their attribution limits when updating a replay adapter.

The VS Code paused-save probe already motivates that last distinction: the provider-backed observation has different saved and current text while `save()` and `isDirty` do not form a sufficient persistence receipt. Its exact host-extension scope must remain attached until source and further native controls establish the cause. The application analysis must inspect the backing bytes and source version instead of merely re-labeling that return value.
