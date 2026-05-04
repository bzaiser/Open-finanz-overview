import os

languages = ['en', 'fr', 'it', 'es']
help_translations = {
    'en': {
        'HELP_TARGET_DATE': "The anchor date for your simulation. All calculations for interest, pension phases, and purchasing power losses start from this day.",
        'HELP_INFLATION_RATE': "The expected annual inflation rate. This reduces the real value (purchasing power) of your future wealth. A value of 2% is a common benchmark.",
        'HELP_SALARY_INCREASE': "The average annual increase in your gross salary until retirement.",
        'HELP_PENSION_INCREASE': "The annual adjustment of your pension benefits. In many countries, this value often follows general wage development.",
        'HELP_INTEREST_BUFFER': "A global return surcharge on all your liquid assets (accounts and portfolios). If you have 1% interest on an account and enter 2% here, that account will yield 3% interest. Ideal for lump-sum scenarios.",
        'HELP_REAL_ESTATE_GROWTH': "The expected annual value increase of your real estate properties."
    },
    'fr': {
        'HELP_TARGET_DATE': "La date d'ancrage de votre simulation. Tous les calculs d'intérêts, de phases de retraite et de pertes de pouvoir d'achat commencent à partir de ce jour.",
        'HELP_INFLATION_RATE': "Le taux d'inflation annuel attendu. Cela réduit la valeur réelle (pouvoir d'achat) de votre patrimoine futur. Une valeur de 2% est une référence courante.",
        'HELP_SALARY_INCREASE': "L'augmentation annuelle moyenne de votre salaire brut jusqu'à la retraite.",
        'HELP_PENSION_INCREASE': "L'ajustement annuel de vos prestations de retraite. Dans de nombreux pays, cette valeur suit souvent l'évolution générale des salaires.",
        'HELP_INTEREST_BUFFER': "Une surtaxe de rendement globale sur tous vos actifs liquides (comptes et portefeuilles). Si vous avez 1% d'intérêt sur un compte et entrez 2% ici, ce compte rapportera 3% d'intérêt. Idéal pour les scénarios forfaitaires.",
        'HELP_REAL_ESTATE_GROWTH': "L'augmentation annuelle attendue de la valeur de vos biens immobiliers."
    },
    'it': {
        'HELP_TARGET_DATE': "La data di riferimento per la tua simulazione. Tutti i calcoli per interessi, fasi pensionistiche e perdite di potere d'acquisto iniziano da questo giorno.",
        'HELP_INFLATION_RATE': "Il tasso di inflazione annuale atteso. Questo riduce il valore reale (potere d'acquisto) della tua ricchezza futura. Un valore del 2% è un parametro comune.",
        'HELP_SALARY_INCREASE': "L'aumento annuo medio del tuo stipendio lordo fino al pensionamento.",
        'HELP_PENSION_INCREASE': "L'adeguamento annuale delle tue prestazioni pensionistiche. In molti paesi, questo valore segue spesso l'andamento generale dei salari.",
        'HELP_INTEREST_BUFFER': "Una maggiorazione del rendimento globale su tutte le tue attività liquide (conti e portafogli). Se hai l'1% di interesse su un conto e inserisci il 2% qui, quel conto renderà il 3% di interesse. Ideale per scenari forfettari.",
        'HELP_REAL_ESTATE_GROWTH': "L'aumento annuo atteso del valore delle tue proprietà immobiliari."
    },
    'es': {
        'HELP_TARGET_DATE': "La fecha de anclaje para su simulación. Todos los cálculos de intereses, fases de jubilación y pérdidas de poder adquisitivo comienzan a partir de este día.",
        'HELP_INFLATION_RATE': "La tasa de inflación anual esperada. Esto reduce el valor real (poder adquisitivo) de su riqueza futura. Un valor del 2% es un referente común.",
        'HELP_SALARY_INCREASE': "El incremento anual promedio de su salario bruto hasta la jubilación.",
        'HELP_PENSION_INCREASE': "El ajuste anual de sus prestaciones de jubilación. En muchos países, este valor suele seguir la evolución general de los salarios.",
        'HELP_INTEREST_BUFFER': "Un recargo de rendimiento global en todos sus activos líquidos (cuentas y carteras). Si tiene un 1% de interés en una cuenta e ingresa un 2% aquí, esa cuenta rendirá un 3% de interés. Ideal para escenarios de suma global.",
        'HELP_REAL_ESTATE_GROWTH': "El aumento de valor anual esperado de sus propiedades inmobiliarias."
    }
}

for lang in languages:
    po_path = f'locale/{lang}/LC_MESSAGES/django.po'
    if os.path.exists(po_path):
        with open(po_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_entries = []
        for msgid, msgstr in help_translations[lang].items():
            if f'msgid "{msgid}"' not in content:
                new_entries.append(f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n')
        
        if new_entries:
            with open(po_path, 'a', encoding='utf-8') as f:
                f.write(''.join(new_entries))
            print(f"Updated {po_path}")
        else:
            print(f"No new entries for {po_path}")
