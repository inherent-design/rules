const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
exports.activate = async function(context) {
  const meta = JSON.parse(fs.readFileSync(process.env.RULES_VSCODE_TASK_META, 'utf8'));
  const rows = [], owned = [], disposables = [];
  const ids = new WeakMap(); let next = 1;
  const id = execution => { if (!ids.has(execution)) ids.set(execution, next++); return ids.get(execution); };
  let providerDisposed = false, workerAlive = false;
  const active = () => vscode.tasks.taskExecutions.filter(e => e.task.name.startsWith('rules-')).map(e => ({id:id(e), name:e.task.name}));
  function note(kind, fields={}) {
    rows.push({sequence:rows.length, kind, ...fields, active:active(), workerAlive});
    fs.writeFileSync(meta.output, JSON.stringify({schema:1, status:'collecting', rows}, null, 2)+'\n');
  }
  function listen(event, kind, extra=()=>({})) {
    disposables.push(event(e => note(kind,{name:e.execution.task.name,id:id(e.execution),...extra(e)})));
  }
  listen(vscode.tasks.onDidStartTask,'task-start');listen(vscode.tasks.onDidEndTask,'task-end');
  listen(vscode.tasks.onDidStartTaskProcess,'process-start',e=>({pid:e.processId}));
  listen(vscode.tasks.onDidEndTaskProcess,'process-end',e=>({exitCode:e.exitCode===undefined?null:e.exitCode}));
  const sleep = ms => new Promise(r=>setTimeout(r,ms));
  async function until(test,label,ms=6000) { const start=Date.now();while(!test()){if(Date.now()-start>ms)throw Error('Timed out: '+label);await sleep(20);} }
  const ended = name => rows.some(r=>r.kind==='task-end'&&r.name===name);
  function childTask(name, mode) {
    const args=[meta.worker,'--log',meta.childLog,'--name',name,'--mode',mode,'--gate',meta.gate,
      '--value','a b','--value','Ω 日本','--value','$RULES_LITERAL'];
    const t=new vscode.Task({type:'rules-task-study',name},vscode.TaskScope.Workspace,'rules-'+name,'rules-study',
      new vscode.ProcessExecution(meta.python,args,{cwd:meta.project,env:{RULES_LITERAL:'must-not-expand'}}),[]);
    t.presentationOptions={reveal:vscode.TaskRevealKind.Never,panel:vscode.TaskPanelKind.Dedicated,showReuseMessage:false};
    return t;
  }
  let closeHold;
  function custom(name, hold=false) {
    const t=new vscode.Task({type:'rules-task-study',name},vscode.TaskScope.Workspace,'rules-'+name,'rules-study',new vscode.CustomExecution(async definition=>{
      note('custom-callback',{name:'rules-'+name,definition});
      const write=new vscode.EventEmitter(), close=new vscode.EventEmitter();
      const pty={onDidWrite:write.event,onDidClose:close.event,
        open(){note('pty-open',{name:'rules-'+name});if(hold){workerAlive=true;closeHold=()=>{workerAlive=false;note('worker-retired',{name:'rules-'+name});};}
          else setTimeout(()=>{note('pty-report-close',{name:'rules-'+name,code:7});close.fire(7);},30);},
        close(){note('pty-close-request',{name:'rules-'+name});close.fire(0);}}
      return pty;
    }),[]);
    t.presentationOptions={reveal:vscode.TaskRevealKind.Never,panel:vscode.TaskPanelKind.Dedicated,showReuseMessage:false};
    return t;
  }
  try {
    note('profile',{version:vscode.version,uiKind:vscode.env.uiKind,remoteName:vscode.env.remoteName??null});
    const provided=custom('provider-hold',true);
    const provider=vscode.tasks.registerTaskProvider('rules-task-study',{
      provideTasks(){note('provider-fetch');return [provided];},
      resolveTask(task){note('provider-resolve',{definition:task.definition});return task;}
    });
    const fetched=await vscode.tasks.fetchTasks({type:'rules-task-study'});
    note('fetched',{names:fetched.map(t=>t.name)});
    const bad=new vscode.Task({type:'rules-task-study',name:'invalid'},vscode.TaskScope.Workspace,'rules-invalid','rules-study');
    try {await vscode.tasks.executeTask(bad);note('invalid-accepted');}catch(error){note('invalid-refused',{message:String(error)});}
    let execution=await vscode.tasks.executeTask(custom('custom-seven'));
    owned.push(execution);note('execute-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>ended('rules-custom-seven'),'custom end');
    execution=await vscode.tasks.executeTask(fetched.find(t=>t.name==='rules-provider-hold'));
    owned.push(execution);note('execute-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>rows.some(r=>r.kind==='pty-open'&&r.name===execution.task.name),'provider open');
    provider.dispose();providerDisposed=true;note('provider-disposed');
    const later=await vscode.tasks.fetchTasks({type:'rules-task-study'});note('fetched-after-dispose',{names:later.map(t=>t.name)});
    execution.terminate();note('terminate-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>ended('rules-provider-hold'),'held task end');
    note('after-task-end-before-owned-worker-cleanup');closeHold();
    execution=await vscode.tasks.executeTask(childTask('process-seven','exit'));owned.push(execution);note('execute-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>ended('rules-process-seven'),'process seven end');
    execution=await vscode.tasks.executeTask(childTask('process-stop','wait'));owned.push(execution);note('execute-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>rows.some(r=>r.kind==='process-start'&&r.name==='rules-process-stop'),'process start');
    execution.terminate();note('terminate-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>ended('rules-process-stop'),'process stop end');
    const configured=await vscode.tasks.fetchTasks();
    note('configured-fetched',{names:configured.filter(t=>t.name.startsWith('rules-')).map(t=>t.name)});
    const dependent=configured.find(t=>t.name==='rules-dependent');if(!dependent)throw Error('Configured dependency task missing');
    execution=await vscode.tasks.executeTask(dependent);owned.push(execution);note('execute-returned',{name:execution.task.name,id:id(execution)});
    await until(()=>rows.some(r=>r.kind==='process-start'&&r.name==='rules-background'),'background process');
    fs.writeFileSync(meta.gate,'ready\n');note('readiness-gate-released');
    await until(()=>ended('rules-dependent'),'dependent task end');
    const bg=vscode.tasks.taskExecutions.find(e=>e.task.name==='rules-background');
    note('dependency-finished',{backgroundStillActive:!!bg});
    if(bg){owned.push(bg);bg.terminate();note('terminate-returned',{name:bg.task.name,id:id(bg)});await until(()=>ended('rules-background'),'background end');}
    await until(()=>active().length===0,'no active owned tasks');
    note('complete');
    fs.writeFileSync(meta.output,JSON.stringify({schema:1,status:'complete',providerDisposed,rows},null,2)+'\n');
  } catch(error) {
    note('fixture-error',{message:String(error),stack:error.stack});
    fs.writeFileSync(meta.output,JSON.stringify({schema:1,status:'failed',rows,error:String(error)},null,2)+'\n');
  } finally {
    if(closeHold&&workerAlive)closeHold();
    for(const e of vscode.tasks.taskExecutions)if(e.task.name.startsWith('rules-'))e.terminate();
    await sleep(300);
    for(const d of disposables)d.dispose();
    await vscode.commands.executeCommand('workbench.action.quit');
  }
};
