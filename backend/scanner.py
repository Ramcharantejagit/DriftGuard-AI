from pathlib import Path
import hashlib
import os
import re
from typing import List, Dict

IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".next", ".idea", ".vscode"
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json",
    ".md", ".txt", ".env", ".yml", ".yaml", ".toml"
}

SECRET_PATTERNS = [
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Generic API key", re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{10,}['\"]")),
]

BACKEND_ROUTE_PATTERNS = [
    re.compile(r'@(?:app|router)\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'),
    re.compile(r'@(?:app|bp)\.route\(\s*["\']([^"\']+)["\']'),
]

FRONTEND_CALL_PATTERNS = [
    re.compile(r'fetch\(\s*["\']([^"\']+)["\']'),
    re.compile(r'axios\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']'),
]

ENV_PATTERNS = [
    re.compile(r'os\.getenv\(\s*["\']([A-Z0-9_]+)["\']'),
    re.compile(r'os\.environ\.get\(\s*["\']([A-Z0-9_]+)["\']'),
    re.compile(r'process\.env\.([A-Z0-9_]+)'),
]

def _finding(kind, severity, title, message, file, line=1, suggestion=""):
    raw = f"{kind}|{file}|{line}|{title}|{message}"
    fid = hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:12]
    return {
        "id": fid,
        "type": kind,
        "severity": severity,
        "title": title,
        "message": message,
        "file": file,
        "line": line,
        "suggestion": suggestion,
        "fingerprint": fid,
    }

def _iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name.startswith(".env"):
            try:
                if path.stat().st_size <= 1_000_000:
                    yield path
            except OSError:
                pass

def _rel(path: Path, root: Path):
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path)

def scan_project(root_path: str) -> Dict:
    root = Path(root_path)
    findings: List[dict] = []
    files = list(_iter_text_files(root))

    backend_routes = set()
    frontend_calls = []
    used_env = set()
    env_example = set()
    readme_text = ""
    all_files_rel = {_rel(p, root) for p in files}

    file_count = 0
    line_count = 0

    for path in files:
        file_count += 1
        rel = _rel(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        line_count += text.count("\n") + 1

        if path.name.lower() in {"readme.md", "readme.txt"}:
            readme_text += "\n" + text

        if path.name == ".env.example":
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    env_example.add(line.split("=", 1)[0].strip())

        for regex in BACKEND_ROUTE_PATTERNS:
            for m in regex.finditer(text):
                backend_routes.add(m.group(1))

        for regex in FRONTEND_CALL_PATTERNS:
            for m in regex.finditer(text):
                endpoint = m.group(1)
                if endpoint.startswith("/"):
                    line = text[:m.start()].count("\n") + 1
                    frontend_calls.append((endpoint.split("?")[0], rel, line))

        for regex in ENV_PATTERNS:
            used_env.update(regex.findall(text))

        for idx, line in enumerate(text.splitlines(), start=1):
            line_stripped = line.strip()

            if "TODO" in line or "FIXME" in line:
                findings.append(_finding(
                    "tech-debt", "low", "Technical debt marker",
                    line_stripped[:180], rel, idx,
                    "Convert the note into a tracked issue or resolve it before release."
                ))

            debug_hit = (
                re.search(r"\bconsole\.log\s*\(", line) or
                re.search(r"\bprint\s*\(", line)
            )
            if debug_hit and "driftguard-ignore" not in line:
                findings.append(_finding(
                    "debug-code", "low", "Debug statement found",
                    line_stripped[:180], rel, idx,
                    "Remove or replace this with structured logging before production."
                ))

            for secret_name, regex in SECRET_PATTERNS:
                if regex.search(line):
                    findings.append(_finding(
                        "secret", "critical", f"Potential {secret_name}",
                        "A value that resembles a credential is present in source code.",
                        rel, idx,
                        "Move the secret to an environment variable and rotate the exposed credential."
                    ))

    # API drift
    normalized_routes = set()
    for route in backend_routes:
        normalized_routes.add(route.rstrip("/") or "/")

    for endpoint, rel, line in frontend_calls:
        norm = endpoint.rstrip("/") or "/"
        # tolerate path parameters by comparing static prefixes
        exact = norm in normalized_routes
        loose = any(
            r == norm or
            re.sub(r"\{[^/]+\}", "X", r) == re.sub(r"\d+|[A-Za-z0-9_-]{6,}", "X", norm)
            for r in normalized_routes
        )
        if not exact and not loose:
            findings.append(_finding(
                "api-drift", "high", "Frontend/backend API drift",
                f"Frontend calls '{endpoint}', but no matching backend route was found.",
                rel, line,
                "Create the backend route or update the frontend request path."
            ))

    # Environment drift
    missing_env = sorted(v for v in used_env if v not in env_example)
    for var in missing_env:
        findings.append(_finding(
            "env-drift", "medium", "Environment variable undocumented",
            f"{var} is used in code but is missing from .env.example.",
            ".env.example", 1,
            f"Add {var}= to .env.example so setup requirements stay documented."
        ))

    # README file references
    if readme_text:
        referenced = set(re.findall(r'`([^`\n]+\.[A-Za-z0-9]{1,8})`', readme_text))
        for ref in sorted(referenced):
            clean = ref.strip().replace("\\", "/")
            if "/" in clean or "." in clean:
                if clean not in all_files_rel and not (root / clean).exists():
                    if not clean.startswith(("http://", "https://")):
                        findings.append(_finding(
                            "docs-drift", "medium", "README may reference a missing file",
                            f"README references '{clean}', but that file was not found.",
                            "README.md", 1,
                            "Update the documentation or restore/rename the referenced file."
                        ))

    # Remove duplicates
    unique = {}
    for f in findings:
        unique[f["fingerprint"]] = f
    findings = list(unique.values())

    sev_weight = {"low": 2, "medium": 6, "high": 12, "critical": 25}
    raw_score = sum(sev_weight.get(f["severity"], 1) for f in findings)
    risk_score = min(100, raw_score)

    counts = {k: 0 for k in ["critical", "high", "medium", "low"]}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    findings.sort(key=lambda x: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 9),
        x["file"], x["line"]
    ))

    return {
        "root": str(root),
        "risk_score": risk_score,
        "findings": findings,
        "stats": {
            "files_scanned": file_count,
            "lines_scanned": line_count,
            "findings": len(findings),
            **counts,
        },
        "routes_found": sorted(backend_routes),
        "frontend_calls_found": sorted({x[0] for x in frontend_calls}),
    }
