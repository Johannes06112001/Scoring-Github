[README.md](https://github.com/user-attachments/files/27208283/README.md)
# Top-100 Open-Source Benchmark

Dieses Repository berechnet automatisch die **Mittelwerte der 100 meistgesehnten Open-Source-Projekte** auf GitHub und stellt sie als Referenzwert (= 100 %) bereit.

## Konzept (aus Meeting-Notizen)

| Was | Wie |
|---|---|
| Top-100 Projekte | Als Benchmark **festgelegt** – pragmatisch, nicht streng wissenschaftlich |
| Mittelwert | Arithmetisches Mittel der quantitativen KPIs = **100 % Referenz** |
| Ziel | Kleinere Projekte relativ zum Markt einordnen |

### KPIs über Mittelwert (quantitativ)

- `stars` – GitHub Stars
- `commits_30d` – Commits der letzten 30 Tage
- `contributors` – Anzahl einzigartiger Contributors
- `open_issues` – Offene Issues & Pull Requests

### Statische KPIs (ja / nein – kein Mittelwert nötig)

- `has_readme` – README vorhanden
- `has_license` – Lizenz vorhanden

---

## Repo-Struktur

```
top100-benchmark/
├── .github/
│   └── workflows/
│       └── update_benchmarks.yml   # Scheduler (Mo + Do, 04:00 UTC)
├── scripts/
│   ├── fetch_top100.py             # Daten holen + Mittelwert berechnen
│   └── score_repo.py               # Einzelnes Repo bewerten
├── data/
│   └── benchmarks.json             # Output (wird automatisch committed)
├── index.html                      # GitHub Pages Dashboard
└── README.md
```

---

## Setup

### 1. Repository anlegen

```bash
gh repo create top100-benchmark --public
git remote add origin https://github.com/ZR-JT/top100-benchmark.git
git push -u origin main
```

### 2. GitHub Pages aktivieren

Repository → **Settings → Pages → Source: `gh-pages` branch**

### 3. GitHub Actions Secret

Der `GITHUB_TOKEN` wird automatisch von GitHub Actions bereitgestellt – kein manuelles Secret nötig.  
Für höhere Rate-Limits (5000 req/h statt 60 req/h) kann ein persönliches Access Token hinterlegt werden:

```
Repository → Settings → Secrets → Actions → New repository secret
Name: GITHUB_TOKEN_PAT
```

Dann in `update_benchmarks.yml` ersetzen:
```yaml
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN_PAT }}
```

### 4. Workflow manuell starten

GitHub → **Actions → Update Top-100 Benchmarks → Run workflow**

---

## Einzelnes Repo bewerten (lokal)

```bash
pip install requests
export GITHUB_TOKEN=ghp_...
python scripts/score_repo.py facebook/react
```

Ausgabe in `data/score_facebook__react.json`:

```json
{
  "scores_pct_of_benchmark": {
    "stars":        210.4,
    "commits_30d":   87.2,
    "contributors": 145.0,
    "open_issues":   63.1
  },
  "static_checks": {
    "has_readme": true,
    "has_license": true
  }
}
```

> **Interpretation:** 210 % Stars bedeutet, das Repo hat mehr als doppelt so viele Stars wie der Top-100-Durchschnitt.

---

## Update-Intervall

Konfiguriert in `.github/workflows/update_benchmarks.yml`:

```yaml
- cron: "0 4 * * 1"   # Montag 04:00 UTC
- cron: "0 4 * * 4"   # Donnerstag 04:00 UTC
```

Für tägliche Updates:
```yaml
- cron: "0 4 * * *"
```
