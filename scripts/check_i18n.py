#!/usr/bin/env python3
import os
import re
import sys

# Regex to find German-looking strings in translation tags
# Matches _("...") or {% trans "..." %} containing äöüß or specific German keywords
GERMAN_PATTERN = re.compile(r'(_\("|\{% trans ")([^"]*[äöüßÄÖÜ][^"]*|Datum|Betrag|Aktion|Status|Datei|Kategorie|Name|Vorname|Nachname|E-Mail|Wähle|Gelernt|Gedächtnis|Auswahl|Jahr|Filter|erfolgreich|gelöscht|geändert|hinzugefügt|duplizieren|hochzählen|Lebensmitteleinkäufe|kategorisiert|Automatisch|Ziel|Suchbegriffe|Buchungstext|Buchung|Umsatz|Saldo)\"', re.IGNORECASE)

def check_files():
    errors = 0
    # Files to check
    extensions = ('.py', '.html')
    exclude_dirs = ['venv', '.git', 'node_modules', 'locale', 'scratch']
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(extensions):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = GERMAN_PATTERN.findall(content)
                    if matches:
                        for match in matches:
                            # Filter out false positives like stable IDs (HELP_..., CHART_...)
                            if re.match(r'^(CHART_|WIDGET_|SUMMARY_|DESC_|HELP_)', match[1]):
                                continue
                            print(f"❌ ERROR: German string found in {path}: {match[1]}")
                            errors += 1
    return errors

if __name__ == "__main__":
    print("🔍 Running I18n Linter (English-Base Check)...")
    error_count = check_files()
    if error_count > 0:
        print(f"\n🛑 Found {error_count} I18n violations! Fix them before pushing.")
        sys.exit(1)
    else:
        print("\n✅ All translation tags are clean (English-Base policy followed).")
        sys.exit(0)
