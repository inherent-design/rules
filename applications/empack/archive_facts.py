"""Interpret retained study inputs into explicit predicate witnesses, not a ZIP decoder."""
import string
import struct
import unicodedata

U64_MAX = (1 << 64) - 1
META_LIMIT = 16 * 1024 * 1024
RECORD_FIELDS = ['headerReadable', 'signature', 'nameReadable', 'utf8Declaration', 'rawUnique', 'spanWithin']


def path_facts(value):
    parts = value.split('/')
    control = lambda c: ord(c) < 32 or 0x7f <= ord(c) <= 0x9f
    common = any(p in ['', '.', '..'] or '\\' in p or any(map(control, p)) for p in parts)
    drive = len(value) >= 2 and value[0] in string.ascii_letters and value[1] == ':'
    devices = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
    def native_only(part):
        base = part.split('.')[0].rstrip(' ')
        upper = ''.join(chr(ord(c)-32) if 'a' <= c <= 'z' else c for c in base)
        device = upper in devices or any(upper.startswith(prefix) and upper[len(prefix):] in
            ['1','2','3','4','5','6','7','8','9','¹','²','³'] for prefix in ['COM','LPT'])
        return any(c in ':<>"|?*' for c in part) or part.endswith(('.', ' ')) or device
    return dict(commonUnsafe=common, drivePrefix=drive, portableOnlyUnsafe=any(map(native_only, parts)))


def metadata_facts(data, entry_limit, cancel_after, identity):
    """Bounded corpus decoder. Optional fields are unknown when not reached.

    This reads declarations and checks their available byte ranges. It performs
    no decompression, integrity verification, extraction, or native cancellation.
    """
    result = dict(id=identity, endValid=False, singleDisk=None, zip64Shape=None, entries=None,
        entryLimit=entry_limit, metadataBytes=None, noDirectoryOverflow=None, directoryWithin=None,
        records=[], cancelAfter=None if cancel_after < 0 else cancel_after, finalCount=None)
    candidates = []
    for pos in range(max(0, len(data)-65557), max(0, len(data)-21)):
        if data[pos:pos+4] == b'PK\x05\x06' and pos+22+struct.unpack_from('<H', data, pos+20)[0] == len(data):
            candidates.append(pos)
    if not candidates: return result
    end = candidates[-1]; result['endValid'] = True
    _, disk, central_disk, _on_disk, count, size, offset, _comment = struct.unpack_from('<4sHHHHIIH', data, end)
    result['singleDisk'] = disk == central_disk == 0
    if not result['singleDisk']: return result
    boundary, extension = end, 0
    if count == 0xffff or size == 0xffffffff or offset == 0xffffffff:
        result['zip64Shape'] = False
        if end < 20: return result
        sig, locator_disk, record_at, disks = struct.unpack_from('<4sIQI', data, end-20)
        if sig != b'PK\x06\x07' or locator_disk != 0 or disks != 1: return result
        if record_at+56 > end-20 or record_at+56 > U64_MAX: return result
        fields = struct.unpack_from('<4sQHHIIQQQQ', data, record_at)
        sig, record_size, _made, _needed, d1, d2, _n1, count, size, offset = fields
        if sig != b'PK\x06\x06' or d1 != 0 or d2 != 0 or record_size < 44: return result
        if record_at+12+record_size > U64_MAX or record_at+12+record_size != end-20: return result
        extension = record_size-44; boundary = record_at
    result.update(zip64Shape=True, entries=count)
    if count > entry_limit: return result
    result['metadataBytes'] = size+extension
    if size+extension > META_LIMIT: return result
    result['noDirectoryOverflow'] = offset+size <= U64_MAX
    if not result['noDirectoryOverflow']: return result
    central_end = offset+size; result['directoryWithin'] = central_end <= boundary
    if not result['directoryWithin']: return result
    assert count <= 20, 'The admitted study corpus is bounded, not an arbitrary archive reader.'
    records = [{field:None for field in RECORD_FIELDS} for _ in range(count)]
    result['records'] = records; seen = set(); position = offset
    for index, record in enumerate(records):
        if cancel_after >= 0 and index >= cancel_after: return result
        record['headerReadable'] = position+46 <= len(data)
        if not record['headerReadable']: return result
        header = data[position:position+46]; position += 46
        record['signature'] = header[:4] == b'PK\x01\x02'
        if not record['signature']: return result
        flags = struct.unpack_from('<H', header, 8)[0]
        length, extra, comment = struct.unpack_from('<HHH', header, 28)
        record['nameReadable'] = position+length <= len(data)
        if not record['nameReadable']: return result
        name = data[position:position+length]; position += length
        utf8 = True
        if flags & (1 << 11):
            try: name.decode('utf-8')
            except UnicodeDecodeError: utf8 = False
        record['utf8Declaration'] = utf8
        if not utf8: return result
        record['rawUnique'] = name not in seen
        if not record['rawUnique']: return result
        seen.add(name); position += extra+comment
        record['spanWithin'] = position <= central_end
        if not record['spanWithin']: return result
    result['finalCount'] = position == central_end
    return result


def coherent_tree(infos):
    """Selected corpus projection of the portable index, not Unicode-table equivalence."""
    spelling, files = {}, set()
    for entry in infos:
        name = entry.filename[:-1] if entry.is_dir() else entry.filename
        parts = name.split('/'); prefix = ''
        for i, part in enumerate(parts):
            prefix = prefix + '/' + part if prefix else part
            key = unicodedata.normalize('NFD', unicodedata.normalize('NFD', prefix).casefold())
            if key in files: return False
            if key in spelling and (spelling[key] != prefix or (not entry.is_dir() and i == len(parts)-1)):
                return False
            spelling[key] = prefix
            if not entry.is_dir() and i == len(parts)-1: files.add(key)
    return True


def closed_metadata_admission(facts):
    """Admit known prefix facts for the non-cancelled local import corpus.

    Unknown is not a failed archive predicate. A known earlier rejection can
    stop the check before facts that were deliberately left unobserved.
    """
    assert facts['cancelAfter'] is None, 'This projection has no injected cancellation.'
    count, size = facts['entries'], facts['metadataBytes']
    predicates = [facts['endValid'], facts['singleDisk'], facts['zip64Shape'],
        None if count is None else count <= facts['entryLimit'],
        None if size is None else size <= META_LIMIT,
        facts['noDirectoryOverflow'], facts['directoryWithin']]
    predicates += [r[k]for r in facts['records']for k in RECORD_FIELDS]
    predicates += [facts['finalCount']]
    for value in predicates:
        assert value is not None, 'Needed archive fact is unknown in native metadata projection.'
        if value is False: return False
    return True
