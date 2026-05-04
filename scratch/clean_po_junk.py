import os
import re

def clean_po_file(file_path):
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by entries (separated by blank lines)
    entries = re.split(r'\n\n', content)
    new_entries = []
    
    # German IDs we want to remove
    ids_to_remove = ['Vorname', 'Nachname', 'E-Mail-Adresse', 'Nachtmodus Einstellungen vom System übernehmen']
    
    for entry in entries:
        skip = False
        for bad_id in ids_to_remove:
            if f'msgid "{bad_id}"' in entry:
                skip = True
                break
        
        if not skip and entry.strip():
            new_entries.append(entry.strip())
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_entries) + '\n')
    print(f"Cleaned {file_path}")

for lang in ['de', 'en', 'fr', 'it', 'es']:
    clean_po_file(f'locale/{lang}/LC_MESSAGES/django.po')
