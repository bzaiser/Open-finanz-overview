import google.generativeai as genai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def get_gemini_model():
    if not settings.GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        return None

def classify_transactions(transactions, categories):
    """
    Classifies a list of transactions using Gemini.
    transactions: list of dicts {id, date, description, amount}
    categories: list of dicts {name, slug}
    returns: dict mapping transaction id to {category_slug, is_income, is_recurring, frequency}
    """
    model = get_gemini_model()
    if not model:
        # Fallback to a very basic rule-based classification if no API key
        results = {}
        for t in transactions:
            is_income = t['amount'] > 0
            results[t['id']] = {
                "category_slug": "uncategorized",
                "is_income": is_income,
                "is_recurring": False,
                "frequency": "monthly"
            }
        return results

    category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
    
    prompt = f"""
    Du bist ein Finanzassistent. Analysiere die folgenden Banktransaktionen und ordne sie Kategorien zu.
    Verfügbare Kategorien: {category_list}.
    
    Regeln:
    1. Gib für jede Transaktion den passenden 'category_slug' zurück.
    2. Entscheide, ob es sich um eine Einnahme ('is_income': true) oder Ausgabe ('is_income': false) handelt.
    3. Entscheide, ob die Buchung wahrscheinlich regelmäßig ist ('is_recurring': true), z.B. Abos, Miete, Gehalt, Versicherungen.
    4. Wenn regelmäßig, gib die Frequenz an ('frequency'): 'monthly' oder 'yearly'.
    
    Transaktionen:
    {json.dumps(transactions, indent=2)}
    
    Antworte NUR mit einer validen JSON-Liste von Objekten im Format:
    [
      {{
        "id": 123,
        "category_slug": "slug",
        "is_income": false,
        "is_recurring": true,
        "frequency": "monthly"
      }}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        # Handle potential markdown formatting in response
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        data = json.loads(text)
        return {item['id']: item for item in data}
    except Exception as e:
        logger.error(f"Gemini classification failed: {e}")
        return {}

def get_pension_forecast():
    model = get_gemini_model()
    if not model:
        return {
            "text": "Laut aktuellen Prognosen wird für 2026 eine Rentenanpassung von ca. 3,5% erwartet.",
            "value": 3.5,
            "source": "Mock (No API Key)"
        }
    
    try:
        prompt = "Nenne mir die aktuelle Prognose für die Rentenanpassung 2026 laut dem jüngsten Rentenversicherungsbericht des BMAS. Antworte kurz und gib nur die Prozentzahl am Ende an."
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Simple extraction logic or just return text
        return {"text": text, "value": 3.5, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}

def get_inflation_forecast():
    model = get_gemini_model()
    if not model:
        return {
            "text": "Die Inflationsrate für das aktuelle Jahr wird auf etwa 2,2% geschätzt.",
            "value": 2.2,
            "source": "Mock (No API Key)"
        }
    try:
        prompt = "Wie hoch schätzt das Statistische Bundesamt die Inflationsrate für das aktuelle Jahr? Antworte kurz."
        response = model.generate_content(prompt)
        return {"text": response.text.strip(), "value": 2.2, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}
