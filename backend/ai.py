import os
import requests

MODEL = os.getenv("DRIFTGUARD_OLLAMA_MODEL", "").strip()

def fallback_explanation(finding: dict) -> str:
    templates = {
        "api-drift": (
            "This can cause a runtime 404/405 or broken UI flow. "
            "Confirm the intended API contract, then make the frontend request and backend route use the same path and HTTP method."
        ),
        "secret": (
            "Credentials in source control can be copied from Git history even after the visible line is removed. "
            "Rotate the credential, move it to an environment variable, and remove it from committed history if necessary."
        ),
        "env-drift": (
            "Undocumented environment variables make local setup and deployment fragile. "
            "Add the variable name to .env.example with a safe placeholder and describe what it controls."
        ),
        "tech-debt": (
            "TODO/FIXME comments are useful during development but can become invisible debt. "
            "Either resolve it now or convert it into a tracked issue with an owner and priority."
        ),
        "debug-code": (
            "Debug output can leak data, create noisy logs, or slow down hot paths. "
            "Remove it or replace it with structured logging at an appropriate log level."
        ),
        "docs-drift": (
            "Documentation drift slows onboarding and causes users to follow invalid setup steps. "
            "Update the file reference so the README matches the repository's current structure."
        ),
    }
    base = templates.get(finding.get("type"), "Review this finding and align the code with the intended project contract.")
    return base + " Suggested action: " + finding.get("suggestion", "")

def explain_finding(finding: dict) -> dict:
    if not MODEL:
        return {"source": "built-in", "text": fallback_explanation(finding)}

    prompt = f"""
You are a senior software reliability engineer.
Explain this repository finding in at most 120 words.
Be concrete. Include: why it matters, likely failure mode, and safest fix.

Finding:
Type: {finding.get('type')}
Severity: {finding.get('severity')}
File: {finding.get('file')}:{finding.get('line')}
Title: {finding.get('title')}
Message: {finding.get('message')}
Suggested fix: {finding.get('suggestion')}
""".strip()

    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        if text:
            return {"source": f"ollama:{MODEL}", "text": text}
    except Exception:
        pass

    return {"source": "built-in", "text": fallback_explanation(finding)}
