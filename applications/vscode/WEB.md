# vscode.dev: untitled edits and reload

This band covers anonymous vscode.dev 1.147.0 at `8a14f0cc1b08d531eb83255ea3764ae22aa932b5` in Chromium 156.0.8078.4 on macOS arm64. It observes one ordinary untitled document before and after a page reload in the same isolated browser profile. The Unicode marker and dirty indicator remain. It establishes no local-file save or durable project guarantee.

The [served-page identity](../sources/vscode-web-serving.json) and executed workbench module have the same application revision. The UI calls itself “Visual Studio Code (Preview),” even though the served version metadata says `stable`. Neither label establishes feature parity with the desktop product. The [tool receipt](../sources/playwright-web-tool.json) identifies Playwright 1.64.1 and its matching cached Chromium revision 1248; the package archive's registry integrity was verified. No browser was downloaded or globally installed for this band.

## Working copy and saved file are different states

| Observation | What it establishes | What remains unknown |
| --- | --- | --- |
| Exact New Untitled Text File command selected | An ordinary editor was requested, rather than a comparison editor. | Other command and editor modes. |
| Marker rendered, tab dirty | The visible working copy contains that marker and advertises unsaved changes. | Complete model bytes and exported resource URI. |
| Marker and dirty dot after reload | This same-profile reload restored the visible draft. | Future restoration, browser-process restart, eviction, quota failure, or another browser. |
| File picker, OPFS, and IndexedDB APIs present | These APIs exist in this host. | Permission grants, successful file operations, and persisted project state. |

The pinned [untitled model](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vs/workbench/services/untitled/common/untitledTextEditorModel.ts) creates UTF-8 backup content. On resolution it uses a returned backup when present and marks a restored untitled working copy dirty. Its first-line caption is distinct from the resource identity. These excerpts explain a plausible restoration path; the UI fixture does not inspect backup storage or prove which internal write restored this run.

[Lean](WebDraft.lean) and [Bend](WebDraft.bend) express a conditional observation projection: successful restoration retains the admitted logical resource and rendered text, leaves the working copy dirty, and supplies no file-write receipt. The four Lean and two Bend laws concern that projection. They do not verify backup scheduling, browser persistence, complete document content, or durability. A logical within-run key is an adapter premise, not a measured URI.

## Evidence and fixture corrections

The [ordinary-editor receipt](../evidence/vscode-web-untitled-reload-20261124T022405483Z/receipt.json), screenshots, and explicit [image review](../evidence/vscode-web-untitled-reload-20261124T022405483Z/review.json) retain the selected action, visible marker, before-reload tab state, and limits. After-reload dirty state was reviewed in the screenshot; it was not captured as DOM data. No sign-in, personal profile, remote repository, local file grant, or file export was used. The headless context closed in the runner's `finally` block.

Earlier runs remain attributable:

- `vscode-web-boot-20261124T021205233Z`: workbench boot and capability presence only.
- `vscode-web-untitled-reload-20261124T021558839Z`: fixture assumed a visible textarea; the editor used native EditContext. It failed before the intended edit.
- `vscode-web-untitled-reload-20261124T021755716Z`: fixture read the first rendered editor container rather than the active view. The intended assertion did not complete.
- `vscode-web-untitled-reload-20261124T022038104Z`: substring matching selected Compare New Untitled Text Files. Its actual comparison-editor observation is retained and excluded from ordinary-editor acceptance.

The corrected runner selects a unique exact command, checks editor focus, and searches the rendered views. Input-method text is not canonical document content: the retained EditContext diagnostic contains duplicated marker text while the editor renders it once. Keep that input buffer separate from working-copy and backing evidence.

The [replay adapter](web_conformance.py) checks source/receipt/screenshot identities, the selected command, rendered marker, and explicit image-review basis. It compares the restoration projection with Lean and the marker/no-file-receipt projection with Bend. It rejects both a deliberately different command and the actual earlier comparison-editor run. Replay never launches a browser:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/web_conformance.py applications/evidence/vscode-web-untitled-reload-20261124T022405483Z
```

Compile `WebDraft.lean` to `.build/applications/vscode/WebDraft.olean` first. `web_boot.mjs` is a separate owner-run collection tool, outside ordinary CI. Its isolated profiles are ignored generated work; raw receipts, screenshots, and consequential fixture failures are retained.

## Preservation, proposals, and remaining investigation

Keep the distinction between an editable draft, a restored backup, a local-file write, a browser download, and a saved project. The existing dirty marker makes that distinction visible for this case; no product defect is established by this band. A supplementary automation receipt could expose backup identity and confirmed finalization when the implementation actually knows them. It must not turn a restored tab into a claim about filesystem durability. The keep-current alternative is to retain the normal UI and require specialized integrations to obtain their own save/export evidence.

For empack's portable-authoring candidate, draft recovery should preserve unresolved edits without manufacturing an exported pack or saved-file receipt. Test quota failure, canceled writes, process loss, and concurrent owners separately. Browser storage success and consumer export need their own evidence, even when the editor can recover a tab.

Local-handle registration and restored permissions remain source investigations, with selected ranges in [the source record](../sources/vscode-selections.json). The provider registers file and directory handles in separate maps but uses name-based resource keys and shared persisted lookup. Caller admission and handle identity must be traced before deciding whether cross-kind or reopened-name collisions can occur. This is an unresolved question, not a confirmed vscode.dev defect. Local-file pickers, permission changes, writable finalization, process restart, other browsers, extensions, and the joined project import/save/export flow remain unqualified.
