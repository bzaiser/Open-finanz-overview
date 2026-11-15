# Finanzplan – Das High-End Finanz-, Vorsorge- & Immobilien-Cockpit 🚀

[![Language: Multi-5](https://img.shields.io/badge/Language-Multi--5-blue)](#-internationalisierung)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with: Django](https://img.shields.io/badge/Backend-Django--6-green)](https://www.djangoproject.com/)
[![Built with: Google Antigravity](https://img.shields.io/badge/AI--Assisted-Google%20Antigravity-orange?logo=google)](https://deepmind.google/technologies/)

> [!TIP]
> **English Documentation**: You can find the English version of the documentation here: [README.md](README.md) 🇺🇸

**Das ganzheitliche Finanz-, Vorsorge- und Immobilien-Cockpit** — Eine hochpräzise 30+-Jahre-Simulations-Engine für Haushalte, Familien und Immobilienbesitzer mit echter Kaufkraftberechnung, Risiko- & Notfall-Audit, Krisen-Stresstests, Dokumenten-Tresor und 100 % Self-Hosted-Datensicherung.

---

## 🌟 Vision & Überblick

Finanzplan ist mehr als nur eine Tracking-App. Es ist eine **Simulations-Engine** für dein Leben. Es projiziert deine finanzielle Kurve über 30+ Jahre und berücksichtigt dabei Vermögenswerte, Immobilien, Darlehen, Vorsorgeansprüche, Kinder-Lebenszyklen, wiederkehrende Cashflows und Einmalereignisse – und das alles unter strikter Berücksichtigung der inflationsbedingten Entwertung deiner Kaufkraft.

---

## ✨ Kernmodule & Experten-Features

### 📈 1. Präzisions-Simulations-Engine & Dashboard (`/finance/dashboard/`)
- **Real- vs. Nominalwert**: Jede Kennzahl und jede Chart.js-Zeitreihe zeigt sowohl nominale Euro-Werte als auch die inflationsbereinigte **reale Kaufkraft** in heutigen Preisen.
- **Interaktive Stichtags-Zeitreise**: Verschiebe den Stichtag auf jeden beliebigen Monat bis zum Simulations-Endalter (Standard: 90 Jahre) inkl. aufklappbarer KPI-Hover-Cards und individuellem Karten-Konfigurator (`⚙️`).
- **Krisen- & Stresstest-Simulator**: Simuliere *Jobverlust (ALG I)*, *Berufsunfähigkeit (BU)*, *Börsencrash (-X %)*, *Anschlussfinanzierungs-Schock (+X %)* oder *Notfallausgaben* im direkten Vergleich zur Baseline-Kurve („Ohne Krise“).

### 🏛️ 2. Altersvorsorge, Versicherungen & Risiko-/Notfall-Check (`/finance/pensions/`)
- **4 Vorsorge-Durchführungswege**: Gesetzliche Rente (DRV inkl. Entgeltpunkten, aktuellem Rentenwert `40,79 €` und Erwerbsminderungsrente), Private Kapital-/Rentenversicherung & bAV, Beamtenpension sowie Berufsständisches Versorgungswerk / VBL.
- **3 Auszahlungsmodelle**: Monatlicher Auszahlungsplan mit Kapitalverzehr, lebenslange Rente oder einmalige Kapitalabfindung (automatischer Zufluss ins Barvermögen).
- **Versicherungs- & Absicherungs-Check (`InsurancePolicy`)**: Ampel-Checkliste für Pflicht- und Kernversicherungen, BU-Lücken-Berechnung (80-%-Regel), Risikoleben-Bedarf (3× bzw. 5× Jahreseinkommen mit Kindern + Restschuld), Notgroschen-Reichweite sowie **Physische Bargeldreserve (Blackout- & Kartenausfall-Schutz)** mit Haushalts-Richtwert (`500 € + 250 € Partner + 150 € je Kind`) und 1-Klick-Anlage.

### 🏘️ 3. Immobilien, Darlehen & Steuer-Cockpit (`/finance/real-estate/`)
- **Darlehens- & Tilgungsrechner**: Annuitäten-, Tilgungs- und endfällige Darlehen mit LTV-Überwachung, Zinsbindungs-Frühwarnung und **interaktivem Sondertilgungs-Simulator** (Zinsersparnis & Laufzeitverkürzung).
- **Sanierungsfahrplan (`PropertyComponent`)**: Lebenszyklus-Tracking für Dach, Heizung, Fenster & Fassade inkl. 20-Jahres-Rücklagen-Prognose.
- **Steuern (Anlage V) & Zahlungskalender**: 12-Monats-Cashflow-Kalender und automatische Berechnung von Gebäude-AfA, Schuldzinsen, Erhaltungsaufwand und zu versteuerndem Vermietungsergebnis.

### 💰 4. Vermögen, Konten & Physische Sachwerte (`/finance/assets/`)
- **Alle Anlageklassen**: Strukturierte Reiter für Giro/Bargeld, Tagesgeld/Geldmarkt, ETF-/Wertpapierdepots, Krypto, Edelmetalle und physische Sachwerte (`PhysicalAsset` inkl. Unterhaltskosten & geplantem Verkaufsdatum).
- **Tagesgeld-Hopping**: Überwachung von Aktionszinsen (`interest_teaser_rate` / `interest_teaser_until`) mit automatischem Rückfall auf den Basiszins nach Ablauf.
- **Automatische Sparplan-Reconciliation**: Konto-Sparpläne (`monthly_savings_amount`) bauen monatlich verzinstes Vermögen auf, ohne mit manuellen Spar-Cashflows doppelt gezählt zu werden.

### 📂 5. Dokumenten-Tresor & Globale Volltextsuche (`/finance/documents/` & `Strg+K`)
- **Zentrales Dokumenten-Archiv (`Document Vault`)**: Direkte Verknüpfung von Dokumenten mit Immobilien, Darlehen, Vorsorgeverträgen, Versicherungen und Konten.
- **Integrierter Browser-Viewer**: Lokale Direkt-Vorschau für PDF, Bilder, Textdateien, Microsoft Word (`.docx`) und Excel (`.xlsx`).
- **Volltext-Indizierung & Globale Suche (`Strg+K`)**: Durchsucht in Echtzeit alle Finanzdatensätze sowie den extrahierten Textinhalt aller hochgeladenen PDF-, Word-, Excel- und Textdokumente.

### 🪄 6. 7-Schritte Einrichtungs-Wizard, Kinder-Profile & Jahres-Assistent
- **Standmitteilungs- & Einrichtungs-Wizard (`/finance/wizard/`)**: Erfasst in 7 thematisch harmonisierten Schritten Haushalt, Partner, **Kinder-Profile (`ChildProfile` inkl. Selbstständigkeits-Alter & automatischer Kindergeld-Terminierung)**, DRV-Renteninformationen, Privatvorsorge, Cashflows, Vermögen, Immobilien und Kredite mit chronologischem Stichtags-Schutz (`AssetSnapshot` / `PensionSnapshot`).
- **Jährlicher Anpassungs-Assistent (`/finance/cash-flows/`)**: Schreibt Gehälter und Verträge zum Jahreswechsel mit sauberer Stichtags-Historie fort und zieht verknüpfte Versicherungspolicen automatisch mit.
- **KI-Bankimport (`/finance/import/`)**: CSV-/PDF-Kontoauszugsimport mit Regel-Filtern (`> 2 %` Preisabweichungs-Wächter) und optionaler KI-Kategorisierung (Ollama / Google Gemini).
- **6 Lebenssituationen & 5 Demoprofile**: Maßgeschneiderte Presets für *Standard/Familie (`demo_familie`)*, *Geringverdiener (`gering`)*, *Alleinerziehend (`allein`)*, *Studierende (`student`)* und *Frührentner (`rentner`)*.

### 🎨 7. Design Studio v2, Desktop-Pipette & Voll-Backup-System (`/profile/`)
- **Design Studio v2 & Farbharmonien**: Kuratierte Farb-Presets (*Deep Ocean*, *Emerald Trust*, *Sunset Gold*, *Midnight Purple*) oder freie Farbauswahl für Tag- & Nachtmodus – in der Windows-Desktop-App inklusive **bildschirmweiter Farbpipette (Eyedropper)**.
- **Asynchrones Voll-Backup & Externe Rotation**: 1-Klick-ZIP-Sicherung (Datenbank + sämtliche Dokumente) mit Live-Fortschrittsbalken, optionaler Synchronisation in einen externen Zielordner (NAS / Cloud / USB), automatischer Backup-Rotation und Erinnerungs-Wächter.

---

## 🛠 Tech Stack

- **Backend**: Django 6.0.2
- **Frontend**: Bootstrap 5, HTMX, Alpine.js, Chart.js 4
- **KI-Integration**: LangChain, Ollama, Google Gemini
- **Infrastruktur**: Native Windows-Desktop-App (`.exe`) & Docker / Docker Compose

---

## 🚀 Erste Schritte

Wir bieten zwei Wege an, dein Finanz-Cockpit zu betreiben, je nach deiner Umgebung.

### Option A: Windows Installer / Desktop App (.exe)
**Ideal für**: Nutzer unter Windows, die eine native App mit vollwertigem Installer wünschen (ohne Docker, WSL2 oder Python-Installation).
1. **Installer herunterladen**: Lade `FinanzplanDesktop_Setup.exe` aus dem Ordner `dist_installer/` oder den GitHub Releases herunter.
2. **Installation**: Starte den Installer (`FinanzplanDesktop_Setup.exe`), wähle auf Wunsch ein Desktop-Icon aus und folge dem Assistenten.
3. **Starten**: Die Anwendung startet direkt als native Desktop-App im eigenen Fenster mit integriertem Server, Bildschirm-Pipette und automatischer Datenbank-Verwaltung.

*(Alternativ: Für portable Nutzung ohne Installer kann `native-dist/setup-native.bat` und `start-dashboard.bat` verwendet werden.)*

### Option B: Server/NAS (Docker & Podman)
**Ideal für**: Fortgeschrittene Nutzer, NAS-Systeme (Synology/QNAP) oder Linux-Server.
1. **Klonen**: `git clone https://github.com/bzaiser/Open-finanz-overview.git`.
2. **Konfiguration**: `cp .env.example .env`.
3. **Start**: `./update-fast.sh` (oder `docker-compose up -d`).

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

## 🔒 Sicherheit, Datenschutz & Rechtlicher Hinweis (Haftungsausschluss)

Deine Finanzdaten sind sensibel. Deshalb ist Finanzplan so konzipiert, dass es **komplett selbst gehostet** werden kann.

> [!CAUTION]
> **Verbindliche Nutzungs- & Sicherheitsregeln:**
> 1. **Rein privater Gebrauch & Open Source (`AS IS`)**: Diese Software wird unentgeltlich unter der MIT-Lizenz ausschließlich für den privaten, nicht-kommerziellen Gebrauch bereitgestellt – ohne jegliche Gewährleistung für Richtigkeit, Vollständigkeit oder Verfügbarkeit.
> 2. **Keine Finanz-, Steuer-, Versicherungs- oder Rechtsberatung**: Alle Simulationen, Renten-, Zins-, Tilgungs-, Risiko- und Steuerberechnungen (z. B. Anlage V / AfA) sind unverbindliche mathematische Modellrechnungen. Es wird keinerlei Haftung für Rechenfehler, veraltete Gesetzesparameter oder Vermögensschäden übernommen.
> 3. **Striktes Verbot von Passwörtern, PINs, TANs & Krypto-Seeds**: Hinterlege in der Anwendung oder im Dokumenten-Tresor **niemals** Online-Banking-Zugangsdaten, Passwörter, PINs, TANs, Kreditkarten-CVVs, Private Keys oder Krypto-Seed-Phrases (12/24 Wörter).
> 4. **Eigenverantwortung für Verschlüsselung, Malware-Schutz & Backups**: Festplattenverschlüsselung (BitLocker/LUKS), Betriebssystem-Updates, Schutz gegen Schadsoftware/Viren/Ransomware sowie regelmäßige, extern verschlüsselte Backups liegen zu 100 % in der Eigenverantwortung des Benutzers.

---

## 🤖 Entwickelt mit Antigravity
Dieses Projekt wurde unter Einsatz von **Google Antigravity** (Advanced Agentic Pair-Programming) konzipiert, entwickelt und iteriert.

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Weitere Einzelheiten findest du in der Datei [LICENSE](LICENSE).

---
*Erstellt mit ❤️ von Bernd Zaiser*
