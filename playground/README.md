# Playground

The implemented resource ledger tracks CPU/GPU memory, resource kind, owner, allocation phase and policy/usage revisions. A world/epoch/service accounting owner can outlive a renderer compatibility domain. Reserving a target charges both GPU or CPU usage and the target category. Sharing a token adds no second charge. Splitting an exclusive reserved token transfers allowance. Retirement keeps the charge until its final owner releases it.

| Boundary | Model interpretation |
| --- | --- |
| Application host → runtime | The host owns platform services and orders attachment, update and close. An activity requests bounded work under an owner/epoch. Completion is an observation requiring current ownership before publication. |
| Dataset → region and halo | A coordinate is meaningful relative to a dataset, index frame, channel and epoch. Missing neighbor coverage blocks a dependent kernel. A covered zero is a valid input. |
| Immutable tick → regional candidates | The simulation contract requires one input root, explicit tick and coherent halos. Workers read immutable values. Cross-region writes become intents with domain-defined arbitration. |
| Candidates → next world | Admit working storage, compare expected revisions, resolve conflicting writes and publish a complete barrier. Persist pending work and activity along with tick and patches to resume deterministically. |
| World → mesh, navigation, collision or UI | Each product has its own dependency footprint, generation, and freshness policy. Presentation may display a previous result while it rebuilds. Physics or navigation needs an explicit policy for missing/stale authoritative coverage. |
| Prepared bytes → device submission | Reserve, allocate, submit, await completion and retire. Budget refusal, allocation fault and device loss have different recovery paths. A native physics step mutates solver state; a failed step may require region recovery. |

[Model.lean](Model.lean) includes a two-region propagation fixture for the **specified** simulation barrier and a separate projection of the **implemented** ledger. A missing halo, stale base or failed reservation preserves the root. Two readable old values (1,9) produce (9,1) at the next tick with zero exterior halos. Sequential in-place traversal would change that answer. The loss theorem proves total usage alone cannot predict target admission. [LedgerProbe.cpp](LedgerProbe.cpp) runs the actual C++ ledger and checks refusal, partition and destruction. The fixture establishes model behavior; native solver accuracy, GPU ordering and distributed replication require their own adapters. See [source pins](../sources.json).
