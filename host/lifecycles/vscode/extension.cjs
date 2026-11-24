const vscode=require('vscode');
const fs=require('node:fs/promises');
const path=require('node:path');

exports.activate=async context=>{
  const out=process.env.RULES_VSCODE_OUTPUT;
  if(!out) return;
  const root=path.dirname(out),backing=path.join(root,'document.txt');
  const rows=[];
  const trace=(feature,predicate,observed,decision,extra={})=>{
    rows.push({v:2,profile:'vscode-'+vscode.version,app:'vscode-desktop',
      feature,operationId:feature,target:'rules-study:/document.txt',basis:'1',
      predicate,observed,outcome:{decision,...extra}});
  };
  try {
    await fs.mkdir(root,{recursive:true});
    await fs.writeFile(backing,'original');
    const changes=new vscode.EventEmitter();
    context.subscriptions.push(changes);
    let entered,release,hold=false;
    const writerEntered=new Promise(r=>entered=r);
    const gate=new Promise(r=>release=r);
    const uri=vscode.Uri.parse('rules-study:/document.txt');
    context.subscriptions.push(vscode.workspace.registerFileSystemProvider('rules-study',{
      onDidChangeFile:changes.event,
      watch:()=>({dispose(){}}),
      stat:async()=>{
        const s=await fs.stat(backing);
        return {type:vscode.FileType.File,ctime:s.ctimeMs,mtime:s.mtimeMs,size:s.size};
      },
      readFile:()=>fs.readFile(backing),
      writeFile:async(_uri,bytes)=>{
        if(hold) { entered();await gate; }
        await fs.writeFile(backing,bytes);
        // The direct operation supplies its own result. No independent watcher event is injected.
      },
      readDirectory:()=>[],createDirectory:()=>{},
      delete:()=>{throw vscode.FileSystemError.NoPermissions();},
      rename:()=>{throw vscode.FileSystemError.NoPermissions();},
    },{isCaseSensitive:true}));
    let doc=await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(doc);
    async function setText(text) {
      const edit=new vscode.WorkspaceEdit();
      edit.replace(uri,new vscode.Range(doc.positionAt(0),doc.positionAt(doc.getText().length)),text);
      if(!await vscode.workspace.applyEdit(edit))throw Error('edit refused');
    }
    await setText('revision-1');
    const first=doc.version;
    hold=true;
    const saving=doc.save();
    await Promise.race([writerEntered,new Promise((_,reject)=>setTimeout(()=>reject(Error('provider write did not start')),8000))]);
    await setText('revision-2');
    release();
    const returned=await saving;
    hold=false;
    await new Promise(resolve=>setTimeout(resolve,100));
    const captured=await fs.readFile(backing,'utf8');
    trace('save-raced-edit','save_status',{confirmed:captured==='revision-1',newer_edit:doc.version>first},
      doc.isDirty ? 1 : 0,{saveReturn:returned,buffer:doc.getText(),written:captured,dirty:doc.isDirty});
    // Save the new buffer, close its editor, reopen the resource through the same provider.
    const last=await doc.save();
    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
    doc=await vscode.workspace.openTextDocument(uri);
    trace('save-and-reopen','save_status',{confirmed:last && (await fs.readFile(backing,'utf8'))==='revision-2',newer_edit:false},
      doc.isDirty ? 1 : 0,{buffer:doc.getText(),written:await fs.readFile(backing,'utf8'),dirty:doc.isDirty});
    await fs.writeFile(out,JSON.stringify({version:vscode.version,uiKind:vscode.env.uiKind,rows},null,2));
  } catch(error) {
    await fs.writeFile(out,JSON.stringify({error:error.stack,rows},null,2));
  } finally {
    await vscode.commands.executeCommand('workbench.action.quit');
  }
};
