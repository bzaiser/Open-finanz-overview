# Project Rules

## Template Tags
- **STRICT Single Line Rule**: Every single Django template tag (`{% ... %}` or `{{ ... }}`) MUST be contained entirely on a single line. 
  - **NO EXCEPTIONS**: Even if the line becomes extremely long, do NOT split tags across lines.
  - **Reasoning**: Splitting tags (e.g., placing `{%` on one line and `%}` on another) breaks the Django template parser, leading to "Invalid block tag" errors or literal code appearing on the page.
  - **Example**:
    - [CORRECT] `{% if item.id == 'foo' %}{{ item.value }}{% endif %}`
    - [INCORRECT] 
      ```html
      {% if item.id == 
         'foo' %}
      ```
- **Tag Consolidation**: Prefer keeping biological units (like an `if` block wrapping a `trans` tag) on one line if it aids in following the no-split rule: `{% if ... %}{% trans ... %}{% endif %}`.
- **{% trans %} Placement**: Innerhalb von HTML-Elementen (wie `<label>`, `<div>`, `<span>`) muss der `{% trans %}`-Tag immer auf einer **eigenen Zeile** stehen, um die Lesbarkeit und Erkennung durch das i18n-System zu optimieren. Der Tag selbst darf dabei nicht umgebrochen werden.
- **NO Special Characters in IDs (Use Keys)**: In `{% trans "..." %}`-Tags dürfen in der `msgid` (dem Schlüssel) KEINE Sonderzeichen verwendet werden. Insbesondere das Prozentzeichen `%` ist strikt verboten. Bei Sätzen mit Sonderzeichen oder komplexer Formatierung MÜSSEN stattdessen eindeutige Schlüssel-Begriffe (z.B. `HELP_AI_DESC`) verwendet werden. Sonderzeichen gehören ausschließlich in die Übersetzung (`msgstr`).

## General Frontend
## General Frontend
- **Single Line Variables**: Always keep variables like `{{ currency }}` on the same line as the value they accompany.

## Git Deployment
- **STRICT Push Targets (Dual-Repo / Single-Branch)**: Alle Änderungen MÜSSEN zwingend in ZWEI Repositories auf dem `main`-Branch gepusht werden:
  1. `bzaiser/finanzplan.git` (origin) $\rightarrow$ Branch: `main`
  2. `bzaiser/Open-finanz-overview.git` (overview) $\rightarrow$ Branch: `main`
- **Vorgehensweise**: Führe nach jedem Commit die Pushes für alle Zielkombinationen aus:
  ```bash
  git push origin main
  git push overview main
  ```
- **Migration Synchronisation (CRITICAL)**: Bevor eine neue Datenbank-Migration erstellt wird, MUSS die KI den Stand in BEIDEN Remotes prüfen:
  - `git ls-tree -r origin/main finance/migrations/`
  - `git ls-tree -r overview/main finance/migrations/`
- **Linearitäts-Gebot**: Beide Repositories müssen exakt dieselbe Migrations-Historie teilen.
- **STRICT Push-First Rule**: Bevor dem Nutzer eine Antwort, Rückmeldung oder Erklärung gesendet wird, MÜSSEN alle Code-Änderungen zwingend auf allen oben genannten Remotes (`origin/main`, `overview/main`) erfolgreich gepusht sein. Erklärungen folgen immer ERST NACH dem erfolgreichen Push.

## Standard-Workflow (Interne Agent-Regeln)
Der Agent folgt bei JEDER Aufgabe strikt diesem Ablauf:
1. **Research & Analyse**: Gründliches Verständnis des Problems und der Code-Basis.
2. **Implementierung**: Durchführung der Code-Änderungen.
3. **Commit & Push-First**:
   - Änderungen committen.
   - **ERST** Push auf beide Ziele (`origin/main`, `overview/main`) erfolgreich abschließen.
4. **Antwort an Nutzer**: Erst nach dem erfolgreichen Push erfolgt die Rückmeldung oder Erklärung an den Nutzer.

## Infrastructure & Environment
- **STRICT: NO Local Docker**: Es darf NIEMALS versucht werden, `docker` oder `docker-compose` Befehle lokal auszuführen. Es darf auch NICHT nach einem lokalen Docker-Daemon gesucht werden. 
- **Migrationen**: Datenbank-Migrationen (`makemigrations`, `migrate`) werden NIEMALS vom Agenten ausgeführt. Diese erfolgen ausschließlich durch den Nutzer auf dem Remote-System über die dortigen Update-Scripte (z.B. `update-fast.sh`).
- **KEINE Lokalen Installationen**: Führe niemals `pip install`, `npm install`, `apt-get install` oder andere Installationsbefehle lokal aus. 
- **Remote-Only Execution**: Alle produktiven Befehle (wie `update-fast.sh`) werden erst nach dem Push direkt auf dem Zielserver ausgeführt.

## Troubleshooting & Support
- **Three-Strike Rule**: Wenn ein Problem (z.B. eine Fehlermeldung oder ein Bug) nach **drei Versuchen** durch die KI nicht behoben werden konnte, muss die KI SOFORT stoppen.
- **Vorgehensweise**: Anstatt weiter zu "frickeln", muss die KI die relevanten Stellen im Code (Dateien und Zeilennummern) klar benennen und dem Nutzer präsentieren, damit dieser selbst nachsehen kann.

## Translations & I18N
- **STRICT: NO Overhaul of Translation Procedures**: Bestehende Übersetzungsverfahren (z. B. die Verwendung von `gettext` / `_eager`) dürfen NICHT eigenmächtig durch andere Verfahren (wie `gettext_lazy` / `_`) ersetzt werden, nur um einen einzelnen Übersetzungsfehler zu beheben. Fehler müssen innerhalb des bestehenden Systems durch Korrektur der `msgid` oder der Sprachdateien gelöst werden.
- **NO tracked .mo files**: (Entsprechend der aktuellen Bereinigung) Kompilierte `.mo`-Dateien werden nicht in Git getrackt, um Merge-Konflikte zu vermeiden. Die Generierung erfolgt ausschließlich auf dem Zielsystem.

