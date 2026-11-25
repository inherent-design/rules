"""Closed fixture interpretation; neither Prism grammar is reimplemented here."""
import json
from pathlib import Path
import re

VOCABULARY = ['<self>', 'child', 'success', 'two words', 'Ω 日本', 'exit7', 'hold',
              'wrapper-child', 'wrapper argument', 'original game argument', '<missing>',
              'program', "'two", "words'", 'program\targument', 'argument', 'tail', 'two', 'words']


def packets(run):
    load = lambda name: json.loads((run / name).read_text())
    receipt = load('receipt.json')
    observed = load('observed.json')['cases']
    binaries = {v['path'] for v in receipt['binaries'].values()}

    def identity(text):
        if text in binaries:
            return 0
        if text == str(Path(receipt['work']) / 'not-installed'):
            return 10
        assert text in VOCABULARY, ('Outside command token vocabulary', text)
        return VOCABULARY.index(text)

    # The authored Java-data vector is read from the frozen driver, independently of child output.
    source = (run / 'driver.cpp').read_text()
    matches = re.findall(r'task\.gameArgs = \{([^}]+)\};', source)
    assert len(matches) == 1
    game = [identity(s) for s in json.loads('[' + matches[0] + ']')]
    inputs, expected, parser = [], [], []
    for case in observed:
        request = load(case['requestFile'])
        before = case['packets'][0]
        assert before['phase'] == 'before' and before['mode'] == request['mode']
        assert before['raw'] == request['command']
        assert before['qtVersion'] == receipt['qt']['pkgVersion']
        assert before['qtNoDebug'] == (case['variant'] == 'release')
        after = case['packets'][1] if len(case['packets']) > 1 else None
        if after:
            assert after['phase'] == 'after' and not after['timedOut']
        if request['mode'] == 'parse':
            assert case['helperExitCode'] == 0 and after is None and case['child'] is None
            parser.append(dict(id=case['id'], hook=before['hookArgs'], wrapper=before['wrapperArgs']))
            continue
        mode = ['pre', 'post', 'wrapper'].index(request['mode'])
        tokens = before['wrapperArgs'] if mode == 2 else before['hookArgs']
        encoded = [identity(s) for s in tokens]
        result = 3 if request['abort'] else 1 if 'exit7' in tokens else 2 if encoded[:1] == [10] else 0
        inputs.append(dict(id=case['id'], mode=mode, rawNonempty=bool(request['command']),
                           trimmedEmpty=not request['command'].strip(), tokens=encoded,
                           programExists=encoded[:1] == [0], processResult=result,
                           abortRequested=request['abort'], gameArgs=game))
        child = case['child']
        if case['helperExitCode'] < 0:
            assert after is None and child is None
            kind = 5  # Observed abrupt helper termination, not a defined safe product refusal.
        elif mode != 2:
            assert case['helperExitCode'] == 0 and after and after['terminal']
            kind = 1
        elif child:
            assert case['helperExitCode'] == 0 and after and after['terminal']
            kind = 3 if child['argv'][0] == 'wrapper-child' else 2
        else:
            assert case['helperExitCode'] == 0 and after and after['terminal'] and not after['successful']
            kind = 4
        if child:
            assert case['childAbsent'] and child['cwd'] == request['cwd']
            assert child['value'] == request['environment']['RULES_VALUE']
        expected.append(dict(id=case['id'], disposition=kind, terminal=after['terminal'] if after else False,
                             successful=after['successful'] if after else False, child=child is not None,
                             abortAccepted=after['abortAccepted'] if after else False,
                             childArgs=[identity(s) for s in child['argv']] if child else []))
    literal_parser_controls = {
        'parse-single-quotes-release': (['program', "'two", "words'"], ['program', 'two words']),
        'parse-tab-release': (['program', 'argument'], ['program\targument']),
        'parse-empty-argument-release': (['program', 'tail'], ['program', 'tail']),
        'parse-unquoted-value-release': (['program', 'two', 'words'], ['program', 'two', 'words']),
        'parse-quoted-value-release': (['program', 'two words'], ['program', 'two words']),
    }
    for row in parser:
        assert (row['hook'], row['wrapper']) == literal_parser_controls[row['id']]
    return dict(schema=1, cases=inputs), expected, parser
