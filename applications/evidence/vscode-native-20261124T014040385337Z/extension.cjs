const vscode = require('vscode');
const fs = require('node:fs/promises');
const path = require('node:path');

exports.activate = async context => {
  const metaPath = process.env.RULES_VSCODE_FIXTURE;
  if (!metaPath) return;
  const meta = JSON.parse(await fs.readFile(metaPath, 'utf8'));
  const target = path.join(meta.work, 'project', 'document.txt');
  const uri = vscode.Uri.file(target);
  const control = path.join(meta.work, 'control.json');
  const rows = [], events = [];
  let handled = 0, busy = false, watcherChanges = 0, doc;
  const identity = {version: vscode.version, uiKind: vscode.env.uiKind,
    workspace: vscode.workspace.workspaceFolders?.map(f => f.uri.toString()) || [],
    extensionPath: context.extensionPath, extensionHostPid: process.pid,
    parentPid: process.ppid, codePid: process.env.VSCODE_PID || null};
  const persist = async status => {
    await fs.writeFile(meta.output + '.tmp', JSON.stringify({identity, status, handled, rows, events}, null, 2) + '\n');
    await fs.rename(meta.output + '.tmp', meta.output);
  };
  const snapshot = async (operation, returned = null) => {
    rows.push({operationId: String(handled), operation,
      observed: {uri: doc.uri.toString(), version: String(doc.version), dirty: doc.isDirty,
        closed: doc.isClosed, buffer: doc.getText(), disk: await fs.readFile(target, 'utf8'), watcherChanges},
      outcome: {returned}});
    await persist('ready');
  };
  const waitFor = async predicate => {
    const deadline = Date.now() + 5000;
    while (!predicate() && Date.now() < deadline) await new Promise(r => setTimeout(r, 40));
    return predicate();
  };
  const replace = async text => {
    const edit = new vscode.WorkspaceEdit();
    edit.replace(uri, new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length)), text);
    return vscode.workspace.applyEdit(edit);
  };
  try {
    context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(e => {
      if (e.document.uri.toString() === uri.toString())
        events.push({kind: 'text-change', version: String(e.document.version), reason: e.reason ?? null});
    }));
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(d => {
      if (d.uri.toString() === uri.toString()) events.push({kind: 'save', version: String(d.version)});
    }));
    const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(path.dirname(target), 'document.txt'));
    context.subscriptions.push(watcher, watcher.onDidChange(() => {watcherChanges++;}));
    doc = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(doc, {preview: false});
    await snapshot('open');
    const timer = setInterval(async () => {
      if (busy) return;
      busy = true;
      try {
        let request;
        try { request = JSON.parse(await fs.readFile(control, 'utf8')); }
        catch (e) { if (e.code === 'ENOENT') return; throw e; }
        if (!Number.isSafeInteger(request.sequence) || request.sequence <= handled) return;
        handled = request.sequence;
        let returned = null;
        switch (request.action) {
          case 'edit-one': returned = await replace('draft-one\n'); break;
          case 'edit-two': returned = await replace('draft-two\n'); break;
          case 'save': returned = await doc.save(); break;
          case 'undo': returned = await vscode.commands.executeCommand('undo'); break;
          case 'redo': returned = await vscode.commands.executeCommand('redo'); break;
          case 'external-clean': {
            const prior = watcherChanges;
            await fs.writeFile(target, 'external-clean\n');
            returned = {watchEvent: await waitFor(() => watcherChanges > prior),
              bufferReloaded: await waitFor(() => doc.getText() === 'external-clean\n')};
            break;
          }
          case 'edit-dirty': returned = await replace('local-unsaved\n'); break;
          case 'external-dirty': {
            const prior = watcherChanges;
            await fs.writeFile(target, 'external-dirty\n');
            returned = {watchEvent: await waitFor(() => watcherChanges > prior)};
            break;
          }
          case 'revert': returned = await vscode.commands.executeCommand('workbench.action.files.revert'); break;
          case 'quit':
            clearInterval(timer);
            await snapshot('quit-requested');
            await persist('quit-requested');
            await vscode.commands.executeCommand('workbench.action.quit');
            return;
          default: throw Error('Unsupported fixture action: ' + request.action);
        }
        await snapshot(request.action, returned ?? null);
      } catch (error) {
        rows.push({operationId: String(handled), outcome: {error: String(error.stack || error)}});
        await persist('error');
      } finally { busy = false; }
    }, 80);
    context.subscriptions.push({dispose: () => clearInterval(timer)});
  } catch (error) {
    rows.push({outcome: {error: String(error.stack || error)}});
    await persist('error');
  }
};
