# Repository conventions

The bootstrap draws on re:desktop for a single proof compilation and small source-bound module handoff, re:form and empack for source/generation ownership and plain diagnostics, cfgate for bounded branch CI and concurrency cancellation, and Playground for small adapter boundaries and conventional commit subjects.

AGENTS.md owns durable contributor rules, CONTRIBUTING.md owns the contribution entry point, and docs/development.md owns reproducible tooling and CI scope. Model explanations own assumptions and applicability. Recorded evidence owns what actually ran. Personal task continuation stays in the owner's task store.

Repository metadata uses Apache-2.0 for original contributions, LF files, an EditorConfig, and Markdown formatting without forced line wrapping. Renovate proposes bounded dependency updates. Source security runs weekly or on request. Retained upstream research code keeps its original licensing and source identity.

Changing a proof-tool version requires inspecting the upstream release and updating all matching archive hashes in toolchain.json. A dependency PR alone cannot qualify a new toolchain. App-specific research and controlled native runs remain with their execution owners.
