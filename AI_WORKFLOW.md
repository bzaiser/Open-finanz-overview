# AI Workspace & Workflow Context

Dieses Dokument dient als zentrales Gedächtnis für alle zukünftigen KI-Assistenten-Sitzungen in diesem Workspace. Es beschreibt die Architektur, die wichtigsten Repositories und die grundlegenden Deployment- und Arbeits-Workflows von Bernd.

**Die KI ist angewiesen, diese Datei bei Bedarf zu konsultieren, um Kontext-Rückfragen zu minimieren.**

---

## 1. Repositories & Projekte

Die Entwicklung findet primär unter `/home/bernd/Documents/dev/` statt. Die beiden Hauptprojekte sind:

### A. Urlaubsplanung (`/home/bernd/Documents/dev/urlaubsplanung`)
Ein umfassendes Dashboard für die Reise- und Camper-Planung.
*   **Kern-Features:**
    *   KI-gestützte Logik für Reise-Events (Berechnung von Pufferzeiten, Ankunftszeiten, automatische Splittung von Hotel-Aufenthalten in Check-in/Check-out).
    *   Polarsteps-Synchronisation: Nutzt eine "Safe Sync"-Architektur mit `polarsteps_step_id`, um Datenverlust oder Duplikate bei manuellen Routen zu verhindern.
    *   Travel Planning Matrix: Eine 17-spaltige Tabelle (AG Grid / HTML) für schnelles Tabbing, mit Sticky Headern und automatischem Speichern (Saved Toasts).
    *   Geocoding-Service: Strikte, automatisierte Ortsauflösungen für lückenloses Karten-Rendering.
*   **Fokus:** Visuell ansprechendes, robustes UI ("Zero-Refresh" wo möglich), Mobile-Responsiveness (z.B. für das Diary Modal) und strikte Logistik-Validierung.

### B. Finanzplan / Open-finanz-overview (`/home/bernd/Documents/dev/finanzplan`)
Ein Dashboard zur Finanzverwaltung und -übersicht.
*   **Code-Basis:** Die Code-Basis wird in *zwei* separate Repositories gepusht.
*   **Kern-Features:**
    *   "Zünder" (Bootstrapper): Ein Skript für idiotensicheres, automatisiertes Deployment auf frischen Windows-Systemen (installiert Git, clont das Repo, startet Container via Podman/Docker, lädt Demo-Daten).
    *   Dashboard mit AG Grid, intuitiven Headern und Finanzübersichten.
*   **Fokus:** Einfache Nutzbarkeit (One-Click Setup für Endnutzer), strikte Trennung von Codebase und produktiven Daten.

---

## 2. Infrastruktur & Deployment

*   **NAS / Docker:** Auf dem NAS laufen **3 Docker-Container**, die primär durch `.env`-Dateien gesteuert werden. Das ist zwingend bei der Ausführung von Docker-Befehlen zu beachten.
    *   *Regel für die KI:* Die KI hat keinen direkten Zugriff auf das NAS. Alles läuft über vorgeschlagene Befehle am lokalen Rechner.
    *   *NAS-Deployment Workflow:* Die Aktualisierung der Container auf dem NAS erfolgt ausschließlich über drei Skripte: `update.sh`, `update.fast.sh` und `update-turbo.sh`.
    *   *Git-Zwang:* Ohne einen Git-Push vom lokalen Rechner aus kann Bernd die Änderungen nicht auf dem NAS testen oder die genannten Update-Skripte sinnvoll ausführen.
*   **Zünder-Deployment (Windows):** Für Endanwender (z.B. beim Finanzplan) wird ein Bootstrapper verwendet, der Podman/Docker eigenständig verwaltet.
*   **Fire Tablet:** Sporadische Deployments von Apps (z.B. mit Toga/BeeWare), bei denen eine minimalistische Basis wichtig ist, um Hardware-Inkompatibilitäten auszuschließen.

---

## 3. Workflow-Regeln für den KI-Assistenten

1.  **Strenge Git-Hygiene:** 
    *   Zusätzliche Dateien, die nur lokal in der Entwicklungsumgebung gebraucht werden (z.B. lokale DBs, Test-Skripte), dürfen **unter keinen Umständen** mit `git add` hochgeladen oder eigenmächtig in die `.gitignore` geschrieben werden. Bitte nur committen, was wirklich in die Produktion gehört.
2.  **Datenbanken-Debugging:** Die produktiven Datenbanken liegen auf dem NAS in den Docker-Containern. Wenn Bernd einen Fehler meldet, der konkrete Daten betrifft, darf die KI **nicht** versuchen, das Problem durch lokales Suchen in der Entwicklungs-Datenbank zu analysieren, da die relevanten Daten dort gar nicht vorhanden sind.
3.  **Nicht raten, sondern nachschauen:** Bevor tiefgreifende Änderungen gemacht werden, soll die KI den existierenden Code prüfen, insbesondere etablierte Muster (z.B. für Datenbank-Imports oder UI-Komponenten).
4.  **Sicherheit und Erhalt von Daten:** Bestehende Nutzerdaten oder manuell gepflegte Inhalte (z.B. manuell erstellte Reiserouten neben Polarsteps-Imports) dürfen durch automatisierte Prozesse nicht gelöscht werden (Non-destructive operations).
5.  **Terminal-Befehle:** 
    *   Befehle dürfen vorgeschlagen, aber nie ungefragt mit `SafeToAutoRun: true` abgesetzt werden, wenn sie destruktive Seiteneffekte haben könnten oder Remote-Verbindungen (NAS) aufbauen.
6.  **UI/UX Standards:** Wenn neue UI-Elemente erstellt werden, müssen sie visuell hochwertig, flüssig (Micro-Animations, kein Flackern) und responsiv gestaltet sein. Es dürfen keine Standard-HTML-Formulare ohne entsprechendes Styling verwendet werden.
7.  **STRIKTES VERBOT von Over-Engineering (Minimalinvasive Änderungen):** 
    *   Wegen kleiner Designänderungen, Übersetzungsfehlern oder Textänderungen auf Buttons darf **unter keinen Umständen** die Architektur umgebaut oder die generelle Vorgehensweise geändert werden.
    *   Strukturelle Umbauten bedürfen *immer* der expliziten Notwendigkeit und der vorherigen Genehmigung von Bernd.
    *   **Keine Ausnahmen:** Selbst wenn Bernd in einer Session zuvor einem Umbau zugestimmt hat, ist das *kein* Freifahrtschein, diese Logik auf andere Bereiche anzuwenden. Jede größere Änderung muss separat evaluiert werden.

*(Dieses Dokument kann jederzeit durch den Nutzer oder die KI ergänzt werden, sobald sich neue Projekt-Säulen oder Workflow-Regeln etablieren.)*
