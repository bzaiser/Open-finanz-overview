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


def classify_transactions(transactions, categories):
    """
    Main entry point for transaction classification.
    Hybrid approach: Keyword Fallback -> Groq -> Gemini.
    """
    final_results = {}
    remaining_transactions = []
    
    # 1. Local Keyword Pre-Check (Saves API costs & prevents Rate Limits)
    for t in transactions:
        local_match = simple_keyword_classify(t['description'], categories)
        if local_match:
            final_results[str(t['id'])] = local_match
        else:
            remaining_transactions.append(t)
            
    if not remaining_transactions:
        return final_results, "KI-Status: 100% lokal erkannt."

    # 2. Try Groq for the rest
    if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
        results, error = classify_with_groq(remaining_transactions, categories)
        if results:
            final_results.update(results)
            return final_results, "KI aktiv via Groq (Llama-3)."
    
    # 3. Try Gemini for the rest
    model = get_gemini_client()
    if model:
        try:
            category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
            prompt = f"Kategorisiere bitte diese Bankbuchungen als JSON (Kategorien: {category_list}): {json.dumps(remaining_transactions)}"
            # Tiny sleep to avoid Gemini rate limits too
            time.sleep(1)
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
    
    # 4. Final Rule-based Fallback for anything left
    for t in remaining_transactions:
        if str(t['id']) not in final_results:
            final_results[str(t['id'])] = {
                "category_slug": "uncategorized",
                "is_income": t['amount'] > 0,
                "is_recurring": False,
                "frequency": "monthly",
                "reasoning": "Standard-Zuweisung (KI Limit überschritten)"
            }
            
    return final_results, "Limit erreicht (Hybrid Modus)."

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
