from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import other_rules, python_rules
from .llm import LLM, LLMError, get_llm
from .rules import EXT, SEVERITY, Finding, detect_language, generic_checks

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target", ".idea"}
CHECKERS = {"python": python_rules.check, "javascript": other_rules.javascript, "java": other_rules.java, "go": other_rules.go}


@dataclass
class FileReport:
    path: str
    language: str
    lines: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        penalty = sum(SEVERITY[f.severity] for f in self.findings)
        return max(0, 100 - round(100 * penalty / max(self.lines, 40) * 2))


def review_text(text: str, path: str = "<stdin>", language: str | None = None) -> FileReport | None:
    lang = language or detect_language(path, text)
    if not lang:
        return None
    findings = CHECKERS[lang](text) + generic_checks(text)
    unique = {(f.rule, f.line): f for f in reversed(findings)}   # one finding per rule per line
    return FileReport(str(path), lang, len(text.splitlines()), sorted(unique.values(), key=lambda f: (f.line, f.rule)))


def review_path(path: str | Path) -> list[FileReport]:
    p = Path(path)
    files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in EXT and not (SKIP_DIRS & set(f.parts)))
    out = []
    for f in files:
        r = review_text(f.read_text(errors="replace"), str(f))
        if r:
            out.append(r)
    return out


def explain(finding: Finding, text: str, llm: LLM | None = None, context: int = 3) -> str | None:
    llm = llm or get_llm()
    if not llm.available:
        return None
    lines = text.splitlines()
    snippet = "\n".join(lines[max(0, finding.line - 1 - context):finding.line + context])
    try:
        return llm.complete(f"Rule {finding.rule}: {finding.message}\nCode:\n{snippet}\nIn 2 sentences explain why this matters here and show the minimal fix.",
                            system="You are a senior code reviewer. Do not invent code that is not shown.", max_tokens=200).strip()
    except LLMError:
        return None


def to_markdown(reports: list[FileReport]) -> str:
    total = [f for r in reports for f in r.findings]
    o = ["# Code review", "", f"{len(reports)} file(s), {len(total)} finding(s): " + ", ".join(f"{s} {sum(f.severity == s for f in total)}" for s in SEVERITY), ""]
    for r in sorted(reports, key=lambda r: r.score):
        o += [f"## {r.path} ({r.language}, {r.lines} lines) - score {r.score}/100"]
        o += [f"- **{f.severity.upper()}** `{f.rule}` line {f.line}: {f.message}" + (f" -> {f.suggestion}" if f.suggestion else "") for f in r.findings] or ["- no findings"]
        o.append("")
    return "\n".join(o)


def to_json(reports: list[FileReport]) -> str:
    return json.dumps([{**{k: v for k, v in asdict(r).items()}, "score": r.score} for r in reports], indent=1)
