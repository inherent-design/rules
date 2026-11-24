#!/usr/bin/env python3
"""Small profile matrix using the same disposable lifecycle capture and pins."""
import json
from journeys import Lab


def main():
    profiles = [
        ('narrow', dict(stdin='tty', stdout='pipe', stderr='tty', width=28), {}),
        ('fully-piped-ci', dict(stdin='pipe', stdout='pipe', stderr='pipe', width=80), {'CI': '1', 'NO_COLOR': '1', 'TERM': 'dumb'}),
        ('input-only-tty', dict(stdin='tty', stdout='pipe', stderr='pipe', width=80), {}),
        ('terminal-c-locale', dict(stdin='tty', stdout='tty', stderr='tty', width=28), {'LC_ALL': 'C', 'LANG': 'C', 'LC_CTYPE': 'C'}),
    ]
    for name, profile, env in profiles:
        lab = Lab(profile)
        try:
            for tool in ('npm', 'pnpm', 'yarn', 'empack'):
                lab.setup(tool)
                lab.env.update(env)
                if tool != 'empack':
                    path = lab.project / 'package.json'
                    manifest = json.loads(path.read_text())
                    manifest['description'] = 'Terminal Ω 日本'
                    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
                else:
                    path = lab.project / 'empack.yml'
                    path.write_text(path.read_text().replace('Terminal Fixture', 'Terminal Ω 日本'))
                lab.case(name + '-help', ['--help'], 'Help must be distinguishable from successful work; record channel, styling, width, and status independently.', 'Choose a command from the actual help; do not infer install success.')
                if tool == 'yarn':
                    lab.case(name + '-install', ['install', '--json'], 'Populate a valid local lock before structured inspection.', 'Check lock before info.')
                query = {'npm': ['pkg', 'get', '--json'], 'pnpm': ['list', '--json'],
                         'yarn': ['info', '--json'], 'empack': ['check', '--documents', '--json']}[tool]
                lab.case(name + '-json', query, 'Observe whether the selected command emits parseable structured output under this stream profile.', 'Decode the actual stdout/merged stream; do not strip arbitrary human text to manufacture a pass.')
                if tool == 'empack':
                    lab.case(name + '-approval', ['sync'], 'Absent --yes, stdin/stderr capability and an explicit answer govern approval; decline must preserve project files.',
                             'Use --dry-run to inspect or --yes only after deciding to apply.', marker='Apply this', action='n\n', timeout=3)
                if tool == 'pnpm':
                    lab.case(name + '-prompt-gate', ['run', 'fixture-fail'], 'Configured prompt gate must distinguish EOF/no terminal from available input. Declining an install is distinct from cancelling the requested script.',
                             'Read whether installation was declined and whether the explicitly requested script still ran.', marker='?', action='n\n', timeout=3,
                             overrides={'pnpm_config_verify_deps_before_run': 'prompt'})
        finally:
            lab.finish()


if __name__ == '__main__':
    main()
