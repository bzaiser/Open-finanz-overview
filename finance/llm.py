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

import time
import random

def simple_keyword_classify(description, categories):
    """
    Local keyword-based fallback that intelligently matches against
    the user's existing category list.
    """
    desc = str(description).lower()
    
    # Map keywords to intended category-related search terms
    keyword_map = {
        'miete': ['miete', 'wohnen', 'housing'],
        'gehalt': ['einkommen', 'gehalt', 'lohn', 'income'],
        'lohn': ['einkommen', 'gehalt', 'lohn', 'income'],
        'edeka': ['lebensmittel', 'groceries', 'einkauf'],
        'rewe': ['lebensmittel', 'groceries', 'einkauf'],
        'aldi': ['lebensmittel', 'groceries', 'einkauf'],
        'lidl': ['lebensmittel', 'groceries', 'einkauf'],
        'penny': ['lebensmittel', 'groceries', 'einkauf'],
        'netto': ['lebensmittel', 'groceries', 'einkauf'],
        'amazon': ['shopping', 'einkauf'],
        'paypal': ['shopping', 'einkauf'],
        'netflix': ['freizeit', 'entertainment', 'abo'],
        'spotify': ['freizeit', 'entertainment', 'abo'],
        'apple': ['services', 'it', 'software'],
        'google': ['services', 'it', 'software'],
        'versicherung': ['versicherung', 'insurance'],
        'tankstelle': ['verkehr', 'tanken', 'transport', 'auto'],
        'aral': ['verkehr', 'tanken', 'transport', 'auto'],
        'shell': ['verkehr', 'tanken', 'transport', 'auto'],
        'db bahn': ['verkehr', 'bahn', 'transport'],
    }

    # Helper to find a matching category slug from user's list
    def find_best_slug(search_terms):
        for term in search_terms:
            for cat in categories:
                if term in cat['slug'].lower() or term in cat['name'].lower():
                    return cat['slug']
        return "uncategorized"

    for key, search_terms in keyword_map.items():
        if key in desc:
            matching_slug = find_best_slug(search_terms)
            return {
                "category_slug": matching_slug,
                "is_income": 'gehalt' in desc or 'lohn' in desc,
                "is_recurring": True,
                "frequency": "monthly",
                "reasoning": f"Lokale intelligente Erkennung für: {key.capitalize()}"
            }
    return None

def classify_with_groq(transactions, categories):
    """
    Experimental fallback using the Groq API with Retry Logic.
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
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Du bist ein präziser Finanz-Experte, der nur JSON antwortet."},
            {"role": "user", "content": f"Kategorisiere diese Transaktionen (Kategorien: {category_list}): {json.dumps(transactions)}"}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    # Retry Loop (3 attempts)
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code == 429: # Rate Limit
                wait_time = (attempt + 1) * 2
                logger.warning(f"Groq Rate Limit (429). Warte {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content']
            result_data = json.loads(text)
            
            if isinstance(result_data, dict):
                for key, val in result_data.items():
                    if isinstance(val, list):
                        result_data = val
                        break
            
            return {str(item['id']): item for item in result_data}, None
        except Exception as e:
            if attempt == 2:
                return None, f"Groq Fehler nach 3 Versuchen: {str(e)}"
            time.sleep(1)
            
    return None, "Groq fehlgeschlagen."


def classify_with_ollama(transactions, categories):
    """
    Ollama-Integration für lokale Kategorisierung.
    """
    if not settings.OLLAMA_BASE_URL:
        return None, "Ollama URL nicht konfiguriert."

    category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    
    prompt = (
        f"Du bist ein präziser Finanz-Experte. Kategorisiere diese Bankbuchungen und antworte NUR im JSON-Format. "
        f"Mögliche Kategorien (mit Slugs): {category_list}\n\n"
        f"Transaktionen: {json.dumps(transactions)}\n\n"
        f"Antworte mit einem JSON-Array von Objekten, jedes mit: id, category_slug, is_income (boolean), is_recurring (boolean), frequency (monthly/yearly/once), reasoning (kurz)."
    )
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        # Erhöhter Timeout für lokale LLMs auf NAS/Docker
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        text = data.get('response', '')
        
        # Bereinigen von potentiellem Markdown-Output falls 'format':'json' ignoriert wurde
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        
        result_data = json.loads(text)
        
        # Normalisierung des Outputs (Liste von Objekten erwartet)
        if isinstance(result_data, list):
            return {str(item['id']): item for item in result_data}, None
        elif isinstance(result_data, dict):
             # Falls die KI die Liste in ein Feld wie 'transactions' packt
             if 'transactions' in result_data:
                 return {str(item['id']): item for item in result_data['transactions']}, None
             # Falls das oberste Level direkt die IDs sind
             return {str(k): v for k, v in result_data.items() if isinstance(v, dict)}, None
        
        return None, "Ollama lieferte kein gültiges JSON-Array."
    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        return None, str(e)


def classify_transactions(transactions, categories):
    """
    Zentrale Einstiegsfunktion für die Kategorisierung.
    Wählt den Provider basierend auf der Einstellung 'LLM_PROVIDER'.
    """
    provider = getattr(settings, 'LLM_PROVIDER', 'hybrid').lower()
    final_results = {}
    remaining_transactions = []
    
    # 0. Lokaler Keyword-Check (Spart Ressourcen & Kosten)
    for t in transactions:
        local_match = simple_keyword_classify(t['description'], categories)
        if local_match:
            final_results[str(t['id'])] = local_match
        else:
            remaining_transactions.append(t)
            
    if not remaining_transactions:
        return final_results, "KI-Status: 100% lokal (Keywords) erkannt."

    # 1. Ollama (Lokal)
    if provider == 'ollama':
        results, error = classify_with_ollama(remaining_transactions, categories)
        if results:
            final_results.update(results)
            return final_results, f"KI aktiv via Ollama ({settings.OLLAMA_MODEL})."
        logger.warning(f"Ollama fehlgeschlagen, Fallback auf Hybrid: {error}")

    # 2. Groq (API - Llama 3)
    if provider == 'groq' or (provider == 'hybrid' and getattr(settings, 'GROQ_API_KEY', None)):
        results, error = classify_with_groq(remaining_transactions, categories)
        if results:
            final_results.update(results)
            if provider == 'groq':
                return final_results, "KI aktiv via Groq (Llama-3)."
            # Für Hybrid: Update remaining für Gemini
            remaining_transactions = [t for t in remaining_transactions if str(t['id']) not in final_results]
            if not remaining_transactions:
                return final_results, "KI aktiv via Groq."

    # 3. Gemini (API - Google)
    if provider == 'gemini' or (provider == 'hybrid' and getattr(settings, 'GEMINI_API_KEY', None)):
        model = get_gemini_client()
        if model:
            try:
                category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
                prompt = (
                    f"Kategorisiere bitte diese Bankbuchungen als JSON (Kategorien: {category_list}): "
                    f"{json.dumps(remaining_transactions)}"
                )
                time.sleep(0.5) # Anti-Rate-Limit
                response = model.generate_content(prompt)
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                data = json.loads(text)
                ai_data = {str(item['id']): item for item in data}
                final_results.update(ai_data)
                return final_results, "KI aktiv via Gemini (Google)."
            except Exception as e:
                logger.error(f"Gemini failed: {e}")

    # 4. Finaler Fallback für nicht erkannte Zeilen
    for t in remaining_transactions:
        if str(t['id']) not in final_results:
            final_results[str(t['id'])] = {
                "category_slug": "uncategorized",
                "is_income": t['amount'] > 0,
                "is_recurring": False,
                "frequency": "monthly",
                "reasoning": "Standard-Zuweisung (KI Limit überschritten oder Fehler)"
            }
            
    return final_results, "Hybrid-Modus (Fallback aktiv)."

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
