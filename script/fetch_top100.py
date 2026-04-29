"""

---------------
Fetches the Top 100 most-starred open-source GitHub repositories,
calculates arithmetic means for quantitative KPIs, and writes the
result to data/benchmarks.json.

KPIs calculated via mean (Top-100 reference):
  - stars
  - commits_30d   (commits in the last 30 days)
  - contributors  (total unique contributors)
  - open_issues

Static / binary KPIs (yes/no – no mean needed):
  - has_readme
  - has_license
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from statistics import mean

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
TOP_N = 100
SINCE_DAYS = 30


def _get(url: str, params: dict | None = None) -> dict | list:
    for attempt in range(5):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset_ts - time.time(), 0) + 5
            log.warning("Rate-limited – waiting %.0f s …", wait)
            time.sleep(wait)
            continue
        if resp.status_code == 202:
            # Statistics endpoint queued
            time.sleep(3)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Failed after retries: {url}")


def fetch_top100_repos() -> list[dict]:
    """Return the 100 most-starred, non-fork, non-archived public repos."""
    log.info("Fetching top %d repos by stars …", TOP_N)
    repos = []
    page = 1
    per_page = 30
    while len(repos) < TOP_N:
        data = _get(
            f"{BASE_URL}/search/repositories",
            params={
                "q": "stars:>1000 fork:false archived:false is:public",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
        items = data.get("items", [])
        if not items:
            break
        repos.extend(items)
        page += 1
        time.sleep(0.5)  # be kind to the API

    return repos[:TOP_N]


def get_commits_30d(owner: str, repo: str) -> int:
    """Count commits on the default branch in the last 30 days."""
    since = (datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)).isoformat()
    total = 0
    page = 1
    while True:
        try:
            data = _get(
                f"{BASE_URL}/repos/{owner}/{repo}/commits",
                params={"since": since, "per_page": 100, "page": page},
            )
        except Exception:
            break
        if not data:
            break
        total += len(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.3)
    return total


def get_contributor_count(owner: str, repo: str) -> int:
    """Return total contributor count via the statistics endpoint."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/contributors"
    total = 0
    page = 1
    while True:
        try:
            data = _get(url, params={"per_page": 100, "page": page, "anon": "true"})
        except Exception:
            break
        if not data:
            break
        total += len(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.2)
    return total


def has_file(owner: str, repo: str, path: str) -> bool:
    """Check whether a specific file path exists in the repo root."""
    try:
        _get(f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}")
        return True
    except Exception:
        return False


def process_repos(repos: list[dict]) -> dict:
    results = []
    for i, repo in enumerate(repos, 1):
        owner = repo["owner"]["login"]
        name = repo["name"]
        full_name = repo["full_name"]
        log.info("[%d/%d] Processing %s …", i, TOP_N, full_name)

        commits = get_commits_30d(owner, name)
        contributors = get_contributor_count(owner, name)

        results.append(
            {
                "rank": i,
                "full_name": full_name,
                "stars": repo["stargazers_count"],
                "open_issues": repo["open_issues_count"],
                "commits_30d": commits,
                "contributors": contributors,
                "has_readme": repo.get("has_readme", True),  # nearly always true
                "has_license": repo.get("license") is not None,
                "language": repo.get("language"),
                "url": repo["html_url"],
                "description": repo.get("description", ""),
            }
        )
        time.sleep(0.3)

    return results


def calculate_benchmarks(results: list[dict]) -> dict:
    """Arithmetic mean for each quantitative KPI → 100 % reference value."""
    kpis = ["stars", "commits_30d", "contributors", "open_issues"]
    benchmarks = {}
    for kpi in kpis:
        values = [r[kpi] for r in results if r[kpi] is not None]
        benchmarks[kpi] = round(mean(values), 2) if values else 0.0
    return benchmarks


def main():
    repos = fetch_top100_repos()
    results = process_repos(repos)
    benchmarks = calculate_benchmarks(results)

    output = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_n": TOP_N,
            "since_days": SINCE_DAYS,
        },
        "benchmarks": benchmarks,
        "repos": results,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "benchmarks.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info("Saved → data/benchmarks.json")
    log.info("Benchmarks (= 100 %% reference): %s", benchmarks)


if __name__ == "__main__":
    main()
