const vscode = require('vscode');
const fs = require('fs/promises');
const path = require('path');

exports.activate = async context => {
  const metaPath = process.env.RULES_VSCODE_SEARCH_META;
  if (!metaPath) return;
  const meta = JSON.parse(await fs.readFile(metaPath, 'utf8'));
  const rows = [], events = [];
  const owned = ['a/visible.txt', 'a/hidden.txt', 'a/search-hidden.txt', 'b/visible.txt', 'c/visible.txt', 'outside.txt', 'a/created.txt'];
  const uri = rel => vscode.Uri.file(path.join(meta.work, rel));
  const rel = value => path.relative(meta.work, value.fsPath).split(path.sep).join('/');
  const range = value => [value.start.line, value.start.character, value.end.line, value.end.character];
  const folders = () => (vscode.workspace.workspaceFolders ?? []).map(f => ({path: rel(f.uri), name: f.name, index: f.index}));
  const settle = ms => new Promise(resolve => setTimeout(resolve, ms));
  const files = async () => Object.fromEntries(await Promise.all(owned.map(async name => {
    try { return [name, {present: true, text: await fs.readFile(path.join(meta.work, name), 'utf8')}]; }
    catch (error) { if (error.code === 'ENOENT') return [name, {present: false}]; throw error; }
  })));
  const buffers = () => vscode.workspace.textDocuments.filter(d => d.uri.scheme === 'file' && owned.includes(rel(d.uri)))
    .map(d => ({path: rel(d.uri), version: d.version, dirty: d.isDirty, closed: d.isClosed, text: d.getText()})).sort((a,b) => a.path.localeCompare(b.path));
  const persist = async (status, error = null) => {
    const value = {schema: 1, status, rows, events, error, folders: folders(), files: await files(), buffers: buffers()};
    const temp = meta.output + '.tmp'; await fs.writeFile(temp, JSON.stringify(value, null, 2) + '\n'); await fs.rename(temp, meta.output);
  };
  const row = async (id, kind, result) => {
    rows.push({id, kind, result, folders: folders(), buffers: buffers(), files: await files()});
    await persist('running');
  };
  const findFiles = async (id, include, exclude) => row(id, 'file-search', {
    include: typeof include === 'string' ? include : {base: rel(include.baseUri), pattern: include.pattern},
    exclude: exclude === undefined ? 'default' : exclude === null ? 'none' : exclude,
    paths: (await vscode.workspace.findFiles(include, exclude)).map(rel).sort()
  });
  const textSearch = async (id, query, options) => {
    const matches = [];
    const complete = await vscode.workspace.findTextInFiles({pattern: query, isCaseSensitive: true}, options, result => {
      if (!result.ranges) return;
      matches.push({path: rel(result.uri), ranges: (Array.isArray(result.ranges) ? result.ranges : [result.ranges]).map(range), preview: result.preview.text});
    });
    matches.sort((a,b) => a.path.localeCompare(b.path));
    await row(id, 'text-search', {query, options, matches, complete});
  };
  const replaceBuffer = async (document, text) => {
    const edit = new vscode.WorkspaceEdit(); edit.replace(document.uri, new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length)), text);
    if (!await vscode.workspace.applyEdit(edit)) throw new Error('Fixture setup text edit refused.');
  };
  const apply = async edit => {
    try { return {accepted: await vscode.workspace.applyEdit(edit), error: null}; }
    catch (error) { return {accepted: null, error: String(error)}; }
  };
  const changeFolders = async (id, start, count, additions) => {
    const before = folders();
    let resolveEvent;
    const event = new Promise(resolve => { resolveEvent = resolve; });
    const subscription = vscode.workspace.onDidChangeWorkspaceFolders(value => resolveEvent({added: value.added.map(f => rel(f.uri)), removed: value.removed.map(f => rel(f.uri))}));
    const accepted = vscode.workspace.updateWorkspaceFolders(start, count, ...additions);
    const immediate = folders();
    let observedEvent = null;
    if (accepted) {
      let timer;
      try { observedEvent = await Promise.race([event, new Promise((_,reject) => { timer = setTimeout(() => reject(new Error('Workspace event timed out. Inspect before retry.')), 10000); })]); }
      finally { clearTimeout(timer); }
    }
    subscription.dispose();
    await row(id, 'workspace-change', {before, accepted, immediate, observedEvent});
  };
  try {
    context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders(e => events.push({kind:'workspace', added:e.added.map(f => rel(f.uri)), removed:e.removed.map(f => rel(f.uri))})));
    await settle(250);
    await row('initial', 'snapshot', {findTextInFilesAvailable: typeof vscode.workspace.findTextInFiles === 'function'});
    await findFiles('files-default', '**/*.txt', undefined);
    await findFiles('files-no-excludes', '**/*.txt', null);
    await findFiles('files-relative-a', new vscode.RelativePattern(uri('a'), '**/*.txt'), undefined);
    const token = new vscode.CancellationTokenSource(); token.cancel();
    try { await row('files-pre-cancelled', 'cancel-search', {paths:(await vscode.workspace.findFiles('**/*.txt', null, undefined, token.token)).map(rel).sort(), error:null}); }
    catch (error) { await row('files-pre-cancelled','cancel-search',{paths:null,error:String(error)}); }
    finally { token.dispose(); }
    if (typeof vscode.workspace.findTextInFiles !== 'function') throw new Error('Selected proposed text-search API is unavailable.');
    await textSearch('text-default', 'needle', {include:'**/*.txt',useIgnoreFiles:false});
    await textSearch('text-file-excludes', 'needle', {include:'**/*.txt',useIgnoreFiles:false,useDefaultExcludes:true});
    const a = await vscode.workspace.openTextDocument(uri('a/visible.txt'));
    await vscode.window.showTextDocument(a, {preview:false});
    await replaceBuffer(a, 'buffer-only draft-a\n');
    await row('dirty-a', 'snapshot', {});
    await textSearch('text-disk-after-dirty', 'needle', {include:'**/*.txt',useIgnoreFiles:false});
    await textSearch('text-buffer-after-dirty', 'buffer-only', {include:'**/*.txt',useIgnoreFiles:false});
    const outside = await vscode.workspace.openTextDocument(uri('outside.txt'));
    await vscode.window.showTextDocument(outside, {preview:false});
    await textSearch('text-open-outside', 'needle', {include:'**/*.txt',useIgnoreFiles:false});
    await changeFolders('add-c', 2, 0, [{uri:uri('c'),name:'C'}]);
    await changeFolders('duplicate-c', 3, 0, [{uri:uri('c'),name:'Other C'}]);
    await findFiles('files-after-add', '**/*.txt', null);
    await changeFolders('remove-b', 1, 1, []);
    await findFiles('files-after-remove', '**/*.txt', null);
    await replaceBuffer(a, 'needle base\n');
    if (!await a.save()) throw new Error('Fixture setup save refused.');
    const planned = new vscode.WorkspaceEdit(); planned.replace(a.uri, new vscode.Range(0,0,0,6), 'fixed');
    const basis = {version:a.version, text:a.getText(), range:[0,0,0,6]};
    const prefix = new vscode.WorkspaceEdit(); prefix.insert(a.uri,new vscode.Position(0,0),'prefix ');
    if (!await vscode.workspace.applyEdit(prefix)) throw new Error('Fixture prefix setup refused.');
    const beforeApply = {version:a.version,text:a.getText()};
    await row('apply-stale-range', 'text-edit', {basis,beforeApply,...await apply(planned)});
    const failure = new vscode.WorkspaceEdit(); failure.insert(a.uri,new vscode.Position(0,0),'should-not-apply ');
    failure.insert(uri('a/missing.txt'),new vscode.Position(0,0),'missing');
    await row('apply-missing-text-target', 'text-edit', await apply(failure));
    const mixed = new vscode.WorkspaceEdit(); mixed.createFile(uri('a/created.txt'),{overwrite:false,ignoreIfExists:false});
    mixed.createFile(uri('a/visible.txt'),{overwrite:false,ignoreIfExists:false});
    mixed.insert(a.uri,new vscode.Position(0,0),'after-failed-create ');
    await row('apply-mixed-existing-target', 'resource-edit', await apply(mixed));
    await persist('complete');
    // Save only this fixture's known text documents to avoid an unsaved-dialog
    // during shutdown. This is a separate, recorded cleanup effect.
    const cleanup = [];
    for (const d of vscode.workspace.textDocuments) if (d.isDirty && d.uri.scheme === 'file' && owned.includes(rel(d.uri))) cleanup.push({path:rel(d.uri),saved:await d.save()});
    await row('cleanup-save', 'cleanup', {documents:cleanup});
    await persist('complete'); await settle(100);
    await vscode.commands.executeCommand('workbench.action.quit');
  } catch (error) {
    await persist('failed', {message:String(error),stack:error?.stack??null});
    // A failure is retained, not retried. Owned dirty buffers are saved before
    // quitting this isolated fixture; no caller workspace is reachable here.
    for (const d of vscode.workspace.textDocuments) if (d.isDirty && d.uri.scheme === 'file' && owned.includes(rel(d.uri))) await d.save();
    await vscode.commands.executeCommand('workbench.action.quit');
  }
};
exports.deactivate = () => {};
