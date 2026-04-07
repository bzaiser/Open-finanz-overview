import pandas as pd
import datetime
import re
from decimal import Decimal
from django.utils import timezone
from .models import Category, ImportBatch, PendingTransaction, CashFlowSource, OneTimeEvent, ImportFilter
from .llm import classify_transactions
from django.conf import settings
from django.core.cache import cache
import logging

import logging
import hashlib

def _normalize_description(text: str) -> str:
    """
    Normalize a transaction description for grouping.
    Hyper-Aggressive Noise Suppression v3 (Nuclear Cleaning).
    """
    text = str(text).upper().strip()
    
    # 1. Major brands always prevail
    brands = [
        'EDEKA', 'REWE', 'ALDI', 'LIDL', 'PENNY', 'NETTO', 'KAUFLAND',
        'TEGUT', 'DM-MARKT', 'ROSSMANN', 'MUELLER', 'AMAZON', 'PAYPAL',
        'NETFLIX', 'SPOTIFY', 'DISNEY PLUS', 'DAZN', 'SKY', 'DB VERTRIEB',
        'APPLE.COM', 'GOOGLE *', 'MICROSOFT *', 'SHELL', 'ARAL', 'TOTAL',
        'ESSO', 'JET ', 'VODAFONE', 'TELEKOM', 'O2 ', 'STRATO', 'IONOS'
    ]
    for brand in brands:
        if brand in text: return brand

    # 2. Strip technical prefixes (Girocard, etc.)
    text = re.sub(r'^(GIROCARD|KARTENZAHLUNG|ENTGELT|UMS|SEPA|ZALUNG|LASTSCHRIFT|GUTSCHRIFT)\W+', '', text)
    
    # 3. Nuclear Action: Strip everything that is not a letter or space
    # This removes all IDs, Dates, Store Numbers, IBANs in one go.
    text = re.sub(r'[^A-Z\s]', ' ', text)
    
    # 4. Cleanup whitespace and keep only first 3 words
    words = text.split()
    text = " ".join(words[:3])

    # 5. Generic cleanup of common bank noise keywords
    for stop_word in ['PURCHASE', 'REFERENZ', 'REF', 'DATUM', 'ID', 'TERMINAL', 'MANDAT', 'GLÄUBIGER', 'NR']:
        if stop_word in text:
            text = text.split(stop_word)[0].strip()

    return text[:40] if len(text) > 3 else "SONSTIGE BUCHUNGEN"


class ExcelParserService:
    def __init__(self, user, file_path, filename):
        self.user = user
        self.file_path = file_path
        self.filename = filename
        self._log_messages = []
        import time
        self._last_save_time = time.time()

    def _log(self, batch, message):
        """Helper to append log and save immediately for live UI update with debouncing."""
        import time
        self._log_messages.append(message)
        
        # INCREASED DEBOUNCE: Only save to DB every 4 seconds or on major milestones
        is_milestone = any(x in message for x in ["###", "FEHLER", "KRITISCH"])
        current_time = time.time()
        
        if batch and (is_milestone or (current_time - self._last_save_time > 4.0)):
            batch.ai_log = "\n".join(self._log_messages)
            batch.save(update_fields=['ai_log'])
            self._last_save_time = current_time
        logger.info(message)

    def parse_and_categorize(self, batch=None):
        try:
            # 1. Read Excel
            cache_key = f"import_progress_{self.user.id}"
            cache.set(cache_key, 5, 300) # Start!
            
            self._log(batch, "### ANALYSE INITIALISIERT ###")
            self._log(batch, f"Lese Datei: {self.filename}")
            
            df = pd.read_excel(self.file_path)
            self._log(batch, f"Datei eingelesen: {len(df)} Zeilen Rohdaten gefunden.")
            cache.set(cache_key, 10, 300) 
            
            self._log(batch, "Analysiere Spalten-Struktur...")
            # Find the best header row (deep scan)
            col_map, header_row = self._detect_columns(df)
            cache.set(cache_key, 15, 300)
            self._log(batch, f"Spalten-Zuordnung abgeschlossen (Header in Zeile {header_row}).")

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
                    self._log(batch, "-> Spalte 'Datum' erkannt.")
                elif not final_mapping.get('desc') and any(k in col_name for k in ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck', 'empfänger', 'auftraggeber', 'name']):
                    final_mapping['desc'] = i
                    self._log(batch, "-> Spalte 'Beschreibung' erkannt.")
                elif not final_mapping.get('amount') and any(k in col_name for k in ['betrag', 'amount', 'wert', 'summe', 'umsatz', 'soll', 'haben', 'eur', 'euro']):
                    final_mapping['amount'] = i
                    self._log(batch, "-> Spalte 'Betrag' erkannt.")

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
            
            # --- ROW-LEVEL DUPLICATE DETECTION ---
            self._log(batch, "Prüfe Dateisignatur auf bereits importierte Buchungen...")
            existing_sigs = set(PendingTransaction.objects.filter(batch__user=self.user).values_list('signature', flat=True))
            
            def make_sig(row):
                # Hash of date, amount, and description
                data = f"{row['date']}|{row['amount']}|{row['description']}"
                return hashlib.md5(data.encode()).hexdigest()
            
            df['signature'] = df.apply(make_sig, axis=1)
            cache.set(cache_key, 30, 300)
            
            duplicates_mask = df['signature'].isin(existing_sigs)
            duplicate_count = duplicates_mask.sum()
            
            if duplicate_count > 0:
                self._log(batch, f"Dubletten-Check: {duplicate_count} bekannte Buchungen werden übersprungen.")
                df = df[~duplicates_mask]
            else:
                self._log(batch, "Dubletten-Check: Keine bekannten Buchungen in dieser Datei gefunden.")

            cache.set(cache_key, 35, 300) # Signatures checked

            if df.empty:
                self._log(batch, "KRITISCH: Datei ist leer!")

            # 3. Smart Grouping with user filters
            self._log(batch, "Gruppiere Buchungen nach Jahr und Filtern...")
            # We take all transactions (income and expenses) for comprehensive reconciliation
            groups = self._group_transactions(df)
            self._log(batch, f"Gruppierung abgeschlossen: {len(groups)} Jahressummen gebildet.")
            cache.set(cache_key, 40, 300) # Grouping done

            # 3. Create or use ImportBatch
            if not batch:
                batch = ImportBatch.objects.create(user=self.user, filename=self.filename)

            # 4. Optional AI Categorization for unassigned items
            # To stay FAST, we only send groups that didn't match a manual filter.
            unassigned = [g for g in groups if g.get('category') is None]
            provider = getattr(settings, 'LLM_PROVIDER', 'hybrid').lower()
            
            # Check if any AI provider is active
            ai_configured = (provider == 'ollama' and settings.OLLAMA_BASE_URL) or \
                            (settings.GEMINI_API_KEY or settings.GROQ_API_KEY)

            if unassigned and ai_configured:
                self._log(batch, "### KI-ANALYSE WIRD VORBEREITET ###")
                self._log(batch, f"Sende {len(unassigned)} Jahressummen an Ollama (Windows)...")
                
                # Prepare data for LLM
                llm_input = [{"id": i, "description": g['description'], "amount": float(g['total_amount'])} for i, g in enumerate(unassigned)]
                all_categories = list(Category.objects.all())
                cat_list = [{"id": c.id, "name": c.name, "slug": c.slug} for c in all_categories]
                
                # Call central AI dispatcher with live progress & cancellation check
                cache_key = f"import_progress_{self.user.id}"
                
                def ai_progress(current, total):
                    # AI Phase is approx 40% to 90% of total progress
                    p = 40 + int((current / total) * 50)
                    cache.set(cache_key, p, 300)
                    # We also log it to the batch log for the live console
                    self._log(batch, f"KI-Analyse: Paket {current} von {total} verarbeitet ({p}%)...")

                def ai_cancelled():
                    # Prüfen, ob der Batch in der Zwischenzeit gelöscht wurde
                    return not ImportBatch.objects.filter(id=batch.id).exists()

                results, status_msg, events = classify_transactions(
                    llm_input, cat_list, 
                    progress_callback=ai_progress,
                    is_cancelled_callback=ai_cancelled
                )
                self._log(batch, f"KI-Status: {status_msg}")
                
                # Map results back to groups
                cat_map = {c.slug: c for c in all_categories}
                for i, group in enumerate(unassigned):
                    res = results.get(str(i))
                    if res and res.get('category_slug') != 'uncategorized':
                        cat = cat_map.get(res['category_slug'])
                        if cat:
                            group['category'] = cat
                            group['ai_reasoning'] = res.get('reasoning', "Automatisch von KI kategorisiert")
                            if 'is_income' in res:
                                group['is_income'] = res['is_income']

            # 5. Pre-fetch Plan Data to avoid N+1 queries (AFTER AI Step!)
            self._log(batch, "Abgleich mit Finanzplan wird vorbereitet...")
            years_to_check = {g['latest_date'].year for g in groups if g.get('category')}
            plan_items = CashFlowSource.objects.filter(
                user=self.user, 
                start_date__year__in=years_to_check
            ).select_related('category')
            plan_map = {(p.category_id, p.start_date.year): p for p in plan_items}

            # 6. Save PendingTransactions in chunks
            self._log(batch, f"Erstelle Buchungsvorschläge für {len(groups)} Gruppen...")
            pending_list = []
            
            cache_key = f"import_progress_{self.user.id}"
            cache.set(cache_key, 50, 300)

            for idx, group in enumerate(groups):
                is_income = group['total_amount'] > 0
                ai_reasoning = f"Gruppiert aus {group['count']} Einzelbuchungen."
                
                # --- DUPLICATE DETECTION at Group Level ---
                m_start = group['latest_date'].replace(day=1)
                
                # Check for plan conflict using pre-fetched map
                existing_source = None
                has_conflict = False
                if group.get('category'):
                    lookup_key = (group['category'].id, group['latest_date'].year)
                    existing_source = plan_map.get(lookup_key)

                    if existing_source:
                        has_conflict = True
                        # We only log progress, not every single conflict, to avoid DB overhead
                        if idx % 50 == 0:
                            self._log(batch, f"Abgleich läuft ({idx}/{len(groups)})...")

                # --- AUTO-IGNORE logic ---
                # We ONLY ignore automatically if it definitely exists already (Duplicate).
                # All other items (even unassigned) must stay visible for reconciliation.
                is_ignored = has_conflict
                
                # Use raw description for unassigned items, but grouped description for filtered ones
                display_desc = group.get('raw_desc') if group.get('category') is None else group['description']
                
                # --- PLAN DEVIATION Check (2% Tolerance) ---
                planned_amount = None
                if group.get('linked_cash_flow'):
                    planned_amount = group['linked_cash_flow'].value
                    # If it's an expense but is_income is true in models, we handle signage logic if needed.
                    # Here we assume both are magnitude-based for comparison.
                    diff = abs(abs(group['total_amount']) - abs(planned_amount))
                    # Check tolerance (2%)
                    tolerance = abs(planned_amount) * Decimal('0.02')
                    if diff <= tolerance:
                        # If within tolerance, we treat it as exactly matched to hide alerts
                        planned_amount = group['total_amount']

                pending = PendingTransaction(
                    batch=batch,
                    date=group['latest_date'],
                    description=str(display_desc)[:500],
                    amount=group['total_amount'],
                    planned_amount=planned_amount, # Store the target plan value
                    is_income=group['is_income'],
                    category=group.get('category'),
                    is_ignored=is_ignored, # Auto-ignore if it's already in the plan
                    is_recurring=True,
                    has_conflict=has_conflict,
                    existing_source=existing_source,
                    integration_count=group['count'], # Store how many rows were grouped
                    signature=hashlib.md5(str(group).encode()).hexdigest()
                )
                pending_list.append(pending)

            # Bulk save
            PendingTransaction.objects.bulk_create(pending_list)
            
            cache.set(cache_key, 100, 300)
            self._log(batch, "### ANALYSE ERFOLGREICH ABGESCHLOSSEN ###")
            return batch

        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            raise e

    def _group_transactions(self, df):
        """
        Groups transactions by user-defined filters first, 
        then by normalized description AND month/year.
        """
        user_filters = list(ImportFilter.objects.filter(user=self.user, is_active=True).select_related('category'))
        
        def apply_filters(row):
            desc = str(row['description']).upper()
            for f in user_filters:
                queries = [q.strip().upper() for q in f.search_query.split(';') if q.strip()]
                if any(q in desc for q in queries):
                    # Return (Display-Name, Category, Linked-CashFlow, Is-Income)
                    # Sign of row['amount'] is the source of truth for direction
                    return f.target_name, f.category, f.linked_cash_flow, (row['amount'] > 0)
            return _normalize_description(row['description']), None, None, (row['amount'] > 0)

        # Apply grouping key and potential category
        applied = df.apply(apply_filters, axis=1, result_type='expand')
        df['_group_key'] = applied[0]
        df['_group_category'] = applied[1]
        df['_group_linked_cf'] = applied[2]
        df['_group_is_income'] = applied[3]
        
        df['_month'] = df['date'].dt.month
        df['_year'] = df['date'].dt.year

        groups_dict = {}
        for index, row in df.iterrows():
            # Use pd.isna to handle NaN values from pandas expansion
            cat = row['_group_category'] if pd.notna(row['_group_category']) else None
            linked_cf = row['_group_linked_cf'] if pd.notna(row['_group_linked_cf']) else None
            is_income = row['_group_is_income'] if pd.notna(row['_group_is_income']) else (row['amount'] > 0)
            desc_val = str(row['_group_key']) if pd.notna(row['_group_key']) else "Unkategorisiert"
            
            # UNIQUE KEY for unassigned items to avoid pre-grouping
            if cat is None:
                # Aggregieren pro Jahr (statt pro Monat) für maximale Performance
                key = (f"RAW_{desc_val}", row['_year'], "YEARLY")
            else:
                # YEARLY AGGREGATION for categorized items
                key = (desc_val, row['_year'], "YEARLY")
                
            if key not in groups_dict:
                groups_dict[key] = {
                    'description': desc_val,
                    'base_desc': desc_val,
                    'total_amount': Decimal('0.00'),
                    'count': 0,
                    'latest_date': row['date'].date(),
                    'category': cat,
                    'is_income': is_income,
                    'linked_cash_flow': linked_cf,  # Store the plan link
                    'raw_desc': str(row['description']) # Keep raw for mapping
                }
            
            groups_dict[key]['total_amount'] += Decimal(str(row['amount']))
            groups_dict[key]['count'] += 1
            if row['date'].date() > groups_dict[key]['latest_date']:
                groups_dict[key]['latest_date'] = row['date'].date()

        groups = []
        for key, data in groups_dict.items():
            display_desc = f"{data['description']} ({data['count']} Buchungen)" if data['count'] > 1 else data['description']
            data['description'] = display_desc
            groups.append(data)

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
