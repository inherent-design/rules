#!/usr/bin/env python3
"""Explicit styling controls on separated machine output; no production work."""
from journeys import Lab


def main():
    lab = Lab(dict(stdin='pipe', stdout='pipe', stderr='tty', width=80))
    try:
        for tool in ('npm', 'pnpm', 'yarn', 'empack'):
            lab.setup(tool)
            if tool == 'yarn':
                lab.case('color-setup', ['install', '--json'], 'Create a valid local lock before info.', 'Read lock before info.')
            query = {'npm': ['pkg', 'get', '--json'], 'pnpm': ['list', '--json'],
                     'yarn': ['info', '--json'], 'empack': ['check', '--documents', '--json']}[tool]
            for enabled in (False, True):
                flags = {'npm': ['--color=' + ('always' if enabled else 'false')],
                         'pnpm': ['--color=always'] if enabled else ['--no-color'],
                         'yarn': [], 'empack': ['--color', 'always' if enabled else 'never']}[tool]
                env = {'YARN_ENABLE_COLORS': 'true' if enabled else 'false'} if tool == 'yarn' else {}
                lab.case('color-' + ('always' if enabled else 'never'), flags + query,
                         'Explicit styling may affect the display channel; structured result must be checked independently.',
                         'Decode JSON/NDJSON without deleting bytes to repair it.', overrides=env)
    finally:
        lab.finish()


if __name__ == '__main__':
    main()
