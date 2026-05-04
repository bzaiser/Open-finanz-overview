import os

# Function to escape double quotes for PO files
def escape_po(text):
    return text.replace('"', '\\"')

translations = {
    'de': {
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
        'CHART_DESC_PHYSICAL_ASSETS': 'Visualisiert den Wertverlauf deiner Sachwerte (z.B. Gold, Autos). Durch den eigenen Maßstab sind hier auch kleinere Schwankungen gut sichtbar.',
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
    },
    'en': {
        'CHART_DESC_NET_WORTH': 'This chart projects your total wealth until the end of life. The data comes from your <b>investments</b>, <b>pensions</b>, <b>real estate</b>, and <b>physical assets</b>, minus <b>loans</b>. <br><br>“Nominal” shows the raw numbers of the future. “Real” calculates the purchasing power in today\'s Euros (inflation-adjusted).',
        'CHART_DESC_CASH_FLOW': 'Compares monthly income with expenses. Shows whether you have money left at the end of the year (surplus) or need to use your savings (deficit). <br><br>Based on the <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Cash Flows (Income/Expenses)</a> table.',
        'CHART_DESC_INCOME_EVOLUTION': 'Shows the development of your income over decades. Considers salary jumps, rent increases, and the transition from salary to pension. <br><br>Data sources: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Income</a> and <a href="/admin/finance/pension/" target="_blank" class="alert-link">Pension Contracts</a>.',
        'CHART_DESC_EXPENSE_EVOLUTION': 'Visualizes how your fixed and living costs change due to inflation and the elimination of loans. <br><br>Data sources: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Expenses</a> and <a href="/admin/finance/loan/" target="_blank" class="alert-link">Loans</a>.',
        'CHART_DESC_INFLATION_MONITOR': 'A warning system for your purchasing power. It shows how much your current savings will be worth in the future, based on the inflation rate chosen in the simulation.',
        'CHART_DESC_BUDGET_PIE': 'The percentage distribution of your expenses in the chosen simulation year. Helps identify cost drivers. <br><br>Adjustable in the <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Expenses</a> table.',
        'CHART_DESC_ASSET_ALLOCATION': 'Shows the diversification of your wealth. A balanced mix of liquid assets, real estate, and physical assets is often safer. <br><br>Data from the <a href="/admin/finance/asset/" target="_blank" class="alert-link">Assets</a> table.',
        'WIDGET_DESC_UPCOMING_DATES': 'An automatic calendar for your finances. Shows when loans expire, insurance ends, or one-time payments are due. <br><br>Fed from all tables with an end date.',
        'WIDGET_DESC_INCOME_TABLE': 'Detailed list of your monthly inflows as of the chosen date. <br><br>Adjust here: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Manage Income</a>.',
        'WIDGET_DESC_EXPENSE_TABLE': 'Detailed list of your monthly outflows as of the chosen date. <br><br>Adjust here: <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Manage Expenses</a>.',
        'WIDGET_DESC_ASSET_TABLE': 'Inventory of your accounts and portfolios. Shows the simulated status including the compound interest effect. <br><br>Adjust here: <a href="/admin/finance/asset/" target="_blank" class="alert-link">Assets</a>.',
        'WIDGET_DESC_PENSION_TABLE': 'Overview of your retirement provision. Shows guaranteed amounts and current capital values. <br><br>Adjust here: <a href="/admin/finance/pension/" target="_blank" class="alert-link">Pension Contracts</a>.',
        'WIDGET_DESC_EVENT_TABLE': 'Special events (inheritance, car purchase, gift) in the chosen simulation year. <br><br>Adjust here: <a href="/admin/finance/onetimeevent/" target="_blank" class="alert-link">One-time Events</a>.',
        'WIDGET_DESC_LOAN_TABLE': 'Overview of your debt load. Shows remaining balance and interest rate as of the date. <br><br>Adjust here: <a href="/admin/finance/loan/" target="_blank" class="alert-link">Manage Loans</a>.',
        'CHART_DESC_LOAN_EVOLUTION': 'Visualizes how quickly your debts shrink through repayment. Helps in planning unscheduled repayments. <br><br>Data source: <a href="/admin/finance/loan/" target="_blank" class="alert-link">Loans</a>.',
        'CHART_DESC_REAL_ESTATE': 'Shows the value development of your real estate. Here you see details on value increases that often get lost in the large overall chart.',
        'CHART_DESC_PHYSICAL_ASSETS': 'Visualizes the value progression of your physical assets (e.g., gold, cars). Due to its own scale, even smaller fluctuations are clearly visible here.',
        'CHART_DESC_LIQUID_PENSION': 'Compares your available cash/portfolio balance with your accumulated pension capital over time.',
        'SUMMARY_DESC_ASSETS': 'Sum of all your liquid capital (accounts, stocks, cash) as of the chosen date. <br><br>Managed in <a href="/admin/finance/asset/" target="_blank" class="alert-link">Assets</a>.',
        'SUMMARY_DESC_INCOME': 'Your total monthly net income (salary, rental income, etc.). <br><br>Managed in <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Cash Flows (Income)</a>.',
        'SUMMARY_DESC_EXPENSES': 'Your total monthly expenses including simulated inflation. <br><br>Managed in <a href="/admin/finance/cashflowsource/" target="_blank" class="alert-link">Cash Flows (Expenses)</a>.',
        'SUMMARY_DESC_PENSION': 'Current present value or surrender value of all your pension entitlements. <br><br>Managed in <a href="/admin/finance/pension/" target="_blank" class="alert-link">Pension Contracts</a>.',
        'SUMMARY_DESC_TARGET_PENSION': 'The sum of monthly pensions you expect nominally (without inflation) according to your contracts. Your target value.',
        'SUMMARY_DESC_CURRENT_PENSION': 'The monthly pension you actually receive according to the simulation as of the date (inflation-adjusted).',
        'SUMMARY_DESC_PHYSICAL_ASSETS': 'Total value of your physical assets such as vehicles, gold, or collections. <br><br>Managed in <a href="/admin/finance/physicalasset/" target="_blank" class="alert-link">Physical Assets</a>.',
        'SUMMARY_DESC_REAL_ESTATE': 'Market value of your real estate as of the chosen date. <br><br>Managed in <a href="/admin/finance/realestate/" target="_blank" class="alert-link">Real Estate</a>.',
        'SUMMARY_DESC_TOTAL_WEALTH': 'Your net total wealth: Sum of all assets (liquid, pensions, real estate, physical assets) minus all loans.',
        'SUMMARY_DESC_DEBTS': 'Your entire debt load (remaining balance) as of the chosen date. <br><br>Managed in <a href="/admin/finance/loan/" target="_blank" class="alert-link">Loans</a>.',
    }
}

for lang in ['fr', 'it', 'es']:
    translations[lang] = translations['en'].copy()

for lang, data in translations.items():
    po_path = f'locale/{lang}/LC_MESSAGES/django.po'
    if os.path.exists(po_path):
        with open(po_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove previous attempt (if any)
        new_lines = []
        skip = False
        for line in lines:
            if '# New Chart/Widget Descriptions' in line:
                skip = True
            if not skip:
                new_lines.append(line)
        
        # Add escaped translations
        new_lines.append('\n# New Chart/Widget Descriptions\n')
        for msgid, msgstr in data.items():
            new_lines.append(f'msgid "{msgid}"\n')
            new_lines.append(f'msgstr "{escape_po(msgstr)}"\n\n')
        
        with open(po_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Fixed {po_path}")
