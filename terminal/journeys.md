# Four-tool journey map

This is the breadth-first starting map. Native observations live beside each run receipt; proposed equivalences are not results. npm 11.20.0, pnpm 12.21.0, Yarn Berry 4.19.0, and empack 0.8.8-beta are selected. Node is 26.13.1. The first host fixture pipes stdout, gives stderr a private non-controlling PTY, and selects stdin independently. A TTY descriptor does not establish a present human or permission to answer.

| Journey | npm | pnpm | Yarn Berry | empack |
| --- | --- | --- | --- | --- |
| Discover | `--help` | `--help` | `--help` | `--help`; author/install/publish groups |
| Inspect intent | `pkg get` | inspect package manifest; confirm supported CLI | inspect package manifest; confirm supported CLI | `check --documents --json`, `status` |
| Add/remove | `install` / `uninstall` | `add` / `remove` | `add` / `remove` | `add` / `remove`; forgetting an author entry differs from deleting content |
| Preview/resolve | `install --dry-run` | `install --dry-run` | `install --mode=update-lockfile` writes lock/cache; **not** an equivalent dry run | `sync --dry-run`, `update` previews; lock prerequisites matter |
| Apply/repeat | `install`, repeated install | `install`, repeated install | `install`, repeated install | `sync`; `update --apply` is a separate effect request |
| Refusal/input | invalid command; lock disagreement; hook policy | invalid command; frozen lock; hook policy | invalid command; immutable lock | parser refusal; missing lock; managed conflicts and incomplete evidence |
| Interrupt/partial effects | controlled hook cancellation, inspect before retry | controlled hook cancellation, inspect before retry | controlled hook cancellation, inspect before retry | interrupted publication/runtime and durable recovery are different owners |
| Recovery | inspect manifest/lock/install tree/cache before retry | same, preserving pnpm-specific state | same, preserving Yarn-specific state | inspect status/pending/recovery and preserve uncertain effects |

The first executable pass sampled discovery, refusal, inspection, and preview across all four before deepening installation. [Coverage](coverage.md) now records the completed lifecycle and profile observations and their limits. The pnpm unknown-name case follows its script/command fallback and dependency gate; it is not a pure parser refusal. Version eligibility, solver success, completed installation, and gameplay compatibility are distinct claims.

Expectations to check against native output and pinned documentation: npm documents dry-run as reporting an install without installing; pnpm documents dry-run separately from lockfile-only; Yarn documents update-lockfile as a mode that still fetches and writes a lock. These are different promises, not a popularity vote. References: <https://docs.npmjs.com/cli/v11/commands/npm-install/>, <https://pnpm.io/cli/install>, <https://yarnpkg.com/cli/install>. Current documentation may drift; the tested command and version remain in each receipt.
