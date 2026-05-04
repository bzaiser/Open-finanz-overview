import os
import re

def parse_po(file_path):
    entries = {}
    current_id = None
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('msgid "'):
                current_id = line[7:-1]
            elif line.startswith('msgstr "') and current_id:
                msgstr = line[8:-1]
                entries[current_id] = msgstr
                current_id = None
    return entries

de_entries = parse_po('locale/de/LC_MESSAGES/django.po')
en_entries = parse_po('locale/en/LC_MESSAGES/django.po')

missing_ids = [m for m in de_entries.keys() if m not in en_entries and m != ""]

print(f"Found {len(missing_ids)} missing IDs.")

# For demonstration, print first 20 with their German value
for mid in missing_ids[:20]:
    val = de_entries[mid] if de_entries[mid] else mid
    print(f"ID: {mid} -> DE: {val}")
