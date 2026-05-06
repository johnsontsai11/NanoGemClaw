import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuration and Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

POSSIBLE_ROOTS = [
    "/mnt/repos",              # Container mount
    "/Volumes/DevDisk/Matteo"  # Host development disk
]

REPOS_ROOT = os.environ.get("REPOS_ROOT")
if not REPOS_ROOT:
    for root in POSSIBLE_ROOTS:
        if os.path.isdir(root):
            REPOS_ROOT = root
            break
    if not REPOS_ROOT:
        REPOS_ROOT = "/mnt/repos"


def load_config():
    """Loads the project nickname mapping from JSON."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_path(nickname, config):
    """Resolves nickname to absolute path."""
    path_val = config.get(nickname, nickname)

    if os.path.isabs(path_val):
        resolved_path = path_val
    else:
        resolved_path = os.path.join(REPOS_ROOT, path_val)

    try:
        os.stat(resolved_path)
        if os.path.isdir(resolved_path):
            return resolved_path
    except PermissionError:
        raise PermissionError(
            f"Error: Permission denied accessing '{resolved_path}'. "
            "Check macOS Full Disk Access for your terminal/app."
        )
    except FileNotFoundError:
        pass

    try:
        available = os.listdir(REPOS_ROOT)
    except (PermissionError, FileNotFoundError):
        available = []

    error_msg = f"Error: Project directory '{path_val}' not found in {REPOS_ROOT}."
    if available:
        error_msg += f"\nAvailable in {REPOS_ROOT}: {', '.join(available)}"
    raise ValueError(error_msg)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def workdays_in_range(start_date: str, end_date: str):
    """Return a list of YYYY-MM-DD strings for Mon-Fri in [start_date, end_date]."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:  # 0=Mon … 4=Fri
            days.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return days


def nearest_date_with_commits(target: str, commit_map: dict, max_lookback: int = 10):
    """
    Given a target YYYY-MM-DD and a {date: [msgs]} map, return the nearest
    date key that has commits, searching up to max_lookback workdays in each
    direction (prefer future, then past).
    """
    target_dt = datetime.strptime(target, "%Y-%m-%d")
    for delta in range(1, max_lookback + 1):
        for sign in (1, -1):
            candidate_dt = target_dt + timedelta(days=delta * sign)
            # Skip weekends when walking
            while candidate_dt.weekday() >= 5:
                candidate_dt += timedelta(days=sign)
            candidate = candidate_dt.strftime("%Y-%m-%d")
            if candidate in commit_map:
                return candidate
    return None


# ---------------------------------------------------------------------------
# Git log retrieval
# ---------------------------------------------------------------------------

def fetch_raw_logs(path: str, start_date: str, end_date: str) -> str:
    """Run git log and return raw stdout."""
    cmd = [
        "git", "-C", path, "log",
        "--author=Johnson",
        f"--since={start_date}",
        f"--until={end_date}",
        "--no-merges",
        "--pretty=format:%ad | %s",
        "--date=short",
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def build_commit_map(raw_logs: str) -> dict:
    """Parse raw git log lines into {date: [subject, ...]} dict."""
    commit_map = defaultdict(list)
    for line in raw_logs.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " | " in line:
            date_part, subject = line.split(" | ", 1)
            commit_map[date_part.strip()].append(subject.strip())
    return dict(commit_map)


def get_commit_map_with_lookback(path: str, start_date: str, end_date: str,
                                  lookback_days: int = 14) -> dict:
    """
    Fetch commits in [start_date, end_date]. If empty, extend the search
    window backward so date-shifting can still find nearby commits.
    """
    raw = fetch_raw_logs(path, start_date, end_date)
    commit_map = build_commit_map(raw)

    if not commit_map:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        extended_start = (start_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        print(f"# No commits in range; extending lookback to {extended_start}", file=sys.stderr)
        raw = fetch_raw_logs(path, extended_start, end_date)
        commit_map = build_commit_map(raw)

    return commit_map


# ---------------------------------------------------------------------------
# Scaffold builder
# ---------------------------------------------------------------------------

def build_scaffold(project_name: str, commit_map: dict,
                   workdays: list) -> list:
    """
    Return a list of lines describing each workday's commits.
    Days without commits are marked [SHIFTED FROM <date>] and reference
    the nearest day that has commits.
    """
    lines = [f"=== Project: {project_name} ==="]

    for day in workdays:
        if day in commit_map:
            subjects = commit_map[day]
            lines.append(f"[DATE: {day}]")
            for s in subjects:
                lines.append(f"  - {s}")
        else:
            source = nearest_date_with_commits(day, commit_map)
            if source:
                subjects = commit_map[source]
                lines.append(f"[DATE: {day}] [SHIFTED FROM: {source}]")
                for s in subjects:
                    lines.append(f"  - {s}")
            else:
                lines.append(f"[DATE: {day}] [NO COMMITS FOUND NEARBY]")

    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Git Log Reporter")
    parser.add_argument("nickname", nargs="?", help="Project nickname (or 'all')")
    parser.add_argument("start",    nargs="?", help="Start date (YYYY-MM-DD)")
    parser.add_argument("end",      nargs="?", help="End date (YYYY-MM-DD)")

    parser.add_argument("--project", help="Project nickname (or 'all')")
    parser.add_argument("--start",   dest="flag_start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end",     dest="flag_end",   help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    nickname = args.project or args.nickname
    start    = args.flag_start or args.start
    end      = args.flag_end   or args.end

    if not nickname or not start or not end:
        parser.print_help()
        sys.exit(1)

    config   = load_config()
    workdays = workdays_in_range(start, end)

    def scan_project(name: str):
        """Scan one project and print its scaffold. Errors are non-fatal."""
        try:
            path = resolve_path(name, config)
            commit_map = get_commit_map_with_lookback(path, start, end)
            scaffold = build_scaffold(name, commit_map, workdays)
            print("\n".join(scaffold))
            print()
        except Exception as e:
            print(f"# Warning: Could not scan {name}: {e}", file=sys.stderr)

    try:
        if nickname.lower() == "all":
            # Run all projects defined in config.json
            for name in config:
                scan_project(name)
        else:
            # Support comma-separated list, e.g. "SagePlus,Website"
            names = [n.strip() for n in nickname.split(",") if n.strip()]
            for name in names:
                scan_project(name)

    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
