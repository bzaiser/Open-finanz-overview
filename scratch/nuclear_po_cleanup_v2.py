import os
import re

# List of words to identify German msgid
GERMAN_KEYWORDS = [
    'Rente', 'Simulation', 'Stichtag', 'tatsächlich', 'beziehst', 'inflationsbereinigt',
    'Sachwerte', 'Fahrzeuge', 'Gold', 'Sammlungen', 'Verwaltet', 'Immobilien', 'Marktwert',
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
    
    # Split by entries
    entries = re.split(r'\n\n', content)
    new_entries = []
    
    for entry in entries:
        if not entry.strip(): continue
        
        # Extract the full msgid (including multiline)
        # msgid ""
        # "line 1"
        # "line 2"
        msgid_match = re.search(r'msgid\s+(?:""\s+)?("(?:[^"\\]|\\.)*"(?:\s+"(?:[^"\\]|\\.)*")*)', entry, re.DOTALL)
        
        if msgid_match:
            full_msgid = msgid_match.group(1)
            # Remove quotes and whitespace to get the raw text
            raw_text = "".join(re.findall(r'"(.*)"', full_msgid))
            
            is_bad = False
            if re.search(r'[äöüßÄÖÜ]', raw_text):
                is_bad = True
            else:
                for word in GERMAN_KEYWORDS:
                    if re.search(rf'\b{word}\b', raw_text, re.IGNORECASE):
                        is_bad = True
                        break
            
            # Keep stable IDs
            if re.match(r'^(CHART_|WIDGET_|SUMMARY_|DESC_|HELP_|STATUS_)', raw_text):
                is_bad = False
                
            if is_bad:
                print(f"Removing zombie msgid: {raw_text[:50]}...")
                continue
        
        new_entries.append(entry.strip())
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_entries) + '\n')
    print(f"Cleaned {file_path}")

for lang in ['de', 'en', 'fr', 'it', 'es']:
    clean_po_file(f'locale/{lang}/LC_MESSAGES/django.po')
