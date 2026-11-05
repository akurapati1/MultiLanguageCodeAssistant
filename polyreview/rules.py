"""Finding model + language detection + shared (language-independent) checks."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SEVERITY = {"high": 10, "medium": 4, "low": 1}
EXT = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".ts": "javascript", ".tsx": "javascript", ".java": "java", ".go": "go"}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    line: int
    message: str
    suggestion: str = ""


def detect_language(path: str | Path, text: str = "") -> str | None:
    lang = EXT.get(Path(path).suffix.lower())
    if lang or not text:
        return lang
    if re.search(r"^\s*def \w+\(|^\s*import \w+$|^\s*from \w+ import", text, re.M):
        return "python"
    if re.search(r"\bpackage main\b|\bfunc \w+\(", text):
        return "go"
    if re.search(r"\bpublic (static )?(class|void)\b", text):
        return "java"
    if re.search(r"\bfunction\b|=>|\bconst \w+ =", text):
        return "javascript"
    return None


SECRETS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"), "hard-coded credential"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "API key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "GitHub token"),
]
PLACEHOLDER = re.compile(r"(?i)(example|changeme|your[_-]|xxx|<.*>|\$\{|os\.environ|getenv|process\.env)")


def generic_checks(text: str) -> list[Finding]:
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        for pat, what in SECRETS:
            if pat.search(line) and not PLACEHOLDER.search(line):
                out.append(Finding("SEC001", "high", i, f"Possible {what} committed in source", "Load secrets from environment variables or a secret manager and rotate this one."))
        if len(line) > 140:
            out.append(Finding("STY001", "low", i, f"Line is {len(line)} characters long", "Wrap or extract to keep lines under ~120 characters."))
        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line):
            out.append(Finding("STY002", "low", i, "Unresolved TODO/FIXME marker", "Track it in an issue or resolve it."))
    if len(lines) > 600:
        out.append(Finding("STY003", "medium", 1, f"File has {len(lines)} lines", "Split into smaller modules."))
    return out


def block_lengths(text: str, header: re.Pattern) -> list[tuple[int, int, str]]:
    """For brace languages: (start_line, length, name) of blocks opened on lines matching `header`."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        m = header.search(line)
        if not m:
            continue
        depth, started = 0, False
        for j in range(i, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            started = started or "{" in lines[j]
            if started and depth <= 0:
                out.append((i + 1, j - i + 1, m.group(1)))
                break
    return out
