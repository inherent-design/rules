#!/usr/bin/env python3
"""Bounded native path observations in an owned scratch tree;no application launch."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import unicodedata

SOURCE=Path(__file__).read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()


def identity(path):
    try:
        s=path.stat()
    except OSError as e:
        return dict(available=False,error=type(e).__name__,errno=e.errno,winerror=getattr(e,'winerror',None))
    if not s.st_ino:
        return dict(available=False,error='IdentityUnavailable',errno=None,winerror=None)
    return dict(available=True,device=str(s.st_dev),inode=str(s.st_ino))


def chain(path,root):
    """A quiescent fixture walk,not an attacker-safe ancestry algorithm."""
    try:p=path.resolve(strict=True)
    except OSError as e:return dict(complete=False,entries=[],error=type(e).__name__)
    root_id=identity(root);entries=[]
    for _ in range(64):
        item=identity(p)
        if not item['available']:return dict(complete=False,entries=entries,error=item['error'])
        entries.append(item)
        if item==root_id:return dict(complete=True,entries=entries)
        if p.parent==p:break
        p=p.parent
    return dict(complete=False,entries=entries,error='OutsideOwnedRootOrDepthLimit')


def observe(root,source,target,name):
    s,t=identity(source),identity(target)
    try:same=os.path.samefile(source,target);same_error=None
    except OSError as e:same=None;same_error=type(e).__name__
    if s['available']and t['available']:assert same==(s==t)
    return dict(case=name,kind='pair',request=dict(operation='protected-tree-preflight',
        source=str(source.relative_to(root)),target=str(target.relative_to(root))),
        observed=dict(source=s,target=t,samefile=same,samefileError=same_error,
            sourceChain=chain(source,root),targetChain=chain(target,root),
            exactSpellingEqual=str(source)==str(target),
            nfcSpellingEqual=unicodedata.normalize('NFC',str(source))==unicodedata.normalize('NFC',str(target))))


def main():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='rules-path-identity-')as folder:
        root=Path(folder);source=root/'protected';source.mkdir()
        payload=b'owned source sentinel\n';(source/'payload').write_bytes(payload)
        slot=root/'slot';slot.mkdir();(slot/'payload').write_bytes(b'owned target sentinel\n')
        rows.append(observe(root,source,source,'exact-object'))
        upper=root/'PROTECTED';rows.append(observe(root,source,upper,'case-alias-first-lookup'))
        if not identity(upper)['available']:
            # Only this unique owned absent name may be created,never an alias.
            try:upper.stat()
            except FileNotFoundError:
                upper.mkdir();rows.append(observe(root,source,upper,'case-distinct-created'))
        rows.append(observe(root,source,slot,'separate-sibling'))
        rows.append(observe(root,source,root,'target-contains-source'))
        child=source/'child';child.mkdir();rows.append(observe(root,source,child,'target-inside-source'))
        rows.append(observe(root,source,root/'absent','missing-target'))
        composed=root/'caf\u00e9';composed.mkdir();decomposed=root/'cafe\u0301'
        rows.append(observe(root,composed,decomposed,'unicode-normalization-first-lookup'))
        if not identity(decomposed)['available']:
            try:decomposed.stat()
            except FileNotFoundError:
                decomposed.mkdir();rows.append(observe(root,composed,decomposed,'unicode-distinct-created'))
        link=root/'source-link'
        try:os.symlink(source,link,target_is_directory=True)
        except OSError as e:
            rows.append(dict(case='symlink-unavailable',kind='unavailable',observed=dict(error=type(e).__name__,errno=e.errno,winerror=getattr(e,'winerror',None))))
        else:rows.append(observe(root,source,link,'symlink-alias'))
        before=dict(source=identity(source),target=identity(slot));assert before['source']!=before['target']
        held=root/'held-target';slot.rename(held)
        moved=False
        try:
            source.rename(slot);moved=True
            now=identity(slot);assert now==before['source']and now!=before['target']
            assert(slot/'payload').read_bytes()==payload
            rows.append(dict(case='preflight-binding-replaced',kind='rebound',
                request=dict(operation='protected-tree-preflight',source='protected',target='slot'),
                observed=dict(before=before,nowTarget=now,oldSource=identity(source),
                    sourcePayloadPreserved=True,sourcePayloadSha256=sha((slot/'payload').read_bytes()))))
        finally:
            if moved:slot.rename(source)
            held.rename(slot)
        assert identity(source)==before['source']and identity(slot)==before['target']
        assert(source/'payload').read_bytes()==payload
        assert(slot/'payload').read_bytes()==b'owned target sentinel\n'
    assert Path(__file__).read_bytes()==SOURCE,'Producer changed during observation.'
    result=dict(schema=1,contract='owned-path-observations-v1',profile=dict(system=platform.system(),release=platform.release(),machine=platform.machine(),
        python=platform.python_version(),pythonExecutableSha256=sha(Path(sys.executable).read_bytes()),filesystemType='not measured'),
        capturedAt=datetime.now(timezone.utc).isoformat(),producerSha256=sha(SOURCE),cases=rows,ownedSourcePreserved=True,ownedRebindRestored=True,
        limits=['Single-process quiescent scratch tree;stat/samefile/resolve and sequential rename only. No other application or personal tree.',
                'No race-safe writer,live grant,mutation boundary,crash,durability,ID reuse or generic ancestry proof.',
                'Case/normalization/symlink behavior belongs to this selected fixture and host;unavailable is retained.',
                'TemporaryDirectory cleanup retires only this generated scratch tree after restoring both moved directories.'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
