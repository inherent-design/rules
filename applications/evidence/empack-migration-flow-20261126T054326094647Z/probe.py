"""Released-CLI target validation in two disposable one-root projects; no game or build."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
BINARY = Path('/Users/zer0cell/.local/bin/empack')
EXPECTED = '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')


def main():
    assert sha(BINARY) == EXPECTED
    previous = ROOT / 'applications/empack/update-flow/probe.py'
    assert previous.read_bytes() == subprocess.check_output(['git', 'show', '142200b46ff6d8c6bef9ce7d168fdc4b7f6727c2:applications/empack/update-flow/probe.py'])
    spec = importlib.util.spec_from_file_location('prior_fixture_snapshot', previous)
    prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    preread = ROOT / '.build/empack-migration-preread'
    metadata = json.loads((preread / 'receipt.json').read_text())
    for item in metadata['requests']:
        assert sha(preread / (item['name'] + '.json')) == item['sha256']
    versions = json.loads((preread / 'versions.json').read_text())
    selected = {v['id']: v for v in versions if v['id'] in ['wmIZ4wP4', 'sOzRw3CG']}
    assert len(selected) == 2
    for v in selected.values():
        assert v['project_id'] == 'uXXizFIs' and 'fabric' in v['loaders'] and not v['dependencies']
        assert '1.21.1' in v['game_versions']
    assert '1.21' in selected['wmIZ4wP4']['game_versions']
    assert '1.21' not in selected['sOzRw3CG']['game_versions']
    assert any(v['loader']['version'] == '0.16.0' for v in json.loads((preread / 'fabric-target.json').read_text()))
    run = ROOT / 'applications/evidence' / ('empack-migration-flow-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-empack-migration-', dir='/private/tmp'))
    for name in ['projects', 'state', 'cache', 'tmp', 'independent-api']:
        (work / name).mkdir(mode=0o700)
    for item in metadata['requests']:
        (work / 'independent-api' / (item['name'] + '.json')).write_bytes((preread / (item['name'] + '.json')).read_bytes())
    write(run / 'metadata.json', dict(requests=metadata['requests'], sampledAt=metadata['at'], project='uXXizFIs',
        oldGame='1.21.1', targetGame='1.21', loader='0.16.0', compatible=selected['wmIZ4wP4'], incompatible=selected['sOzRw3CG'],
        scope='Independent public API samples, not intercepted native responses. Deliberate older target game; provider metadata only, not gameplay compatibility.'))
    author_template = """schema: 6
pack: {id: rules.migration.CASE, name: Rules migration CASE, version: '1', authors: [Fixture]}
runtime:
  minecraft: '1.21.1'
  loader: {kind: fabric, pin: '0.16.0'}
  java: {preferred: 21}
dependencies:
  ferrite:
    source: modrinth:uXXizFIs
    pin: 'PIN'
    type: mod
build:
  default: [client]
  profiles:
    client: {target: prism, delivery: bundled, environment: client}
"""
    for name, pin in [('compatible', 'wmIZ4wP4'), ('incompatible', 'sOzRw3CG')]:
        project = work / 'projects' / name; project.mkdir(); (project / 'pack').mkdir()
        (project / 'empack.yml').write_text(author_template.replace('CASE', name).replace('PIN', pin))
        (work / 'state' / name).mkdir(mode=0o700); (work / 'cache' / name).mkdir(mode=0o700)
    env = dict(PATH=os.environ['PATH'], LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'), NO_COLOR='1', DO_NOT_TRACK='1')
    setup = dict(schema=1, work=str(work), binary=str(BINARY), binarySha256=EXPECTED,
                 producerSha256=sha(run / 'probe.py'), snapshotHelper='applications/empack/update-flow/probe.py',
                 snapshotHelperSha256=sha(previous), metadataSha256=sha(run / 'metadata.json'),
                 environmentKeys=sorted(env), privateMetadataSha256={p.name: sha(p) for p in (work / 'independent-api').iterdir()},
                 scope='Two own author projects with separate state/cache roots; public API reads, referenced mod selections, no engine build, artifact export, channel, Java/game, personal pack or host install changes.')
    write(run / 'setup.json', setup)
    commands = []

    def command(name, label, arguments, *, preview=False, failure=False, structured=False):
        project = work / 'projects' / name
        scopes = dict(project=project, state=work / 'state' / name, cache=work / 'cache' / name)
        before = {k: prior.image(p) for k, p in scopes.items()}
        argv = [str(BINARY), '--state-dir', str(scopes['state']), '--cache-dir', str(scopes['cache']),
                '--workdir', str(project), '--net-timeout', '45', '--color', 'never', '--yes', *arguments]
        began = time.monotonic()
        child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        print(json.dumps(dict(start=label, pid=child.pid)), flush=True)
        timed = False
        try: stdout, stderr = child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed = True; os.killpg(child.pid, signal.SIGKILL); stdout, stderr = child.communicate()
        (run / (label + '.stdout')).write_bytes(stdout); (run / (label + '.stderr')).write_bytes(stderr)
        try: os.killpg(child.pid, 0); absent = False
        except ProcessLookupError: absent = True
        after = {k: prior.image(p) for k, p in scopes.items()}
        row = dict(id=label, project=name, argv=argv, pid=child.pid, exitCode=child.returncode,
                   timedOut=timed, groupAbsent=absent, seconds=time.monotonic() - began, before=before, after=after,
                   streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        commands.append(row); write(run / 'commands.json', commands)
        print(json.dumps(dict(finish=label, exitCode=child.returncode, seconds=row['seconds'])), flush=True)
        assert not timed and absent and ((child.returncode != 0) if failure else (child.returncode == 0)), 'Retain unexpected native result; no automatic retry.'
        if preview or failure: assert before['project'] == after['project'], 'Preview/refusal changed captured project files.'
        if structured: write(run / (label + '.json'), json.loads(stdout))

    migration = ['migrate', '--minecraft', '1.21', '--loader', 'fabric', '--loader-version', '0.16.0']
    try:
        command('compatible', 'compatible-sync', ['sync'])
        command('compatible', 'compatible-preview', ['--dry-run', *migration, '--json'], preview=True, structured=True)
        command('compatible', 'compatible-apply', migration)
        command('compatible', 'compatible-check', ['check', '--json'], preview=True, structured=True)
        command('incompatible', 'incompatible-sync', ['sync'])
        command('incompatible', 'incompatible-preview', ['--dry-run', *migration, '--json'], preview=True, failure=True)
        command('incompatible', 'incompatible-apply', migration, failure=True)
        command('incompatible', 'explicit-unpin', ['unpin', 'ferrite'])
        command('incompatible', 'automatic-preview', ['--dry-run', *migration, '--json'], preview=True, structured=True)
        command('incompatible', 'automatic-apply', migration)
        command('incompatible', 'automatic-check', ['check', '--json'], preview=True, structured=True)
        assert sha(BINARY) == EXPECTED
        write(run / 'receipt.json', dict(schema=1, complete=True, commands=len(commands),
            allRecordedGroupsAbsent=all(r['groupAbsent'] for r in commands), producerSha256=sha(run / 'probe.py'),
            binarySha256=EXPECTED, setupSha256=sha(run / 'setup.json'), metadataSha256=sha(run / 'metadata.json'),
            allocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
            scope='Eleven actual released-CLI operations in two isolated projects. Project/state/cache before/after images observed separately; error cause, selections, compatibility and physical effects need independent review. No intercepted network trace, payload materialization, game or arbitrary graph/platform qualification.'))
        print(json.dumps(dict(run=str(run), complete=True, commands=len(commands))), flush=True)
    except BaseException as error:
        write(run / 'failure.json', dict(error=str(error), commands=len(commands), allRecordedGroupsAbsent=all(r['groupAbsent'] for r in commands)))
        print(json.dumps(dict(run=str(run), complete=False)), flush=True); raise


if __name__ == '__main__':
    main()
