import os
import re

# Comprehensive list of German words/patterns to identify as bad msgid
GERMAN_WORDS = [
    'Datum', 'Betrag', 'Aktion', 'Status', 'Datei', 'Kategorie', 'Name', 
    'Vorname', 'Nachname', 'E-Mail', 'Excel', 'Wähle', 'Gelernt', 'Gedächtnis',
    'Auswahl', 'Jahr', 'Filter', 'erfolgreich', 'gelöscht', 'geändert', 'hinzugefügt',
    'duplizieren', 'hochzählen', 'Lebensmitteleinkäufe', 'kategorisiert', 'Automatisch',
    'Ziel', 'Suchbegriffe', 'Buchungstext', 'Buchung', 'Umsatz', 'Saldo'
]

def clean_po_file(file_path):
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by entries (separated by blank lines or comments)
    entries = re.split(r'\n(?=#|msgid)', content)
    new_entries = []
    
    for entry in entries:
        if not entry.strip(): continue
        
        # Extract msgid
        match = re.search(r'msgid\s+"(.*)"', entry)
        if match:
            msgid = match.group(1)
            
            is_bad = False
            # Check for German characters
            if re.search(r'[äöüßÄÖÜ]', msgid):
                is_bad = True
            
            # Check for specific words (whole word match)
            for word in GERMAN_WORDS:
                if re.search(rf'\b{word}\b', msgid, re.IGNORECASE):
                    is_bad = True
                    break
            
            # Exception: if it's already a known stable key like CHART_... or DESC_...
            if re.match(r'^(CHART_|WIDGET_|SUMMARY_|DESC_|HELP_)', msgid):
                is_bad = False
                
            if is_bad:
                print(f"Removing bad msgid: {msgid}")
                continue
        
        new_entries.append(entry.strip())
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_entries) + '\n')
    print(f"Cleaned {file_path}")

for lang in ['de', 'en', 'fr', 'it', 'es']:
    clean_po_file(f'locale/{lang}/LC_MESSAGES/django.po')
