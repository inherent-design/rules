// Owned development extension: selected API observations and real UI commands.
const vscode=require('vscode');
const fs=require('node:fs');
const path=require('node:path');
const ID='rules-study.activation-target';
exports.activate=async context=>{
  const meta=JSON.parse(fs.readFileSync(process.env.RULES_ACTIVATION_META,'utf8'));
  const output=path.join(meta.capture,process.env.RULES_ACTIVATION_PHASE+'.observed.json');
  const control=path.join(meta.private,'control.json');
  const rows=[],changes=[];let handled=0,busy=false,heldApi=null,state='starting';
  const identity={version:vscode.version,pid:process.pid,parentPid:process.ppid,
    codePid:process.env.VSCODE_PID||null,phase:process.env.RULES_ACTIVATION_PHASE,
    uiKind:vscode.env.uiKind,remoteName:vscode.env.remoteName??null,
    workspace:vscode.workspace.workspaceFolders?.map(f=>f.uri.toString())||[],
    controller:context.extensionUri.toString(),trusted:vscode.workspace.isTrusted};
  const persist=status=>{
    state=status;
    const tmp=output+'.tmp';fs.writeFileSync(tmp,JSON.stringify({schema:1,identity,status,handled,rows,changes},null,2)+'\n');fs.renameSync(tmp,output);
  };
  const view=()=>{
    const extension=vscode.extensions.getExtension(ID);
    return {visible:!!extension,isActive:extension?.isActive??null,kind:extension?.extensionKind??null,
      version:extension?.packageJSON.version??null,path:extension?.extensionPath??null,
      knownOwned:vscode.extensions.all.filter(e=>e.id.startsWith('rules-study.')).map(e=>({id:e.id,active:e.isActive})),
      heartbeat:fs.existsSync(process.env.RULES_ACTIVATION_HEARTBEAT)?JSON.parse(fs.readFileSync(process.env.RULES_ACTIVATION_HEARTBEAT,'utf8')):null};
  };
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const snap=(action,returned=null,error=null)=>{rows.push({sequence:handled,action,observed:view(),returned,error});persist('ready');};
  context.subscriptions.push(vscode.extensions.onDidChange(()=>{changes.push({observed:view()});persist(state);}));
  snap('startup');
  const timer=setInterval(async()=>{
    if(busy)return;busy=true;
    try{
      if(!fs.existsSync(control))return;
      const request=JSON.parse(fs.readFileSync(control,'utf8'));
      if(request.phase!==identity.phase||request.sequence<=handled)return;
      if(request.sequence!==handled+1)throw Error('Nonsequential owned request.');
      handled=request.sequence;rows.push({sequence:handled,action:'requested-'+request.action,observed:view()});persist('pending');
      let returned=null,error=null;
      try{
        if(request.action==='activate'){
          const ext=vscode.extensions.getExtension(ID);if(!ext)throw Error('Target is absent from current extension API.');
          heldApi=await ext.activate();returned=heldApi.ping('activation-ack');
        }else if(request.action==='held-ping'){
          if(!heldApi)throw Error('No previously captured target API.');returned=heldApi.ping('held-after-policy');
        }else if(request.action==='disable-workspace'||request.action==='enable-workspace'){
          const command=request.action==='disable-workspace'?'workbench.extensions.action.disableAllWorkspace':'workbench.extensions.action.enableAllWorkspace';
          returned=(await vscode.commands.executeCommand(command))??null;
        }else if(request.action==='observe'){
          await wait(350);
        }else if(request.action==='quit'){
          snap('quit-requested');persist('quit-requested');
          await vscode.commands.executeCommand('workbench.action.quit');return;
        }else throw Error('Unknown owned action.');
      }catch(e){error={name:e.name,message:e.message};}
      await wait(500);snap(request.action,returned,error);
    }catch(e){rows.push({action:'controller-error',error:String(e)});persist('error');}
    finally{busy=false;}
  },80);
  context.subscriptions.push({dispose(){clearInterval(timer);}});
};
exports.deactivate=()=>{};
