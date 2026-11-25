const vscode=require('vscode'),fs=require('fs'),path=require('path');
const utf8=new TextEncoder(),text=b=>new TextDecoder().decode(b),pause=ms=>new Promise(r=>setTimeout(r,ms));
exports.activate=function(context){
 const meta=JSON.parse(fs.readFileSync(process.env.RULES_VFS_FIXTURE,'utf8')),output=meta.output,work=meta.work;
 const calls=[],events=[],providers=[],registrations=[],rows=[];let handled=0,status='ready',busy=false,clock=1000;
 const err=e=>({name:e?.name??null,code:e?.code??null,message:String(e?.message??e)});
 function persist(){const value={schema:1,version:vscode.version,handled,status,rows,calls,events,providers:providers.map(p=>p.snapshot())};const temp=output+'.tmp';fs.writeFileSync(temp,JSON.stringify(value,null,2)+'\n');fs.renameSync(temp,output);}
 class Provider{
  constructor(id,{enforceReadonly=false}={}){this.id=id;this.enforceReadonly=enforceReadonly;this.files=new Map();this.dirs=new Set(['/']);this.readonly=new Set();this.emitter=new vscode.EventEmitter();this.onDidChangeFile=this.emitter.event;this.hold=null;this.activeWatches=0;providers.push(this);}
  log(op,uri,extra={}){calls.push({provider:this.id,op,path:uri.path,...extra});}
  snapshot(){return{id:this.id,files:Object.fromEntries([...this.files].map(([p,b])=>[p,text(b)])),directories:[...this.dirs].sort(),readonly:[...this.readonly].sort(),activeWatches:this.activeWatches};}
  seed(p,body){this.files.set(p,utf8.encode(body));}
  watch(uri,options){this.log('watch',uri,{options});this.activeWatches++;return new vscode.Disposable(()=>{this.log('watch-disposed',uri);this.activeWatches--;});}
  stat(uri){this.log('stat',uri);if(this.dirs.has(uri.path))return{type:vscode.FileType.Directory,ctime:1,mtime:clock,size:0};const b=this.files.get(uri.path);if(!b)throw vscode.FileSystemError.FileNotFound(uri);return{type:vscode.FileType.File,ctime:1,mtime:clock,size:b.length,permissions:this.readonly.has(uri.path)?vscode.FilePermission.Readonly:undefined};}
  readDirectory(uri){this.log('readDirectory',uri);if(!this.dirs.has(uri.path))throw vscode.FileSystemError.FileNotFound(uri);const prefix=uri.path==='/'?'/':uri.path+'/';return [...this.files].filter(([p])=>p.startsWith(prefix)&&!p.slice(prefix.length).includes('/')).map(([p])=>[p.slice(prefix.length),vscode.FileType.File]);}
  readFile(uri){this.log('readFile',uri);const b=this.files.get(uri.path);if(!b)throw vscode.FileSystemError.FileNotFound(uri);return b;}
  createDirectory(uri){this.log('createDirectory',uri);this.dirs.add(uri.path);clock++;}
  async writeFile(uri,bytes,options){this.log('write-enter',uri,{hex:Buffer.from(bytes).toString('hex'),options});if(this.enforceReadonly&&this.readonly.has(uri.path)){this.log('write-refused',uri,{reason:'fixture-provider-readonly'});throw vscode.FileSystemError.NoPermissions('Fixture provider denies this file');}if(this.hold&&this.hold.path===uri.path){const hold=this.hold;hold.entered=true;await hold.promise;this.hold=null;}this.files.set(uri.path,new Uint8Array(bytes));clock++;this.log('write-complete',uri,{hex:Buffer.from(bytes).toString('hex')});}
  delete(uri){this.log('delete',uri);if(!this.files.delete(uri.path))throw vscode.FileSystemError.FileNotFound(uri);clock++;}
  rename(oldUri,newUri,options){this.log('rename',oldUri,{target:newUri.path,options});const b=this.files.get(oldUri.path);if(!b)throw vscode.FileSystemError.FileNotFound(oldUri);if(this.files.has(newUri.path)&&!options.overwrite)throw vscode.FileSystemError.FileExists(newUri);this.files.set(newUri.path,b);this.files.delete(oldUri.path);clock++;}
  defer(p){let release;const promise=new Promise(r=>{release=r;});this.hold={path:p,promise,release,entered:false};return this.hold;}
 }
 function register(scheme,p,readonly=false){const d=vscode.workspace.registerFileSystemProvider(scheme,p,{isCaseSensitive:true,isReadonly:readonly});registrations.push(d);return d;}
 async function until(predicate,ms=4000){const end=Date.now()+ms;while(!predicate()){if(Date.now()>end)throw Error('Fixture wait timed out');await pause(20);}}
 function snapshot(){return providers.map(p=>p.snapshot());}
 async function record(name,action){const before=snapshot(),start=calls.length,eventStart=events.length;let result,error=null;try{result=await action();}catch(e){error=err(e);}rows.push({name,before,after:snapshot(),callStart:start,callEnd:calls.length,eventStart,eventEnd:events.length,result:result??null,error});persist();return{result,error};}
 const writable=new Provider('writable');writable.seed('/file.txt','original\n');const writableReg=register('rules-vfs-write',writable);const uri=vscode.Uri.parse('rules-vfs-write:/file.txt');
 const operations={
  async baseline(){
   await until(()=>vscode.workspace.fs.isWritableFileSystem('rules-vfs-write')===true);
   await record('unknown-scheme',async()=>({writable:vscode.workspace.fs.isWritableFileSystem('rules-vfs-unknown')??null,known:vscode.workspace.fs.isWritableFileSystem('rules-vfs-unknown')!==undefined}));
   await record('unknown-read',()=>vscode.workspace.fs.readFile(vscode.Uri.parse('rules-vfs-unknown:/file.txt')));
   await record('writable-stat',async()=>({writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme),stat:await vscode.workspace.fs.stat(uri)}));
   await record('read-copy',async()=>{const b=await vscode.workspace.fs.readFile(uri),original=text(b);b[0]=88;return{original,mutated:text(b),again:text(await vscode.workspace.fs.readFile(uri))};});
   await record('missing-file',()=>vscode.workspace.fs.readFile(vscode.Uri.parse('rules-vfs-write:/missing.txt')));
   await record('duplicate-registration',()=>{const p=new Provider('rejected-duplicate');return register(uri.scheme,p);});
   await record('write-normal',async()=>{await vscode.workspace.fs.writeFile(uri,utf8.encode('first saved\n'));return{text:text(await vscode.workspace.fs.readFile(uri))};});
   await record('write-creates-parent',async()=>{const u=vscode.Uri.parse('rules-vfs-write:/new/child.txt');await vscode.workspace.fs.writeFile(u,utf8.encode('child\n'));return{stat:await vscode.workspace.fs.stat(u),text:text(await vscode.workspace.fs.readFile(u))};});
   await record('list-directory',()=>vscode.workspace.fs.readDirectory(vscode.Uri.parse('rules-vfs-write:/new')));
  },
  async readonly(){
   const global=new Provider('scheme-readonly');global.seed('/file.txt','scheme original\n');register('rules-vfs-readonly',global,true);await until(()=>vscode.workspace.fs.isWritableFileSystem('rules-vfs-readonly')===false);const ro=vscode.Uri.parse('rules-vfs-readonly:/file.txt');
   await record('readonly-scheme-stat',async()=>({writable:vscode.workspace.fs.isWritableFileSystem(ro.scheme),stat:await vscode.workspace.fs.stat(ro)}));
   await record('readonly-scheme-write',()=>vscode.workspace.fs.writeFile(ro,utf8.encode('should not reach provider\n')));
   writable.readonly.add('/file.txt');await record('readonly-file-stat',async()=>({writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme),stat:await vscode.workspace.fs.stat(uri)}));
   await record('readonly-file-permissive-provider',async()=>{await vscode.workspace.fs.writeFile(uri,utf8.encode('provider permitted\n'));return{text:text(await vscode.workspace.fs.readFile(uri))};});
   writable.enforceReadonly=true;await record('readonly-file-enforcing-provider',()=>vscode.workspace.fs.writeFile(uri,utf8.encode('provider should refuse\n')));writable.enforceReadonly=false;writable.readonly.clear();
  },
  async queued(){
   const u=vscode.Uri.parse('rules-vfs-write:/queue.txt');writable.seed('/queue.txt','queue original\n');const hold=writable.defer('/queue.txt');
   const first=vscode.workspace.fs.writeFile(u,utf8.encode('first queued\n'));await until(()=>hold.entered);
   const bytes=utf8.encode('second queued\n');let secondDone=false;const second=vscode.workspace.fs.writeFile(u,bytes).then(()=>{secondDone=true;});bytes[0]=88;
   await pause(80);await record('queue-before-release',()=>({secondDone,writeEntries:calls.filter(c=>c.provider===writable.id&&c.op==='write-enter'&&c.path==='/queue.txt').length}));
   hold.release();await first;await second;await record('queue-mutated-input-result',async()=>({secondDone,text:text(await vscode.workspace.fs.readFile(u))}));
  },
  async incarnation(){
   const old=new Provider('old-incarnation');old.seed('/file.txt','old backing\n');const oldReg=register('rules-vfs-incarnation',old);await until(()=>vscode.workspace.fs.isWritableFileSystem('rules-vfs-incarnation')===true);const u=vscode.Uri.parse('rules-vfs-incarnation:/file.txt'),hold=old.defer('/file.txt');
   let oldDone=false;const pending=vscode.workspace.fs.writeFile(u,utf8.encode('old completed\n')).then(()=>{oldDone=true;});await until(()=>hold.entered);oldReg.dispose();
   await record('disposed-scheme-view',()=>({writable:vscode.workspace.fs.isWritableFileSystem(u.scheme)??null,known:vscode.workspace.fs.isWritableFileSystem(u.scheme)!==undefined,oldDone}));
   const fresh=new Provider('new-incarnation');fresh.seed('/file.txt','new backing\n');register(u.scheme,fresh);await until(()=>vscode.workspace.fs.isWritableFileSystem(u.scheme)===true);
   await record('rebound-before-old-completes',async()=>({oldDone,current:text(await vscode.workspace.fs.readFile(u))}));hold.release();await pending;
   await record('old-write-completed-after-rebind',async()=>({oldDone,current:text(await vscode.workspace.fs.readFile(u)),old:old.snapshot(),fresh:fresh.snapshot()}));
  },
  async watch(){
   const observed=[];const watcher=vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.parse('rules-vfs-write:/'),'**/*'));watcher.onDidChange(u=>{observed.push(u.toString());events.push({kind:'watch-changed',uri:u.toString()});});await until(()=>writable.activeWatches>0);
   writable.emitter.fire([{type:vscode.FileChangeType.Changed,uri}]);await until(()=>observed.length>0);await record('watched-event-delivered',()=>({observed:[...observed],activeWatches:writable.activeWatches}));watcher.dispose();await until(()=>writable.activeWatches===0);const prior=observed.length;writable.emitter.fire([{type:vscode.FileChangeType.Changed,uri}]);await pause(250);await record('watch-disposed-quiet-window',()=>({before:prior,after:observed.length,waitMs:250,activeWatches:writable.activeWatches}));
  },
  async detached(){
   await until(()=>vscode.workspace.fs.isWritableFileSystem(uri.scheme)===true);
   writableReg.dispose();await record('disposed-immediate-view',()=>({known:vscode.workspace.fs.isWritableFileSystem(uri.scheme)!==undefined,writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme)??null}));
   await pause(500);await record('disposed-settled-view',()=>({known:vscode.workspace.fs.isWritableFileSystem(uri.scheme)!==undefined,writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme)??null,waitMs:500}));await record('disposed-read',()=>vscode.workspace.fs.readFile(uri));
   const replacement=new Provider('readonly-replacement');replacement.seed('/file.txt','readonly replacement\n');const reg=register(uri.scheme,replacement,true);await until(()=>vscode.workspace.fs.isWritableFileSystem(uri.scheme)===false);await record('readonly-rebound-view',async()=>({known:true,writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme),text:text(await vscode.workspace.fs.readFile(uri))}));
   reg.dispose();await pause(500);await record('readonly-disposed-settled-view',()=>({known:vscode.workspace.fs.isWritableFileSystem(uri.scheme)!==undefined,writable:vscode.workspace.fs.isWritableFileSystem(uri.scheme)??null,waitMs:500}));await record('readonly-disposed-read',()=>vscode.workspace.fs.readFile(uri));
  },
  async quit(){for(const d of registrations)d.dispose();for(const p of providers)p.emitter.dispose();status='quit-requested';persist();await vscode.commands.executeCommand('workbench.action.quit');}
 };
 async function poll(){if(busy)return;const p=path.join(work,'control.json');if(!fs.existsSync(p))return;const request=JSON.parse(fs.readFileSync(p,'utf8'));if(request.sequence<=handled)return;if(request.sequence!==handled+1||!Object.hasOwn(operations,request.action)){status='invalid-control';persist();return;}busy=true;try{await operations[request.action]();handled=request.sequence;status='ready';}catch(e){status='fixture-failed';events.push({kind:'fixture-error',action:request.action,error:err(e)});handled=request.sequence;}finally{busy=false;persist();}}
 const timer=setInterval(poll,60);context.subscriptions.push(new vscode.Disposable(()=>clearInterval(timer)));persist();
};
