import os
import requests

# Pfad zur .env Datei (relativ zum Skript im Hauptverzeichnis)
dotenv_path = './.env'

def load_env_manual(path):
    env_vars = {}
    if not os.path.exists(path):
        print(f"DEBUG: .env Datei nicht gefunden unter: {os.path.abspath(path)}")
        return env_vars
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

env = load_env_manual(dotenv_path)
api_key = env.get('GROQ_API_KEY')

print(f"--- Groq API Test (Server/Local) ---")
if not api_key:
    print(f"FEHLER: GROQ_API_KEY wurde in {os.path.abspath(dotenv_path)} nicht gefunden!")
    exit(1)

print(f"Key gefunden: {api_key[:4]}...{api_key[-4:] if len(api_key)>8 else ''}")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama3-8b-8192",
    "messages": [
        {"role": "user", "content": "Hallo Groq, bist du online? Antworte kurz mit JA."}
    ]
}

try:
    print("Sende Test-Anfrage...")
    response = requests.post(url, headers=headers, json=data, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("ERFOLG! Groq hat geantwortet.")
        print("Antwort:", response.json()['choices'][0]['message']['content'])
    else:
        print("FEHLER von Groq:")
        print(response.text)
except Exception as e:
    print(f"Netzwerk-Fehler: {e}")
