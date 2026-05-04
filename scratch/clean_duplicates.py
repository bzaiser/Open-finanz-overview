import os

def clean_po_file(path):
    if not os.path.exists(path):
        return
    
    with open(path, 'r', encoding='UTF-8') as f:
        lines = f.readlines()
    
    seen_ids = set()
    new_lines = []
    current_block = []
    current_id = None
    is_header = True
    
    for line in lines:
        if line.startswith('msgid ""') and is_header:
            # Keep header
            current_block.append(line)
            is_header = False
            continue
            
        if line.startswith('msgid "'):
            # Finish previous block
            if current_id is not None:
                if current_id not in seen_ids:
                    new_lines.extend(current_block)
                    seen_ids.add(current_id)
                current_block = []
            
            current_id = line.strip().split('msgid ')[1]
            current_block.append(line)
        elif line.startswith('msgstr') or line.startswith('"') or line.startswith('#'):
            current_block.append(line)
        elif line.strip() == '':
            if current_block:
                current_block.append(line)
        else:
            current_block.append(line)
            
    # Final block
    if current_id is not None and current_id not in seen_ids:
        new_lines.extend(current_block)

    with open(path, 'w', encoding='UTF-8') as f:
        f.writelines(new_lines)
    print(f"Cleaned {path}")

for lang in ['de', 'it', 'es', 'fr']:
    clean_po_file(f'locale/{lang}/LC_MESSAGES/django.po')
