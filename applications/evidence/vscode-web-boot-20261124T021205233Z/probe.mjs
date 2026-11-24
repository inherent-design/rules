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
const run=join(root,'applications/evidence','vscode-web-boot-'+new Date().toISOString().replace(/[-:.]/g,''));
const work=join(run,'work');
await mkdir(work,{recursive:true});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const errors=[],modules=[],pending=[];
let context,observation,error;
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
  const metadata=await page.evaluate(()=>({title:document.title,
    versionInfo:document.querySelector('meta[name="vscode:versionInfo"]')?.getAttribute('content'),
    baseURL:document.querySelector('meta[name="vscode:baseURL"]')?.getAttribute('content'),
    userAgent:navigator.userAgent,platform:navigator.platform,secure:isSecureContext,
    capabilities:{openPicker:typeof showOpenFilePicker==='function',savePicker:typeof showSaveFilePicker==='function',
      directoryPicker:typeof showDirectoryPicker==='function',opfs:typeof navigator.storage.getDirectory==='function',indexedDB:!!indexedDB}}));
  await Promise.all(pending);
  observation={...metadata,url:page.url(),browserVersion:context.browser().version(),sdkVersion:sdk.version,
    workbenchPresent:await page.locator('.monaco-workbench').count()>0,
    visibleText:(await page.locator('body').innerText()).slice(0,4000),pages:context.pages().length,
    workbenchModules:modules,errors};
} catch(e) {error={name:e.name,message:e.message};}
finally {if(context)await context.close();}
const receipt={schema:1,kind:'Anonymous vscode.dev boot in isolated headless Chromium; not file save/reopen qualification',
  entrypointSha256:digest(await readFile(fileURLToPath(import.meta.url))),sdkPackage:packagePath,sdkVersion:sdk.version,
  platform:os.platform(),architecture:os.arch(),seconds:(performance.now()-started)/1000,
  observation,error,limits:['No sign-in,remote repository,local file grant,editing,persistence,or browser relaunch tested.',
    'API presence is not permission or successful operation. Headless boot is not graphical keyboard/accessibility acceptance.']};
await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({run,browser:observation?.browserVersion,versionInfo:observation?.versionInfo,workbenchPresent:observation?.workbenchPresent,modules:modules.length,error},null,2));
if(error)process.exitCode=1;
