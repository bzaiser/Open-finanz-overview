import os

def escape_po(text):
    return text.replace('"', '\\"')

translations_de = {
        # Profile / Core
        'First Name': 'Vorname',
        'Last Name': 'Nachname',
        'Email Address': 'E-Mail-Adresse',
        'Follow System Night Mode Settings': 'Nachtmodus Einstellungen vom System übernehmen',
        'Birth Date': 'Geburtsdatum',
        
        # UI Common
        'Date': 'Datum',
        'File': 'Datei',
        'Status': 'Status',
        'Action': 'Action',
        'Amount': 'Betrag',
        'Amount (€)': 'Betrag (€)',
        'Category': 'Kategorie',
        'Target Name': 'Ziel-Name',
        'Search Terms': 'Suchbegriffe',
        'Transaction Text': 'Buchungstext',
        'Assign Category': 'Kategorie zuweisen',
        'Uploading file...': 'Lade Datei hoch...',
        'Please wait, the data is being transferred to the server.': 'Bitte warten, die Daten werden zum Server übertragen.',
        'Delete': 'Löschen',
        'Edit': 'Bearbeiten',
        'Really delete filter?': 'Filter wirklich löschen?',
        
        # Success Messages
        'Filter added successfully.': 'Filter erfolgreich hinzugefügt.',
        'Filter updated successfully.': 'Filter erfolgreich geändert.',
        'Filter deleted.': 'Filter gelöscht.',
        'Import batch deleted.': 'Import-Batch gelöscht.',
        'Profile updated successfully!': 'Profil erfolgreich aktualisiert!',
        
        # AI / Imports
        'Automatically categorized by AI': 'Automatisch von KI kategorisiert',
        'Learned from your memory': 'Aus deinem Gedächtnis gelernt',
        'Duplicate selection & increment date': 'Auswahl duplizieren & Datum hochzählen',
        
        # Descriptions (IDs)
        'CHART_DESC_NET_WORTH': 'Diese Grafik projiziert dein Gesamtvermögen bis zum Lebensende. Die Daten stammen aus deinen <b>Anlagen</b>, <b>Renten</b>, <b>Immobilien</b> und <b>Sachwerten</b>, abzüglich der <b>Kredite</b>. <br><br>„Nominal“ zeigt die nackten Zahlen der Zukunft. „Real“ berechnet die Kaufkraft in heutigen Euros (inflationsbereinigt).',
        'CHART_DESC_CASH_FLOW': 'Vergleicht monatliche Einnahmen mit Ausgaben. Zeigt, ob du am Ende des Jahres Geld übrig hast (Überschuss) oder an dein Erspartes gehen musst (Defizit). <br><br>Basis ist die Tabelle <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Zahlungsströme (Einnahmen/Ausgaben)</a>.',
        'CHART_DESC_INCOME_EVOLUTION': 'Zeigt die Entwicklung deiner Einnahmen über Jahrzehnte. Berücksichtigt Gehaltssprünge, Mietsteigerungen und den Übergang von Gehalt zu Rente. <br><br>Datenquellen: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Einnahmen</a> und <a href="/admin/finance/pension/" target="_blank" class="alert-link">Rentenverträge</a>.',
        'CHART_DESC_EXPENSE_EVOLUTION': 'Visualisiert, wie sich deine Fixkosten und Lebenshaltungskosten durch Inflation und den Wegfall von Krediten verändern. <br><br>Datenquellen: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Ausgaben</a> und <a href="/admin/finance/loan/" target="_blank" class="alert-link">Kredite</a>.',
        'CHART_DESC_INFLATION_MONITOR': 'Ein Warnsystem für deine Kaufkraft. Es zeigt, wie viel deine heutige Sparsumme in der Zukunft noch wert ist, basierend auf der in der Simulation gewählten Inflationsrate.',
        'CHART_DESC_BUDGET_PIE': 'Die prozentuale Verteilung deiner Ausgaben im gewählten Simulationsjahr. Hilft dabei, Kostentreiber zu identifizieren. <br><br>Anpassbar in der Tabelle <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Ausgaben</a>.',
        'CHART_DESC_ASSET_ALLOCATION': 'Zeigt die Diversifikation deines Vermögens. Ein ausgewogener Mix aus liquiden Mitteln, Immobilien und Sachwerten ist oft sicherer. <br><br>Daten aus der Tabelle <a href="/admin/finance/asset/" target="_blank" class="alert-link">Vermögenswerte</a>.',
        'WIDGET_DESC_UPCOMING_DATES': 'Ein automatischer Kalender für deine Finanzen. Zeigt, wann Kredite auslaufen, Versicherungen enden oder Einmalzahlungen fällig werden. <br><br>Speist sich aus allen Tabellen mit Enddatum.',
        'WIDGET_DESC_INCOME_TABLE': 'Detaillierte Liste deiner monatlichen Zuflüsse zum gewählten Stichtag. <br><br>Hier anpassen: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Einnahmen verwalten</a>.',
        'WIDGET_DESC_EXPENSE_TABLE': 'Detaillierte Liste deiner monatlichen Abflüsse zum gewählten Stichtag. <br><br>Hier anpassen: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Ausgaben verwalten</a>.',
        'WIDGET_DESC_ASSET_TABLE': 'Inventur deiner Konten und Depots. Zeigt den simulierten Stand inklusive Zinseszinseffekt. <br><br>Hier anpassen: <a href="/admin/finance/asset/" target="_blank" class="alert-link">Vermögenswerte</a>.',
        'WIDGET_DESC_PENSION_TABLE': 'Übersicht deiner Altersvorsorge. Zeigt garantierte Beträge und aktuelle Kapitalwerte. <br><br>Hier anpassen: <a href="/admin/finance/pension/" target="_blank" class="alert-link">Rentenverträge</a>.',
        'WIDGET_DESC_EVENT_TABLE': 'Besondere Ereignisse (Erbe, Autokauf, Schenkung) im gewählten Simulationsjahr. <br><br>Hier anpassen: <a href="/admin/finance/onetimeevent/" target="_blank" class="alert-link">Einmalereignisse</a>.',
        'WIDGET_DESC_LOAN_TABLE': 'Übersicht deiner Schuldenlast. Zeigt Restsaldo und Zinssatz zum Stichtag. <br><br>Hier anpassen: <a href="/admin/finance/loan/" target="_blank" class="alert-link">Kredite verwalten</a>.',
        'CHART_DESC_LOAN_EVOLUTION': 'Visualisiert, wie schnell deine Schulden durch Tilgung schrumpfen. Hilft bei der Planung von Sondertilgungen. <br><br>Datenquelle: <a href="/admin/finance/loan/" target="_blank" class="alert-link">Kredite</a>.',
        'CHART_DESC_REAL_ESTATE': 'Zeigt die Wertentwicklung deiner Immobilien. Hier siehst du Details zu Wertsteigerungen, die im großen Gesamt-Chart oft untergehen.',
        'CHART_DESC_PHYSICAL_ASSETS': 'Visualisiert den Wertverlauf deiner Sachwerte (z.B. Gold, Autos). Durch den eigenen Maßstab sind hier auch kleinere SchwANKungen gut sichtbar.',
        'CHART_DESC_LIQUID_PENSION': 'Vergleicht dein verfügbares Bargeld/Depotguthaben mit deinem angesparten Rentenkapital über die Zeit.',
        'SUMMARY_DESC_ASSETS': 'Summe deines gesamten liquiden Kapitals (Konten, Aktien, Cash) zum gewählten Datum. <br><br>Verwaltet in <a href="/admin/finance/asset/" target="_blank" class="alert-link">Vermögenswerte</a>.',
        'SUMMARY_DESC_INCOME': 'Dein gesamtes monatliches Netto-Einkommen (Gehalt, Mieteinnahmen, etc.). <br><br>Verwaltet in <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Zahlungsströme (Einnahmen)</a>.',
        'SUMMARY_DESC_EXPENSES': 'Deine gesamten monatlichen Ausgaben inklusive simulierter Inflation. <br><br>Verwaltet in <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Zahlungsströme (Ausgaben)</a>.',
        'SUMMARY_DESC_PENSION': 'Aktueller Barwert bzw. Rückkaufwert all deiner Rentenanwartschaften. <br><br>Verwaltet in <a href="/admin/finance/pension/" target="_blank" class="alert-link">Rentenverträge</a>.',
        'SUMMARY_DESC_TARGET_PENSION': 'Die Summe der monatlichen Renten, die du laut deinen Verträgen nominal (ohne Inflation) erwartest. Dein Zielwert.',
        'SUMMARY_DESC_CURRENT_PENSION': 'Die monatliche Rente, die du laut Simulation zum Stichtag tatsächlich beziehst (inflationsbereinigt).',
        'SUMMARY_DESC_PHYSICAL_ASSETS': 'Gesamtwert deiner Sachwerte wie Fahrzeuge, Gold oder Sammlungen. <br><br>Verwaltet in <a href="/admin/finance/physicalasset/" target="_blank" class="alert-link">Sachwerte</a>.',
        'SUMMARY_DESC_REAL_ESTATE': 'Marktwert deiner Immobilien zum gewählten Datum. <br><br>Verwaltet in <a href="/admin/finance/realestate/" target="_blank" class="alert-link">Immobilien</a>.',
        'SUMMARY_DESC_TOTAL_WEALTH': 'Dein Netto-Reinvermögen: Summe aller Werte (liquide, Renten, Immobilien, Sachwerte) minus alle Kredite.',
        'SUMMARY_DESC_DEBTS': 'Deine gesamte Schuldenlast (Restsaldo) zum gewählten Datum. <br><br>Verwaltet in <a href="/admin/finance/loan/" target="_blank" class="alert-link">Kredite</a>.',
}

langs = ['de', 'en', 'fr', 'it', 'es']

for lang in langs:
    po_path = f'locale/{lang}/LC_MESSAGES/django.po'
    if os.path.exists(po_path):
        with open(po_path, 'a', encoding='utf-8') as f:
            f.write('\n\n# MASTER SYNC - CLEAN LOCALIZATION\n')
            for msgid, de_val in translations_de.items():
                if lang == 'de':
                    msgstr = de_val
                else:
                    msgstr = msgid # English is the key
                f.write(f'msgid "{msgid}"\nmsgstr "{escape_po(msgstr)}"\n\n')
        print(f"Master synced {po_path}")
