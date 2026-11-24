# Extension support and workspace-trust admission

This band executes selected, unmodified VS Code 1.147.0 method bodies from revision `8a14f0cc1b08d531eb83255ea3764ae22aa932b5` under Node 26.13.1 with explicit dependency adapters. It compares support-policy precedence and one trust-related disable predicate. It does not launch VS Code, install or execute an extension, display a trust prompt, or qualify a security sandbox. The earlier native configuration run disabled trust and supplies none of those missing checks.

## Separate facts

| Fact | Meaning |
| --- | --- |
| Trust feature enabled | Environment/configuration decides whether the trust feature participates. It is not the workspace's stored trust decision. |
| Workspace trusted | The management service's current decision about this workspace. URI resolution, remote policy, persistence, and transitions have their own premises. |
| Untrusted-workspace support | An extension's effective `true`, `false`, or `"limited"` support policy after user/product/manifest precedence. |
| Trust-related disable predicate | Whether trust blocks this particular extension, considering its location and effective support. |
| Complete enablement and execution | Other user, validity, environment, virtual-workspace, host-kind, dependency, and lifecycle gates also apply. Passing one predicate does not imply execution. |

The [source selections](../sources/vscode-trust-selections.json) identify the executed methods and separately inspected callers. The extension manifest service first reports support when trust is disabled or the extension has neither a main nor a browser entry point. Otherwise, the first defined value wins:

1. A user override with no version restriction or an exact matching version.
2. A product override.
3. The extension manifest's support declaration.
4. A product default.
5. `false` when none is present.

An explicit false remains a value; it does not fall through. The version condition is exact string equality, not a semantic version range. The source constructor reads the user inspection value into a cached identifier map. Constructor loading, cache refresh, setting schema, and identity normalization are source context only; the fixture supplies admitted maps with one lowercase generated identity.

The enablement service's trust predicate first passes trusted workspaces. In an untrusted workspace it blocks an extension located inside that workspace, regardless of a permissive support declaration. For an extension outside the workspace, only effective support `false` causes this predicate to block it. `"limited"` does not block the entire extension through this predicate. That says nothing about which features the extension disables or what its code can do.

Trust enablement itself has another rule: the environment's disable switch wins; otherwise a Boolean setting is used, with absent/non-Boolean input defaulting to enabled. The management service's separately inspected trust calculation returns trusted when the feature is disabled. The fixture deliberately varies predicate parameters independently, including combinations not established reachable in the full application. Those rows are function controls, not production lifecycle traces.

## Evidence and models

The successful [receipt](../evidence/vscode-trust-20261124T074001256Z/receipt.json) binds source selections, original producer, extracted TypeScript, stripped JavaScript, Node version, and compressed observations. The source methods are unchanged; dependency adapters supply maps, configuration values, and a Boolean workspace-membership answer. They do not implement the actual identifier map, configuration service, or URI containment library. TypeScript stripping removes types and `private` modifiers; it does not replace the method bodies.

[Lean](Trust.lean) matches all 3,072 support-policy combinations, their 12,288 trust-disable predicate results, and eight enablement-flag cases. [Bend](Trust.bend) compares a selected 111 support combinations and their 444 disable predicates, covering every user/version gate and every product/manifest/default combination without a user assignment. The matrix is finite function evidence; it is not thousands of independent workflows. Eight Lean laws and four Bend laws preserve explicit denial, version filtering, workspace-local refusal, limited support, and the distinction between passing this predicate and complete enablement.

The [replay](trust_conformance.py) checks retained compressed observations and exact selected bodies, then runs only the models. It refuses unknown schema, support, and version-admission codes. It rejects interpretations that declaration equals enablement, that limited means false, that false means absent, or that an old version override always applies after an upgrade. Selected upstream files must be present at their recorded hashes in the ignored source cache; replay never fetches them or launches the application.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/trust_conformance.py applications/evidence/vscode-trust-20261124T074001256Z
```

The original collector first selected an interface declaration instead of its implementation. Type stripping erased that declaration, so the first attempted call failed. That [excluded fixture](../evidence/vscode-trust-20261124T073941320Z/disposition.json) has no support cases and establishes no product failure. The corrected extractor selects the exact implementation signature and records a separate successful run. Retained method excerpts keep their [upstream license](../sources/THIRD_PARTY.md).

## Preserve policy; clarify provenance

No correctness defect is established in these predicates. Preserve explicit user/product overrides, exact version binding, the distinction between limited and denied support, and the workspace-local restriction. Do not replace these with one ambient Boolean called trusted. Preserve the existing complete enablement pipeline and dependency checks rather than extracting a permissive shortcut from this study.

An inspection improvement could reuse those existing decisions and expose the effective support value, its source, version eligibility, workspace/location basis, and actual disable reason. A user should be able to distinguish a manifest restriction from their own override, an override that stopped matching after an upgrade, and another enablement gate. Inspect existing management APIs and UI before adding a new public receipt. The keep-current alternative is to improve explanations around the existing enablement state without changing policy or serialized settings.

Before adoption, exercise the installed desktop and web extension managers with real URI containment, user/profile updates, exact/mismatched versions, workspace-local extensions, dependency gates, trusted-to-untrusted transitions, and extensions already running. Observe prompts, cancellation, persisted decisions, effective enablement, process/host effects, and visible feedback separately. No claim here establishes that revoking trust retires running code. Remote, virtual, and managed workspaces remain separate profiles. A change to public inspection or override semantics also needs API and settings compatibility review.

For empack, the useful rule is narrower: capability availability, selected-operation requirements, native authority, and consumer compatibility are distinct facts. Show the policy and captured basis that admit or refuse an operation. An author declaration or a convenient host capability does not grant permission to mutate a native instance. This supports the existing current/0.9 proposal without importing VS Code's trust system or selecting a new execution service.
