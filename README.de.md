# Finanzplan – Das High-End Finanz- & Vorsorge-Cockpit 🚀

[![Language: Multi-5](https://img.shields.io/badge/Language-Multi--5-blue)](#-internationalisierung)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with: Django](https://img.shields.io/badge/Backend-Django--6-green)](https://www.djangoproject.com/)
[![Built with: Google Antigravity](https://img.shields.io/badge/AI--Assisted-Google%20Antigravity-orange?logo=google)](https://deepmind.google/technologies/)

> [!TIP]
> **English Documentation**: You can find the English version of the documentation here: [README.md](README.md) 🇺🇸

**Das ganzheitliche Finanz-, Vorsorge- und Immobilien-Cockpit** — Eine hochpräzise 30+-Jahre-Simulations-Engine für Haushalte, Familien und Immobilienbesitzer mit echter Kaufkraftberechnung, Risiko-Audit und Krisen-Stresstests.

---

## 🌟 Vision & Überblick

Finanzplan ist mehr als nur eine Tracking-App. Es ist eine **Simulations-Engine** für dein Leben. Es projiziert deine finanzielle Kurve über 30+ Jahre und berücksichtigt dabei Vermögenswerte, Immobilien, Darlehen, Vorsorgeansprüche, wiederkehrende Cashflows und Einmalereignisse – und das alles unter strikter Berücksichtigung der inflationsbedingten Entwertung deiner Kaufkraft.

---

## ✨ Kernmodule & Experten-Features

### 📈 1. Präzisions-Simulations-Engine & Dashboard (`/finance/dashboard/`)
- **Real- vs. Nominalwert**: Jede Kennzahl und jede Chart.js-Zeitreihe zeigt sowohl nominale Euro-Werte als auch die inflationsbereinigte **reale Kaufkraft** in heutigen Preisen.
- **Interaktive Stichtags-Zeitreise**: Verschiebe den Stichtag auf jeden beliebigen Monat bis zum Simulations-Endalter (Standard: 90 Jahre) inkl. aufklappbarer KPI-Hover-Cards.
- **Krisen- & Stresstest-Simulator**: Simuliere *Jobverlust (ALG I)*, *Berufsunfähigkeit (BU)*, *Börsencrash (-X %)*, *Anschlussfinanzierungs-Schock (+X %)* oder *Notfallausgaben* im direkten Vergleich zur Baseline-Kurve („Ohne Krise“).

### 🏛️ 2. Altersvorsorge, Versicherungen & Risiko-Check (`/finance/pensions/`)
- **4 Vorsorge-Durchführungswege**: Gesetzliche Rente (DRV inkl. Entgeltpunkten, aktuellem Rentenwert `40,79 €` und Erwerbsminderungsrente), Private Kapital-/Rentenversicherung, Beamtenpension sowie Berufsständisches Versorgungswerk / VBL.
- **3 Auszahlungsmodelle**: Monatlicher Auszahlungsplan mit Kapitalverzehr, lebenslange Rente oder einmalige Kapitalabfindung (automatischer Zufluss ins Barvermögen).
- **Versicherungs- & Absicherungs-Check (`InsurancePolicy`)**: Ampel-Checkliste für Pflicht- und Kernversicherungen, BU-Lücken-Berechnung (80 %-Regel), Risikoleben-Bedarf (3× Jahreseinkommen + Restschuld) und Notgroschen-Reichweite.

### 🏘️ 3. Immobilien, Darlehen & Steuer-Cockpit (`/finance/real-estate/`)
- **Darlehens- & Tilgungsrechner**: Annuitäten-, Tilgungs- und endfällige Darlehen mit LTV-Überwachung, Zinsbindungs-Frühwarnung und **interaktivem Sondertilgungs-Simulator** (Zinsersparnis & Laufzeitverkürzung).
- **Sanierungsfahrplan (`PropertyComponent`)**: Lebenszyklus-Tracking für Dach, Heizung, Fenster & Fassade inkl. 20-Jahres-Rücklagen-Prognose.
- **Steuern (Anlage V) & Zahlungskalender**: 12-Monats-Cashflow-Kalender und automatische Berechnung von Gebäude-AfA, Schuldzinsen, Erhaltungsaufwand und zu versteuerndem Vermietungsergebnis.

### 💰 4. Vermögen, Konten & Sachwerte (`/finance/assets/`)
- **Alle Anlageklassen**: Giro/Bargeld, Tagesgeld, ETF-/Wertpapierdepots, Krypto, Edelmetalle und physische Sachwerte (`PhysicalAsset`).
- **Tagesgeld-Hopping**: Überwachung von Aktionszinsen (`interest_teaser_rate` / `interest_teaser_until`) mit automatischem Rückfall auf den Basiszins nach Ablauf.
- **Automatische Sparplan-Reconciliation**: Konto-Sparpläne (`monthly_savings_amount`) bauen monatlich verzinstes Vermögen auf, ohne mit manuellen Spar-Cashflows doppelt gezählt zu werden.

### 🪄 5. Geführter Einrichtungs-Wizard & 5 Zielgruppen-Demoprofile
- **Standmitteilungs-Wizard (`/finance/wizard/`)**: Erfasst Haushalt, Partner, DRV-Renteninformationen, Privatvorsorge, Cashflows, Vermögen, Immobilien und Kredite mit intelligentem Stichtags-Schutz (`AssetSnapshot`).
- **Jährlicher Anpassungs-Assistent (`/finance/cash-flows/`)**: Schreibt Gehälter und Verträge zum Jahreswechsel mit sauberer Stichtags-Historie fort.
- **6 Lebenssituationen & 1-Klick-Demodaten**: Maßgeschneiderte Presets für *Standard/Familie (`demo_familie`)*, *Geringverdiener (`gering`)*, *Alleinerziehend (`allein`)*, *Studierende (`student`)* und *Frührentner (`rentner`)*.

### 🎨 6. Design-Harmonie-System
- **Mathematische Farbharmonien**: Wähle aus fertigen Farb-Presets (*Deep Ocean*, *Emerald Trust*, *Sunset Gold*, *Midnight Purple*) oder erstelle eigene Paletten.
- **Glassmorphism UI & Night-Mode**: High-End-Tiefeneffekte mit automatischem Dark/Light-Mode.

---

## 🛠 Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Bootstrap 5, HTMX, Alpine.js, Chart.js 4
- **KI-Integration**: LangChain, Ollama, Google Gemini
- **Infrastruktur**: Docker & Docker Compose

---

## 🚀 Erste Schritte

Wir bieten zwei Wege an, dein Finanz-Cockpit zu betreiben, je nach deiner Umgebung.

### Option A: Windows Installer / Desktop App (.exe)
**Ideal für**: Nutzer unter Windows, die eine native App mit vollwertigem Installer wünschen (ohne Docker, WSL2 oder Python-Installation).
1. **Installer herunterladen**: Lade `FinanzplanDesktop_Setup.exe` aus dem Ordner `dist_installer/` oder den GitHub Releases herunter.
2. **Installation**: Starte den Installer (`FinanzplanDesktop_Setup.exe`), wähle auf Wunsch ein Desktop-Icon aus und folge dem Assistenten.
3. **Starten**: Die Anwendung startet direkt als native Desktop-App im eigenen Fenster mit integriertem Server und automatischer Datenbank-Verwaltung.

*(Alternativ: Für portable Nutzung ohne Installer kann `native-dist/setup-native.bat` und `start-dashboard.bat` verwendet werden.)*

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

## 🤖 Entwickelt mit Antigravity
Dieses Projekt wurde unter Einsatz von **Google Antigravity** (Advanced Agentic Pair-Programming) konzipiert, entwickelt und iteriert.

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Weitere Einzelheiten findest du in der Datei [LICENSE](LICENSE).

---
*Erstellt mit ❤️ von Bernd Zaiser*
