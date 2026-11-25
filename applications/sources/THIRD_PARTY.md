# Retained application source excerpts

Original study fixtures, adapters, and models remain separate from upstream source. A retained method excerpt keeps its upstream license; it does not become original rules code.

| Retained excerpts | Upstream basis | License |
| --- | --- | --- |
| `evidence/vscode-trust-20261124T074001256Z/fragment.ts` and its type-stripped `fragment.js` | Microsoft VS Code `8a14f0cc1b08d531eb83255ea3764ae22aa932b5`: selected manifest-support, trust-enable, and trust-disable method bodies, with clearly identified fixture adapters | [Microsoft copyright and MIT terms](licenses/vscode-MIT.txt), with [retrieval identity](licenses/vscode-receipt.json) |
| `evidence/vscode-filesystem-source/*.ts.txt` and `fragment.cjs` | The same VS Code commit: selected filesystem registration, capability, and write excerpts; the executable bridge/map/query fragments distinguish unchanged source from a proposed expression | [Microsoft copyright and MIT terms](licenses/vscode-MIT.txt), with [source selections](vscode-filesystem-selections.json) |

The `inputs.json` records in `evidence/empack-operations-20261125T090143715136Z/` and `evidence/empack-operations-20261125T090212235915Z/` quote empack’s `Interrupted` and `Cancellation` source blocks from `0b4462e3032b4f09230b15329722eabefb7f574c`. They retain the original [Apache 2.0 terms](licenses/empack-Apache-2.0.txt) and [source identity](empack-operation-selections.json). The surrounding fixture code and models are separate study artifacts.

Other selected upstream source files and downloaded tools remain in ignored caches. Their URLs, hashes, inspected ranges, and evidence limits are recorded in the owning source selections. Public model comparisons do not assert reproducible application builds or relicense cached upstream projects.
