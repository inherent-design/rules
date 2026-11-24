#!/usr/bin/env python3
"""Replay retained trust-related source predicates; no VS Code launch."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);run=parser.parse_args().run.resolve()
    receipt=json.loads((run/'receipt.json').read_text());selection=json.loads((run/'selection.json').read_text())
    assert receipt['schema']==1 and receipt['kind']=='unmodified-source-methods-with-adapters'
    assert receipt['revision']==selection['revision']=='8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
    assert sha(run/'probe.mjs')==receipt['producerSha256'] and sha(run/'selection.json')==receipt['selectionSha256']
    assert sha(run/'observed.json.gz')==receipt['compressedSha256']
    raw=gzip.decompress((run/'observed.json.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==receipt['observedSha256']
    observed=json.loads(raw);rows=observed['supportRows'];assert len(rows)==receipt['supportCases']==3072
    assert receipt['blockedPredicates']==12288 and len(observed['enabledRows'])==receipt['enabledCases']==8
    fragment=run/'fragment.ts';assert sha(fragment)==receipt['typescriptSha256']
    assert sha(run/'fragment.js')==receipt['javascriptSha256']
    for source in selection['sources']:assert sha(ROOT/source['cache'])==source['sha256']
    # Independently check exact method boundaries against the retained fragment.
    def between(text,start,end):
        a=text.index(start);return text[a:text.index(end,a+len(start))]
    sources={r['id']:(ROOT/r['cache']).read_text()for r in selection['sources']}
    bodies=[between(sources['manifest'],'\tgetExtensionUntrustedWorkspaceSupportType(manifest: IExtensionManifest): ExtensionUntrustedWorkspaceSupportType {','\n\tgetExtensionVirtualWorkspaceSupportType'),
        between(sources['manifest'],'\tprivate getConfiguredExtensionWorkspaceTrustRequest(manifest:','\n\tprivate toArray'),
        between(sources['enablement'],'\tprivate _isDisabledByWorkspaceTrust(extension:','\n\tprivate _isDisabledByExtensionDependency'),
        between(sources['trust'],'\tisWorkspaceTrustEnabled(): boolean {','\n}\n\nexport class WorkspaceTrustManagementService')]
    assert all(fragment.read_text().count(body)==1 for body in bodies)
    files=[HERE/p for p in ['Trust.lean','TrustCase.lean','Trust.bend','trust_probe.mjs','trust_conformance.py']]
    files += [run/p for p in ['receipt.json','selection.json','probe.mjs','observed.json.gz','fragment.ts','fragment.js']]
    basis={str(p.relative_to(ROOT)):sha(p)for p in files}
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'trust.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/vscode/TrustCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    inputs=[{k:v for k,v in r.items()if k not in ['observed','blocked']}for r in rows]
    assert len({tuple(r.values())for r in inputs})==3072
    result=replay(dict(schema=1,cases=inputs));assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==[dict(selected=r['observed'],blocked=r['blocked'])for r in rows]
    # The smaller Bend subset spans each configured/version gate and every
    # product-override/manifest/default combination with no user assignment.
    selected=[r for r in rows if (r['override']==3 and r['declared']==1 and r['fallback']==2)or
        (r['trustEnabled'] and r['hasEntry'] and r['configured']==0 and r['version']==0)]
    assert len(selected)==111
    names=['Missing','Deny','Allow','Limited'];bit=lambda b:'True{}'if b else'False{}'
    calls=[];expected=[]
    for r in selected:
        expression='T.support('+','.join([bit(r['trustEnabled']),bit(r['hasEntry']),bit(r['version']!=2)]+['T.'+names[r[k]]+'{}'for k in ['configured','override','declared','fallback']])+')'
        calls.append('T.label('+expression+') ++ "\\n"');expected.append(str(r['observed']))
        for index,(trusted,inside)in enumerate([(False,False),(False,True),(True,False),(True,True)]):
            calls.append('Bool.show(T.blocked('+bit(trusted)+','+bit(inside)+','+expression+')) ++ "\\n"');expected.append(str(r['blocked'][index]))
    runner=generated/'TrustCase.bend';runner.write_text('import Base\nimport ../Trust.bend as T\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr;assert result.stdout.splitlines()==expected
    enabled=[]
    for r in observed['enabledRows']:
        value=r['setting'];setting='some true'if value is True else'some false'if value is False else'none'
        enabled.append('trustEnabled '+('true'if r['disabled']else'false')+' ('+setting+')')
    script=generated/'TrustEnabledCase.lean';script.write_text('import Lean\nimport applications.vscode.Trust\nopen Lean ApplicationStudy.VscodeTrust\ndef main : IO Unit := IO.println (toJson (['+', '.join(enabled)+'] : List Bool)).compress\n')
    result=subprocess.run([lean,'--run',str(script)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr;assert json.loads(result.stdout)==[r['observed']for r in observed['enabledRows']]
    invalids=[('schema',dict(schema=2,cases=[]),'Unsupported trust schema'),
        ('support',dict(schema=1,cases=[dict(inputs[0],configured=4)]),'Unknown support code'),
        ('version',dict(schema=1,cases=[dict(inputs[0],version=3)]),'Unknown version-admission code')]
    for name,value,message in invalids:
        result=replay(value);assert result.returncode==2 and message in result.stderr,name
    path.write_text(json.dumps(dict(schema=1,cases=inputs))+'\n')
    assert all(sha(ROOT/p)==h for p,h in basis.items()),'Inputs changed during replay.'
    assert any(r['observed']==2 and r['blocked']==[False,True,False,False]for r in rows)
    assert any(r['observed']==3 and r['blocked']==[False,True,False,False]for r in rows)
    assert any(r['configured']==2 and r['version']==2 and r['observed']==1 for r in rows)
    report=dict(schema=1,basisSha256=basis,leanSourceSupportCases=3072,leanSourceDisablePredicates=12288,leanEnablementFlagCases=8,
        bendSelectedSupportCases=111,bendDisablePredicates=444,refusedResearchInputs=[r[0]for r in invalids],
        rejectedInterpretations=['Support declaration equals full extension enablement.','Limited support means false.',
            'An explicit false override is absent.','Any old version override applies to the new version.',
            'Passing the trust predicate proves extension execution is safe or admitted by every gate.'],
        limits=['Unmodified selected bodies with admitted map/config/resource membership adapters;no native VS Code UI/extension host or installed app conformance.',
            'Lowercase generated identity only;no actual identifier normalization,settings parser/map constructor reload or URI containment qualification.',
            'Full enablement includes user/environment/validity/virtual workspace/dependency/host kind and other gates outside this projection.',
            'Independent predicate parameters include combinations not claimed reachable in the full application;trust-disabled plus untrusted is not a production lifecycle trace.',
            'No trust prompt,grant persistence/revocation,task execution,running-extension retirement or sandbox boundary qualification.',
            'Feature enabled and workspace trusted are separate values;the earlier configuration native run disabled trust and proves none of these production gates.'])
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
