# Finanz-Übersicht 🚀

[![Language: Multi-5](https://img.shields.io/badge/Language-Multi--5-blue)](#-internationalisierung)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with: Django](https://img.shields.io/badge/Backend-Django--6-green)](https://www.djangoproject.com/)

> [!TIP]
> **English Documentation**: You can find the English version of the documentation here: [README.md](README.md) 🇺🇸

**Das High-End Finanz-Cockpit** — Ein hochentwickeltes Werkzeug für langfristige Finanzprognosen, das dir extreme Klarheit über dein zukünftiges Nettovermögen verschafft.

---

## 🌟 Vision & Überblick

Finanzplan ist mehr als nur eine Tracking-App. Es ist eine **Simulations-Engine** für dein Leben. Es projiziert deine finanzielle Kurve über 30+ Jahre und berücksichtigt dabei Vermögenswerte, Verbindlichkeiten, wiederkehrende Cashflows und Einmalereignisse – und das alles unter strikter Berücksichtigung der inflationsbedingten Entwertung deiner Kaufkraft.

---

## ✨ Experten-Features

### 🧠 Intelligenter KI-Bank-Import (2.0)
Unser KI-gestützter Import liest nicht nur CSV-Dateien; er **versteht** sie.
- **Mustererkennung**: Bereinigt Bankbeschreibungen automatisch und sucht nach sich wiederholenden Mustern.
- **Gelerntes Gedächtnis**: Merkt sich deine früheren Kategorisierungen und wendet sie automatisch auf neue Importe an.
- **Dubletten-Fingerabdruck**: Jede Transaktion erhält einen eindeutigen Hash, um überlappende Importe zu verhindern.
- **Privacy First**: Wähle zwischen **100% lokaler KI** (Ollama) oder Hochleistungs-Cloud-Providern (Gemini, Groq).

### 📈 Präzisions-Simulations-Engine
Verstehe die Mathematik hinter deinem Vermögen.
- **Real- vs. Nominalwert**: Unterscheide zwischen dem absoluten Geld, das du hast, und seiner realen Kaufkraft.
- **Inflationspuffer**: Konfigurierbare Inflationsraten zur Visualisierung deines "echten" Nettovermögens.
- **Dynamiken & Indexierung**: Simuliere Karriereschritte mit Gehaltsdynamiken und vertraglich indexierte Rentensteigerungen.
- **Zinseszins-Logik**: Monatliche Verzinsung des Wachstums für jede einzelne Anlageklasse.

### 🎨 Design-Harmonie-System
Ein Premium-Erlebnis für Premium-Daten.
- **Mathematische Farbharmonien**: Wähle eine Primärfarbe und unsere Engine berechnet perfekt abgestimmte komplementäre oder analoge Paletten.
- **Glassmorphism UI**: High-End-Tiefeneffekte mit Backdrop-Filtern und Transparenz.
- **Night-Mode Perfektion**: Eine dedizierte Midnight-Theme-Engine für augenschonende Analysen bei Nacht.

---

## 🛠 Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Bootstrap 5, HTMX, Alpine.js, Chart.js 4
- **KI-Integration**: LangChain, Ollama, Google Gemini
- **Infrastruktur**: Docker & Docker Compose

---

## 🚀 Erste Schritte

Wir bieten zwei Wege an, dein Finanz-Cockpit zu betreiben, je nach deiner Umgebung.

### Option A: Einfacher Desktop (Windows Native)
**Ideal für**: "Normale" Nutzer unter Windows, die eine Ein-Klick-Lösung ohne Docker/WSL2 suchen.
1. **Download/Klonen**: Lade das Repository herunter.
2. **Setup**: Gehe in den Ordner `native-dist/` und starte `setup-native.bat` (nur beim ersten Mal).
3. **Start**: Klicke doppelt auf `start-dashboard.bat`.

### Option B: Server/NAS (Docker & Podman)
**Ideal für**: Fortgeschrittene Nutzer, NAS-Systeme (Synology/QNAP) oder Linux-Server.
1. **Klonen**: `git clone https://github.com/bzaiser/Open-finanz-overview.git`.
2. **Konfiguration**: `cp .env.example .env`.
3. **Start**: `./update-fast.sh` (oder `docker-compose up -d`).

---

---

## 🌍 Internationalisierung

Finanzplan ist für ein globales Publikum gebaut. Wir unterstützen:
- 🇩🇪 **Deutsch** (DE)
- 🇺🇸 **Englisch** (EN)
- 🇫🇷 **Französisch** (FR)
- 🇪🇸 **Spanisch** (ES)
- 🇮🇹 **Italienisch** (IT)

Unser System nutzt eine **Key-basierte i18n-Strategie** für maximale Stabilität, insbesondere bei speziellen Formatierungen wie Währungen und Prozenten.

---

## 🔒 Sicherheit & Datenschutz

Deine Finanzdaten sind sensibel. Deshalb ist Finanzplan so konzipiert, dass es **komplett selbst gehostet** werden kann. Keine Daten verlassen jemals deine Kontrolle, es sei denn, du entscheidest dich explizit für einen Cloud-basierten KI-Anbieter. Selbst dann werden nur anonymisierte Transaktionsbeschreibungen verarbeitet.

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Weitere Einzelheiten findest du in der Datei [LICENSE](LICENSE).

---
*Erstellt mit ❤️ von Bernd Zaiser*
