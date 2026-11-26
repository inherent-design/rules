const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return {promise, resolve};
}
exports.activate = function (context) {
  const meta = JSON.parse(fs.readFileSync(process.env.RULES_LANGUAGE_FIXTURE, 'utf8'));
  if (vscode.version !== meta.version) throw new Error('Runtime version changed after preflight.');
  if (path.resolve(meta.output) !== path.join(path.resolve(meta.run), 'observed.json')) throw new Error('Invalid output scope.');
  const uri = vscode.Uri.file(path.join(meta.work, 'project', 'document.rules-language'));
  const base = 'alpha beta\n';
  const calls = [], events = [], rows = [], scaffold = [];
  let doc, editor, pending, activeProviders = 0, handled = 0, busy = false, status = 'ready', action = 'startup';
  const error = e => ({name:e?.name ?? null, message:String(e?.message ?? e)});
  function write() {
    const temporary = meta.output + '.tmp';
    fs.writeFileSync(temporary, JSON.stringify({schema:1, version:vscode.version, status, handled, activeProviders, rows, calls, events, scaffold}, null, 2) + '\n');
    fs.renameSync(temporary, meta.output);
  }
  function own(document) {
    if (document.uri.toString() !== uri.toString()) throw new Error('Refused an unowned document.');
  }
  function snapshot() {
    return doc ? {version:doc.version, text:doc.getText(), dirty:doc.isDirty, closed:doc.isClosed,
      activeIsOwn:vscode.window.activeTextEditor?.document.uri.toString() === uri.toString()} : null;
  }
  async function until(predicate, label, ms = 3000) {
    const end = Date.now() + ms;
    while (!predicate()) {
      if (Date.now() >= end) throw new Error('Observation timeout: ' + label);
      await pause(10);
    }
  }
  const range = () => new vscode.Range(0, 0, 0, 5);
  function editValue(text) {
    const value = new vscode.WorkspaceEdit();
    value.replace(uri, range(), text);
    return value;
  }
  async function reset() {
    doc = await vscode.workspace.openTextDocument(uri);
    own(doc);
    editor = await vscode.window.showTextDocument(doc, {preview:false});
    const before = snapshot();
    const value = new vscode.WorkspaceEdit();
    value.replace(uri, new vscode.Range(0, 0, doc.lineCount - 1, doc.lineAt(doc.lineCount - 1).text.length), base);
    const result = await vscode.workspace.applyEdit(value);
    if (!result) throw new Error('Fixture reset was refused; preserve the state.');
    await until(() => doc.getText() === base, 'reset text');
    editor.selection = new vscode.Selection(1, 0, 1, 0);
    scaffold.push({action, kind:'owned-reset', before, after:snapshot(), result});
  }
  async function insertPrefix() {
    const before = snapshot();
    calls.push({action, api:'TextEditor.edit', role:'intervening-edit', before});
    const result = await editor.edit(builder => builder.insert(new vscode.Position(0, 0), 'shift '));
    if (!result) throw new Error('Controlled intervening edit was refused.');
    await until(() => doc.version > before.version, 'intervening version');
    return {before, after:snapshot(), result};
  }
  async function record(run) {
    await reset();
    const before = snapshot();
    const result = await run();
    await pause(0);
    rows.push({action, before, result, after:snapshot(), activeProviders});
  }
  function plain(edits) {
    return edits === undefined ? {kind:'undefined'} : {kind:'edits', edits:edits.map(e => ({range:[e.range.start.line,e.range.start.character,e.range.end.line,e.range.end.character],newText:e.newText}))};
  }
  function workspaceValue(value) {
    return value === undefined ? {kind:'undefined'} : {kind:'workspace-edit', entries:value.entries().map(([u, edits]) => ({uri:u.toString(),...plain(edits)}))};
  }
  function hold(kind) {
    if (pending) throw new Error('Another controlled provider is pending.');
    pending = {kind, entered:deferred(), release:deferred(), done:deferred(), canceled:deferred()};
    return pending;
  }
  async function provider(kind, document, token, text) {
    own(document);
    const mode = pending?.kind === kind ? pending : null;
    const entry = {action, kind, basis:{version:document.version,text:document.getText()}, canceledAtEntry:token.isCancellationRequested};
    activeProviders++;
    calls.push({action,api:kind === 'format' ? 'provideDocumentFormattingEdits' : 'provideRenameEdits',basis:entry.basis});
    let listener;
    try {
      listener = token.onCancellationRequested(() => { events.push({action,kind:'provider-canceled',provider:kind}); mode?.canceled.resolve(true); write(); });
      mode?.entered.resolve();
      if (mode) await mode.release.promise;
      entry.completedAgainst = {version:document.version,text:document.getText()};
      entry.canceledAtReturn = token.isCancellationRequested;
      events.push({kind:'provider-returned',...entry});
      if (kind === 'format') return [vscode.TextEdit.replace(range(), text)];
      return editValue(text);
    } finally {
      listener?.dispose(); activeProviders--; mode?.done.resolve(); write();
    }
  }
  const selector = {scheme:'file',language:'rules-language-study'};
  context.subscriptions.push(vscode.languages.registerDocumentFormattingEditProvider(selector, {
    provideDocumentFormattingEdits(document, options, token) { return provider('format',document,token,'FMT'); }
  }));
  context.subscriptions.push(vscode.languages.registerRenameProvider(selector, {
    prepareRename(document) { own(document); return {range:range(),placeholder:'alpha'}; },
    provideRenameEdits(document, position, newName, token) { return provider('rename',document,token,newName); }
  }));
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(event => {
    if (event.document.uri.toString() === uri.toString()) events.push({kind:'document-change',action,version:event.document.version,text:event.document.getText()});
  }));

  const operations = {
    async 'workspace-fresh'() { await record(async () => {
      const basis = snapshot(), value = editValue('EDIT');
      calls.push({action,api:'workspace.applyEdit',role:'selected-edit',basis,submittedAt:snapshot()});
      return {basis,applied:await vscode.workspace.applyEdit(value)};
    }); },
    async 'workspace-late'() { await record(async () => {
      const basis = snapshot(), value = editValue('EDIT'), intervening = await insertPrefix();
      calls.push({action,api:'workspace.applyEdit',role:'stored-edit',basis,submittedAt:snapshot()});
      return {basis,intervening,applied:await vscode.workspace.applyEdit(value)};
    }); },
    async 'caller-guarded'() { await record(async () => {
      const basis = snapshot(), value = editValue('EDIT'), intervening = await insertPrefix();
      const allowed = doc.version === basis.version;
      const result = allowed ? await vscode.workspace.applyEdit(value) : undefined;
      return {kind:'authored-caller-policy',basis,intervening,allowed,apiCalled:allowed,result:result === undefined ? {kind:'not-called'} : {kind:'returned',value:result}};
    }); },
    async 'editor-parallel'() { await record(async () => {
      const firstBasis = snapshot();
      const first = editor.edit(builder => builder.replace(range(),'ONE'));
      const secondBasis = snapshot();
      const second = editor.edit(builder => builder.replace(range(),'TWO'));
      return {firstBasis,secondBasis,results:await Promise.all([first,second])};
    }); },
    async 'editor-sequential'() { await record(async () => {
      const firstBasis = snapshot(), first = await editor.edit(builder => builder.replace(range(),'ONE'));
      await until(() => doc.version > firstBasis.version,'sequential first edit');
      const secondBasis = snapshot(), second = await editor.edit(builder => builder.replace(range(),'TWO'));
      return {firstBasis,secondBasis,results:[first,second]};
    }); },
    async 'editor-parallel-empty'() { await record(async () => {
      const firstBasis = snapshot(), first = editor.edit(builder => builder.replace(range(),'ONE'));
      const secondBasis = snapshot(), second = editor.edit(() => {});
      return {firstBasis,secondBasis,results:await Promise.all([first,second]),secondHasNoEdits:true};
    }); },
    async 'format-compute'() { await record(async () => {
      const basis = snapshot();
      const result = await vscode.commands.executeCommand('vscode.executeFormatDocumentProvider',uri,{tabSize:2,insertSpaces:true});
      return {basis,returned:plain(result),apiAppliedAnything:false};
    }); },
    async 'format-compute-late-apply'() { await record(async () => {
      const mode = hold('format'), basis = snapshot();
      try {
        const request = vscode.commands.executeCommand('vscode.executeFormatDocumentProvider',uri,{tabSize:2,insertSpaces:true});
        await Promise.race([mode.entered.promise,pause(5000).then(() => { throw new Error('Provider did not enter.'); })]);
        const intervening = await insertPrefix();mode.release.resolve();
        const result = await request;await mode.done.promise;
        const beforeApply = snapshot();let applied = null;
        if (result) { const edit = new vscode.WorkspaceEdit();edit.set(uri,result);applied = await vscode.workspace.applyEdit(edit); }
        return {basis,intervening,returned:plain(result),beforeApply,applied};
      } finally { mode.release.resolve();pending = null; }
    }); },
    async 'interactive-format-late'() { await record(async () => {
      if (vscode.window.activeTextEditor?.document.uri.toString() !== uri.toString()) throw new Error('Active editor is outside the fixture.');
      const mode = hold('format'), basis = snapshot();
      try {
        const request = vscode.commands.executeCommand('editor.action.formatDocument');
        await Promise.race([mode.entered.promise,pause(5000).then(() => { throw new Error('Interactive provider did not enter.'); })]);
        const intervening = await insertPrefix();
        const canceledWithinWindow = await Promise.race([mode.canceled.promise,pause(500).then(() => false)]);
        mode.release.resolve();const result = await request;await mode.done.promise;
        return {basis,intervening,canceledWithinWindow,windowMs:500,commandReturn:result === undefined ? {kind:'undefined'} : {kind:'value',value:result}};
      } finally { mode.release.resolve();pending = null; }
    }); },
    async 'rename-compute'() { await record(async () => {
      const basis = snapshot();
      const result = await vscode.commands.executeCommand('vscode.executeDocumentRenameProvider',uri,new vscode.Position(0,1),'REN');
      return {basis,returned:workspaceValue(result)};
    }); },
    async 'rename-compute-late-apply'() { await record(async () => {
      const mode = hold('rename'), basis = snapshot();
      try {
        const request = vscode.commands.executeCommand('vscode.executeDocumentRenameProvider',uri,new vscode.Position(0,1),'REN');
        await Promise.race([mode.entered.promise,pause(5000).then(() => { throw new Error('Rename provider did not enter.'); })]);
        const intervening = await insertPrefix();mode.release.resolve();
        const result = await request;await mode.done.promise;const beforeApply = snapshot();
        const applied = result ? await vscode.workspace.applyEdit(result) : null;
        return {basis,intervening,returned:workspaceValue(result),beforeApply,applied};
      } finally { mode.release.resolve();pending = null; }
    }); },
    async quit() {
      if (activeProviders) throw new Error('Provider callbacks still active; do not claim retirement.');
      for (const document of vscode.workspace.textDocuments) {
        if (document.uri.toString() === uri.toString() && document.isDirty) {
          if (!await document.save()) throw new Error('Owned document did not save.');
        } else if (document.isDirty) throw new Error('Unowned dirty document; leave this window intact.');
      }
      status = 'quit-requested';write();
      await vscode.commands.executeCommand('workbench.action.quit');
    }
  };
  async function poll() {
    if (busy) return;
    const control = path.join(meta.work,'control.json');
    if (!fs.existsSync(control)) return;
    const request = JSON.parse(fs.readFileSync(control,'utf8'));
    if (request.sequence <= handled) return;
    if (request.sequence !== handled + 1 || !Object.hasOwn(operations,request.action)) { status = 'invalid-control';write();return; }
    busy = true;action = request.action;
    try { await operations[action]();handled = request.sequence;if (action !== 'quit') status = 'ready'; }
    catch (e) { pending?.release.resolve();status = 'fixture-failed';handled = request.sequence;events.push({kind:'fixture-error',action,error:error(e)}); }
    finally { busy = false;write(); }
  }
  const timer = setInterval(() => poll().catch(e => { status='fixture-failed';events.push({kind:'control-error',error:error(e)});write(); }),60);
  context.subscriptions.push(new vscode.Disposable(() => clearInterval(timer)));
  write();
};
