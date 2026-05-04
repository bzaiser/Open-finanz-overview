import os
import re

def get_full_header(content):
    # Find the end of the header block (msgstr "" followed by metadata lines)
    # The header block ends with \n\n followed by a new msgid or comment
    match = re.search(r'(msgid ""\s+msgstr\s+""\s+(".*?"\s+)+)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def parse_po(file_path):
    if not os.path.exists(file_path):
        return "", {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    header = get_full_header(content)
    
    # Body starts after the header
    body = content.replace(header, "").strip()
    
    entries = re.split(r'\n\n', body)
    parsed = {}
    
    for entry in entries:
        if not entry.strip(): continue
        msgid_match = re.search(r'msgid\s+(?:""\s+)?("(?:[^"\\]|\\.)*"(?:\s+"(?:[^"\\]|\\.)*")*)', entry, re.DOTALL)
        if msgid_match:
            full_msgid = msgid_match.group(1)
            raw_msgid = "".join(re.findall(r'"(.*)"', full_msgid))
            parsed[raw_msgid] = entry.strip()
                
    return header, parsed

def sync_all_to_de():
    de_header, de_entries = parse_po('locale/de/LC_MESSAGES/django.po')
    if not de_header:
        print("CRITICAL: Could not find header in German PO file!")
        return
        
    langs = ['en', 'fr', 'it', 'es']
    
    for lang in langs:
        target_path = f'locale/{lang}/LC_MESSAGES/django.po'
        target_header, target_entries = parse_po(target_path)
        
        # Build language specific header from DE header
        # Find "Language: \n" and replace with "Language: {lang}\n"
        lang_header = de_header.replace('"Language: \\n"', f'"Language: {lang}\\n"')
        
        new_content = [lang_header]
        
        for msgid, de_entry in de_entries.items():
            if msgid in target_entries:
                new_content.append(target_entries[msgid])
            else:
                val = msgid if lang == 'en' else ""
                cleared_entry = re.sub(r'msgstr\s+.*', f'msgstr "{val}"', de_entry, flags=re.DOTALL)
                new_content.append(cleared_entry)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(new_content) + '\n')
            
        print(f"Synced {lang} to German structure.")

if __name__ == "__main__":
    sync_all_to_de()
