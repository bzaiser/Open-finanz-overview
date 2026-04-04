import pandas as pd
import datetime
import re
from decimal import Decimal
from django.utils import timezone
from .models import Category, ImportBatch, PendingTransaction
from .llm import classify_transactions
from django.conf import settings
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
        self._log_messages = []
        import time
        self._last_save_time = time.time()

    def _log(self, batch, message):
        """Helper to append log and save immediately for live UI update."""
        import time
        self._log_messages.append(message)
        
        # Only save to DB if it's a major milestone or at least 1.5s since last save
        # This prevents SQLite "database is locked" during heavy parallel processing
        is_milestone = any(x in message for x in ["###", "FEHLER", "KRITISCH", "Speichere", "KI analysiert"])
        current_time = time.time()
        
        if batch and (is_milestone or (current_time - self._last_save_time > 1.5)):
            batch.ai_log = "\n".join(self._log_messages)
            batch.save(update_fields=['ai_log'])
            self._last_save_time = current_time
        logger.info(message)

    def parse_and_categorize(self, batch=None):
        try:
            # 1. Read Excel
            df = pd.read_excel(self.file_path)
            self._log(batch, f"### START ANALYSE: {self.filename} ###")
            self._log(batch, f"Datei eingelesen: {len(df)} Zeilen Rohdaten gefunden.")
            self._log(batch, f"Rohspalten: {list(df.columns)}")
            
            if not df.empty:
                self._log(batch, f"Probe (Zeile 1): {df.iloc[0].to_dict()}")

            # Find the best header row (deep scan)
            col_map, header_row = self._detect_columns(df)
            
            # Re-align DataFrame if header was not in row 0
            if header_row > 0:
                self._log(batch, f"Kopfzeile in Zeile {header_row} gefunden. Richte Daten neu aus...")
                header_row_values = df.iloc[header_row-1]
                df.columns = header_row_values
                df = df.iloc[header_row:]
            
            # 2. Identify and rename columns robustly
            final_mapping = {}
            row_to_check = [str(c).lower().strip() for c in df.columns]
            self._log(batch, f"Suche Schlüsselbegriffe in: {row_to_check}")
            
            for i, col_name in enumerate(row_to_check):
                if not final_mapping.get('date') and any(k in col_name for k in ['datum', 'date', 'buchungstag', 'valuta', 'wertstellung', 'tag']):
                    final_mapping['date'] = i
                    self._log(batch, f"-> 'Datum' in Spalte {i} ('{df.columns[i]}') erkannt.")
                elif not final_mapping.get('desc') and any(k in col_name for k in ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck', 'empfänger', 'name']):
                    final_mapping['desc'] = i
                    self._log(batch, f"-> 'Beschreibung' in Spalte {i} ('{df.columns[i]}') erkannt.")
                elif not final_mapping.get('amount') and any(k in col_name for k in ['betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll', 'haben', 'eur', 'euro']):
                    final_mapping['amount'] = i
                    self._log(batch, f"-> 'Betrag' in Spalte {i} ('{df.columns[i]}') erkannt.")

            if 'date' not in final_mapping or 'amount' not in final_mapping:
                available = [str(c) for c in df.columns]
                self._log(batch, f"FEHLER: 'Datum' oder 'Betrag' fehlt! Gefunden: {available}")
                raise ValueError(f"Spalten für Datum/Betrag fehlen! Gefunden: {available}")

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

            # Clean data - convert date and handle German number formats
            self._log(batch, "Bereinigung: Formate prüfen...")
            df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            
            def clean_amount(val):
                if pd.isna(val) or val == '': return Decimal('0.00')
                if isinstance(val, (int, float, Decimal)): return Decimal(str(round(float(val), 2)))
                s = str(val).strip()
                s = re.sub(r'[^\d,.€$\-]', '', s)
                s = s.replace('€', '').replace('$', '').strip()
                if ',' in s and ('.' not in s or s.find('.') < s.find(',')):
                    s = s.replace('.', '').replace(',', '.')
                try:
                    return Decimal(s)
                except:
                    return Decimal('0.00')

            df['amount'] = df['amount'].apply(clean_amount)
            
            # Logging failures but KEEPING rows
            invalid_dates = df['date'].isna().sum()
            if invalid_dates > 0: 
                self._log(batch, f"WARNUNG: {invalid_dates} Zeilen mit ungültigem Datum. Nutze heute.")
                df['date'] = df['date'].fillna(pd.Timestamp.now())

            # Final check
            initial_count = len(df)
            self._log(batch, f"Bereinigung fertig: {initial_count} Zeilen verarbeitet.")

            if df.empty:
                self._log(batch, "KRITISCH: Datei ist leer!")

            # 3. Smart Grouping
            groups = self._group_transactions(df)
            self._log(batch, f"Gruppierung: {len(groups)} Buchungen zusammengefasst.")

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

            # AI Categorization in chunks (Smaller for local LLMs/Ollama for better progress)
            provider = getattr(settings, 'LLM_PROVIDER', 'hybrid').lower()
            chunk_size = 10 if provider == 'ollama' else 50
            ai_results = {}
            error_logs = []
            total_items = len(transactions_for_ai)
            cache_key = f"import_progress_{self.user.id}"
            cache.set(cache_key, 0, 300) # Initial 0%

            if total_items == 0:
                cache.set(cache_key, 100, 300)
            else:
                for i in range(0, total_items, chunk_size):
                    self._log(batch, f"KI analysiert Chunk {i//chunk_size + 1}...")
                    chunk = transactions_for_ai[i:i+chunk_size]
                    results, status_msg, events = classify_transactions(chunk, categories)
                    
                    # Log all intermediate events/errors from the AI
                    for event in events:
                        self._log(batch, f"KI-Event: {event}")
                    
                    if results:
                        ai_results.update(results)
                        self._log(batch, f"KI-Status: {status_msg}")
                    else:
                        self._log(batch, f"FEHLER Chunk {i//chunk_size + 1}: {status_msg}")
                    
                    # Update progress in cache
                    progress = int((min(i + chunk_size, total_items) / total_items) * 100)
                    cache.set(cache_key, progress, 300)
                    
                    # Throttling: Small sleep to avoid AI Rate Limits (reduced for speed)
                    import time
                    time.sleep(0.2)

            if error_logs:
                self._log(batch, f"KI Fehler: {error_logs[0]}")
            
            # AI analysis finished - progress will be marked 100 in the task caller
            pass

            # 5. Save PendingTransactions in chunks to avoid DB locks
            self._log(batch, f"Starte Speichern von {len(groups)} Buchungen...")
            pending_list = []
            for idx, group in enumerate(groups):
                res = ai_results.get(str(idx), {})
                cat_slug = res.get('category_slug', 'uncategorized')
                category = Category.objects.filter(slug__iexact=cat_slug).first()

                pending = PendingTransaction(
                    batch=batch,
                    date=group['latest_date'],
                    description=str(group['description'])[:500], # Safety truncation
                    amount=group['total_amount'],
                    is_income=res.get('is_income', group['total_amount'] > 0),
                    category=category,
                    is_recurring=group['is_recurring'] or res.get('is_recurring', False),
                    frequency=res.get('frequency', 'monthly'),
                    ai_reasoning=str(res.get('reasoning', ''))[:500] # Safety truncation
                )
                pending_list.append(pending)

            # Chunked save for reliability
            total_saved = 0
            chunk_size_db = 100
            for i in range(0, len(pending_list), chunk_size_db):
                chunk = pending_list[i:i+chunk_size_db]
                PendingTransaction.objects.bulk_create(chunk)
                total_saved += len(chunk)
                self._log(batch, f"-> {total_saved} von {len(pending_list)} Buchungen gespeichert...")
            
            cache.set(cache_key, 100, 300) # FINAL 100%
            self._log(batch, "### ANALYSE ERFOLGREICH ABGESCHLOSSEN ###")
            return batch

        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            raise e

    def _group_transactions(self, df):
        """
        Groups transactions by normalized description AND month/year.
        """
        df['_key'] = df['description'].apply(_normalize_description)
        df['_month'] = df['date'].dt.month
        df['_year'] = df['date'].dt.year

        groups = []
        for (key, year, month), group_df in df.groupby(['_key', '_year', '_month'], dropna=False):
            count = len(group_df)
            total_amount = group_df['amount'].sum()
            
            valid_dates = group_df['date'].dropna()
            latest_date = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()
            
            modes = group_df['description'].mode()
            base_desc = modes.iloc[0] if not modes.empty else (key if key else "Unbekannt")
            display_desc = base_desc
            if count > 1:
                display_desc = f"{base_desc} ({count} Buchungen)"

            groups.append({
                'description': str(display_desc),
                'total_amount': Decimal(str(round(float(total_amount), 2))),
                'count': count,
                'latest_date': latest_date,
                'is_recurring': count >= 2
            })

        groups.sort(key=lambda x: (x['latest_date'], -abs(float(x['total_amount']))), reverse=True)
        return groups

    def _detect_columns(self, df):
        """
        Heuristic to find date, description, and amount columns.
        """
        date_keywords = ['datum', 'date', 'buchungstag', 'valuta', 'buchungsdatum', 'wertstellung', 'tag']
        desc_keywords = ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck', 'empfänger', 'auftraggeber', 'name']
        amount_keywords = ['betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll', 'haben', 'eur', 'euro']

        mapping = self._check_row_for_keywords(df.columns, date_keywords, desc_keywords, amount_keywords)
        if mapping:
            return mapping, 0

        for i in range(min(20, len(df))):
            row_values = [str(x).lower() for x in df.iloc[i].values]
            mapping = self._check_row_for_keywords(row_values, date_keywords, desc_keywords, amount_keywords)
            if mapping:
                final_mapping = {}
                for key, val in mapping.items():
                    col_idx = row_values.index(val)
                    final_mapping[key] = df.columns[col_idx]
                return final_mapping, i + 1

        found_cols = list(df.columns)
        first_row = [str(x) for x in df.iloc[0].values] if not df.empty else "Empty"
        raise ValueError(f"Keine Header gefunden! Spalten: {found_cols}, Reihe 1: {first_row}")

    def _check_row_for_keywords(self, row_values, date_k, desc_k, amount_k):
        row_str = [str(x).lower() for x in row_values]
        mapping = {}
        for val in row_str:
            if not mapping.get('date') and any(k in val for k in date_k):
                mapping['date'] = val
            elif not mapping.get('desc') and any(k in val for k in desc_k):
                mapping['desc'] = val
            elif not mapping.get('amount') and any(k in val for k in amount_k):
                mapping['amount'] = val
        if len(mapping) >= 2 and 'date' in mapping and 'amount' in mapping:
            return mapping
        return None
