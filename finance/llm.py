import google.generativeai as genai
from django.conf import settings
import json
import logging
import requests

logger = logging.getLogger(__name__)

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        return None

def classify_with_groq(transactions, categories):
    """
    Experimental fallback using the Groq API (fast, free, OpenAI-compatible).
    Model: llama-3.3-70b-versatile
    """
    if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
        return None, "Groq API Key nicht konfiguriert."
    
    category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Du bist ein Finanzassistent. Analysiere die folgenden Banktransaktionen und ordne sie Kategorien zu.
    Verfügbare Kategorien: {category_list}.
    
    Du MUSST als valide JSON-Liste antworten:
    [
      {{
        "id": "original_id",
        "category_slug": "slug",
        "is_income": false,
        "is_recurring": true,
        "frequency": "monthly",
        "reasoning": "Kurze Begründung"
      }}
    ]

    Transaktionen:
    {json.dumps(transactions, indent=2)}
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Du bist ein präziser Finanz-Experte, der nur JSON antwortet."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        text = data['choices'][0]['message']['content']
        
        # Parse JSON from content
        result_data = json.loads(text)
        # Groq might return a wrapper object {"transactions": [...]} or just the list
        if isinstance(result_data, dict):
            # Try to find the list inside
            for key, val in result_data.items():
                if isinstance(val, list):
                    result_data = val
                    break
        
        return {str(item['id']): item for item in result_data}, None
    except Exception as e:
        return None, f"Groq Fehler: {str(e)}"


def classify_transactions(transactions, categories):
    """
    Main entry point for transaction classification.
    Favors Groq if GROQ_API_KEY is present (more reliable for 404 avoidance).
    Falls back to Gemini.
    """
    # 1. Try Groq if available
    if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
        results, error = classify_with_groq(transactions, categories)
        if results:
            return results, "KI aktiv via Groq (Llama-3)."
        logger.warning(f"Groq failed, trying Gemini: {error}")

    # 2. Try Gemini
    model = get_gemini_client()
    if model:
        try:
            category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
            prompt = f"Analysiere diese Transaktionen: {json.dumps(transactions)}. Kategorien: {category_list}. Regelsatz: JSON format like [{{'id': '...', 'category_slug': '...', 'reasoning': '...'}}]"
            response = model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)
            return {str(item['id']): item for item in data}, "KI aktiv via Gemini (Google)."
        except Exception as e:
            logger.error(f"Gemini fallback failed: {e}")
    
    # 3. Rule-based Fallback
    results = {}
    for t in transactions:
        is_income = t['amount'] > 0
        results[str(t['id'])] = {
            "category_slug": "uncategorized",
            "is_income": is_income,
            "is_recurring": False,
            "frequency": "monthly",
            "reasoning": "Regel-basierter Fallback (alle KIs fehlgeschlagen)"
        }
    return results, "Alle KI-Modelle fehlgeschlagen or No Keys found."

def get_pension_forecast():
    # Use Gemini for general knowledge (better than small Llama sometimes)
    model = get_gemini_client()
    if not model:
        return {"text": "Keine KI aktiv für Renten-Prognose.", "value": 3.5, "source": "Cache"}
    try:
        response = model.generate_content("Rentenanpassung 2026 Prognose kurz.")
        return {"text": response.text.strip(), "value": 3.5, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}

def get_inflation_forecast():
    model = get_gemini_client()
    if not model:
        return {"text": "Keine KI aktiv für Inflation.", "value": 2.2, "source": "Cache"}
    try:
        response = model.generate_content("Inflationsrate Deutschland 2025/2026 Prognose kurz.")
        return {"text": response.text.strip(), "value": 2.2, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}
