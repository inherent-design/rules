"""Closed authored-workspace interpretation, independent of the two rule models."""
import json
from pathlib import PurePosixPath
import posixpath
import re

NAMES = ['alpha', 'beta', 'gamma']
PREFIX = 'rules-version-'


def version(text):
    assert re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', text), text
    return dict(zip(['major','minor','patch'],map(int,text.split('.')),strict=True))


def version_tuple(v):
    return v['major'],v['minor'],v['patch']


def resolve(old, strategy):
    if strategy == 'patch':
        return dict(old,patch=old['patch']+1)
    if strategy == 'minor':
        return dict(major=old['major'],minor=old['minor']+1,patch=0)
    return version(strategy)


def manifest(images, name):
    item = images[f'packages/{name}/package.json']
    return json.loads(bytes.fromhex(item['bytesHex']))


def decisions(images):
    """Literal emitted YAML profile, not a general YAML decoder."""
    releases, declined, undecided = {}, set(), set()
    for path, image in images.items():
        if not path.startswith('.yarn/versions/'):
            continue
        assert re.fullmatch(r'\.yarn/versions/[a-f0-9]{8}\.yml',path)
        section = None
        for line in bytes.fromhex(image['bytesHex']).decode().splitlines():
            if not line.strip():
                continue
            if line in ['releases:', 'declined:', 'undecided:']:
                section=line[:-1];continue
            if section == 'releases':
                match=re.fullmatch(r'  rules-version-(alpha|beta|gamma): ([a-z0-9.]+)',line)
                assert match,line
                name,strategy=match.groups()
                assert strategy in ['patch','minor','1.1.0']
                releases.setdefault(name,[]).append(strategy)
            else:
                match=re.fullmatch(r'  - rules-version-(alpha|beta|gamma)',line)
                assert section in ['declined','undecided'] and match,line
                (declined if section=='declined' else undecided).add(match[1])
    return releases, declined, undecided


def targets(images):
    releases,_,_=decisions(images)
    return {name:max([resolve(version(manifest(images,name)['version']),s) for s in strategies],key=version_tuple)
            for name,strategies in releases.items()}


def local_inputs_available(images):
    available=True
    for name in NAMES:
        value=manifest(images,name)
        for section in ['dependencies','devDependencies']:
            for ident,rng in value.get(section,{}).items():
                if rng.startswith('workspace:'):
                    assert ident in [PREFIX+'alpha',PREFIX+'beta']
                else:
                    assert ident==PREFIX+'missing' and rng=='file:../../missing.tgz'
                    target=posixpath.normpath(str(PurePosixPath('packages')/name/rng[5:]))
                    assert target=='missing.tgz'
                    available=available and target in images
    return available


def packets(runs):
    inputs={k:[] for k in ['scopes','records','applies','checks','ranges']}
    inputs['schema']=1
    expected={k:[] for k in inputs if k!='schema'}
    facts=[]
    for run in runs:
        setup=json.loads((run/'setup.json').read_text())
        for row in json.loads((run/'commands.json').read_text()):
            args=row['argv'][2:]
            before,after=row['before'],row['after']
            stdout=(run/(row['id']+'.stdout')).read_text()
            base=dict(id=row['id'],exitCode=row['exitCode'],capture=run.name)
            if args[0]=='install':
                assert setup.get('mode','initial')=='initialized-check' and row['exitCode']==0
                facts.append(dict(**base,qualification='Fixture initialization only, not a modeled version/check operation.'));continue
            if args[:2]==['version','check'] and setup.get('mode','initial')=='initial':
                assert row['exitCode']==1 and "doesn't seem to be present in your lockfile" in stdout
                assert before==after
                facts.append(dict(**base,qualification='Excluded check: fixture failed earlier lock admission; expected exit1 alone was insufficient.'));continue
            release_before,declined_before,_=decisions(before)
            release_after,declined_after,_=decisions(after)
            decided_before=set(release_before)|declined_before
            dry='--dry-run' in args;force='--force' in args
            # Captures have overlapping command labels, so retain run identity.
            identity=run.name+':'+row['id']
            if args[:2]==['version','check']:
                assert setup.get('mode','initial')=='initialized-check' and row['gitBefore']==row['gitAfter']
                assert before==after
                git_status=row['gitBefore']['status'].splitlines()
                changed={n:any(line[3:].startswith('packages/'+n+'/') for line in git_status) for n in NAMES}
                inputs['checks'].append(dict(id=identity,**{'changed'+dict(zip(NAMES,'ABC',strict=True))[n]:changed[n] for n in NAMES},
                                             **{'decided'+dict(zip(NAMES,'ABC',strict=True))[n]:n in decided_before for n in NAMES},
                                             bumpA='alpha' in release_before,bumpB='beta' in release_before))
                expected['checks'].append(dict(id=identity,successful=row['exitCode']==0))
                # Check useful failure identity, not just the nonzero status.
                missing_modified={n for n in NAMES if changed[n] and n not in decided_before}
                missing_dependent={(source,destination) for source,destination in [('beta','alpha'),('gamma','beta')]
                                   if destination in release_before and source not in decided_before}
                causes=[line for line in stdout.splitlines() if "doesn't have a release strategy attached" in line]
                actual_modified=set();actual_dependent=set()
                for line in causes:
                    modified=re.search(r"rules-version-(alpha|beta|gamma)@workspace:packages/\1 has been modified but doesn't have a release strategy attached",line)
                    dependent=re.search(r"rules-version-(alpha|beta|gamma)@workspace:packages/\1 doesn't have a release strategy attached, but depends on rules-version-(alpha|beta|gamma) which is planned for release",line)
                    assert bool(modified)!=bool(dependent),line
                    if modified:actual_modified.add(modified[1])
                    if dependent:actual_dependent.add((dependent[1],dependent[2]))
                assert actual_modified==missing_modified and actual_dependent==missing_dependent
                assert len(causes)==len(actual_modified)+len(actual_dependent)

            elif '--deferred' in args:
                name=row['workspace'];old=version(manifest(before,name)['version']);strategy=args[1]
                decline=strategy=='decline';target=old if decline else resolve(old,strategy)
                inputs['records'].append(dict(id=identity,current=old,target=target,priorDecision=name in decided_before,
                                              priorBump=name in release_before,decline=decline,force=force,dryRun=dry))
                expected['records'].append(dict(id=identity,accepted=row['exitCode']==0,decision=name in set(release_after)|declined_after,
                                                bump=name in release_after))
                for n in NAMES:
                    assert before[f'packages/{n}/package.json']==after[f'packages/{n}/package.json']
            elif args[1]=='patch':
                assert dry and '--recursive' in args and before==after
                root=NAMES.index(row['workspace'])
                native=[json.loads(line) for line in stdout.splitlines() if line.strip()]
                assert all(r['deferred'] is False and r['oldVersion']==manifest(before,r['ident'][len(PREFIX):])['version'] for r in native)
                inputs['scopes'].append(dict(id=identity,root=root,recursive=True))
                expected['scopes'].append(dict(id=identity,selected=[NAMES.index(r['ident'][len(PREFIX):]) for r in native]))
                for r in native:
                    old=version(r['oldVersion']);assert version(r['newVersion'])==dict(old,patch=old['patch']+1)
            else:
                assert args[:2]==['version','apply'] and '--json' in args
                selected=set(NAMES) if '--all' in args else {row['workspace']}
                resolved=targets(before)
                any_lower=any(version_tuple(resolved[n])<version_tuple(version(manifest(before,n)['version'])) for n in selected if n in resolved)
                available=local_inputs_available(before)
                wire=[json.loads(line) for line in stdout.splitlines() if line.strip()]
                announcements={r['ident'][len(PREFIX):]:r for r in wire if 'newVersion' in r}
                assert len(announcements)==sum('newVersion' in r for r in wire)
                saved_map={}
                for name in NAMES:
                    old=version(manifest(before,name)['version']);target=resolved.get(name,old)
                    actual=version(manifest(after,name)['version'])
                    has_release=name in resolved
                    if has_release and name in selected:
                        assert old!=target,'Native saved-change projection excludes equal-target requests'
                    key=identity+':'+name
                    inputs['applies'].append(dict(id=key,current=old,target=target,hasRelease=has_release,
                                                 anySelectedLower=any_lower,force=force,dryRun=dry,inputAvailable=available,selected=name in selected))
                    saved=actual!=old
                    if saved:
                        assert actual==target
                    saved_map[name]=saved
                    expected['applies'].append(dict(id=key,version=actual,retained=name in release_after,announced=name in announcements,
                                                    saved=saved,successful=row['exitCode']==0))
                    if name in announcements:
                        assert version(announcements[name]['oldVersion'])==old and version(announcements[name]['newVersion'])==target
                for source,destination in [('beta','alpha'),('gamma','beta')]:
                    rng=manifest(before,source)['dependencies'][PREFIX+destination]
                    match=re.fullmatch(r'(workspace:[~^])([0-9.]+)',rng);assert match,rng
                    old_range=version(match[2]);target=resolved.get(destination,version(manifest(before,destination)['version']))
                    actual_range=manifest(after,source)['dependencies'][PREFIX+destination]
                    assert actual_range.startswith(match[1])
                    inputs['ranges'].append(dict(id=identity+':'+source+'->'+destination,old=old_range,target=target,saved=(not any_lower or force) and not dry and available and destination in selected and destination in resolved))
                    expected['ranges'].append(dict(id=identity+':'+source+'->'+destination,target=version(actual_range[len(match[1]):])))
            facts.append(dict(**base,qualification='Selected version-decision operation',changedFiles=[k for k in sorted(set(before)|set(after))
                              if before.get(k,{}).get('sha256')!=after.get(k,{}).get('sha256')]))
    return inputs,expected,facts
