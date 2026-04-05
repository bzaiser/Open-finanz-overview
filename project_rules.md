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
- **STRICT Push Targets**: Alle Änderungen MÜSSEN zwingend in zwei spezifische Remote-Ziele / Branches gepusht werden:
  1. `https://github.com/bzaiser/finanzplan` (origin) $\rightarrow$ Branch: `master`
  2. `https://github.com/bzaiser/Open-finanz-overview` (public) $\rightarrow$ Branch: `main`
- **Vorgehensweise**: Führe nach jedem Commit beide Pushes aus: `git push origin master:master` und `git push public master:main`.

## Infrastructure & Environment
- **NO Local Docker**: Es darf NIEMALS versucht werden, `docker` oder `docker-compose` Befehle lokal auszuführen. Es gibt keinen lokalen Docker-Daemon.
- **NO Local Virtual Environment**: Es gibt keine lokale virtuelle Umgebung (`venv`). Python-Skripte dürfen nur direkt mit dem System-Python ausgeführt werden, falls nötig.
- **Remote-Only Execution**: Alle produktiven Befehle (wie `update-fast.sh`) werden erst nach dem Push direkt auf dem Zielserver ausgeführt.

## Troubleshooting & Support
- **Three-Strike Rule**: Wenn ein Problem (z.B. eine Fehlermeldung oder ein Bug) nach **drei Versuchen** durch die KI nicht behoben werden konnte, muss die KI SOFORT stoppen.
- **Vorgehensweise**: Anstatt weiter zu "frickeln", muss die KI die relevanten Stellen im Code (Dateien und Zeilennummern) klar benennen und dem Nutzer präsentieren, damit dieser selbst nachsehen kann.
