// Owner-run anonymous web boot check. No user profile, account, or local file picker.
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import os from 'node:os';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const packagePath=join(root,'applications/tools/playwright-core-1.64.1/package/package.json');
const require=createRequire(packagePath);
const {chromium}=require('.');
const sdk=JSON.parse(await readFile(packagePath,'utf8'));
const mode=process.argv[2]??'boot';
if(!['boot','untitled-reload'].includes(mode))throw Error('Use boot or untitled-reload.');
const run=join(root,'applications/evidence','vscode-web-'+mode+'-'+new Date().toISOString().replace(/[-:.]/g,''));
const work=join(run,'work');
await mkdir(work,{recursive:true});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const errors=[],modules=[],pending=[];
let context,observation,error,editing;
const started=performance.now();
try {
  context=await chromium.launchPersistentContext(join(work,'profile'),{headless:true,chromiumSandbox:true,
    viewport:{width:1280,height:900},env:{PATH:'/usr/bin:/bin',HOME:os.homedir(),LANG:'en_US.UTF-8'}});
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push({kind:'pageerror',message:e.message.slice(0,300)}));
  page.on('response',response=>{
    if(/^https:\/\/main\.vscode-cdn\.net\/stable\/[a-f0-9]{40}\/out\/vs\/workbench\/workbench\.web\.main\.internal\.js$/.test(response.url()))
      pending.push(response.body().then(body=>modules.push({url:response.url(),status:response.status(),sha256:digest(body),bytes:body.length})).catch(e=>errors.push({kind:'module-body',message:e.message.slice(0,200)})));
  });
  await page.goto('https://vscode.dev/?vscode-lang=en',{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForSelector('.monaco-workbench',{timeout:45000});
  await page.waitForTimeout(1500);
  if(mode==='untitled-reload') {
    const marker='rules-web-draft-20261124-Ω-日本';
    await page.keyboard.press('F1');
    const input=page.locator('.quick-input-widget input').first();
    await input.fill('>File: New Untitled Text File');
    const option=page.locator('.quick-input-list .monaco-list-row').first();
    await option.waitFor({state:'visible'});
    const selected=await option.innerText();
    if(!selected.includes('New Untitled Text File'))throw Error('Unexpected palette choice: '+selected);
    await page.keyboard.press('Enter');
    const editor=page.locator('.monaco-editor').last();
    await editor.waitFor({state:'visible'});
    await editor.click({position:{x:120,y:30}});
    const focus=await page.evaluate(()=>({nativeEditContext:typeof EditContext==='function',
      activeTag:document.activeElement?.tagName,activeClass:document.activeElement?.className,
      inEditor:!!document.activeElement?.closest('.monaco-editor'),
      editors:[...document.querySelectorAll('.monaco-editor')].map(n=>({role:n.getAttribute('role'),height:n.getBoundingClientRect().height}))}));
    await writeFile(join(run,'editor-focus.json'),JSON.stringify(focus,null,2)+'\n');
    if(!focus.inEditor)throw Error('Created editor did not own keyboard focus; inspect editor-focus.json.');
    await page.keyboard.insertText(marker);
    await page.waitForTimeout(200);
    const typed=await page.evaluate(()=>({activeEditContextText:document.activeElement?.editContext?.text,
      allRenderedText:[...document.querySelectorAll('.view-lines')].map(n=>n.textContent),
      activeClass:document.activeElement?.className}));
    await writeFile(join(run,'typed-state.json'),JSON.stringify(typed,null,2)+'\n');
    await page.waitForFunction(value=>[...document.querySelectorAll('.view-lines')].some(n=>n.textContent?.includes(value)),marker,{timeout:5000});
    const before={renderedText:await page.locator('.view-lines').allTextContents(),
      tabs:await page.locator('.tab').evaluateAll(nodes=>nodes.map(n=>({label:n.getAttribute('aria-label'),className:n.className})))};
    await page.screenshot({path:join(run,'before-reload.png')});
    await page.waitForTimeout(2000); // observation delay, not a backup-completion receipt
    const dialogs=[];
    page.on('dialog',async dialog=>{dialogs.push({type:dialog.type(),message:dialog.message(),decision:'accept-owned-fixture-reload'});await dialog.accept();});
    await page.reload({waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForSelector('.monaco-workbench',{timeout:45000});
    let restored=false;
    try {await page.waitForFunction(value=>[...document.querySelectorAll('.view-lines')].some(n=>n.textContent?.includes(value)),marker,{timeout:10000});restored=true;}
    catch(e) {if(e.name!=='TimeoutError')throw e;}
    await page.screenshot({path:join(run,'after-reload.png')});
    editing={marker,paletteChoice:selected,before,dialogs,markerObservedAfterReload:restored,
      afterRenderedText:await page.locator('.view-lines').allTextContents(),
      qualification:'Rendered marker in one same-origin/profile reload only; no file grant/export or durability receipt.'};
  }
  const metadata=await page.evaluate(()=>({title:document.title,
    versionInfo:document.querySelector('meta[name="vscode:versionInfo"]')?.getAttribute('content'),
    baseURL:document.querySelector('meta[name="vscode:baseURL"]')?.getAttribute('content'),
    userAgent:navigator.userAgent,platform:navigator.platform,secure:isSecureContext,
    capabilities:{openPicker:typeof showOpenFilePicker==='function',savePicker:typeof showSaveFilePicker==='function',
      directoryPicker:typeof showDirectoryPicker==='function',opfs:typeof navigator.storage.getDirectory==='function',indexedDB:!!indexedDB}}));
  await Promise.all(pending);
  observation={...metadata,url:page.url(),browserVersion:context.browser().version(),sdkVersion:sdk.version,editing,
    workbenchPresent:await page.locator('.monaco-workbench').count()>0,
    visibleText:(await page.locator('body').innerText()).slice(0,4000),pages:context.pages().length,
    workbenchModules:modules,errors};
} catch(e) {error={name:e.name,message:e.message};}
finally {if(context)await context.close();}
const receipt={schema:1,mode,kind:'Anonymous vscode.dev headless UI observation; not local-file or durable-project qualification',
  entrypointSha256:digest(await readFile(fileURLToPath(import.meta.url))),sdkPackage:packagePath,sdkVersion:sdk.version,
  platform:os.platform(),architecture:os.arch(),seconds:(performance.now()-started)/1000,
  observation,error,limits:['No sign-in,remote repository,local file grant/export,or browser-process relaunch tested.',
    'API presence is not permission or successful operation. Headless boot is not graphical keyboard/accessibility acceptance.']};
await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
await writeFile(join(run,'probe.mjs'),await readFile(fileURLToPath(import.meta.url)));
console.log(JSON.stringify({run,browser:observation?.browserVersion,versionInfo:observation?.versionInfo,workbenchPresent:observation?.workbenchPresent,markerObservedAfterReload:editing?.markerObservedAfterReload,modules:modules.length,error},null,2));
if(error)process.exitCode=1;
