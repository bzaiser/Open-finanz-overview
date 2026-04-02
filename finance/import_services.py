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
            log_messages = [f"Datei eingelesen: {len(df)} Zeilen gefunden."]

            # Find the best header row (deep scan)
            col_map, header_row = self._detect_columns(df)
            
            # Re-align DataFrame if header was not in row 0
            if header_row > 0:
                header_row_values = df.iloc[header_row-1]
                df.columns = header_row_values
                df = df.iloc[header_row:]
            
            # 2. Identify and rename columns robustly
            final_mapping = {}
            row_to_check = [str(c).lower() for c in df.columns]
            
            # Simple keyword search on current column names
            for i, col_name in enumerate(row_to_check):
                if not final_mapping.get('date') and any(k in col_name for k in ['datum', 'date', 'buchungstag', 'valuta', 'wertstellung', 'tag']):
                    final_mapping['date'] = i
                elif not final_mapping.get('desc') and any(k in col_name for k in ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck', 'empfänger', 'name']):
                    final_mapping['desc'] = i
                elif not final_mapping.get('amount') and any(k in col_name for k in ['betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll', 'haben', 'eur', 'euro']):
                    final_mapping['amount'] = i

            if 'date' not in final_mapping or 'amount' not in final_mapping:
                available = [str(c) for c in df.columns]
                raise ValueError(f"Konnte Spalten für Datum und Betrag nicht identifizieren. Gefunden: {available}")

            # Direct renaming by index
            new_cols = list(df.columns)
            new_cols[final_mapping['date']] = 'date'
            new_cols[final_mapping['amount']] = 'amount'
            if 'desc' in final_mapping:
                new_cols[final_mapping['desc']] = 'description'
            df.columns = new_cols
            
            # Ensure description exists
            if 'description' not in df.columns:
                df['description'] = "Kein Verwendungszweck"

            log_messages.append(f"Spalten erfolgreich zugeordnet (Index: {final_mapping})")

            # Clean data - convert date and handle German number formats
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            def clean_amount(val):
                if pd.isna(val): return None
                if isinstance(val, (int, float, Decimal)): return Decimal(str(val))
                # Handle string format (e.g. "1.234,56")
                s = str(val).replace('.', '').replace(',', '.')
                try:
                    return Decimal(s)
                except:
                    return None

            df['amount'] = df['amount'].apply(clean_amount)
            
            # Drop rows where we couldn't parse date or amount
            initial_count = len(df)
            df = df.dropna(subset=['date', 'amount'])
            log_messages.append(f"Gültige Buchungen: {len(df)} (von {initial_count}).")

            # 2. Smart Grouping
            groups = self._group_transactions(df)
            log_messages.append(f"Transaktionen nach Gruppierung: {len(groups)} Zeilen.")

            # 3. Create or use ImportBatch
            if not batch:
                batch = ImportBatch.objects.create(user=self.user, filename=self.filename)
            
            # Save the detection log
            batch.ai_log = "\n".join(log_messages)
            batch.save()

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
        # We use dropna=False to ensure we don't lose transactions with unparseable dates
        for (key, year, month), group_df in df.groupby(['_key', '_year', '_month'], dropna=False):
            count = len(group_df)
            total_amount = group_df['amount'].sum()
            
            # Safe date extraction
            valid_dates = group_df['date'].dropna()
            latest_date = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()
            
            # Use most frequent original description, or just the key
            modes = group_df['description'].mode()
            base_desc = modes.iloc[0] if not modes.empty else (key if key else "Unbekannt")
            
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
        Scans the first 20 rows of the file to find the actual header row.
        """
        date_keywords = ['datum', 'date', 'buchungstag', 'valuta', 'buchungsdatum', 'wertstellung', 'tag']
        desc_keywords = ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck', 'empfänger', 'auftraggeber', 'name']
        amount_keywords = ['betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll', 'haben', 'eur', 'euro']

        # 1. First try if the current columns are already the headers
        mapping = self._check_row_for_keywords(df.columns, date_keywords, desc_keywords, amount_keywords)
        if mapping:
            return mapping, 0 # Header at row 0 (already in columns)

        # 2. If not, scan the first 20 rows of data
        for i in range(min(20, len(df))):
            row_values = [str(x).lower() for x in df.iloc[i].values]
            mapping = self._check_row_for_keywords(row_values, date_keywords, desc_keywords, amount_keywords)
            if mapping:
                # We found the header row! 
                # Map the original column names to our internal keywords
                final_mapping = {}
                for key, val in mapping.items():
                    # val is the actual text found in that row. We need to find which column index that was.
                    col_idx = row_values.index(val)
                    final_mapping[key] = df.columns[col_idx]
                return final_mapping, i + 1 # Header is at row i, data starts at i + 1

        # Failure: Log what we saw to help debugging
        found_cols = list(df.columns)
        first_row = [str(x) for x in df.iloc[0].values] if not df.empty else "Empty"
        raise ValueError(
            f"Konnte Tabellenkopf nicht finden. Spalten: {found_cols}. Erste Zeile Rohdaten: {first_row}. "
            f"Stelle sicher, dass die Datei Spalten für Datum, Beschreibung und Betrag enthält."
        )

    def _check_row_for_keywords(self, row_values, date_k, desc_k, amount_k):
        """Helper to check if a row looks like a header."""
        row_str = [str(x).lower() for x in row_values]
        mapping = {}
        
        for val in row_str:
            if not mapping.get('date') and any(k in val for k in date_k):
                mapping['date'] = val
            elif not mapping.get('desc') and any(k in val for k in desc_k):
                mapping['desc'] = val
            elif not mapping.get('amount') and any(k in val for k in amount_k):
                mapping['amount'] = val
        
        if len(mapping) >= 3:
            return mapping
        return None
