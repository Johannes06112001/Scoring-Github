"""
score_repo.py
-------------
Compares a single GitHub repository against the Top-100 benchmark averages
and outputs a JSON score report.

Usage:
    python scripts/score_repo.py owner/repo
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

BASE_URL = "https://api.github.com"
SINCE_DAYS = 30


def _get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_repo_metrics(full_name: str) -> dict:
    owner, repo = full_name.split("/", 1)
    data = _get(f"{BASE_URL}/repos/{owner}/{repo}")

    # commits in last 30 days
    since = (datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).isoformat()
    commits = 0
    page = 1
    while True:
        c = _get(
            f"{BASE_URL}/repos/{owner}/{repo}/commits",
            params={"since": since, "per_page": 100, "page": page},
        )
        commits += len(c)
        if len(c) < 100:
            break
        page += 1
        time.sleep(0.2)

    # contributors
    contributors = 0
    page = 1
    while True:
        c = _get(
            f"{BASE_URL}/repos/{owner}/{repo}/contributors",
            params={"per_page": 100, "page": page, "anon": "true"},
        )
        contributors += len(c)
        if len(c) < 100:
            break
        page += 1
        time.sleep(0.2)

    return {
        "full_name": full_name,
        "stars": data["stargazers_count"],
        "open_issues": data["open_issues_count"],
        "commits_30d": commits,
        "contributors": contributors,
        "has_readme": True,
        "has_license": data.get("license") is not None,
        "language": data.get("language"),
        "url": data["html_url"],
        "description": data.get("description", ""),
    }


def score_against_benchmarks(metrics: dict, benchmarks: dict) -> dict:
    """Express each KPI as a percentage of the benchmark mean (= 100 %)."""
    kpis = ["stars", "commits_30d", "contributors", "open_issues"]
    scores = {}
    for kpi in kpis:
        ref = benchmarks.get(kpi, 1)
        val = metrics.get(kpi, 0)
        scores[kpi] = round((val / ref) * 100, 2) if ref else None
    return scores


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/score_repo.py owner/repo")
        sys.exit(1)

    target = sys.argv[1]

    bench_path = os.path.join(os.path.dirname(__file__), "..", "data", "benchmarks.json")
    if not os.path.exists(bench_path):
        log.error("data/benchmarks.json not found – run fetch_top100.py first.")
        sys.exit(1)

    with open(bench_path, encoding="utf-8") as f:
        bench_data = json.load(f)

    benchmarks = bench_data["benchmarks"]
    log.info("Fetching metrics for %s …", target)
    metrics = get_repo_metrics(target)
    scores = score_against_benchmarks(metrics, benchmarks)

    report = {
        "meta": {
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "benchmark_generated_at": bench_data["meta"]["generated_at"],
            "target_repo": target,
        },
        "metrics": metrics,
        "benchmarks_reference": benchmarks,
        "scores_pct_of_benchmark": scores,
        "static_checks": {
            "has_readme": metrics["has_readme"],
            "has_license": metrics["has_license"],
        },
    }

    out_path = os.path.join(
        os.path.dirname(__file__), "..", "data", f"score_{target.replace('/', '__')}.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log.info("Score report saved → %s", out_path)
    log.info("Scores (%% of benchmark mean):")
    for kpi, pct in scores.items():
        log.info("  %-20s %7.1f %%", kpi, pct)


if __name__ == "__main__":
    main()
