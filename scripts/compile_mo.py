import re
import struct
from pathlib import Path

def parse_po(file_path):
    entries = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match msgid and msgstr pairs
    pattern = re.compile(
        r'msgid\s+((?:"(?:[^"\\]|\\.)*"\s*)+)\s*msgstr\s+((?:"(?:[^"\\]|\\.)*"\s*)+)',
        re.MULTILINE
    )

    def clean_str(s):
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', s)
        joined = "".join(parts)
        return joined.encode('raw_unicode_escape').decode('unicode_escape')

    for match in pattern.finditer(content):
        raw_id, raw_str = match.groups()
        msgid = clean_str(raw_id)
        msgstr = clean_str(raw_str)
        entries[msgid] = msgstr

    return entries

def generate_mo(entries, output_path):
    keys = sorted(entries.keys())
    
    offsets = []
    ids = b''
    strs = b''
    
    for key in keys:
        val = entries[key]
        key_bytes = key.encode('utf-8') + b'\x00'
        val_bytes = val.encode('utf-8') + b'\x00'
        
        offsets.append((len(ids), len(key_bytes) - 1, len(strs), len(val_bytes) - 1))
        ids += key_bytes
        strs += val_bytes
        
    num_strings = len(keys)
    keystart = 7 * 4 + 16 * num_strings
    valuestart = keystart + len(ids)
    
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets.extend([l1, o1 + keystart])
        voffsets.extend([l2, o2 + valuestart])
        
    header = struct.pack(
        "Iiiiiii",
        0x950412de, # Magic number
        0,          # Format revision
        num_strings,
        7 * 4,      # Offset to msgid table
        7 * 4 + num_strings * 8, # Offset to msgstr table
        0, 0        # Hash table
    )
    
    mo_data = header + struct.pack(f"{len(koffsets)}i", *koffsets) + struct.pack(f"{len(voffsets)}i", *voffsets) + ids + strs
    with open(output_path, 'wb') as f:
        f.write(mo_data)
        
    print(f"Compiled {num_strings} strings to {output_path}")

def compile_all():
    locale_dir = Path('locale')
    for po_file in locale_dir.rglob('django.po'):
        mo_file = po_file.with_suffix('.mo')
        entries = parse_po(po_file)
        generate_mo(entries, mo_file)

if __name__ == '__main__':
    compile_all()
