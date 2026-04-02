import pandas as pd
import datetime
import re
from decimal import Decimal
from django.utils import timezone
from .models import Category, ImportBatch, PendingTransaction
from .llm import classify_transactions
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def _normalize_description(text: str) -> str:
    """
    Normalize a transaction description for grouping.
    Detects major brands and returns a clean brand name if found.
    Otherwise, strips reference numbers, dates, and extra whitespace.
    """
    text = str(text).upper().strip()
    
    # Common brands to aggregate (High-level grouping)
    brands = [
        'EDEKA', 'REWE', 'ALDI', 'LIDL', 'PENNY', 'NETTO', 'KAUFLAND',
        'TEGUT', 'DM-MARKT', 'ROSSMANN', 'MUELLER', 'AMAZON', 'PAYPAL',
        'NETFLIX', 'SPOTIFY', 'DISNEY PLUS', 'DAZN', 'SKY', 'DB VERTRIEB',
        'APPLE.COM', 'GOOGLE *', 'MICROSOFT *', 'SHELL', 'ARAL', 'TOTAL',
        'ESSO', 'JET ', 'VODAFONE', 'TELEKOM', 'O2 ', 'STRATO', 'IONOS'
    ]
    
    for brand in brands:
        if brand in text:
            return brand

    # Remove common noise: long digit sequences, dates like 2024-01-01, reference codes
    text = re.sub(r'\b\d{6,}\b', '', text)           # long numbers (account/ref IDs)
    text = re.sub(r'\b\d{2}[./]\d{2}[./]\d{2,4}\b', '', text)  # dates
    text = re.sub(r'\b(DATUM|REFERENZ|REF|NR|BUCHUNGS|MANDATS|ID|GLÄUBIGER)[:\s#]?\w+\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Take first 60 chars as the "key" — the meaningful part is usually front-loaded
    return text[:60]


class ExcelParserService:
    def __init__(self, user, file_path, filename):
        self.user = user
        self.file_path = file_path
        self.filename = filename

    def parse_and_categorize(self, batch=None):
        try:
            # 1. Read Excel
            df = pd.read_excel(self.file_path)

            # Column detection
            col_map = self._detect_columns(df)

            # Standardize DataFrame
            df = df.rename(columns={
                col_map['date']: 'date',
                col_map['desc']: 'description',
                col_map['amount']: 'amount'
            })

            # Clean data
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date', 'amount'])
            df['amount'] = df['amount'].apply(lambda x: Decimal(str(x)))

            # 2. Smart Grouping: collapse similar recurring transactions
            groups = self._group_transactions(df)

            # 3. Create or use ImportBatch
            if not batch:
                batch = ImportBatch.objects.create(user=self.user, filename=self.filename)

            categories = list(Category.objects.values('name', 'slug'))

            # 4. Send UNIQUE groups to AI (not every raw row!)
            transactions_for_ai = []
            for idx, group in enumerate(groups):
                transactions_for_ai.append({
                    "id": idx,
                    "description": group['description'],
                    "amount": float(group['total_amount']),
                    "total_amount": float(group['total_amount']),
                    "occurrences": group['count'],
                    "is_likely_recurring": group['is_recurring'],
                })

            # AI Categorization in chunks of 20
            ai_results = {}
            error_logs = []
            total_items = len(transactions_for_ai)
            cache_key = f"import_progress_{self.user.id}"
            cache.set(cache_key, 0, 300) # Initial 0%

            if total_items == 0:
                # No transactions to analyze? Mark as done.
                cache.set(cache_key, 100, 300)
            else:
                for i in range(0, total_items, 20):
                    chunk = transactions_for_ai[i:i+20]
                    results, error = classify_transactions(chunk, categories)
                    if results:
                        ai_results.update(results)
                    if error:
                        error_logs.append(error)
                    
                    # Update progress in cache
                    progress = int((min(i + 20, total_items) / total_items) * 100)
                    cache.set(cache_key, progress, 300)

            if error_logs:
                batch.ai_log = "\n".join(set(error_logs))
                batch.save()
            
            # Reset progress when done
            cache.set(cache_key, 100, 10)

            # 5. Save one PendingTransaction per group
            pending_list = []
            for idx, group in enumerate(groups):
                # Lookup AI result by string-cast index to ensure a match
                res = ai_results.get(str(idx), {})
                cat_slug = res.get('category_slug', 'uncategorized')
                # Use iexact for case-insensitive matching
                category = Category.objects.filter(slug__iexact=cat_slug).first()

                pending = PendingTransaction(
                    batch=batch,
                    date=group['latest_date'],
                    description=group['description'],
                    amount=group['total_amount'],
                    is_income=res.get('is_income', group['total_amount'] > 0),
                    category=category,
                    is_recurring=group['is_recurring'] or res.get('is_recurring', False),
                    frequency=res.get('frequency', 'monthly'),
                    ai_reasoning=res.get('reasoning', '')
                )
                pending_list.append(pending)

            PendingTransaction.objects.bulk_create(pending_list)
            return batch

        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            raise e

    def _group_transactions(self, df):
        """
        Groups transactions by normalized description AND month/year.
        Returns a list of group dicts with:
          - description: clean brand + month/year
          - total_amount: sum of all amounts in that bucket
          - count: how many transactions were collapsed
          - is_recurring: True if it appears in multiple months (not currently computed here)
          - latest_date: the date to show in the UI
        """
        df['_key'] = df['description'].apply(_normalize_description)
        df['_month'] = df['date'].dt.month
        df['_year'] = df['date'].dt.year

        groups = []
        # Group by Normalized Description, Year and Month
        for (key, year, month), group_df in df.groupby(['_key', '_year', '_month']):
            count = len(group_df)
            total_amount = group_df['amount'].sum()
            latest_date = group_df['date'].max().date()
            
            # Use most frequent original description, or just the key
            modes = group_df['description'].mode()
            base_desc = modes.iloc[0] if not modes.empty else key
            
            # Format: "BRAND (3 Buchungen) [MM/YYYY]"
            display_desc = base_desc
            if count > 1:
                display_desc = f"{base_desc} ({count} Buchungen)"

            groups.append({
                'description': str(display_desc),
                'total_amount': Decimal(str(round(float(total_amount), 2))),
                'count': count,
                'latest_date': latest_date,
                'is_recurring': count >= 2 # Within a single month, it's a recurring habit
            })

        # Sort: by date descending, then by amount magnitude descending
        groups.sort(key=lambda x: (x['latest_date'], -abs(float(x['total_amount']))), reverse=True)
        return groups

    def _detect_columns(self, df):
        """
        Heuristic to find date, description, and amount columns.
        Supports many common German bank export formats.
        """
        cols = df.columns
        mapping = {}

        # Date detection - extended with more German bank formats
        date_keywords = [
            'datum', 'date', 'buchungstag', 'valuta', 'buchungsdatum',
            'wertstellungsdatum', 'wertstellung', 'auftragsdatum', 'tag', 'time'
        ]
        for c in cols:
            if any(x in str(c).lower() for x in date_keywords):
                mapping['date'] = c
                break

        # Description detection - extended
        desc_keywords = [
            'zweck', 'beschreibung', 'text', 'info', 'verwendungszweck',
            'buchungstext', 'empfänger', 'auftraggeber', 'beguenstigter',
            'name', 'memo', 'betreff', 'details', 'zahlungsempfanger',
            'transaktionsbeschreibung', 'grund', 'mitteilung'
        ]
        for c in cols:
            if any(x in str(c).lower() for x in desc_keywords):
                mapping['desc'] = c
                break

        # Amount detection - extended
        amount_keywords = [
            'betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll',
            'haben', 'buchungsbetrag', 'zahlungsbetrag', 'eur', 'euro'
        ]
        for c in cols:
            if any(x in str(c).lower() for x in amount_keywords):
                if pd.to_numeric(df[c], errors='coerce').notnull().any():
                    mapping['amount'] = c
                    break

        if len(mapping) < 3:
            missing = [k for k in ['date', 'desc', 'amount'] if k not in mapping]
            found_cols = list(cols)
            raise ValueError(
                f"Konnte folgende Spalten nicht erkennen: {missing}. "
                f"Gefundene Spalten in der Datei: {found_cols}. "
                f"Bitte stelle sicher, dass deine Datei Spalten für Datum, Beschreibung und Betrag enthält."
            )

        return mapping
