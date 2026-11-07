import re
from pathlib import Path

def dedup_po(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into entries
    # Each entry typically starts with comments or msgid
    entries = re.split(r'\n(?=(?:#[^\n]*\n)*msgid\s+)', content)
    
    seen = set()
    cleaned_entries = []
    
    pattern = re.compile(r'msgid\s+((?:"(?:[^"\\]|\\.)*"\s*)+)', re.MULTILINE)
    
    def extract_msgid(text):
        m = pattern.search(text)
        if not m:
            return None
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
        return "".join(parts)

    duplicates_removed = 0
    for entry in entries:
        mid = extract_msgid(entry)
        if mid is None:
            cleaned_entries.append(entry)
            continue
        # Header entry msgid == ""
        if mid == "":
            cleaned_entries.append(entry)
            continue
        if mid in seen:
            duplicates_removed += 1
            continue
        seen.add(mid)
        cleaned_entries.append(entry)

    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write("\n".join(cleaned_entries))

    print(f"{file_path}: removed {duplicates_removed} duplicates, kept {len(cleaned_entries)} entries.")

if __name__ == '__main__':
    for po_file in Path('locale').rglob('django.po'):
        dedup_po(po_file)
