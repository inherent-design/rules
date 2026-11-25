/* Selected Microsoft VS Code method bodies. Copyright (c) Microsoft Corporation.
 * MIT license: ../../sources/licenses/vscode-MIT.txt.
 * Study scaffolding and the explicitly labeled candidate are new. */
const files = {FileSystemProviderCapabilities:{"FileReadWrite": 2, "PathCaseSensitive": 1024, "Readonly": 2048}};
const URI={from:x=>x};
function run(candidate){
const store={_providerInfo:new Map(),
$acceptProviderInfos(uri,capabilities){
		if (capabilities === null) {
			this._providerInfo.delete(uri.scheme);
		} else {
			this._providerInfo.set(uri.scheme, capabilities);
		}
	},
getCapabilities(scheme){
		return this._providerInfo.get(scheme);
	}};
const fileSystemInfo=store,infoProxy=store;
const writable=function(scheme){
				const capabilities = fileSystemInfo.getCapabilities(scheme);
				if (typeof capabilities === 'number') {
					return !(capabilities & files.FileSystemProviderCapabilities.Readonly);
				}
				return undefined;
			};
const current=e => infoProxy.$acceptProviderInfos(URI.from({ scheme: e.scheme, path: '/dummy' }), e.provider?.capabilities ?? null);
const proposed=e => infoProxy.$acceptProviderInfos(URI.from({ scheme: e.scheme, path: '/dummy' }), e.added ? (e.provider?.capabilities ?? null) : null);
const callback=candidate?proposed:current;
const trace=[];
for(const event of [
 {id:'add-writable',added:true,scheme:'fixture',provider:{capabilities:1026}},
 {id:'remove-writable',added:false,scheme:'fixture',provider:{capabilities:1026}},
 {id:'add-readonly',added:true,scheme:'fixture',provider:{capabilities:3074}},
 {id:'other-scheme',added:true,scheme:'other',provider:{capabilities:1026}},
 {id:'remove-readonly',added:false,scheme:'fixture',provider:{capabilities:3074}},
 {id:'absent-provider-removal',added:false,scheme:'fixture'}
]){callback(event);trace.push({event,known:store.getCapabilities(event.scheme)!==undefined,
 writable:writable(event.scheme)??null,fixtureWritable:writable('fixture')??null});}
return trace;
}
console.log(JSON.stringify({schema:1,current:run(false),proposed:run(true)},null,2));
