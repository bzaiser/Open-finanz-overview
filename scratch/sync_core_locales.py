import os

translations = {
    'de': {
        'First Name': 'Vorname',
        'Last Name': 'Nachname',
        'Email Address': 'E-Mail-Adresse',
        'Follow System Night Mode Settings': 'Nachtmodus Einstellungen vom System übernehmen',
    },
    'en': {
        'First Name': 'First Name',
        'Last Name': 'Last Name',
        'Email Address': 'Email Address',
        'Follow System Night Mode Settings': 'Follow System Night Mode Settings',
    }
}

for lang in ['fr', 'it', 'es']:
    translations[lang] = translations['en'].copy()

for lang, data in translations.items():
    po_path = f'locale/{lang}/LC_MESSAGES/django.po'
    if os.path.exists(po_path):
        with open(po_path, 'a', encoding='utf-8') as f:
            f.write('\n# Core Form Translations\n')
            for msgid, msgstr in data.items():
                f.write(f'msgid "{msgid}"\nmsgstr "{msgstr}"\n\n')
        print(f"Updated {po_path}")
