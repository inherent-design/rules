export const predicates=Object.freeze({
  draft:['retained','current','writable'],
  execute:['capable','complete','approved'],
  save_status:['confirmed','newer_edit'],
  collect:['covered','saved','undo','plan','active'],
  retire:['closed','end_confirmed'],
  consume:['identity','compatible','covered'],
  finalized:['receipt','valid'],
});
export function revision(value) {
  if(typeof value!=='string' || !/^(0|[1-9][0-9]*)$/.test(value)) {
    throw TypeError('revision must be a canonical unsigned decimal string');
  }
  return BigInt(value);
}
export function decodeTrace(row) {
  if(row.v!==2) throw Error('unsupported lifecycle trace version');
  for(const key of ['profile','app','feature','operationId','target']) {
    if(typeof row[key]!=='string'||!row[key])throw Error('missing lifecycle identity: '+key);
  }
  revision(row.basis);
  const keys=predicates[row.predicate];
  if(!keys)throw Error('unknown lifecycle predicate');
  const flags=keys.map(k=>row.observed?.[k]);
  if(flags.some(f=>typeof f!=='boolean'))throw Error('missing Boolean host witness');
  if(!Number.isInteger(row.outcome?.decision))throw Error('missing observed decision');
  return {flags,key:JSON.stringify([row.profile,row.app,row.target,row.operationId])};
}
