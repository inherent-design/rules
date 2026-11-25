const fs=require('node:fs');const {createRequire}=require('node:module');
const path=require('node:path');const root=process.argv[2];const req=createRequire(path.join(root,'package.json'));
const output={};for(const name of ['rules-deploy-lib','rules-deploy-ext','rules-deploy-leaf','rules-deploy-opt','rules-deploy-dev']){
try{const found=req.resolve(name);output[name]={value:req(name),realpath:fs.realpathSync(found)};}catch(error){output[name]={error:error.code};}}
output.app=req('./index.cjs');console.log(JSON.stringify(output));
