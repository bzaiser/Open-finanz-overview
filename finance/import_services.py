import pandas as pd
import datetime
import re
from decimal import Decimal
from django.utils import timezone
from .models import Category, ImportBatch, PendingTransaction
from .llm import classify_transactions
import logging

logger = logging.getLogger(__name__)


def _normalize_description(text: str) -> str:
    """
    Normalize a transaction description for grouping.
    Strips reference numbers, dates, and extra whitespace so that
    e.g. "NETFLIX 12345 Dec" and "NETFLIX 67890 Nov" collapse to "NETFLIX".
    """
    text = str(text).upper().strip()
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

    def parse_and_categorize(self):
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

            # 3. Create ImportBatch
            batch = ImportBatch.objects.create(user=self.user, filename=self.filename)

            categories = list(Category.objects.values('name', 'slug'))

            # 4. Send UNIQUE groups to AI (not every raw row!)
            transactions_for_ai = []
            for idx, group in enumerate(groups):
                transactions_for_ai.append({
                    "id": idx,
                    "description": group['description'],
                    "amount": float(group['avg_amount']),
                    "occurrences": group['count'],
                    "is_likely_recurring": group['is_recurring'],
                })

            # AI Categorization in chunks of 20
            ai_results = {}
            for i in range(0, len(transactions_for_ai), 20):
                chunk = transactions_for_ai[i:i+20]
                results = classify_transactions(chunk, categories)
                ai_results.update(results)

            # 5. Save one PendingTransaction per group
            pending_list = []
            for idx, group in enumerate(groups):
                res = ai_results.get(idx, {})
                cat_slug = res.get('category_slug', 'uncategorized')
                category = Category.objects.filter(slug=cat_slug).first()

                pending = PendingTransaction(
                    batch=batch,
                    date=group['latest_date'],
                    description=group['description'],
                    amount=group['avg_amount'],
                    is_income=res.get('is_income', group['avg_amount'] > 0),
                    category=category,
                    is_recurring=group['is_recurring'] or res.get('is_recurring', False),
                    frequency=res.get('frequency', 'monthly')
                )
                pending_list.append(pending)

            PendingTransaction.objects.bulk_create(pending_list)
            return batch

        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            raise e

    def _group_transactions(self, df):
        """
        Groups transactions by normalized description.
        Returns a list of group dicts with:
          - description: clean display name
          - avg_amount: typical amount
          - count: how many times it appeared
          - is_recurring: True if it appeared 2+ times
          - latest_date: most recent occurrence
        """
        df['_key'] = df['description'].apply(_normalize_description)

        groups = []
        for key, group_df in df.groupby('_key'):
            count = len(group_df)
            avg_amount = group_df['amount'].mean()
            latest_date = group_df['date'].max().date()
            # Use the most frequent original description as display name, fallback to key
            modes = group_df['description'].mode()
            display_desc = modes.iloc[0] if not modes.empty else key
            # Recurring if it appears more than once
            is_recurring = count >= 2

            groups.append({
                'description': str(display_desc),
                'avg_amount': Decimal(str(round(float(avg_amount), 2))),
                'count': count,
                'is_recurring': is_recurring,
                'latest_date': latest_date,
            })

        # Sort: recurring first, then by amount descending
        groups.sort(key=lambda x: (-int(x['is_recurring']), -abs(float(x['avg_amount']))))
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
