#!/usr/bin/env python3
"""Targeted empack refusal, early cancellation, and independent partial effects."""
import json
import zipfile
from journeys import Lab


def main():
    lab = Lab(dict(stdin='tty', stdout='pipe', stderr='tty', width=80))
    try:
        lab.setup('empack')
        lab.case('cancel-at-approval', ['sync'], 'Cancel before approving a missing-lock synchronization plan; preserve project and durable state.',
                 'Inspect actual files/status; no approval was given.', marker='Apply this', action='interrupt')
        lab.case('status-after-early-cancel', ['status', '--json'], 'Inspection should show what actually exists after early cancellation.', 'Do not assume cancellation created or removed a lock.')
        lab.case('recovery-after-early-cancel', ['recover'], 'Inspect rather than presume interrupted publication.', 'Finish/restore only if an owned interrupted operation is reported.')
        lab.case('apply-after-inspection', ['--yes', 'sync'], 'Explicitly request synchronization after inspecting the cancelled outcome.', 'Check the newly recorded state.')
        (lab.project / 'supplied').mkdir()
        with zipfile.ZipFile(lab.project / 'supplied/resource.zip', 'w') as archive:
            archive.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 34, 'description': 'Terminal fixture'}}))
        lab.case('continue-independent', ['--net-timeout', '1', '--yes', 'add', 'supplied/resource.zip', './supplied/missing.zip', '--type', 'resourcepack', '--continue-independent'],
                 'One supplied file exists and one does not. Independent continuation may save the valid group and still return failure.',
                 'Inspect current files and the named failed group before retry; do not repeat the already-saved addition blindly.')
        lab.case('status-after-partial', ['status', '--json'], 'Read actual state after the failed or partial add.', 'Use the observed authored keys to choose any next operation.')
        lab.case('check-after-partial', ['check', '--json'], 'Check what is recorded without completing missing input or inferring gameplay compatibility.', 'Resolve the specific missing source separately.')
    finally:
        lab.finish()


if __name__ == '__main__':
    main()
