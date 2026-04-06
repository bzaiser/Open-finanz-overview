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
- **NO Special Characters in IDs**: In `{% trans "..." %}`-Tags dürfen in der `msgid` (dem Schlüssel) KEINE Sonderzeichen verwendet werden. Insbesondere das Prozentzeichen `%` ist strikt verboten, da es als Formatierungs-Platzhalter missverstanden wird. Sonderzeichen gehören nur in die Übersetzung (`msgstr`).

## General Frontend
## General Frontend
- **Single Line Variables**: Always keep variables like `{{ currency }}` on the same line as the value they accompany.

## Git Deployment
- **STRICT Push Targets (Dual-Branch/Dual-Repo)**: Alle Änderungen MÜSSEN zwingend in ZWEI Repositories auf jeweils ZWEI Branches gepusht werden:
  1. `bzaiser/finanzplan.git` (origin) $\rightarrow$ Branches: `main` **UND** `master`
  2. `bzaiser/Open-finanz-overview.git` (public) $\rightarrow$ Branches: `main` **UND** `master`
- **Vorgehensweise**: Führe nach jedem Commit die Pushes für alle Zielkombinationen aus:
  ```bash
  git push origin main && git push origin master
  git push public main && git push public master
  ```
- **Migration Synchronisation (CRITICAL)**: Bevor eine neue Datenbank-Migration erstellt wird, MUSS die KI den Stand in BEIDEN Remotes prüfen:
  - `git ls-tree -r origin/master finance/migrations/`
  - `git ls-tree -r public/main finance/migrations/`
- **Linearitäts-Gebot**: Beide Repositories müssen exakt dieselbe Migrations-Historie teilen. Wenn ein Repo voraus ist, muss das andere Repo erst auf denselben Stand gebracht werden.
- **STRICT Push-First Rule**: Bevor dem Nutzer gemeldet wird "Fertig" oder "Probier es aus", MÜSSEN alle Änderungen auf allen oben genannten Branches/Remotes erfolgreich gepusht sein.

## Infrastructure & Environment
- **STRICT: NO Local Docker**: Es darf NIEMALS versucht werden, `docker` oder `docker-compose` Befehle lokal auszuführen. Es darf auch NICHT nach einem lokalen Docker-Daemon gesucht werden. 
- **Migrationen**: Datenbank-Migrationen (`makemigrations`, `migrate`) werden niemals lokal ausgeführt. Diese erfolgen ausschließlich auf dem Remote-System über die dortigen Update-Scripte.
- **KEINE Lokalen Installationen**: Führe niemals `pip install`, `npm install`, `apt-get install` oder andere Installationsbefehle lokal aus. Abhängigkeiten werden ausschließlich über das Docker-System auf dem Zielserver verwaltet.
- **NO Local Virtual Environment**: Es gibt keine lokale virtuelle Umgebung (`venv`). Python-Skripte dürfen nur direkt mit dem System-Python ausgeführt werden, falls nötig.
- **Remote-Only Execution**: Alle produktiven Befehle (wie `update-fast.sh`) werden erst nach dem Push direkt auf dem Zielserver ausgeführt.

## Troubleshooting & Support
- **Three-Strike Rule**: Wenn ein Problem (z.B. eine Fehlermeldung oder ein Bug) nach **drei Versuchen** durch die KI nicht behoben werden konnte, muss die KI SOFORT stoppen.
- **Vorgehensweise**: Anstatt weiter zu "frickeln", muss die KI die relevanten Stellen im Code (Dateien und Zeilennummern) klar benennen und dem Nutzer präsentieren, damit dieser selbst nachsehen kann.
