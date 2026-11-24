// A domain adapter supplies typed edges and complete root groups. A metadata
// reference can remain meaningful after its target's content is reclaimed.
export function retained(graph) {
  const names=new Set(graph.nodes);
  const links=new Map();
  let covered=graph.covered===true;
  for(const edge of graph.edges) {
    if(edge.ownership==='history') continue;
    if(edge.ownership!=='retain') { covered=false;continue; }
    if(!names.has(edge.source)||!names.has(edge.target))covered=false;
    const list=links.get(edge.source)??[];
    list.push(edge.target);
    links.set(edge.source,list);
  }
  const groups={};
  for(const kind of ['saved','undo','plan','active']) {
    if(!Array.isArray(graph.roots[kind]))covered=false;
    const pending=[...(graph.roots[kind]??[])],seen=new Set();
    while(pending.length) {
      const key=pending.pop();
      if(seen.has(key))continue;
      if(!names.has(key))covered=false;
      seen.add(key);
      pending.push(...(links.get(key)??[]));
    }
    groups[kind]=seen;
  }
  return {covered,groups};
}
export function collectionWitness(graph,target) {
  const {covered,groups}=retained(graph);
  return {covered,...Object.fromEntries(Object.entries(groups).map(([key,ids])=>[key,ids.has(target)]))};
}
