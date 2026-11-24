
const WORKSPACE_TRUST_ENABLED='security.workspace.trust.enabled';
// Lowercase generated IDs only; real identifier normalization is not modeled.
const getGalleryExtensionId=(publisher,name)=>publisher+'.'+name;
class SupportFragment {
  constructor(enabled,configured,product){
    this.workspaceTrustEnablementService={isWorkspaceTrustEnabled:()=>enabled};
    this._configuredExtensionWorkspaceTrustRequestMap=new Map(configured?[["fixture.extension",configured]]:[]);
    this._productExtensionWorkspaceTrustRequestMap=new Map(product?[["fixture.extension",product]]:[]);
  }
	getExtensionUntrustedWorkspaceSupportType(manifest: IExtensionManifest): ExtensionUntrustedWorkspaceSupportType {
		// Workspace trust feature is disabled, or extension has no entry point
		if (!this.workspaceTrustEnablementService.isWorkspaceTrustEnabled() || (!manifest.main && !manifest.browser)) {
			return true;
		}

		// Get extension workspace trust requirements from settings.json
		const configuredWorkspaceTrustRequest = this.getConfiguredExtensionWorkspaceTrustRequest(manifest);

		// Get extension workspace trust requirements from product.json
		const productWorkspaceTrustRequest = this.getProductExtensionWorkspaceTrustRequest(manifest);

		// Use settings.json override value if it exists
		if (configuredWorkspaceTrustRequest !== undefined) {
			return configuredWorkspaceTrustRequest;
		}

		// Use product.json override value if it exists
		if (productWorkspaceTrustRequest?.override !== undefined) {
			return productWorkspaceTrustRequest.override;
		}

		// Use extension manifest value if it exists
		if (manifest.capabilities?.untrustedWorkspaces?.supported !== undefined) {
			return manifest.capabilities.untrustedWorkspaces.supported;
		}

		// Use product.json default value if it exists
		if (productWorkspaceTrustRequest?.default !== undefined) {
			return productWorkspaceTrustRequest.default;
		}

		return false;
	}

	private getConfiguredExtensionWorkspaceTrustRequest(manifest: IExtensionManifest): ExtensionUntrustedWorkspaceSupportType | undefined {
		const extensionId = getGalleryExtensionId(manifest.publisher, manifest.name);
		const extensionWorkspaceTrustRequest = this._configuredExtensionWorkspaceTrustRequestMap.get(extensionId);

		if (extensionWorkspaceTrustRequest && (extensionWorkspaceTrustRequest.version === undefined || extensionWorkspaceTrustRequest.version === manifest.version)) {
			return extensionWorkspaceTrustRequest.supported;
		}

		return undefined;
	}

	private getProductExtensionWorkspaceTrustRequest(manifest: IExtensionManifest): ExtensionUntrustedWorkspaceSupport | undefined {
		const extensionId = getGalleryExtensionId(manifest.publisher, manifest.name);
		return this._productExtensionWorkspaceTrustRequestMap.get(extensionId);
	}

}
class EnablementFragment {
  constructor(support,inside){this.extensionManifestPropertiesService=support;this.contextService={isInsideWorkspace:()=>inside};}
	private _isDisabledByWorkspaceTrust(extension: IExtension, workspaceType: WorkspaceType): boolean {
		if (workspaceType.trusted) {
			return false;
		}

		if (this.contextService.isInsideWorkspace(extension.location)) {
			return true;
		}

		return this.extensionManifestPropertiesService.getExtensionUntrustedWorkspaceSupportType(extension.manifest) === false;
	}

}
class TrustEnabledFragment {
  constructor(disable,value){this.environmentService={disableWorkspaceTrust:disable};this.configurationService={getValue:()=>value};}
	isWorkspaceTrustEnabled(): boolean {
		if (this.environmentService.disableWorkspaceTrust) {
			return false;
		}

		const enabled = this.configurationService.getValue(WORKSPACE_TRUST_ENABLED);
		return typeof enabled === 'boolean' ? enabled : true;
	}
}
globalThis.fragments={SupportFragment,EnablementFragment,TrustEnabledFragment};
