"""Closed fixture interpretation, with no Handlebars or arbitrary file access."""
import re
import unicodedata
from archive_facts import path_facts


def address_facts(value):
    layer, separator, name = value.partition('/')
    recognized = bool(separator) and layer in ['common', 'client', 'server']
    explicit = name.endswith('.template')
    destination = name[:-len('.template')] if explicit else name
    valid = None
    if recognized:
        valid = not any(path_facts(destination).values())
    return dict(recognized=recognized, valid=valid, explicit=explicit), layer, destination


def collision_free(paths):
    # Only the selected NFD/casefold corpus. Not Rust Unicode-table equivalence.
    keys = [unicodedata.normalize('NFD', unicodedata.normalize('NFD', p).casefold()) for p in paths]
    return all(a != b and not a.startswith(b + '/') and not b.startswith(a + '/')
        for i, a in enumerate(keys) for b in keys[i + 1:])


def fixture_body(data, mode, name):
    try:
        text = data.decode('utf-8')
        utf8 = True
    except UnicodeDecodeError:
        text = None
        utf8 = False
    # This recognizer accepts only the source grammar actually authored in this
    # corpus. New expressions require new interpretation, not a silent fallback.
    known = True
    output = data
    if mode != 0 and utf8:
        tokens = re.findall(r'\{\{(.*?)\}\}', text)
        assert all(t in ['NAME', 'shell_quote NAME', 'UNKNOWN_RULES_VALUE'] for t in tokens), tokens
        assert text.count('{{') == text.count('}}') == len(tokens)
        known = 'UNKNOWN_RULES_VALUE' not in tokens
        if known:
            quoted = "'" + name.replace("'", "'\"'\"'") + "'"
            output = text.replace('{{shell_quote NAME}}', quoted).replace('{{NAME}}', name).encode()
        else:
            output = None
    elif mode == 1 and not utf8:
        output = None
    facts = dict(mode=mode, utf8=utf8, known=known)
    code = 0 if mode == 0 or (mode == 2 and not utf8) else 2 if not utf8 else 1 if known else 3
    return facts, code, output


def project_facts(sources, name):
    facts = dict(addresses=True, sameLayer=True, namespaceValid=True, bodies=True, game=True)
    layers = {'common': {}, 'client': {}}
    bodies = []
    for relative, encoded in sorted(sources.items()):
        addressed, layer, destination = address_facts(relative)
        if not addressed['recognized']:
            continue
        if not addressed['valid']:
            facts['addresses'] = False
        if layer not in layers:
            continue
        if destination in layers[layer]:
            facts['sameLayer'] = False
        layers[layer][destination] = dict(source=relative, bytes=bytes.fromhex(encoded),
            mode=1 if addressed['explicit'] else 2)
    for layer in layers.values():
        facts['sameLayer'] &= collision_free(list(layer))
    selected = {**layers['common'], **layers['client']}
    facts['namespaceValid'] = collision_free(list(selected))
    outputs = {}
    for path, item in selected.items():
        bf, code, output = fixture_body(item['bytes'], item['mode'], name)
        bodies.append((item['source'], bf, code))
        facts['bodies'] &= code in [0, 1]
        facts['game'] &= path != '.minecraft/config/marker.txt'
        outputs[path] = output
    return facts, outputs, bodies


def properties_bytes(value):
    # Java's properties syntax serializes Unicode as UTF-16 code units.
    units = value.encode('utf-16-be')
    output = []
    for at in range(0, len(units), 2):
        unit = int.from_bytes(units[at:at + 2], 'big')
        output.append('\\ ' if unit == 32 else '\\\\' if unit == 92 else chr(unit)
            if 33 <= unit <= 126 else '\\u' + format(unit, '04x'))
    return ''.join(output).encode()


def ini_bytes(value):
    # Scalar syntax only. Its consumer interpretation is not executed here.
    text = '@String(' + value + ')' if '\0' in value else '@' + value if value.startswith('@') else value
    parts = ['"']
    hex_tail = False
    for ch in text:
        if ord(ch) < 32 or ord(ch) == 127 or (hex_tail and ch in '0123456789abcdefABCDEF'):
            parts.append('\\x' + format(ord(ch), 'x'))
            hex_tail = True
        else:
            parts.append(('\\' if ch in '\\"' else '') + ch)
            hex_tail = False
    return (''.join(parts) + '"').encode()
