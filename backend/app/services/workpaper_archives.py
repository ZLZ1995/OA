"""Archive names and non-extracting validation, including encrypted/split archives."""
import re
import zipfile

PATTERN = re.compile(r"\.(?:zip|rar|7z|tar|gz|bz2|xz|z\d{2,3}|r\d{2,3}|(?:zip|7z)\.\d{3,})$", re.I)

def supported(name):
    return bool(PATTERN.search(name or ""))

def validate_volumes(names):
    groups = {}
    seen = set()
    for name in names:
        lower = name.lower()
        if lower in seen:
            raise ValueError("同一轮不能提交同名文件")
        seen.add(lower)
        match = re.match(r"^(.*?)(\.part)(\d+)(\.rar)$", lower) or re.match(r"^(.*?)(\.(?:7z|zip)\.)(\d+)$", lower) or re.match(r"^(.*?)(\.[zr])(\d{2,3})$", lower)
        if match:
            key = (match[1], match[2])
            groups.setdefault(key, []).append(int(match[3]))
    for (_, kind), numbers in groups.items():
        start = 0 if kind == '.r' else 1
        ordered = sorted(numbers)
        if ordered != list(range(start, start + len(ordered))):
            raise ValueError("分卷存在缺号或重复，请上传全部分卷")

def valid_upload(name, stream):
    if not supported(name):
        return False
    stream.seek(0)
    head = stream.read(512)
    stream.seek(0)
    if not head:
        return False
    # Continuation volumes are raw bytes and cannot be validated independently.
    if re.search(r"\.(?:z\d{2,3}|r\d{2,3}|(?:zip|7z)\.\d{3,})$", name, re.I) or re.search(r"\.part\d+\.rar$", name, re.I):
        return True
    ext = name.lower().rsplit('.', 1)[-1]
    if ext == 'zip':
        return zipfile.is_zipfile(stream)
    signatures = {'rar': (b'Rar!\x1a\x07',), '7z': (b'7z\xbc\xaf\x27\x1c',),
                  'gz': (b'\x1f\x8b',), 'bz2': (b'BZh',), 'xz': (b'\xfd7zXZ\x00',)}
    if ext == 'tar':
        return head[257:262] == b'ustar'
    return head.startswith(signatures.get(ext, ()))
