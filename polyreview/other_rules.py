"""Regex/brace-based checks for JavaScript/TypeScript, Java and Go (no external parsers)."""
from __future__ import annotations

import re

from .rules import Finding, block_lengths

JS_FN = re.compile(r"(?:function\s+(\w+)\s*\(|(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{)")
JAVA_METHOD = re.compile(r"^\s*(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\],\s]+?\s+(\w+)\s*\([^)]*\)\s*(?:throws [\w, ]+)?\{")
GO_FUNC = re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(")


def _scan(text: str, rules: list[tuple[str, str, str, str, str]], skip_comments: tuple[str, ...] = ("//", "*", "/*")) -> list[Finding]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith(skip_comments):
            continue
        for rule, sev, pattern, msg, fix in rules:
            if re.search(pattern, line):
                out.append(Finding(rule, sev, i, msg, fix))
    return out


def javascript(text: str) -> list[Finding]:
    out = _scan(text, [
        ("JS010", "medium", r"(?<![\w$.])var\s+\w+", "`var` has function scope and hoisting surprises", "Use const/let."),
        ("JS020", "medium", r"[^=!<>]==[^=]|!=[^=]", "Loose equality (==/!=) coerces types", "Use === / !==."),
        ("JS030", "high", r"\beval\s*\(|new Function\s*\(", "Dynamic code execution", "Avoid eval/new Function; parse data with JSON.parse."),
        ("JS040", "low", r"console\.(log|debug)\(", "console.log left in code", "Use a logger or remove before shipping."),
        ("JS050", "medium", r"catch\s*(\([^)]*\))?\s*\{\s*\}", "Empty catch block hides failures", "Handle or at least log the error."),
        ("JS060", "high", r"\.innerHTML\s*=", "Assigning innerHTML can enable XSS", "Use textContent or sanitise input."),
        ("JS070", "low", r":\s*any\b", "TypeScript `any` disables type checking", "Use a precise type or `unknown`."),
    ])
    for line, length, name in block_lengths(text, JS_FN):
        if length > 60:
            out.append(Finding("JS011", "medium", line, f"{name or 'anonymous function'} is {length} lines long", "Split into smaller functions."))
    return out


def java(text: str) -> list[Finding]:
    out = _scan(text, [
        ("JV010", "low", r"System\.(out|err)\.print", "System.out used for logging", "Use SLF4J/java.util.logging."),
        ("JV020", "medium", r"catch\s*\(\s*(Exception|Throwable)\s+\w+\s*\)", "Catching Exception/Throwable is too broad", "Catch the specific exceptions you can handle."),
        ("JV030", "medium", r"printStackTrace\s*\(", "printStackTrace() bypasses logging", "Log with context via your logger."),
        ("JV040", "high", r"\"[^\"]*\"\s*==\s*\w+|\w+\s*==\s*\"[^\"]*\"", "String compared with ==", "Use .equals() (or Objects.equals)."),
        ("JV050", "medium", r"catch\s*\([^)]*\)\s*\{\s*\}", "Empty catch block", "Handle or log the exception."),
        ("JV060", "medium", r"public\s+static\s+(?!final)[\w<>\[\]]+\s+\w+\s*(=|;)", "Public mutable static field", "Make it final or encapsulate it."),
        ("JV070", "high", r"\.execute(Query|Update)?\s*\(.*\+", "SQL built by string concatenation", "Use PreparedStatement with parameters."),
    ])
    for line, length, name in block_lengths(text, JAVA_METHOD):
        if length > 50:
            out.append(Finding("JV011", "medium", line, f"Method {name}() is {length} lines long", "Extract helper methods."))
    return out


def go(text: str) -> list[Finding]:
    out = _scan(text, [
        ("GO010", "high", r"^\s*_\s*(,\s*_\s*)?=\s*\w+[\w.]*\(", "Error/return value discarded with `_ =`", "Handle the error explicitly."),
        ("GO020", "medium", r"\bpanic\(", "panic() in library code crashes the caller", "Return an error instead."),
        ("GO030", "low", r"\bfmt\.Print(ln|f)?\(", "fmt.Print used for output", "Use a structured logger."),
        ("GO040", "medium", r"\bgo\s+func\s*\(", "Goroutine launched inline - check lifecycle and error handling", "Use errgroup / context cancellation."),
        ("GO050", "high", r"exec\.Command\(\s*\"(sh|bash)\"\s*,\s*\"-c\"", "Shell command execution", "Pass arguments directly to exec.Command."),
    ])
    for line, length, name in block_lengths(text, GO_FUNC):
        if length > 60:
            out.append(Finding("GO011", "medium", line, f"func {name} is {length} lines long", "Split into smaller functions."))
    return out
