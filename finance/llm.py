from google import genai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        return None
    try:
        return genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={'api_version': 'v1'}
        )
    except Exception as e:
        logger.error(f"Error configuring Gemini Client: {e}")
        return None

def classify_transactions(transactions, categories):
    client = get_gemini_client()
    if not client:
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

    # Discovery: Let's see what models this API Key can actually use
    available_models = []
    try:
        for m in client.models.list():
            if 'generateContent' in m.supported_methods:
                available_models.append(m.name.replace('models/', ''))
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        # Optional fallback to defaults if discovery fails

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
        "is_recurring": true,
        "frequency": "monthly",
        "reasoning": "Kurze Begründung hier"
      }}
    ]
    """

    # Try found models, prioritizing the flash versions
    models_to_try = [m for m in available_models if 'flash' in m] + \
                     [m for m in available_models if 'flash' not in m]
    
    # Absolute fallback if list failed
    if not models_to_try:
        models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
    
    last_error = ""
    for model_name in models_to_try[:5]: # Try top 5
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(text)
            return {str(item['id']): item for item in data}, f"KI aktiv via {model_name}. Verfügbare Modelle: {', '.join(available_models[:10])}"
        except Exception as e:
            last_error = f"{model_name}: {str(e)}"
            continue # Try next model
            
    return {}, f"Alle entdeckten KI-Modelle ({', '.join(available_models[:5])}) fehlgeschlagen. Letzter Fehler: {last_error}"

def get_pension_forecast():
    client = get_gemini_client()
    if not client:
        return {
            "text": "Laut aktuellen Prognosen wird für 2026 eine Rentenanpassung von ca. 3,5% erwartet.",
            "value": 3.5,
            "source": "Mock (No API Key)"
        }
    
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
    prompt = "Nenne mir die aktuelle Prognose für die Rentenanpassung 2026 laut dem jüngsten Rentenversicherungsbericht des BMAS. Antworte kurz und gib nur die Prozentzahl am Ende an."
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            text = response.text.strip()
            return {"text": text, "value": 3.5, "source": f"Gemini ({model_name})"}
        except:
            continue
            
    return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}

def get_inflation_forecast():
    client = get_gemini_client()
    if not client:
        return {
            "text": "Die Inflationsrate für das aktuelle Jahr wird auf etwa 2,2% geschätzt.",
            "value": 2.2,
            "source": "Mock (No API Key)"
        }
    
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
    prompt = "Wie hoch schätzt das Statistische Bundesamt die Inflationsrate für das aktuelle Jahr? Antworte kurz."
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return {"text": response.text.strip(), "value": 2.2, "source": f"Gemini ({model_name})"}
        except:
            continue
            
    return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}
