const vscode = require('vscode');
const fs = require('fs/promises');
const path = require('path');

exports.activate = async context => {
  const metaPath = process.env.RULES_VSCODE_CONFIG_META;
  if (!metaPath) return;
  const meta = JSON.parse(await fs.readFile(metaPath, 'utf8'));
  const rows = [], events = [];
  const value = v => v === undefined ? {present: false} : {present: true, value: v};
  const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  const settle = ms => new Promise(resolve => setTimeout(resolve,ms));
  const contexts = ['a','b'].flatMap(folder => ['plaintext','javascript'].map(languageId => ({folder,languageId,uri:vscode.Uri.file(path.join(meta.work,folder,'fixture.txt'))})));
  const config = c => vscode.workspace.getConfiguration('fixture.scope',{uri:c.uri,languageId:c.languageId});
  const aJs = () => config(contexts.find(c => c.folder==='a' && c.languageId==='javascript'));
  const bJs = () => config(contexts.find(c => c.folder==='b' && c.languageId==='javascript'));
  const aPlain = () => config(contexts.find(c => c.folder==='a' && c.languageId==='plaintext'));
  const sources = async () => Object.fromEntries(await Promise.all(Object.entries(meta.settingsFiles).map(async ([key,file]) => [key,await fs.readFile(file,'utf8')])));
  const persist = async (status,error=null) => {
    const payload = {schema:1,identity:{version:vscode.version,appHost:vscode.env.appHost,remoteName:value(vscode.env.remoteName),workspaceFile:vscode.workspace.workspaceFile?.toString(),trusted:vscode.workspace.isTrusted},status,error,rows,events};
    await fs.writeFile(meta.output+'.tmp',JSON.stringify(payload,null,2)+'\n');await fs.rename(meta.output+'.tmp',meta.output);
  };
  const inspect = (cfg,key) => {
    const state=cfg.inspect(key);
    if (!state) return {present:false};
    return {present:true,key:state.key,languageIds:value(state.languageIds),fields:Object.fromEntries(['defaultValue','globalValue','workspaceValue','workspaceFolderValue','defaultLanguageValue','globalLanguageValue','workspaceLanguageValue','workspaceFolderLanguageValue'].map(field => [field,value(state[field])]))};
  };
  const snapshot = async operation => {
    rows.push({operation,sourceFiles:await sources(),contexts:contexts.map(c => {
      const cfg=config(c);
      return {folder:c.folder,languageId:c.languageId,uri:c.uri.toString(),settings:Object.fromEntries(['value','object','nullable'].map(key => [key,{effective:value(cfg.get(key)),inspect:inspect(cfg,key)}]))};
    }),eventsSeen:events.length});
    await persist('running');
  };
  const wait = async predicate => {
    const deadline=Date.now()+5000;
    while (!predicate() && Date.now()<deadline) await settle(40);
    if (!predicate()) throw new Error('Fixture setting did not reach the requested observed state.');
  };
  const update = async (label,key,val,target,language,predicate) => {
    await aJs().update(key,val,target,language);
    await wait(predicate);await settle(100);await snapshot(label);
  };
  try {
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(event => events.push({section:event.affectsConfiguration('fixture.scope'),contexts:contexts.map(c => ({folder:c.folder,languageId:c.languageId,affects:event.affectsConfiguration('fixture.scope',{uri:c.uri,languageId:c.languageId})}))})));
    await wait(() => aJs().inspect('value')?.defaultValue==='base-default');
    await settle(150);await snapshot('initial');
    await update('set-user-language','value','user-js',vscode.ConfigurationTarget.Global,true,() => aJs().get('value')==='user-js' && bJs().get('value')==='user-js');
    await update('set-workspace-language','value','workspace-js',vscode.ConfigurationTarget.Workspace,true,() => aJs().get('value')==='workspace-js' && bJs().get('value')==='workspace-js');
    await update('set-folder-language','value','folder-a-js',vscode.ConfigurationTarget.WorkspaceFolder,true,() => aJs().get('value')==='folder-a-js' && bJs().get('value')==='workspace-js');
    await update('set-masked-user-value','value','user-new',vscode.ConfigurationTarget.Global,false,() => aJs().inspect('value').globalValue==='user-new');
    await update('remove-folder-language','value',undefined,vscode.ConfigurationTarget.WorkspaceFolder,true,() => aJs().get('value')==='workspace-js');
    await update('remove-workspace-language','value',undefined,vscode.ConfigurationTarget.Workspace,true,() => aJs().get('value')==='user-js');
    await update('remove-user-language','value',undefined,vscode.ConfigurationTarget.Global,true,() => aJs().get('value')==='language-default');
    await update('remove-folder-value','value',undefined,vscode.ConfigurationTarget.WorkspaceFolder,false,() => aPlain().get('value')==='workspace');
    await update('remove-nullable','nullable',undefined,vscode.ConfigurationTarget.Global,false,() => aPlain().get('nullable')==='base-nullable');
    await update('replace-workspace-object','object',{workspaceOnly:'w-new',nested:{w:'w-new',x:'workspace-new'}},vscode.ConfigurationTarget.Workspace,false,() => bJs().get('object')?.nested?.x==='workspace-new');
    await persist('complete');await settle(100);
    await vscode.commands.executeCommand('workbench.action.quit');
  } catch(error) {
    await persist('failed',{message:String(error),stack:error?.stack??null});
    await vscode.commands.executeCommand('workbench.action.quit');
  }
};
exports.deactivate = () => {};
