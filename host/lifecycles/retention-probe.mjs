import assert from 'node:assert/strict';
import {collectionWitness} from './retention.mjs';
const graph={
  covered:true,
  nodes:['snapshot:B','tree:B','blob:shared','blob:A','plan:A'],
  roots:{saved:['snapshot:B'],undo:[],plan:[],active:[]},
  edges:[
    {source:'snapshot:B',target:'snapshot:A',ownership:'history'},
    {source:'snapshot:B',target:'tree:B',ownership:'retain'},
    {source:'tree:B',target:'blob:shared',ownership:'retain'},
    {source:'plan:A',target:'blob:A',ownership:'retain'},
  ],
};
function emit(operation,subject,observed,decision) {
 console.log(JSON.stringify({v:2,profile:'typed-retention-adapter',app:'retention-candidate',
   feature:'typed-reference-closure',operationId:operation,target:subject,basis:'0',predicate:'collect',
   observed,outcome:{decision}}));
}
const historical=collectionWitness(graph,'blob:A');
assert.deepEqual(historical,{covered:true,saved:false,undo:false,plan:false,active:false});
emit('non-owning-lineage','blob:A',historical,1);
const shared=collectionWitness(graph,'blob:shared');
assert(shared.saved);
emit('live-shared-content','blob:shared',shared,0);
const plan=collectionWitness({...graph,roots:{...graph.roots,plan:['plan:A']}},'blob:A');
assert(plan.plan);
emit('live-plan','blob:A',plan,0);
const unknown=collectionWitness({...graph,edges:[...graph.edges,{source:'snapshot:B',target:'blob:A',ownership:'unknown'}]},'blob:A');
assert(!unknown.covered);
emit('unclassified-reference','blob:A',unknown,0);
const withheld=collectionWitness({...graph,covered:false},'blob:A');
assert(!withheld.covered);
emit('incomplete-roots','blob:A',withheld,0);
