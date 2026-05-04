import os
import re

def unwrap_po(file_path):
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('msgstr ""') and i + 1 < len(lines) and lines[i+1].startswith('"'):
            # It's a multiline string
            full_msgstr = ""
            i += 1
            while i < len(lines) and lines[i].startswith('"'):
                full_msgstr += lines[i].strip()[1:-1]
                i += 1
            new_lines.append(f'msgstr "{full_msgstr}"\n')
        else:
            new_lines.append(line)
            i += 1
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Unwrapped {file_path}")

unwrap_po('locale/de/LC_MESSAGES/django.po')
