#!/usr/bin/env python3
"""Attribute reviewed manager effects and open consumer obligations to exact private views."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from polytone_contracts import mask, closing

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

# These are authored source interpretations, not an inferred call/effect graph.
# Phase names retain the original implementation's names; parsing can have effects.
REVIEWS = {
    'configs': dict(
        prepare='Inherited directory/image collection. Construction loads polytone_options.json; pack/reload config overlays also have independent entrypoints.',
        parse='Both world-aware and worldless hooks clear/rebuild the option registry from builtins and enabled definitions, applying the retained config-file snapshot.',
        apply='Own apply and reset bodies are empty. UI edits call a separate disk writer and can request a later pack reload.',
        reset='Empty hook does not clear configs, the file snapshot, thread-local active registry, or reload-request flag.',
        live='Value lookup prefers a thread-local active registry, then the main registry; unknown keys warn and return numeric zero. Pack UI and main-menu UI are separate callers.',
        states=['configs','activeLoadConfigs','configFileSnapshot','needsPackReload'],
        effects=[('parseWithLevel','replaces','option-registry'),('parseWithoutLevel','replaces','option-registry'),('saveConfigsToDisk','writes','options-file'),('loadCurrentReloadConfigs','publishes','thread-local-config-view'),('clearCurrentPackConfigs','revokes','thread-local-config-view')],
        helpers=['parseConfigs','saveConfigsToDisk','loadConfigFromDisk','getValue','loadCurrentPackConfigs','loadCurrentReloadConfigs','clearCurrentPackConfigs'],
        questions=['Atomic text replacement is a delegated FilesUtil contract; no durability or multi-writer claim.', 'Follow UI edit/save/reload acknowledgement and cleanup of temporary config views.']),
    'noises': dict(
        prepare='Inherited resource collection.',parse='Decode each noise configuration, build/register it, then regenerate expression noise functions.',
        apply='Own apply hook is empty; registration and expression-function changes occur in parse.',reset='Clear the noise registry; downstream function ownership remains a separate dependency.',
        live='Expression consumers call generated noise functions rather than the empty apply hook.',states=['noises'],
        effects=[('parseWithLevel','publishes','noise-registry'),('parseWithLevel','publishes','expression-noise-functions'),('resetWithLevel','clears','noise-registry')],helpers=[],
        questions=['Qualify partial registration if a later decode/build fails and lifetime of previously generated function references.']),
    'global_expression': dict(
        prepare='Inherited resource collection.',parse='Register enabled expressions and mutable value slots initialized to each declared default.',
        apply='Own apply hook is empty.',reset='Clear expression/value maps and set lastGameTime to Long.MIN_VALUE.',
        live='tick reads level game time, suppresses a repeated time value, and evaluates entries on interval multiples; getValue returns zero for a missing slot.',
        states=['expressions','values','lastGameTime'],effects=[('parseWithLevel','publishes','expression-slots'),('tick','mutates','expression-slots'),('resetWithLevel','clears','expression-slots')],
        helpers=['tick','getValue','slots'],questions=['Game time is not a wall-clock deadline. Qualify level changes, expression context, off-thread readers, and retained Slot references.']),
    'sound_types': dict(
        prepare='Parse sound_events CSV into the manager field before returning default prepared assets.',
        parse='Construct missing sound events, dynamically register them, then decode/register enabled direct sound types. Existing IDs log and skip.',
        apply='Request SoundManager.reload when custom sound events exist; that request is not playback or reload completion.',
        reset='Unregister custom event IDs, then clear sound-event/type registries.',live='Block-set/property consumers reference sound types; actual sound files and playback remain separate.',
        states=['soundEvents','customSoundEvents','customSoundTypes'],effects=[('prepare','replaces','sound-event-csv'),('parseWithLevel','registers','sound-event-registry'),('applyWithLevel','schedules','sound-manager-reload'),('resetWithLevel','unregisters','sound-event-registry')],helpers=[],
        questions=['Qualify asynchronous sound reload and overlap between dynamic IDs, decoded types, sounds.json, and retained playback consumers.']),
    'biome_id_mappers': dict(
        prepare='Inherited resource collection.',parse='Decode and register biome mappers; registration exceptions warn as duplicates, while decoder failures escape.',
        apply='Own apply hook is empty.',reset='Clear mapper registry.',live='Colormap consumers resolve biome identity through the selected mapper.',states=['biomeIdMappers'],
        effects=[('parseWithLevel','publishes','biome-mapper-registry'),('resetWithLevel','clears','biome-mapper-registry')],helpers=[],
        questions=['Do not treat every caught registration error as an independently proved duplicate. Mapper arithmetic and actual biome identity need their own contract.']),
    'colormaps': dict(
        prepare='Inherited JSON/companion-image collection.',parse='Add builtins, retry pending definitions while progress occurs, strict-decode leftovers, then create default colormaps for orphan textures.',
        apply='Own apply hook is empty.',reset='Clear colormap registries and unregister custom platform color resolvers.',live='Color getters and biome/render consumers can retain references independently of the registry.',states=['colormaps','concurrentColormaps'],
        effects=[('parseWithLevel','publishes','colormap-registry'),('resetWithLevel','clears','colormap-registry'),('resetWithLevel','unregisters','platform-color-resolvers')],helpers=[],
        questions=['Qualify reference cycles/ordering, image identity, concurrent getter instances, and active consumer invalidation.']),
    'custom_particles': dict(
        prepare='Inherited resource collection. Early processing separately decodes model-only data and requests model registration.',
        parse='Decode factories, register/override providers, attach sprite sets, add GPU renderers, then resolve lazy emitter dependencies.',
        apply='Own apply hook is empty; factory/provider effects already occur in parse.',reset='Unregister custom types/providers, move active GPU renderers to pending retirement, and restore overwritten vanilla providers.',
        live='CPU providers, emitter callbacks, GPU renderer list, and level-render-tail retirement are different consumers.',states=['customParticleFactories','gpuParticles','overwrittenVanillaProviders'],
        effects=[('earlyProcess','registers','custom-model-requests'),('parseWithLevel','registers','particle-provider-registry'),('parseWithLevel','retains','gpu-particle-renderers'),('resetWithLevel','requests-retirement','gpu-particle-renderers'),('resetWithLevel','restores','vanilla-particle-providers')],helpers=[],
        questions=['retireAll is not close: pending renderers close in a later render call. No GPU-completion or full logout reclamation proof.']),
    'colors': dict(
        prepare='Inherited single-file stack collection and legacy conversion; not the default directory-only path.',
        parse='Parse color sections with direct mutation of vanilla presentation objects, manager fields, and other managers; per-file exceptions log and continue, then sheep colors regenerate.',
        apply='Call LevelRenderer.createStars; derived sheep colors regenerate in parse, not this hook.',reset='Restore captured map/dye/effect/text/egg/border values and explicit defaults; reset is field-specific rather than a generic rollback.',
        live='Map/environment/dye/particle/fishing/lightning/outline/painting/border/effect/egg/sheep/xporb/redstone/text/palette and entity-shadow paths have separate consumers.',
        states=['vanillaMapColors','vanillaDiffuseColors','vanillaEffectColors','vanillaChatFormatting','customSheepColors'],
        effects=[('parseWithLevel','mutates','vanilla-presentation-state'),('parseWithLevel','publishes','cross-manager-color-inputs'),('applyWithLevel','invokes','level-renderer-create-stars'),('resetWithLevel','restores','captured-presentation-state')],
        helpers=['parseColorJson','regenSheepColors'],questions=['Section and per-entry failure can preserve earlier mutations. Complete field/default/restoration coverage and each renderer consumer remain open.']),
    'colored_lights': dict(
        prepare='Optionally detect texture-derived light colors and replace textureLightColors before returning prepared assets.',
        parse='Resolve enabled typed block/entity/item/particle targets and add their light definitions.',apply='Add texture lights, flatten aliases, select configured backend storage, then install available light-source consumers.',
        reset='Clear definitions/aliases, clear each source and storage, then detach source/storage references.',live='Backend storage, moving/block light sources, voxel aliases, and shader patches require separate renderer capability gates.',
        states=['textureLightColors','lightSources','pointLightStorage','blockLights','particleLights'],effects=[('prepare','replaces','texture-light-candidates'),('parseWithLevel','publishes','light-definitions'),('applyWithLevel','publishes','backend-light-sources'),('resetWithLevel','clears','backend-light-storage')],
        helpers=['reset'],questions=['Backend selection and non-null storage do not establish active shader ownership, device compatibility, or retirement of all consumers.']),
    'block_set': dict(
        prepare='Inherited resource collection.',parse='Register vanilla block-set providers and decoded custom providers.',apply='Log the resulting registry size.',reset='Clear block-set registry and reset generated-name counter.',
        live='Block-property consumers use these providers to build/apply sound-related block-set data.',states=['blockSetTypes','counter'],effects=[('parseWithLevel','publishes','block-set-registry'),('resetWithLevel','clears','block-set-registry')],helpers=[],
        questions=['Qualify registry identity, generated names, duplicate policy, and captured references in modified blocks.']),
    'block_modifiers': dict(
        prepare='Merge legacy OptiFine/Colormatic inputs and own images; replace ofProperties before returning copied maps.',
        parse='Convert legacy/inlined palettes, feed fluid/dimension inputs, decode full/partial modifiers, fill images, add enabled/orphan modifiers, and add colored lights.',
        apply='Apply each modifier to blocks, retain returned prior properties, and install tick/sound/particle/tint behavior.',reset='Apply captured prior properties, clear modifier/ticker/tint tables, and restore captured grass/foliage resolvers.',
        live='Block colors/properties, random tick emitters, terrain particles, fluid/dimension conversion and light consumers are distinct edges.',states=['ofProperties','modifiers','vanillaProperties','particleAndSoundEmitters','terrainParticleTintOverrides'],
        effects=[('prepare','replaces','legacy-block-properties'),('parseWithLevel','publishes','cross-manager-modifiers'),('applyWithLevel','mutates','block-presentation-objects'),('applyWithLevel','retains','block-before-images'),('resetWithLevel','restores','block-before-images')],helpers=[],
        questions=['Captured prior values and enabled/partial inputs are not a transaction across managers. Actual tick and renderer hooks remain unqualified.']),
    'fluid_modifiers': dict(
        prepare='Merge own images and converted Colormatic images.',parse='Merge extra legacy inputs, parse always, fill/adopt texture roles, and add enabled or texture-only modifiers.',
        apply='Log installed modifier count; platform wrapper installation occurs through delegated paths.',reset='Clear modifier/extra tables, clear platform-specific wrappers, and restore captured water resolver.',
        live='Platform fluid extension wrappers and fog/color samplers consume the resulting state.',states=['modifiers','extraModifiers','extraImages','vanillaWaterColorResolver'],effects=[('parseWithLevel','publishes','fluid-modifier-tables'),('resetWithLevel','clears','platform-fluid-wrappers'),('resetWithLevel','restores','water-color-resolver')],helpers=[],
        questions=['Follow platform clearSpecial/addModifier into NeoForge wrappers and confirm active readers retain the intended generation.']),
    'custom_models': dict(
        prepare='Inherited resource collection.',parse='Clear model/layer registries, decode models, register definitions, then build layers; layer construction exceptions log and continue.',apply='Own apply hook is empty.',
        reset='Clear model and layer registries.',live='Model-layer registration/baking consumes generated layer definitions later.',states=['models','layers'],effects=[('parseWithLevel','publishes','custom-model-definitions'),('parseWithLevel','publishes','custom-model-layers'),('resetWithLevel','clears','custom-model-registry')],helpers=['load'],
        questions=['A registered model with a failed layer is a distinct partial result. Full renderer/bake consumers remain open.']),
    'item_modifiers': dict(
        prepare='Inherited resource collection; early model-only decoding separately requests models.',parse='Parse always, fill companion textures, and add enabled or image-only modifiers.',
        apply='Apply to items, capture returned prior properties, attach selected modifiers, then clear pending modifier map.',reset='Apply retained prior properties and detach item modifiers; the shown reset does not itself clear vanillaProperties.',
        live='Item colors/tooltips/rarity/armor/models/pose/overlay and emitted lights are different consumers.',states=['modifiers','vanillaProperties'],effects=[('earlyProcess','registers','custom-model-requests'),('applyWithLevel','mutates','item-presentation-objects'),('applyWithLevel','retains','item-before-images'),('resetWithLevel','restores','item-before-images')],helpers=[],
        questions=['Qualify retained prior-property lifetime and repeated reload paths rather than assuming every table empties at reset.']),
    'item_models': dict(
        prepare='Inherited resource collection; early model-only decoding requests non-auto models.',parse='Rebuild override lists from item-modifier contributions plus enabled standalone definitions; produce auto-model descriptors.',
        apply='Populate override model references using registry access.',reset='Clear override and auto-model lists.',live='Actual item override selection and model bake consume these lists outside reload.',states=['itemModels','autoGeneratedModels','itemModifiersModels'],
        effects=[('earlyProcess','registers','custom-model-requests'),('parseWithLevel','publishes','item-override-lists'),('applyWithLevel','resolves','item-override-models'),('resetWithLevel','clears','item-override-lists')],helpers=[],
        questions=['Qualify transfer of itemModifiersModels, early/late enablement, generated model ownership, and coexistence with Modefite/Compat.']),
    'biome_modifiers': dict(
        prepare='Inherited resource collection.',parse='Decode enabled effects and resolve their biome targets into effectsToApply.',apply='On login/dynamic application, mutate resolved biome effects, retain before-images, and register fog-parameter consumers.',
        reset='Restore retained effects in the current level registry when available, then clear effect and fog tables and request dynamic application.',live='Biome registry incarnation and current level are part of restoration/lookup identity.',states=['needsDynamicApplication','effectsToApply','vanillaEffects','fogParametersModifiers'],
        effects=[('parseWithLevel','publishes','biome-effect-plan'),('applyWithLevel','mutates','biome-effects'),('applyWithLevel','retains','biome-before-images'),('resetWithLevel','restores','current-registry-biome-effects')],helpers=[],
        questions=['A resource ID alone does not identify a biome object across registry/level generations. No cross-world restoration proof.']),
    'variant_textures': dict(
        prepare='Inherited resource collection.',parse='Decode enabled variants and build block/texture mappings.',apply='Own apply hook is empty.',reset='Clear block mappings, quad cache, and forced-tint block set.',
        live='Quad transformation uses biome/region context and selected atlas sprites; cached quads can outlive the lookup operation.',states=['blocksWithVariants','variantQuadsCache','forceTintBlocks'],effects=[('parseWithLevel','publishes','variant-texture-mappings'),('resetWithLevel','clears','variant-quad-cache')],helpers=[],
        questions=['Qualify atlas generations, retained quad/sprite identity, world/biome context, and custom renderer paths.']),
    'lightmaps': dict(
        prepare='Merge converted OptiFine/Colormatic and own lightmap images.',parse='Clear current selection, validate image heights, group normal/rain/thunder images, decode/default associated definitions, add enabled maps, and reject leftover JSON without images.',
        apply='Own apply hook is empty.',reset='Clear map registry; current selection is reset by parse rather than this hook.',live='Dimension/weather/lightning and time-dependent light-texture consumers select and sample maps.',states=['lightmaps','lastDimension','currentLightmap'],
        effects=[('parseWithLevel','replaces','current-lightmap-selection'),('parseWithLevel','publishes','lightmap-registry'),('resetWithLevel','clears','lightmap-registry')],helpers=[],
        questions=['Dimension selection, retained currentLightmap, dimensions/image widths and renderer upload are independently pending.']),
    'dimension_modifiers': dict(
        prepare='Inherited resource collection.',parse='Merge decoded and legacy modifiers, fill companion textures, and resolve enabled/orphan targets.',apply='On login/dynamic application, apply inplace effect changes and current-dimension selection.',
        reset='Request dynamic application and clear selected definition/color/cloud/darkening tables; helper paths own any further restoration.',live='Dimension transitions, sky/fog/weather/cloud/lightmap and sunset callbacks consume live/cached state.',states=['needsDynamicApplication','dimensionEffects','alteredVanillaEffects','cloudFunctions','extraMods'],
        effects=[('parseWithLevel','publishes','dimension-modifier-tables'),('applyWithLevel','mutates','dimension-effect-objects'),('resetWithLevel','clears','dimension-selection-tables')],helpers=[],
        questions=['Track alteredVanillaEffects and current-dimension consumers through actual generation changes; reset method name is not restoration evidence.']),
    'particle_modifiers': dict(
        prepare='Inherited resource collection.',parse='Decode full/partial modifiers, attach companion color data and enabled/orphan modifiers, then decode a separately supplied XP-orb replacement.',apply='Log modifier count.',
        reset='Clear particle modifier table; the shown hook does not clear the separate XP-orb fields.',live='Particle creation/update and XP-orb replacement have different state roots.',states=['particleModifiers','xpOrbReplaceJson','xpOrbReplaceParticle'],
        effects=[('parseWithLevel','publishes','particle-modifier-table'),('parseWithLevel','publishes','xp-orb-replacement'),('resetWithLevel','clears','particle-modifier-table')],helpers=[],
        questions=['Qualify lifetimes of existing particles and separate XP-orb state rather than deriving reset of both from one clear.']),
    'slotify': dict(
        prepare='Inherited resource collection.',parse='Decode enabled GUI definitions; resolve class/menu/title targets into modifier and slot indexes. General class names use Class.forName(String), not metadata-only lookup.',
        apply='Log nonempty target indexes.',reset='Clear menu/class/title and slot indexes.',live='Screen/menu/slot consumers match actual class, registry ID or title; class lookup can initialize existing code before index publication.',
        states=['byClass','byMenuId','byTitle','slotsByClass','slotsByMenuId','slotsByTitle'],effects=[('parseWithLevel','initializes','named-java-class'),('parseWithLevel','publishes','gui-target-indexes'),('resetWithLevel','clears','gui-target-indexes')],helpers=[],
        questions=['ClassNotFoundException is handled locally; initialization/linkage failures are different. No actual GUI pack or security exploit is qualified.']),
    'overlay_modifiers': dict(
        prepare='Reload heart-sprite metadata before returning default assets.',parse='Decode enabled modifiers and replace matching texture IDs with a warning.',apply='Own apply hook is empty.',reset='Clear blit modifier table.',
        live='An active render region and incrementing blit index determine application; heart sprites and render-state boundaries are separate.',states=['blitModifiers','active','index'],effects=[('prepare','replaces','heart-sprite-metadata'),('parseWithLevel','publishes','blit-modifier-table'),('resetWithLevel','clears','blit-modifier-table')],helpers=['reloadHearths'],
        questions=['Follow index scope, interception order, heart metadata, render-state restoration, and mixed GUI consumers.']),
    'entity_modifiers': dict(
        prepare='Inherited resource collection.',parse='Register enabled entity modifiers.',apply='Own apply hook is empty.',reset='Clear emittersPerEntity.',live='Entity tick/emitter and colored-light consumers use resolved entity-type mappings.',states=['emittersPerEntity'],effects=[('parseWithLevel','publishes','entity-modifier-table'),('resetWithLevel','clears','entity-modifier-table')],helpers=[],
        questions=['Actual entity identity, emission timing and already-created particles are outside table clearing.']),
    'creative_tabs_modifiers': dict(
        prepare='Parse creative_tabs CSV into extraTabs before returning default assets.',parse='Register CSV/declared new tabs, add enabled modifiers, and enqueue tab sorting when custom tabs exist.',apply='Invalidate cached creative-tab parameters when refresh is needed.',
        reset='Clear preview, unregister custom tabs, enqueue logout sorting, restore captured attributes, mark old modifiers for refresh, then clear pending modifiers.',
        live='Creative inventory rebuild/preview and tab order consume registry entries and refresh state.',states=['extraTabs','customTabs','vanillaTabs','needsRefresh','modifiers'],effects=[('prepare','replaces','extra-tab-csv'),('parseWithLevel','registers','creative-tab-registry'),('parseWithLevel','schedules','creative-tab-sort'),('applyWithLevel','invalidates','creative-tab-cache'),('resetWithLevel','restores','creative-tab-before-images')],helpers=[],
        questions=['Enqueued sort is not completed sorting, and unregister does not prove all open screens dropped a tab reference.']),
    'post_targets': dict(
        prepare='Inherited resource collection.',parse='Decode per-target specs with logged partial results, publish a copied definition map and set dirty.',apply='Own apply hook is empty.',reset='Clear definitions and call destroyAll on existing render targets.',
        live='ensureAllocated creates/resizes targets later; getTarget returns references used by post chains.',states=['targets','definitions','dirty'],effects=[('parseWithLevel','publishes','post-target-definitions'),('resetWithLevel','requests-retirement','render-target-buffers')],helpers=['ensureAllocated','destroyAll','getTarget'],
        questions=['destroyBuffers does not establish GPU completion or retirement of references held by post chains.']),
    'post_chains': dict(
        prepare='Inherited resource collection.',parse='Close previous chains/depth state before decoding enabled effects into the effect list.',apply='Inherited empty hook; live tick/render owns later loading and application.',
        reset='Close active chains, clear definitions/failures, and close depth snapshot.',live='Tick admission, chain loading, depth capture, resize, processing, sampler bindings and rendering are separate operations.',states=['effects','activeChains','failedChains','depthSnapshot','processingEffect'],
        effects=[('parseWithLevel','requests-retirement','prior-post-chains'),('parseWithLevel','publishes','post-chain-effects'),('resetWithLevel','requests-retirement','post-chain-depth-resources')],helpers=['closeEverything','closeActiveChains','tick','renderAfterMainPostEffect'],
        questions=['Failure after old-chain closure is not rollback. Target/sampler references, backend/device generation and actual GPU lifetime remain open.']),
    'voxel_volume': dict(
        prepare='Inherited collector with no constructor directory; callback registration is the principal input.',parse='Clear block/provider flags and invoke registration callbacks admitted by activation policy and colored-light availability.',apply='Close current volume and compute spread state; reset frame demand.',
        reset='Close volume, close palette only on logout, close both compute helpers, and reset requestedThisFrame.',live='World/block changes, renderer demand, async queues, palette and compute/storage resources have distinct custody.',states=['volume','changedBlocks','palette','requestedThisFrame','registerCallbacks'],
        effects=[('parseWithLevel','invokes','registered-voxel-callbacks'),('applyWithLevel','requests-retirement','voxel-volume'),('resetWithLevel','requests-retirement','voxel-palette-on-logout')],helpers=['closeVolume'],
        questions=['Callback invocation executes external code. Track shared palette lifetime, queued changes, compute submissions and device/world generations.']),
    'shader_uniforms': dict(
        prepare='Inherited resource collection.',parse='Decode enabled per-shader expression maps into a new parsed map.',apply='Publish parsed map as uniformsByShader.',reset='Replace both maps with empty maps.',
        live='Expression evaluation and actual shader binding occur later under rendering context.',states=['parsed','uniformsByShader'],effects=[('parseWithLevel','replaces','parsed-uniform-definitions'),('applyWithLevel','publishes','shader-uniform-map'),('resetWithLevel','clears','shader-uniform-map')],helpers=[],
        questions=['A published expression map is not an initialized shader uniform or proof of active backend compatibility.']),
}


def method(text, name):
    clean=mask(text)
    matches=list(re.finditer(r'^   (?:public|protected|private) [^\n]+\b'+re.escape(name)+r'\(',clean,re.M))
    assert len(matches)==1,(name,len(matches))
    match=matches[0];a=clean.index('{',match.end());z=closing(clean,a)
    return dict(line=text[:match.start()].count('\n')+1,bodySha256=hashlib.sha256(text[a:z+1].encode()).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['artifact','views']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    contracts=json.loads((HERE/'polytone-contracts.json').read_text());receipt=json.loads((args.views/'receipt.json').read_text())
    assert sha(args.artifact)==contracts['artifactSha256']==receipt['inputSha256']
    assert sha(args.views/'receipt.json')==contracts['originalReceiptSha256']
    assert set(REVIEWS)=={m['id'].removeprefix('polytone.') for m in contracts['managers']}
    sources={};nodes=[];root=args.views/'source'
    with zipfile.ZipFile(args.artifact) as archive:
        def remember(relative):
            text=(root/relative).read_text();assert sha(root/relative)==receipt['viewsSha256'][relative]
            member=relative.removesuffix('.java')+'.class'
            sources[relative]=dict(viewSha256=sha(root/relative),originalClassEntry=member,originalClassSha256=hashlib.sha256(archive.read(member)).hexdigest())
            return text
        for m in contracts['managers']:
            text=remember(m['source']);key=m['id'].removeprefix('polytone.');review=REVIEWS[key]
            for symbol in review['states']:assert re.search(r'\b'+symbol+r'\b',text),(key,symbol)
            anchors={name:dict(source=m['source'],**method(text,name)) for name in review['helpers']}
            for phase,b in m['effectivePhases'].items():
                body=remember(b['source']);anchor=method(body,phase)
                assert anchor['bodySha256']==b['bodySha256'] and anchor['line']==b['line']
                anchors[phase]=dict(source=b['source'],**anchor)
            edges=[]
            for operation,kind,target in review['effects']:
                assert operation in anchors and kind in ['replaces','writes','publishes','revokes','mutates','clears','registers','schedules','unregisters','retains','requests-retirement','restores','resolves','initializes','invalidates','invokes']
                edges.append(dict(operation=operation,relation=kind,target=target,evidence='source-interpretation;not-native-or-complete-effect-closure'))
            nodes.append(dict(id=m['id'],reloadOrder=m['reloadOrder'],stateSymbols=review['states'],phaseSemantics={k:review[k] for k in ['prepare','parse','apply','reset','live']},
                methodAnchors=anchors,effectEdges=edges,questions=review['questions'],qualification='bounded source review;manager incomplete'))
        # These delegated owners and the hook locate distinct retention/retirement boundaries.
        delegates={
            'content/particle/gpu/GpuParticles.java':['retireAll','render'],
            'content/particle/gpu/GpuParticleRenderer.java':['close'],
            'content/particle/gpu/GpuParticleHeightmap.java':['close'],
            'common/reloader/PolytoneReloadManager.java':['reload','applyWithLevel','resetWithLevel','recordFailure'],
            'mixins/LevelRendererMixin.java':['polytone$captureLevelDepth'],
        }
        delegated=[]
        for relative,names in delegates.items():
            relative='net/mehvahdjukaar/polytone/'+relative;text=remember(relative)
            delegated += [dict(source=relative,method=name,**method(text,name),qualification='selected declared method;not hook reachability or GPU completion') for name in names]
    result=dict(schema=1,provider=contracts['provider'],artifactSha256=contracts['artifactSha256'],
        contractsSha256=sha(HERE/'polytone-contracts.json'),generatorSha256=sha(Path(__file__)),sourceReceiptSha256=sha(args.views/'receipt.json'),
        managers=nodes,delegatedMethods=delegated,sources=sources,
        commonContracts=['common/Lifecycle.lean','common/Lifecycle.bend'],
        limits=['All28 manager records remain incomplete;source interpretation is not translation equivalence or native behavior.',
            'Method anchors/state names/typed effect edges are reviewed locators,not a complete alias,call,effect or retaining-root analysis.',
            'Shared orchestrator callback order does not make prepare/parse pure or the multi-manager operation atomic.',
            'No game/provider/GUI/world/account operation executed;no actual class-target initialization or GPU close occurred in this source review.'])
    output=HERE/'polytone-lifecycles.json'
    if args.check:assert json.loads(output.read_text())==result,'Source review or public lifecycle map differs'
    else:output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(managers=len(nodes),effectEdges=sum(len(n['effectEdges']) for n in nodes),sources=len(sources),delegatedMethods=len(delegated),completeManagers=0)))


if __name__=='__main__':main()
