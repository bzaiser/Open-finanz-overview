import pandas as pd
import datetime
from decimal import Decimal
from django.utils import timezone
from .models import Category, ImportBatch, PendingTransaction
from .llm import classify_transactions
import logging

logger = logging.getLogger(__name__)

class ExcelParserService:
    def __init__(self, user, file_path, filename):
        self.user = user
        self.file_path = file_path
        self.filename = filename

    def parse_and_categorize(self):
        try:
            # 1. Read Excel
            df = pd.read_excel(self.file_path)
            
            # Simple column detection
            col_map = self._detect_columns(df)
            if not col_map:
                raise ValueError("Could not detect necessary columns (Date, Description, Amount)")

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
            
            # 2. Pattern Recognition (Frequency)
            # Group by description to see if it repeats
            # We'll do this later if needed, for now let AI handle "Likely Recurring"
            
            # 3. Prepare for AI
            batch = ImportBatch.objects.create(user=self.user, filename=self.filename)
            
            categories = list(Category.objects.values('name', 'slug'))
            
            transactions_for_ai = []
            for idx, row in df.iterrows():
                transactions_for_ai.append({
                    "id": int(idx),
                    "date": row['date'].strftime('%Y-%m-%d'),
                    "description": str(row['description']),
                    "amount": float(row['amount'])
                })

            # AI Categorization (Process in chunks if many)
            ai_results = {}
            for i in range(0, len(transactions_for_ai), 20):
                chunk = transactions_for_ai[i:i+20]
                results = classify_transactions(chunk, categories)
                ai_results.update(results)
            
            # 4. Save to PendingTransaction
            pending_list = []
            for idx, row in df.iterrows():
                res = ai_results.get(int(idx), {})
                cat_slug = res.get('category_slug', 'uncategorized')
                category = Category.objects.filter(slug=cat_slug).first()
                
                pending = PendingTransaction(
                    batch=batch,
                    date=row['date'].date(),
                    description=row['description'],
                    amount=row['amount'],
                    is_income=res.get('is_income', row['amount'] > 0),
                    category=category,
                    is_recurring=res.get('is_recurring', False),
                    frequency=res.get('frequency', 'monthly')
                )
                pending_list.append(pending)
            
            PendingTransaction.objects.bulk_create(pending_list)
            return batch

        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            raise e

    def _detect_columns(self, df):
        """
        Heuristic to find date, description, and amount columns.
        """
        cols = df.columns
        mapping = {}
        
        # Date detection
        for c in cols:
            if any(x in str(c).lower() for x in ['datum', 'date', 'buchungstag', 'valuta']):
                mapping['date'] = c
                break
        
        # Description detection
        for c in cols:
            if any(x in str(c).lower() for x in ['zweck', 'beschreibung', 'text', 'info', 'verwendungszweck']):
                mapping['desc'] = c
                break
                
        # Amount detection
        for c in cols:
            if any(x in str(c).lower() for x in ['betrag', 'amount', 'wert', 'summe']):
                # Secondary check: is it numeric?
                if pd.to_numeric(df[c], errors='coerce').notnull().any():
                    mapping['amount'] = c
                    break
        
        if len(mapping) < 3:
            # Fallback based on column index: 0=Date?, 1=Desc?, 2=Amount?
            # Many banks have different orders, so this is risky.
            return None
            
        return mapping
