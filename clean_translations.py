import os
import sys
import re
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / 'locale'

def clean_and_validate_po(file_path):
    print(f"Validating {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    seen_msgids = set()
    new_lines = []
    current_block = []
    current_msgid = None
    is_in_msgid = False
    is_in_msgstr = False

    i = 0
    header_done = False
    
    while i < len(lines):
        line = lines[i]
        
        # Preserve header block
        if not header_done:
            new_lines.append(line)
            if line.strip() == 'msgstr ""':
                # Skip the header string quotes
                i += 1
                while i < len(lines) and lines[i].startswith('"'):
                    new_lines.append(lines[i])
                    i += 1
                header_done = True
                continue
            i += 1
            continue

        # Process entries
        if line.startswith('msgid '):
            msgid_str = line[6:].strip()
            # Handle multi-line msgid
            full_msgid = msgid_str
            peek = i + 1
            while peek < len(lines) and lines[peek].startswith('"'):
                full_msgid += lines[peek].strip()
                peek += 1

            if full_msgid in seen_msgids and full_msgid != '""':
                print(f"  Duplicate msgid found and removed: {full_msgid}")
                # Skip this msgid and its corresponding msgstr lines
                i = peek
                if i < len(lines) and lines[i].startswith('msgstr '):
                    i += 1
                    while i < len(lines) and lines[i].startswith('"'):
                        i += 1
                continue
            else:
                seen_msgids.add(full_msgid)
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"OK: {file_path.name} clean! ({len(seen_msgids)} unique msgids)")

def main():
    for lang in ['de', 'en', 'es', 'fr', 'it']:
        po_path = LOCALE_DIR / lang / 'LC_MESSAGES' / 'django.po'
        if po_path.exists():
            clean_and_validate_po(po_path)

if __name__ == '__main__':
    main()
