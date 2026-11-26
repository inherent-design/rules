// Owned target extension. File receipts witness actual calls, not policy alone.
const fs=require('node:fs');
let timer;
const emit=(kind,extra={})=>fs.appendFileSync(process.env.RULES_ACTIVATION_EVENTS,JSON.stringify({kind,pid:process.pid,phase:process.env.RULES_ACTIVATION_PHASE,...extra})+'\n');
exports.activate=context=>{
  let ticks=0;
  emit('activate',{mode:context.extensionMode,extensionUri:context.extensionUri.toString()});
  timer=setInterval(()=>fs.writeFileSync(process.env.RULES_ACTIVATION_HEARTBEAT,JSON.stringify({pid:process.pid,ticks:++ticks})+'\n'),100);
  context.subscriptions.push({dispose(){clearInterval(timer);emit('dispose');}});
  return {ping(value){emit('ping',{value,ticks});return {value,pid:process.pid,ticks};}};
};
exports.deactivate=()=>{clearInterval(timer);emit('deactivate');};
