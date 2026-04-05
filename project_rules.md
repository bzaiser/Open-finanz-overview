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

## General Frontend
## General Frontend
- **Single Line Variables**: Always keep variables like `{{ currency }}` on the same line as the value they accompany.

## Git Deployment
- **STRICT Push Targets**: Alle Änderungen MÜSSEN zwingend in zwei spezifische Remote-Ziele / Branches gepusht werden:
  1. `https://github.com/bzaiser/finanzplan` (origin) $\rightarrow$ Branch: `master`
  2. `https://github.com/bzaiser/Open-finanz-overview` (public) $\rightarrow$ Branch: `main`
- **Vorgehensweise**: Führe nach jedem Commit beide Pushes aus: `git push origin master:master` und `git push public master:main`.
