from google import genai
from django.conf import settings
import json
import logging
import requests

logger = logging.getLogger(__name__)

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        return None
    try:
        return genai.Client(api_key=settings.GEMINI_API_KEY)
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

    import re
    for key, search_terms in keyword_map.items():
        # Match only full words to avoid false positives (e.g. 'Apple' matching in 'Kapple')
        pattern = rf"\b{re.escape(key)}\b"
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            matched_substring = match.group(0)
            matching_slug = find_best_slug(search_terms)
            return {
                "category_slug": matching_slug,
                "is_income": 'gehalt' in desc or 'lohn' in desc,
                "is_recurring": True,
                "frequency": "monthly",
                "reasoning": f"Stichwort-Treffer '{matched_substring}' in Buchung gefunden"
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
                
            if response.status_code == 401:
                key_preview = settings.GROQ_API_KEY[:4] + "..." if settings.GROQ_API_KEY else "KEIN_KEY"
                logger.error(f"Groq 401 Unauthorized! Key-Vorschau: {key_preview}. Prüfen Sie Ihren Key in der .env.")

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
                key_preview = settings.GROQ_API_KEY[:4] + "..." if settings.GROQ_API_KEY else "KEIN_KEY"
                return None, f"Groq Fehler (401/Auth). Key-Vorschau: {key_preview}. Details: {str(e)}"
            time.sleep(1)
            
    return None, "Groq fehlgeschlagen (Unbekannt)."


def classify_with_ollama(transactions, categories):
    """
    Ollama-Integration für lokale Kategorisierung via /api/chat (moderner & stabiler).
    """
    if not settings.OLLAMA_BASE_URL:
        return None, "Ollama URL nicht konfiguriert."

    category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    
    system_prompt = "Du bist ein präziser Finanz-Experte. Antworte AUSSCHLIESSLICH als JSON-Array von Objekten."
    user_prompt = (
        f"Kategorien: {category_list}\n"
        f"Buchungen: {json.dumps(transactions)}\n"
        f"JSON-Felder pro Objekt: id (string), category_slug, is_income (bool), is_recurring (bool)."
    )
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "format": "json"
    }

    try:
        # Erhöhter Timeout für lokale LLMs auf NAS/Docker
        logger.info(f"Ollama Request an {url} (Modell: {settings.OLLAMA_MODEL})")
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code != 200:
            error_data = response.text
            logger.error(f"Ollama Error {response.status_code}: {error_data}")
            if response.status_code == 404:
                return None, f"Ollama Endpunkt oder Modell '{settings.OLLAMA_MODEL}' nicht gefunden (404). Bitte 'ollama pull {settings.OLLAMA_MODEL}' ausführen."
            return None, f"Ollama Server Fehler {response.status_code}: {error_data}"

        data = response.json()
        # Bei /api/chat kommt die Antwort in data['message']['content']
        text = data.get('message', {}).get('content', '')
        
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
    except requests.exceptions.Timeout:
        return None, "Ollama Timeout (Server braucht zu lange). Erhöhe ggf. den Timeout."
    except requests.exceptions.ConnectionError:
        return None, f"Verbindung zu Ollama unter {url} fehlgeschlagen. Ist die IP korrekt und die Firewall offen?"
    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        return None, f"Ollama Fehler: {str(e) or type(e).__name__}"


def classify_transactions(transactions, categories, progress_callback=None, is_cancelled_callback=None):
    """
    Kategorisiert eine Liste von Transaktionen.
    Verwendet Batching (Chunking), um Timeouts bei großen Importen zu verhindern.
    
    progress_callback(current, total) -> Fortschritts-Update
    is_cancelled_callback() -> True, wenn abgebrochen werden soll
    """
    provider = getattr(settings, 'LLM_PROVIDER', 'hybrid').lower()
    final_results = {}
    remaining_all = []
    events = []
    
    # 0. Lokaler Keyword-Check (Sofort-Ergebnisse ohne KI)
    for t in transactions:
        local_match = simple_keyword_classify(t['description'], categories)
        if local_match:
            final_results[str(t['id'])] = local_match
        else:
            remaining_all.append(t)
            
    if not remaining_all:
        return final_results, "KI-Status: 100% lokal (Keywords) erkannt.", events

    # 1. Batching Logic (Chunking)
    # Wir nutzen kleinere Häppchen (10 statt 25), damit Ollama auf Windows schneller antwortet.
    chunk_size = 10 
    total_transactions = len(remaining_all)
    total_chunks = (total_transactions + chunk_size - 1) // chunk_size
    
    self_results = {}
    
    for i in range(0, total_transactions, chunk_size):
        # Abbruch-Check
        if is_cancelled_callback and is_cancelled_callback():
            logger.info("KI-Analyse vom Benutzer abgebrochen.")
            break

        chunk = remaining_all[i:i + chunk_size]
        current_block = (i // chunk_size) + 1
        
        block_msg = f"KI-Analyse: Paket {current_block}/{total_chunks} ({len(chunk)} Zeilen)..."
        logger.info(block_msg)
        events.append(block_msg)
        
        # Provider Dispatching pro Block
        block_results = {}
        error = None

        # A. Ollama (Strikt lokal)
        if provider == 'ollama':
            results, err = classify_with_ollama(chunk, categories)
            if results:
                block_results.update(results)
            else:
                error = err

        # B. Groq (Hybrid / Cloud)
        elif provider == 'groq' or (provider == 'hybrid' and getattr(settings, 'GROQ_API_KEY', None)):
            results, err = classify_with_groq(chunk, categories)
            if results:
                block_results.update(results)
            else:
                error = err
                
        # C. Gemini (Hybrid / Cloud Fallback)
        if not block_results and (provider == 'gemini' or (provider == 'hybrid' and getattr(settings, 'GEMINI_API_KEY', None))):
             try:
                category_list = ", ".join([f"{c['name']} (slug: {c['slug']})" for c in categories])
                prompt = (
                    f"Kategorisiere bitte diese Bankbuchungen als JSON (Kategorien: {category_list}): "
                    f"{json.dumps(chunk)}"
                )
                # Client holen
                client = get_gemini_client()
                if client:
                    response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    data = json.loads(text)
                    block_results = {str(item['id']): item for item in data}
             except Exception as e:
                logger.error(f"Gemini in Block {current_block} fehlgeschlagen: {e}")
                error = str(e)

        # Block-Ergebnisse konsolidieren
        if block_results:
            self_results.update(block_results)
        else:
            # Fallback für diesen spezifischen Block
            for t in chunk:
                self_results[str(t['id'])] = {
                    "category_slug": "uncategorized",
                    "is_income": t['amount'] > 0,
                    "is_recurring": False,
                    "frequency": "monthly",
                    "reasoning": f"Standard (KI Fehler in Block {current_block}): {error}"
                }
        
        # Live-Feedback über Callback (optional)
        if progress_callback:
            progress_callback(current_block, total_chunks)

    final_results.update(self_results)
    
    summary_msg = f"KI-Analyse abgeschlossen ({len(final_results)} Posten)."
    if provider == 'ollama':
        summary_msg = f"KI aktiv via Ollama ({settings.OLLAMA_MODEL})."
        
    return final_results, summary_msg, events

def get_pension_forecast():
    # Use Gemini for general knowledge (better than small Llama sometimes)
    client = get_gemini_client()
    if not client:
        return {"text": "Keine KI aktiv für Renten-Prognose.", "value": 3.5, "source": "Cache"}
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents="Rentenanpassung 2026 Prognose kurz."
        )
        return {"text": response.text.strip(), "value": 3.5, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}

def get_inflation_forecast():
    client = get_gemini_client()
    if not client:
        return {"text": "Keine KI aktiv für Inflation.", "value": 2.2, "source": "Cache"}
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents="Inflationsrate Deutschland 2025/2026 Prognose kurz."
        )
        return {"text": response.text.strip(), "value": 2.2, "source": "Gemini AI"}
    except:
        return {"text": "Fehler bei KI-Abfrage", "value": 0, "source": "Error"}
