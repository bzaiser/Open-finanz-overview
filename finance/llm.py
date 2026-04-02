import google.generativeai as genai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def get_gemini_client():
    """
    Initializes and returns the Gemini model using the stable google-generativeai SDK.
    """
    if not settings.GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # We use a fixed stable model name that is universally supported in the old SDK
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Error configuring Gemini Client: {e}")
        return None

def classify_transactions(transactions, categories):
    model = get_gemini_client()
    if not model:
        # Fallback to a very basic rule-based classification if no API key
        results = {}
        error_msg = "Gemini API Key fehlt oder ist nicht konfiguriert."
        for t in transactions:
            is_income = t['amount'] > 0
            results[str(t['id'])] = {
                "category_slug": "uncategorized",
                "is_income": is_income,
                "is_recurring": False,
                "frequency": "monthly",
                "reasoning": "Regel-basierter Fallback (kein KI-Key)"
            }
        return results, error_msg

    category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
    
    prompt = f"""
    Du bist ein Finanzassistent. Analysiere die folgenden Banktransaktionen und ordne sie Kategorien zu.
    Verfügbare Kategorien: {category_list}.
    
    Regeln:
    1. Gib für jede Transaktion den passenden 'category_slug' zurück.
    2. Entscheide, ob es sich um eine Einnahme ('is_income': true) oder Ausgabe ('is_income': false) handelt.
    3. Entscheide, ob die Buchung wahrscheinlich regelmäßig ist ('is_recurring': true), z.B. Abos, Miete, Gehalt, Versicherungen.
    4. Wenn regelmäßig, gib die Frequenz an ('frequency'): 'monthly' oder 'yearly'.
    5. Gib eine kurze Begründung für deine Wahl an ('reasoning'), z.B. "Erkannt als monatliches Abo", "Regelmäßige Mietzahlung", "Einmalige Ausgabe".
    
    Transaktionen:
    {json.dumps(transactions, indent=2)}
    
    Antworte AUSSCHLIESSLICH mit einer validen JSON-Liste von Objekten im Format:
    [
      {{
        "id": "123",
        "category_slug": "slug",
        "is_income": false,
        "is_recurring": true,  // True bei echten Abos/Verträgen, False bei Einkäufen
        "frequency": "monthly",
        "reasoning": "Kurze Begründung hier (z.B. 'Zusammengefasste Einkäufe')"
      }}
    ]
    
    Hinweis: Wenn eine Transaktion den Zusatz '(x Buchungen)' hat, wurde sie bereits monatlich zusammengefasst. 
    Wähle 'is_recurring': true nur, wenn es sich um einen festen Vertrag/Abo handelt, nicht bei normalen Einkäufen.
    """
    
    try:
        # Use generation_config for stable JSON-like output if possible, 
        # but the parser handles markdown too.
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Robust extraction
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(text)
        # Ensure IDs are strings for reliable mapping
        return {str(item['id']): item for item in data}, None
    except Exception as e:
        error_msg = f"Gemini Fehler (Legacy SDK): {str(e)}"
        logger.error(error_msg)
        return {}, error_msg

def get_pension_forecast():
    model = get_gemini_client()
    if not model:
        return {
            "text": "Laut aktuellen Prognosen wird für 2026 eine Rentenanpassung von ca. 3,5% erwartet.",
            "value": 3.5,
            "source": "Mock (No API Key)"
        }
    
    try:
        prompt = "Nenne mir die aktuelle Prognose für die Rentenanpassung 2026 laut dem jüngsten Rentenversicherungsbericht des BMAS. Antworte kurz und gib nur die Prozentzahl am Ende an."
        response = model.generate_content(prompt)
        return {"text": response.text.strip(), "value": 3.5, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}

def get_inflation_forecast():
    model = get_gemini_client()
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
