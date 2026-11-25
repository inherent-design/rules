# Account identity, refresh policy, and captured launch sessions

This band studies Prism 11.1.1 source at `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. It compares selected source methods, controlled Qt components, and formal projections. It does not launch the installed application, authenticate an account, read a personal account store, or start Minecraft. The [source ledger](../sources/prism-accounts-selections.json), [native receipt](../evidence/prism-accounts-20261125T020020403602Z/receipt.json), and [pure comparison](../evidence/prism-accounts-20261125T020020403602Z/conformance.json) retain the exact boundaries.

## Values and ownership

Account actor identity, account type, profile ID, profile name, entitlement, token state, task state, and launch mode have separate roles. A display name is unsuitable for selecting which mutable account object a launch owns. A local/offline account also does not gain Minecraft entitlement merely because a raw ownership flag is true.

The selected `AccountData` methods preserve the raw profile ID and name separately from the translated missing-profile display text. `fillSession` captures values into another object. Its combined legacy token uses the raw profile ID, whereas its session UUID falls back to a name-derived UUID when that ID is empty. Thus a session can simultaneously contain the display text “No Minecraft profile,” a nonempty fallback UUID, and an empty profile component in its combined token. Those fields do not establish profile readiness.

An offline alias is another role: `MakeOffline` changes the session name and token sentinels while preserving UUID, user type, and mode. `MakeDemo` sets the supplied name, UUID, and demo mode but leaves an existing user type alone. The fixture compares both a reused session and a fresh one. These are partial transformations, not complete session constructors or launch-admission checks.

The model deliberately keeps unknown expiry separate from a known zero. The selected source computes refresh from use count, global validity, and a deadline. Per-token validity, account task state, and entitlement are not interchangeable with that policy.

## What was exercised

The native cohort has 30 cases:

| Scope                  | Cases | Actual boundary                                                                                                                                                    |
| ---------------------- | ----: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity/session units |     7 | Source getters, session capture, offline/demo mutation, and name-UUID derivation.                                                                                  |
| Refresh-policy units   |    12 | Source `shouldRefresh`, with one current-clock call replaced by a declared fixed clock.                                                                            |
| Claim components       |     5 | Source name lookup and claim construction, two actual `UseLock`s, and separate finalization; a captured-actor candidate is compared alongside.                     |
| Login prefixes         |     6 | Source `login` and successful dialog completion with fake UI/network results; each input compares current, refill-only, and admitted-profile-then-refill variants. |

The compiler uses C++20 and Qt 6.12.0. Eighteen method excerpts and five copied source files are verified against the pinned originals. Compilation succeeded with one retained deprecation warning for the fixture's fixed-clock constructor. The fixture supplies application/list access, launch-task signals, account storage, synchronous dialog answers, and already admitted launch decisions. Its `launchInstance` replacement counts requests; it cannot establish a game start. All account actors remain retained until the case finishes. Fixture pointer aliases and omitted account-use notifications do not qualify real QObject ownership, destruction, reentrancy, or asynchronous observers.

The source ledger includes three caller/auth-step selections inspected after collection. They support a source-level premise: a missing profile can finish the profile step as `WORKING`, and subsequent successful flow can mark the account online/certain. They were not compiled into this cohort. These observations do not qualify an actual OAuth exchange, ownership check, provider response, or full caller route.

Post-run compiler, framework, and installed-bundle metadata readbacks retain useful identities. They are not a frozen SDK image, a reproducible upstream build, or evidence that the installed application's bundled Qt was executed.

## Refresh policy

An in-use account does not refresh. Otherwise `None` validity does not refresh, `Assumed` validity does, and `Certain` validity refreshes strictly inside twelve hours. Exactly 43,200 seconds is outside; 43,199 is inside. An absent explicit expiry uses issue time plus one day. If both timestamps are invalid, the selected Qt calculation supplies zero to the decision, so it refreshes. The recorded observation remains `remaining: null` rather than asserting a known zero-second expiry.

The fixtures also cover an expired token, both in-use validity cases, and the fallback boundary. This explains a scheduling decision; it does not establish that token renewal succeeds or that a cached token is accepted by the service.

## Name lookup can claim another actor

The source `ClaimAccount` constructor uses `session->player_name` to obtain the first matching account. The selected session belongs to online actor B. With local actor A preceding B and both named Alex, the source claims A; reversing their order or making the names unique claims B. B remains refreshable in the collision case despite the launch's claim. Two claim objects give counts two, one, and zero as they are finalized separately.

The captured-actor candidate instead retains the selected B directly. It holds B in both list orders and suppresses B's refresh while held. These controlled components establish an identity mismatch in the selected methods under the supplied collection. They do not prove that every actual UI path permits this collection, or that a full application race or credential leak occurred. Offline/demo constructor controls claim no actor; the actual offline caller does not append this step, so those controls are not complete offline-launch evidence.

Keep-current preserves the existing name lookup and its demonstrated ambiguity. A focused alternative is to pass the already selected actor into the claim step and retain its lifetime through finalization. Reuse the existing use-lock mechanism; no new account database or persistent identity format is needed for that change. Verify actual smart-pointer lifetime, notifications, actor removal, concurrent launches, refresh completion, and task finalization before adoption. Existing account-file identity and UI duplicate rules need separate review; do not infer a saved-state migration from this runtime-only proposal.

## Profile setup must precede capture of usable session data

The source login fills the session before opening profile setup. On a successful network result, the actual dialog completion body accepts the dialog without parsing the response into the account. The current prefix then requests launch with the old account/session. The accepted missing-profile fixture retains an empty profile ID and the placeholder-derived UUID. Merely refilling the session after dialog acceptance gives the same result because its source account is still unchanged.

The private candidate first admits profile data for the same actor, updates the account, and then captures the session. The valid fixture produces the new profile ID/name. A deliberately invalid success body is refused by the candidate, while the current and refill-only variants request launch. Cancellation of the dialog requests no launch and retains the already captured incomplete session for observation. Existing-profile, offline-alias, and demo controls agree across all three variants.

The candidate's ID/name format checks establish shape only. The fixture supplies the same-actor authenticated-response premise; the regex does not prove it. A production decision should reuse the existing profile parser/refresh flow or validate the actual response with equivalent admission before session capture. A known or uncertain profile-creation result must not lead to blindly repeating its POST. Separate creation acceptance, subsequent profile observation, session readiness, and requested launch in both state and feedback.

Keep-current avoids changing authentication flow but retains the incomplete-session counterexample. Refill-only is a rejected correction for the accept-only dialog. The admitted-update candidate is a bounded design comparison, not a patched launcher. Full provider errors, response loss, profile readback, durable account saving, mode decisions, GUI cancellation, and actual downstream launch behavior remain unqualified.

## Models, reporting, and remaining checks

[Lean](Accounts.lean) and [Bend](Accounts.bend) model typed account/session roles, relative deadlines, the selected claim, use counts, and the three login variants. Lean laws distinguish unknown time, strict cutoffs, partial mutation, name collisions, sibling claims, and capture after admission. Bend uses bounded unsigned magnitudes for signed seconds; the decoder's 200,000-second bound prevents arithmetic wrap. This replaced unary natural-number clock arithmetic after the checker exhausted its reduction fuel, without dropping the failed boundary from comparison. The [research decoder](AccountsCase.lean) checks its own schema, enums, time bounds, unique actor labels, selection, line framing, and shape witnesses. These comparison restrictions are not restrictions on real Prism users.

The [pure replay](accounts_conformance.py) reads native observations independently, computes name-UUID witnesses separately, and compares all thirty rows field by field in both models. It checks refused research inputs and changed observation fields. Matching these projections does not qualify every source field, the complete auth flow, or the full account feature. In particular, task state and the candidate's profile-validity assignment are outside the compared output fields. Parent add/refresh/select/offline/remove operations remain pending in the inventory; component evidence is recorded separately.

For users, distinguish a display label from a launch identity, refreshing from ready, and profile creation from an admitted profile. Keep actionable failure beside the launch action and retain the selected account context without exposing tokens. A proposed internal readiness result could carry actor identity, launch mode, admitted profile basis, and capture outcome. It should reuse existing account/task mechanisms rather than introduce one universal authenticated Boolean. Offline aliases and demo remain deliberate policies, not silent fallback from an online error.

Before implementation, run isolated real-application tests for duplicate-name admission, actual claim lifetime/finalization, new-profile completion, response ambiguity, and rejected/cancelled dialogs. Confirm unchanged existing-account, offline, and demo behavior on the supported platforms and bundled Qt. Preserve account-store bytes and protocol validity, and test the actual refresh/account-save notifications. These obligations are separate from deterministic method comparisons and require a separately selected test/implementation scope. No production changes or upstream report were made.
