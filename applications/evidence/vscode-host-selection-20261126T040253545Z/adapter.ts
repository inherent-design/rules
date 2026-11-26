const ExtensionHostKind={LocalProcess:1,LocalWebWorker:2,Remote:3};
const ExtensionRunningPreference={None:0,Local:1,Remote:2};
const ExtensionIdentifier={toKey:(id)=>id.value.toLowerCase()};
class NativeFragment {
	public static pickExtensionHostKind(extensionKinds: ExtensionKind[], isInstalledLocally: boolean, isInstalledRemotely: boolean, preference: ExtensionRunningPreference, hasRemoteExtHost: boolean, hasWebWorkerExtHost: boolean): ExtensionHostKind | null {
		const result: ExtensionHostKind[] = [];
		for (const extensionKind of extensionKinds) {
			if (extensionKind === 'ui' && isInstalledLocally) {
				// ui extensions run locally if possible
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Local) {
					return ExtensionHostKind.LocalProcess;
				} else {
					result.push(ExtensionHostKind.LocalProcess);
				}
			}
			if (extensionKind === 'workspace' && isInstalledRemotely) {
				// workspace extensions run remotely if possible
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Remote) {
					return ExtensionHostKind.Remote;
				} else {
					result.push(ExtensionHostKind.Remote);
				}
			}
			if (extensionKind === 'workspace' && !hasRemoteExtHost) {
				// workspace extensions also run locally if there is no remote
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Local) {
					return ExtensionHostKind.LocalProcess;
				} else {
					result.push(ExtensionHostKind.LocalProcess);
				}
			}
			if (extensionKind === 'web' && isInstalledLocally && hasWebWorkerExtHost) {
				// web worker extensions run in the local web worker if possible
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Local) {
					return ExtensionHostKind.LocalWebWorker;
				} else {
					result.push(ExtensionHostKind.LocalWebWorker);
				}
			}
		}
		return (result.length > 0 ? result[0] : null);
	}

}
class BrowserFragment {
	public static pickRunningLocation(extensionKinds: ExtensionKind[], isInstalledLocally: boolean, isInstalledRemotely: boolean, preference: ExtensionRunningPreference): ExtensionHostKind | null {
		const result: ExtensionHostKind[] = [];
		let canRunRemotely = false;
		for (const extensionKind of extensionKinds) {
			if (extensionKind === 'ui' && isInstalledRemotely) {
				// ui extensions run remotely if possible (but only as a last resort)
				if (preference === ExtensionRunningPreference.Remote) {
					return ExtensionHostKind.Remote;
				} else {
					canRunRemotely = true;
				}
			}
			if (extensionKind === 'workspace' && isInstalledRemotely) {
				// workspace extensions run remotely if possible
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Remote) {
					return ExtensionHostKind.Remote;
				} else {
					result.push(ExtensionHostKind.Remote);
				}
			}
			if (extensionKind === 'web' && (isInstalledLocally || isInstalledRemotely)) {
				// web worker extensions run in the local web worker if possible
				if (preference === ExtensionRunningPreference.None || preference === ExtensionRunningPreference.Local) {
					return ExtensionHostKind.LocalWebWorker;
				} else {
					result.push(ExtensionHostKind.LocalWebWorker);
				}
			}
		}
		if (canRunRemotely) {
			result.push(ExtensionHostKind.Remote);
		}
		return (result.length > 0 ? result[0] : null);
	}

}
function determineExtensionHostKinds(
	_localExtensions: IExtensionDescription[],
	_remoteExtensions: IExtensionDescription[],
	getExtensionKind: (extensionDescription: IExtensionDescription) => ExtensionKind[],
	pickExtensionHostKind: (extensionId: ExtensionIdentifier, extensionKinds: ExtensionKind[], isInstalledLocally: boolean, isInstalledRemotely: boolean, preference: ExtensionRunningPreference) => ExtensionHostKind | null
): Map<string, ExtensionHostKind | null> {
	const localExtensions = toExtensionWithKind(_localExtensions, getExtensionKind);
	const remoteExtensions = toExtensionWithKind(_remoteExtensions, getExtensionKind);

	const allExtensions = new Map<string, ExtensionInfo>();
	const collectExtension = (ext: ExtensionWithKind) => {
		if (allExtensions.has(ext.key)) {
			return;
		}
		const local = localExtensions.get(ext.key) || null;
		const remote = remoteExtensions.get(ext.key) || null;
		const info = new ExtensionInfo(local, remote);
		allExtensions.set(info.key, info);
	};
	localExtensions.forEach((ext) => collectExtension(ext));
	remoteExtensions.forEach((ext) => collectExtension(ext));

	const extensionHostKinds = new Map<string, ExtensionHostKind | null>();
	allExtensions.forEach((ext) => {
		const isInstalledLocally = Boolean(ext.local);
		const isInstalledRemotely = Boolean(ext.remote);

		const isLocallyUnderDevelopment = Boolean(ext.local && ext.local.isUnderDevelopment);
		const isRemotelyUnderDevelopment = Boolean(ext.remote && ext.remote.isUnderDevelopment);

		let preference = ExtensionRunningPreference.None;
		if (isLocallyUnderDevelopment && !isRemotelyUnderDevelopment) {
			preference = ExtensionRunningPreference.Local;
		} else if (isRemotelyUnderDevelopment && !isLocallyUnderDevelopment) {
			preference = ExtensionRunningPreference.Remote;
		}

		extensionHostKinds.set(ext.key, pickExtensionHostKind(ext.identifier, ext.kind, isInstalledLocally, isInstalledRemotely, preference));
	});

	return extensionHostKinds;
}

function toExtensionWithKind(
	extensions: IExtensionDescription[],
	getExtensionKind: (extensionDescription: IExtensionDescription) => ExtensionKind[]
): Map<string, ExtensionWithKind> {
	const result = new Map<string, ExtensionWithKind>();
	extensions.forEach((desc) => {
		const ext = new ExtensionWithKind(desc, getExtensionKind(desc));
		result.set(ext.key, ext);
	});
	return result;
}

class ExtensionWithKind {

	constructor(desc,kind) { this.desc=desc;this.kind=kind; }

	public get key(): string {
		return ExtensionIdentifier.toKey(this.desc.identifier);
	}

	public get isUnderDevelopment(): boolean {
		return this.desc.isUnderDevelopment;
	}
}

class ExtensionInfo {

	constructor(local,remote) { this.local=local;this.remote=remote; }

	public get key(): string {
		if (this.local) {
			return this.local.key;
		}
		return this.remote!.key;
	}

	public get identifier(): ExtensionIdentifier {
		if (this.local) {
			return this.local.desc.identifier;
		}
		return this.remote!.desc.identifier;
	}

	public get kind(): ExtensionKind[] {
		// in case of disagreements between extension kinds, it is always
		// better to pick the local extension because it has a much higher
		// chance of being up-to-date
		if (this.local) {
			return this.local.kind;
		}
		return this.remote!.kind;
	}
}

globalThis.fixture={NativeFragment,BrowserFragment,determineExtensionHostKinds};
