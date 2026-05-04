import os
import re

# Extended translation dictionary for core UI elements
translations = {
    'de': {
        'First Name': 'Vorname',
        'Last Name': 'Nachname',
        'Display Name': 'Name',
        'Email Address': 'E-Mail-Adresse',
        'Date': 'Datum',
        'Entry Date': 'Datum',
        'Amount': 'Betrag',
        'Amount (€)': 'Betrag (€)',
        'Category': 'Kategorie',
        'Status': 'Status',
        'Action': 'Action',
        'File': 'Datei',
        'Target Name': 'Ziel-Name',
        'Search Terms': 'Suchbegriffe',
        'Delete': 'Löschen',
        'Edit': 'Bearbeiten',
        'Cancel': 'Abbrechen',
        'Save': 'Speichern',
        'Save changes': 'Änderungen speichern',
        'Filter added successfully.': 'Filter erfolgreich hinzugefügt.',
        'Filter updated successfully.': 'Filter erfolgreich geändert.',
        'Filter deleted.': 'Filter gelöscht.',
        'Automatically categorized by AI': 'Automatisch von KI kategorisiert',
        'Learned from your memory': 'Aus deinem Gedächtnis gelernt',
    },
    'en': {
        'First Name': 'First Name',
        'Last Name': 'Last Name',
        'Display Name': 'Name',
        'Email Address': 'Email Address',
        'Date': 'Date',
        'Entry Date': 'Date',
        'Amount': 'Amount',
        'Amount (€)': 'Amount (€)',
        'Category': 'Category',
        'Status': 'Status',
        'Action': 'Action',
        'File': 'File',
        'Target Name': 'Target Name',
        'Search Terms': 'Search Terms',
        'Delete': 'Delete',
        'Edit': 'Edit',
        'Cancel': 'Cancel',
        'Save': 'Save',
        'Save changes': 'Save changes',
    },
    'fr': {
        'First Name': 'Prénom',
        'Last Name': 'Nom',
        'Display Name': 'Nom',
        'Email Address': 'Adresse e-mail',
        'Date': 'Date',
        'Entry Date': 'Date',
        'Amount': 'Montant',
        'Amount (€)': 'Montant (€)',
        'Category': 'Catégorie',
        'Status': 'Statut',
        'Action': 'Action',
        'File': 'Fichier',
        'Target Name': 'Nom cible',
        'Search Terms': 'Mots-clés',
        'Delete': 'Supprimer',
        'Edit': 'Modifier',
        'Cancel': 'Annuler',
        'Save': 'Enregistrer',
        'Save changes': 'Enregistrer les modifications',
        'Filter added successfully.': 'Filtre ajouté avec succès.',
        'Filter updated successfully.': 'Filtre mis à jour avec succès.',
        'Filter deleted.': 'Filtre supprimé.',
        'Automatically categorized by AI': 'Catégorisé automatisch par l\'IA',
        'Learned from your memory': 'Appris de votre mémoire',
    },
    'it': {
        'First Name': 'Nome',
        'Last Name': 'Cognome',
        'Display Name': 'Nome',
        'Email Address': 'Indirizzo e-mail',
        'Date': 'Data',
        'Entry Date': 'Data',
        'Amount': 'Importo',
        'Amount (€)': 'Importo (€)',
        'Category': 'Categoria',
        'Status': 'Stato',
        'Action': 'Azione',
        'File': 'File',
        'Target Name': 'Nome di destinazione',
        'Search Terms': 'Termini di ricerca',
        'Delete': 'Elimina',
        'Edit': 'Modifica',
        'Cancel': 'Annulla',
        'Save': 'Salva',
        'Save changes': 'Salva modifiche',
        'Filter added successfully.': 'Filtro aggiunto con successo.',
        'Filter updated successfully.': 'Filtro aggiornato con successo.',
        'Filter deleted.': 'Filtro eliminato.',
        'Automatically categorized by AI': 'Categorizzato automaticamente dall\'IA',
        'Learned from your memory': 'Appreso dalla tua memoria',
    },
    'es': {
        'First Name': 'Nombre',
        'Last Name': 'Apellido',
        'Display Name': 'Nombre',
        'Email Address': 'Correo electrónico',
        'Date': 'Fecha',
        'Entry Date': 'Fecha',
        'Amount': 'Monto',
        'Amount (€)': 'Monto (€)',
        'Category': 'Categoría',
        'Status': 'Estado',
        'Action': 'Acción',
        'File': 'Archivo',
        'Target Name': 'Nombre de destino',
        'Search Terms': 'Términos de búsqueda',
        'Delete': 'Eliminar',
        'Edit': 'Editar',
        'Cancel': 'Cancelar',
        'Save': 'Guardar',
        'Save changes': 'Guardar cambios',
        'Filter added successfully.': 'Filtro añadido con éxito.',
        'Filter updated successfully.': 'Filtro actualizado con éxito.',
        'Filter deleted.': 'Filtro eliminado.',
        'Automatically categorized by AI': 'Categorizado automáticamente por la IA',
        'Learned from your memory': 'Aprendido de tu memoria',
    }
}

def escape_po(text):
    return text.replace('"', '\\"')

def apply_translations():
    langs = ['de', 'en', 'fr', 'it', 'es']
    for lang in langs:
        path = f'locale/{lang}/LC_MESSAGES/django.po'
        if not os.path.exists(path): continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        entries = re.split(r'\n\n', content)
        new_entries = []
        
        for entry in entries:
            if not entry.strip(): continue
            msgid_match = re.search(r'msgid\s+(?:""\s+)?("(?:[^"\\]|\\.)*"(?:\s+"(?:[^"\\]|\\.)*")*)', entry, re.DOTALL)
            if msgid_match:
                full_msgid = msgid_match.group(1)
                raw_msgid = "".join(re.findall(r'"(.*)"', full_msgid))
                
                # IMPORTANT: Skip the header (empty msgid)
                if not raw_msgid:
                    new_entries.append(entry.strip())
                    continue
                
                if raw_msgid in translations.get(lang, {}):
                    translated = translations[lang][raw_msgid]
                    entry = re.sub(r'msgstr\s+.*', f'msgstr "{escape_po(translated)}"', entry, flags=re.DOTALL)
                elif lang == 'en':
                    # Fallback for English: msgstr = msgid
                    entry = re.sub(r'msgstr\s+.*', f'msgstr {full_msgid.strip()}', entry, flags=re.DOTALL)
            
            new_entries.append(entry.strip())
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(new_entries) + '\n')
        print(f"Applied core translations to {path}")

if __name__ == "__main__":
    apply_translations()
