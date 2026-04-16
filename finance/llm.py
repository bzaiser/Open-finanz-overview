from google import genai
from django.conf import settings
import json
import logging
import requests
from .utils import safe_float

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
        'netflix': ['freizeit', 'entertainment', 'abo', 'streaming'],
        'spotify': ['freizeit', 'entertainment', 'abo', 'streaming'],
        'apple': ['services', 'it', 'software', 'electronics'],
        'google': ['services', 'it', 'software', 'electronics'],
        'versicherung': ['versicherung', 'insurance'],
        'allianz': ['versicherung', 'insurance'],
        'huk24': ['versicherung', 'insurance'],
        'huk-coburg': ['versicherung', 'insurance'],
        'ergo': ['versicherung', 'insurance'],
        'debeka': ['versicherung', 'insurance'],
        'tankstelle': ['verkehr', 'tanken', 'transport', 'auto'],
        'aral': ['verkehr', 'tanken', 'transport', 'auto'],
        'shell': ['verkehr', 'tanken', 'transport', 'auto'],
        'esso': ['verkehr', 'tanken', 'transport', 'auto'],
        'db bahn': ['verkehr', 'bahn', 'transport'],
        'airline': ['reisen', 'travel', 'hobby', 'urlaub'],
        'airlines': ['reisen', 'travel', 'hobby', 'urlaub'],
        'lufthansa': ['reisen', 'travel', 'hobby', 'urlaub'],
        'aegean': ['reisen', 'travel', 'hobby', 'urlaub'],
        'booking.com': ['reisen', 'travel', 'hobby', 'urlaub'],
        'airbnb': ['reisen', 'travel', 'hobby', 'urlaub'],
        'zug': ['verkehr', 'bahn', 'transport'],
    }

    # Helper to find a matching category slug from user's list
    def find_best_slug(search_terms):
        for term in search_terms:
            term_lower = term.lower()
            for cat in categories:
                # Search in slug AND name
                cat_slug = cat.get('slug', '').lower()
                cat_name = cat.get('name', '').lower()
                if term_lower in cat_slug or term_lower in cat_name:
                    return cat['slug']
        return None  # Fallback to LLM

    import re
    for key, search_terms in keyword_map.items():
        pattern = rf"\b{re.escape(key)}\b"
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            matched_substring = match.group(0)
            matching_slug = find_best_slug(search_terms)
            
            # ONLY return if we actually matched a real category slug
            if matching_slug and matching_slug != "uncategorized":
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
            
            return {str(item['id']): {
                'category_slug': item.get('category_slug'),
                'reasoning': item.get('reasoning'),
                'confidence': safe_float(item.get('confidence', 0.8), 0.8)
            } for item in result_data}, None
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
    
    system_prompt = (
        "Du bist ein präziser Finanz-Experte für private Buchhaltung. "
        "Deine Aufgabe ist es, Bank-Transaktionen in vorgegebene Kategorien einzuordnen. "
        "Regeln: "
        "1. Nutze NUR die bereitgestellten Slugs. "
        "2. Wenn du nicht sicher bist, antworte mit 'uncategorized'. "
        "3. Flüge, Airlines (z.B. Aegean, Lufthansa) und Hotels gehören IMMER zu Reisen/Hobby/Urlaub, NIEMALS zu Renten. "
        "4. 'Beiträge' (Fees) sind meist Versicherungen, Vereine oder Gebühren, KEINE Rentenzahlungen. "
        "5. Analysiere den Händler-Namen genau. Airlines sind Reisekosten. "
        "6. Antworte AUSSCHLIESSLICH als JSON-Array von Objekten."
    )
    
    user_prompt = (
        f"Kategorien (Nutze nur diese Slugs): {category_list}\n\n"
        "Beispiele:\n"
        "- 'EDEKA MARKT': category_slug='lebensmittel', reasoning='Supermarkt'\n"
        "- 'AEGEAN AIRLINES': category_slug='reisen' (oder passend), reasoning='Fluggesellschaft'\n"
        "- 'ALLIANZ': category_slug='versicherung', reasoning='Versicherungsdienstleister'\n\n"
        "Verwende für Reasoning maximal 15 Wörter.\n"
        "Gib id, category_slug, confidence (0.00 bis 1.00) und reasoning für jedes Item zurück.\n"
        "Confidence sollte hoch sein (0.9+) wenn der Händler eindeutig ist, und niedrig (<0.6) wenn du raten musst.\n"
        "WICHTIG: Antworte NUR mit dem JSON-Objekt, absolut kein Text davor oder danach.\n"
        f"Verfügbare Kategorien: {json.dumps(categories)}\n"
        f"Transaktionen: {json.dumps(transactions)}\n"
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
        
        # Bereinigen: Falls die KI doch mal plaudert ("Categories: ...")
        # Wir suchen den Anfang [ und das Ende ] des JSON-Arrays
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx + 1]
        elif "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        
        try:
            result_data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error für: {text}")
            return None, f"JSON Analyse fehlgeschlagen: {e}"
        
        # Normalisierung des Outputs (Liste von Objekten erwartet)
        if isinstance(result_data, list):
            return {str(item['id']): {
                'category_slug': item.get('category_slug'),
                'reasoning': item.get('reasoning'),
                'confidence': safe_float(item.get('confidence', 0.8), 0.8)
            } for item in result_data}, None
        elif isinstance(result_data, dict):
             # Falls die KI die Liste in ein Feld wie 'transactions' packt
             if 'transactions' in result_data:
                 return {str(item['id']): {
                    'category_slug': item.get('category_slug'),
                    'reasoning': item.get('reasoning'),
                    'confidence': safe_float(item.get('confidence', 0.8), 0.8)
                } for item in result_data['transactions']}, None
             # Falls das oberste Level direkt die IDs sind
             return {str(k): {
                'category_slug': v.get('category_slug'),
                'reasoning': v.get('reasoning'),
                'confidence': safe_float(v.get('confidence', 0.8), 0.8)
            } for k, v in result_data.items() if isinstance(v, dict)}, None
        
        return None, "Ollama lieferte kein gültiges JSON-Array."
    except requests.exceptions.Timeout:
        return None, "Ollama Timeout (Server braucht zu lange). Erhöhe ggf. den Timeout."
    except requests.exceptions.ConnectionError:
        return None, f"Verbindung zu Ollama unter {url} fehlgeschlagen. Ist die IP korrekt und die Firewall offen?"
    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        return None, f"Ollama Fehler: {str(e) or type(e).__name__}"


def clean_description(text):
    """
    Remove dates, transaction IDs, TANs, and other noise from bank description.
    """
    if not text:
        return ""
    import re
    # Remove dates (DD.MM.YYYY, DD.MM.YY, DD.MM)
    text = re.sub(r'\d{1,2}\.\d{1,2}\.(\d{4}|\d{2})?', '', text)
    # Remove TANs (6 digits)
    text = re.sub(r'TAN \d{6}', '', text)
    # Remove long ID strings (8+ chars of hex/digits)
    text = re.sub(r'[A-Z0-9]{8,}', '', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def classify_transactions(transactions, categories, provider=None, progress_callback=None, is_cancelled_callback=None):
    """
    Kategorisiert eine Liste von Transaktionen.
    Verwendet Batching (Chunking), um Timeouts zu verhindern.
    """
    final_results = {}
    remaining_all = []
    events = []
    
    # 0. Lokaler Keyword-Check
    for t in transactions:
        cleaned_desc = clean_description(t['description'])
        local_match = simple_keyword_classify(cleaned_desc, categories)
        if local_match:
            local_match['confidence'] = 1.0 # Lokale Keywords sind 100% sicher
            final_results[str(t['id'])] = local_match
        else:
            t['description'] = cleaned_desc # Send clean text to LLM
            remaining_all.append(t)
            
    if not remaining_all:
        return final_results, "KI-Status: 100% lokal erkannt.", events

    # 1. Parallel Batch Processing (Parallel Turbo v4)
    from concurrent.futures import ThreadPoolExecutor
    import time
    
    chunk_size = 40
    total_transactions = len(remaining_all)
    chunks = [remaining_all[i:i + chunk_size] for i in range(0, total_transactions, chunk_size)]
    total_chunks = len(chunks)
    
    events.append(f"Parallel-KI startet. {total_transactions} Gruppen in {total_chunks} Paketen...")
    
    finished_count = 0
    from threading import Lock
    progress_lock = Lock()

    def process_chunk(chunk_data):
        nonlocal finished_count
        
        # Cancel check (rough check inside thread)
        if is_cancelled_callback and is_cancelled_callback():
            return None, "Cancelled"

        results, error = classify_with_ollama(chunk_data, categories)
        
        with progress_lock:
            finished_count += 1
            if progress_callback:
                progress_callback(finished_count, total_chunks)
        
        return results, error

    with ThreadPoolExecutor(max_workers=min(4, total_chunks)) as executor:
        futures = [executor.submit(process_chunk, c) for c in chunks]
        
        for idx, future in enumerate(futures):
            chunk_results, error = future.result()
            current_block = idx + 1
            
            if error:
                if error == "Cancelled":
                    events.append(f"Paket {current_block} ABGEBROCHEN.")
                else:
                    logger.error(f"Error in Paket {current_block}: {error}")
                    events.append(f"LOG: Fehler in Paket {current_block}")
                    # Fallback for this chunk
                    for t in chunks[idx]:
                        final_results[str(t['id'])] = {"category_slug": "uncategorized"}
            elif chunk_results:
                final_results.update(chunk_results)
                events.append(f"Paket {current_block}/{total_chunks} fertig.")

    return final_results, f"Parallel-KI fertig ({len(final_results)} Gruppen).", events

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
