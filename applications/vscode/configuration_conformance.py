#!/usr/bin/env python3
"""Replay captured configuration APIs and raw settings; never launch VS Code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = '8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
FIELDS = ['defaultValue', 'globalValue', 'workspaceValue', 'workspaceFolderValue',
          'defaultLanguageValue', 'globalLanguageValue', 'workspaceLanguageValue', 'workspaceFolderLanguageValue']
PHASES = ['initial', 'set-user-language', 'set-workspace-language', 'set-folder-language',
          'set-masked-user-value', 'remove-folder-language', 'remove-workspace-language',
          'remove-user-language', 'remove-folder-value', 'remove-nullable', 'replace-workspace-object']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate configuration source key is outside this fixture.'
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=unique_object)


def carrier(source, key):
    return dict(present=True, value=source[key]) if key in source else dict(present=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    meta, exit_record, observed = [loads((run / name).read_text()) for name in ['meta.json', 'exit.json', 'observed.json']]
    assert meta['revision'] == exit_record['revision'] == REVISION
    assert exit_record['exitCode'] == 0 and observed['status'] == 'complete' and observed['error'] is None
    assert sha(run/'extension.cjs') == meta['extensionSha256'] == exit_record['extensionSha256']
    assert sha(run/'probe.py') == meta['producerSha256'] == exit_record['launchProducerSha256']
    assert sha(run/'observed.json') == exit_record['observedSha256']
    assert observed['identity']['version'] == '1.147.0' and observed['identity']['appHost'] == 'desktop'
    assert observed['identity']['remoteName'] == {'present': False} and observed['identity']['trusted']
    retention = loads((run/'retention.json').read_text())
    assert retention['movedAfterConfirmedMainExit'] and retention['noMatchingProcessAtMove']
    assert retention['finalSourceBytesMatchLastSnapshot'] and retention['originalWork'] == meta['work']
    process = loads((run/'process.json').read_text())
    assert '--use-inmemory-secretstorage' in process['argv'] and '--user-data-dir' in process['argv']
    rows = observed['rows']; assert [r['operation'] for r in rows] == PHASES
    assert loads((run/'final-settings.json').read_text()) == rows[-1]['sourceFiles']
    package = loads((run/'extension-package.json').read_text())
    properties = package['contributes']['configuration']['properties']
    assert all(p['scope'] == 'language-overridable' for p in properties.values())
    defaults = {key: value['default'] for key, value in properties.items()}
    language_defaults = package['contributes']['configurationDefaults']
    source_ledger = ROOT/'applications/sources/vscode-configuration-selections.json'
    selection = loads(source_ledger.read_text()); assert selection['revision'] == REVISION
    for source in selection['sources']:
        assert sha(ROOT/source['cache']) == source['sha256'], source['path']
    files = [HERE/p for p in ['Configuration.lean','ConfigurationCase.lean','Configuration.bend',
                             'configuration_probe.py','configuration-extension.cjs']]
    files += [Path(__file__), source_ledger]
    files += [run/p for p in ['meta.json','exit.json','observed.json','extension.cjs','probe.py',
                              'extension-package.json','initial-settings.json','final-settings.json',
                              'process.json','retention.json','app.stdout','app.stderr']]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    # Actual recorded producer is frozen. The current exit-propagation guard is
    # a later source-only change; do not attribute it to this native execution.
    assert sha(HERE/'configuration-extension.cjs') == meta['extensionSha256']
    assert sha(HERE/'configuration_probe.py') != meta['producerSha256']
    expected_sources = loads((run/'initial-settings.json').read_text())
    assert expected_sources['user']['security.workspace.trust.enabled'] is False
    raw_cases, inspection_cases, native_expected = [], [], []
    scalar_inputs, scalar_expected = [], []
    field_disagreements = []
    strings = sorted({'base-default','user','workspace','folder-a','folder-b','language-default',
                      'user-js','workspace-js','folder-a-js','user-new','base-nullable'})
    tags = {s: index+1 for index,s in enumerate(strings)}
    def tag(value):
        if not value['present']: return 'None{}'
        data = value['value']; assert data is None or isinstance(data, str)
        return 'Some{' + str(0 if data is None else tags[data]) + 'n}'
    def scalar_label(value):
        return 'absent' if not value['present'] else str(0 if value['value'] is None else tags[value['value']])
    for index, row in enumerate(rows):
        user = expected_sources['user']; workspace = expected_sources['workspace']['settings']; folder = expected_sources['folderA']
        if index == 1: user['[javascript]'] = {'fixture.scope.value':'user-js'}
        elif index == 2: workspace['[javascript]'] = {'fixture.scope.value':'workspace-js'}
        elif index == 3: folder['[javascript]'] = {'fixture.scope.value':'folder-a-js'}
        elif index == 4: user['fixture.scope.value'] = 'user-new'
        elif index in [5,6,7]:
            target = {5:folder,6:workspace,7:user}[index]
            del target['[javascript]']['fixture.scope.value']
            # Removal deletes this assignment, not its empty language container.
        elif index == 8: del folder['fixture.scope.value']
        elif index == 9:
            del user['fixture.scope.nullable']
            # Independently observed app setting normalization in this phase.
            # No causal claim that the nullable update triggered it.
            user['extensions.autoUpdate'] = 'off'
        elif index == 10: workspace['fixture.scope.object'] = {'workspaceOnly':'w-new','nested':{'w':'w-new','x':'workspace-new'}}
        actual_sources = {key: loads(text) for key,text in row['sourceFiles'].items()}
        assert actual_sources == expected_sources, ('Unexpected source edit', row['operation'])
        contexts = row['contexts']; assert [(c['folder'],c['languageId'])for c in contexts] == [
            ('a','plaintext'),('a','javascript'),('b','plaintext'),('b','javascript')]
        for context in contexts:
            sources = [defaults, actual_sources['user'], actual_sources['workspace']['settings'],
                       actual_sources['folderA' if context['folder']=='a' else 'folderB']]
            language = '[' + context['languageId'] + ']'
            scopes = sources + [language_defaults.get(language,{})] + [s.get(language,{}) for s in sources[1:]]
            for key,setting in context['settings'].items():
                full_key = 'fixture.scope.'+key
                identifier = '/'.join([row['operation'],context['folder'],context['languageId'],key])
                slots = [carrier(s,full_key) for s in scopes]
                inspection = setting['inspect']; assert inspection['present'] and inspection['key']==full_key
                inspected = [inspection['fields'][field] for field in FIELDS]
                for field,source_value,public_value in zip(FIELDS,slots,inspected,strict=True):
                    if source_value != public_value:
                        assert field=='globalValue' and key=='nullable' and index<9
                        assert source_value=={'present':True,'value':None} and public_value=={'present':False}
                        field_disagreements.append(dict(id=identifier,field=field,source=source_value,inspected=public_value))
                raw_cases.append(dict(id=identifier,slots=slots))
                inspection_cases.append(dict(id=identifier+'/inspection',slots=inspected))
                native_expected.append(dict(id=identifier,effective=setting['effective']))
                if key != 'object':
                    scalar_inputs.append((slots,inspected))
                    scalar_expected.append(setting['effective'])
    assert len(raw_cases)==132 and len(field_disagreements)==36 and len(scalar_inputs)==88
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'configuration.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return subprocess.run([lean,'--run','applications/vscode/ConfigurationCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=replay(dict(schema=1,cases=raw_cases+inspection_cases)); assert result.returncode==0,result.stdout+result.stderr
    lean_results=json.loads(result.stdout);assert lean_results[:132]==native_expected
    inspection_results=lean_results[132:]
    mismatches=[dict(id=n['id'],native=n['effective'],reconstructed=i['effective'])for n,i in zip(native_expected,inspection_results,strict=True)if n['effective']!=i['effective']]
    assert len(mismatches)==36 and all(r['native']=={'present':True,'value':None} and r['reconstructed']=={'present':True,'value':'base-nullable'}for r in mismatches)
    # Bend uses scalar tags only, independently of recursive object merging.
    calls=[];expected=[]
    for (slots,inspected),native in zip(scalar_inputs,scalar_expected,strict=True):
        for values in [slots,inspected]:
            calls.append('C.label(C.resolve(['+','.join(map(tag,values))+'])) ++ "\\n"')
        expected.append(scalar_label(native))
    calls+=['C.label(C.current_global(Some{0n},None{})) ++ "\\n"', 'C.label(C.prefer(Some{0n},None{})) ++ "\\n"']
    bend_case=generated/'ConfigurationCase.bend'
    bend_case.write_text('import Base\nimport ../Configuration.bend as C\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(bend_case)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    outputs=result.stdout.splitlines();assert outputs[-2:]==['absent','0'] and len(outputs)==178
    assert outputs[:-2:2]==expected
    assert sum(a!=b for a,b in zip(outputs[:-2:2],outputs[1:-2:2],strict=True))==36
    for position,(slots,inspected) in enumerate(scalar_inputs):
        expected_inspection=next(r['effective'] for r in inspection_results if r['id']==[c for c in raw_cases if not c['id'].endswith('/object')][position]['id']+'/inspection')
        assert outputs[2*position+1]==scalar_label(expected_inspection)
    # A successful lower-scope write need not alter any selected effective view.
    before,after=rows[3],rows[4]
    assert [c['settings'] for c in before['contexts']] != [c['settings'] for c in after['contexts']]
    assert [[s['effective']for s in c['settings'].values()]for c in before['contexts']] == [[s['effective']for s in c['settings'].values()]for c in after['contexts']]
    masked_events=observed['events'][before['eventsSeen']:after['eventsSeen']]
    assert masked_events and all(e['section'] and all(not c['affects']for c in e['contexts'])for e in masked_events)
    invalids=[('schema',dict(schema=2,cases=[]),'Unsupported configuration schema'),
              ('scope-count',dict(schema=1,cases=[dict(id='bad',slots=[])]),'requires eight ordered slots'),
              ('presence',dict(schema=1,cases=[dict(id='bad',slots=[dict(present=False,value=None)]+[dict(present=False)]*7)]),'Absent carrier must not contain a value'),
              ('missing-value',dict(schema=1,cases=[dict(id='bad',slots=[dict(present=True)]+[dict(present=False)]*7)]),'Present carrier needs exactly')]
    deep='x'
    for _ in range(18): deep={'nested':deep}
    invalids.append(('depth',dict(schema=1,cases=[dict(id='deep',slots=[dict(present=True,value=deep)]+[dict(present=False)]*7)]),'exceeds the captured depth bound'))
    refused=[]
    for label,value,diagnostic in invalids:
        result=replay(value); assert result.returncode==2 and diagnostic in result.stderr,(label,result.stdout,result.stderr)
        refused.append(label)
    path.write_text(json.dumps(dict(schema=1,cases=raw_cases+inspection_cases),indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in basis.items()), 'Inputs changed during replay.'
    report=dict(schema=1,basisSha256=basis,nativePhases=11,nativeContextSettings=132,
        rawSourceLeanMatches=132,documentedInspectionReconstructionMatches=96,
        documentedInspectionReconstructionDisagreements=mismatches,documentedInspectionFieldDisagreements=field_disagreements,
        bendScalarSourcesMatch=88,bendScalarInspectionReconstructions=88,bendProjectionControls=2,
        maskedChangeEvents=masked_events,refusedResearchInputs=refused,
        additionalSourceObservation=dict(phase='remove-nullable',key='extensions.autoUpdate',before=False,after='off',
            cause='Not independently established; retained alongside selected-key edits,not attributed to the nullable update.'),
        rejectedInterpretations=['Every lower-scope edit changes the effective value.','Generic folder settings always beat language defaults.',
            'Objects and arrays both replace wholesale.','Null and an absent assignment mean the same thing.',
            'The eight documented inspection fields always reconstruct the effective result.','A configuration notification means a scoped effective change.'],
        limits=['One local trusted multi-root desktop API fixture with trust disabled,three registered keys,two folders,two languages and serial updates.',
            'No remote,managed/memory overrides,combined-language selectors,profiles sync,trust enforcement,Settings UI,concurrent writers,crash recovery or general durability qualification.',
            'Null discrepancy is confined to documented globalValue; raw source and effective getter preserve null. Other implementation-specific inspection fields were not captured.',
            'Ordinary HOME with isolated user-data/extensions and in-memory secret storage. Log shows existing ~/.vscode-shared/sharedStorage opened; shared-storage effects were not measured.',
            'Frozen recorded producer is native evidence; current nonzero-exit propagation guard has source/syntax checks only.'])
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['basisSha256','documentedInspectionReconstructionDisagreements','documentedInspectionFieldDisagreements']},indent=2))


if __name__=='__main__': main()
