from __future__ import annotations

import ast

from .rules import Finding

BRANCH = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp, ast.Assert, ast.comprehension)
BUILTINS = {"list", "dict", "set", "str", "int", "id", "type", "input", "max", "min", "sum", "len", "map", "filter", "file", "all", "any"}


def complexity(fn: ast.AST) -> int:
    n = 1
    for node in ast.walk(fn):
        if isinstance(node, BRANCH):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
    return n


def depth(node: ast.AST, level: int = 0) -> int:
    best = level
    for child in ast.iter_child_nodes(node):
        inc = isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncFor, ast.AsyncWith))
        best = max(best, depth(child, level + inc))
    return best


def check(text: str) -> list[Finding]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [Finding("PY000", "high", exc.lineno or 1, f"Syntax error: {exc.msg}", "Fix the syntax before reviewing further.")]
    out: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            c, length = complexity(node), (node.end_lineno or node.lineno) - node.lineno + 1
            if c > 15:
                out.append(Finding("PY010", "high", node.lineno, f"{node.name}() has cyclomatic complexity {c}", "Split into smaller functions; extract branches into helpers."))
            elif c > 10:
                out.append(Finding("PY010", "medium", node.lineno, f"{node.name}() has cyclomatic complexity {c}", "Consider extracting branches into helpers."))
            if length > 60:
                out.append(Finding("PY011", "medium", node.lineno, f"{node.name}() is {length} lines long", "Functions this long hide bugs; split by responsibility."))
            if len(node.args.args) + len(node.args.kwonlyargs) > 6:
                out.append(Finding("PY012", "low", node.lineno, f"{node.name}() takes many parameters", "Group related parameters in a dataclass."))
            if depth(node) > 3:
                out.append(Finding("PY013", "medium", node.lineno, f"{node.name}() nests {depth(node)} levels deep", "Use early returns / guard clauses."))
            if not ast.get_docstring(node) and not node.name.startswith("_") and length > 8:
                out.append(Finding("PY020", "low", node.lineno, f"Public function {node.name}() has no docstring", "Add a one-line docstring describing intent."))
            for d in node.args.defaults + node.args.kw_defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    out.append(Finding("PY030", "high", d.lineno, "Mutable default argument", "Default to None and create the object inside the function."))
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                out.append(Finding("PY040", "high", node.lineno, "Bare `except:` swallows KeyboardInterrupt and real bugs", "Catch specific exceptions (or `except Exception`) and log them."))
            elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                out.append(Finding("PY041", "medium", node.lineno, "Exception silently ignored (`except ...: pass`)", "At least log the exception."))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            out.append(Finding("PY050", "high", node.lineno, f"Use of {node.func.id}()", "Avoid executing dynamic code; use ast.literal_eval or a parser."))
        elif isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comp, ast.Constant) and comp.value is None:
                    out.append(Finding("PY060", "low", node.lineno, "Comparison to None with ==/!=", "Use `is None` / `is not None`."))
        elif isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            out.append(Finding("PY070", "medium", node.lineno, f"Star import from {node.module}", "Import the names you use explicitly."))
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in BUILTINS:
                    out.append(Finding("PY080", "low", node.lineno, f"Variable `{t.id}` shadows a builtin", "Rename it."))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen") and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
            out.append(Finding("PY090", "high", node.lineno, "os.system/popen builds a shell command", "Use subprocess.run([...]) with an argument list."))
        elif isinstance(node, ast.keyword) and node.arg == "shell" and isinstance(node.value, ast.Constant) and node.value.value is True:
            out.append(Finding("PY091", "high", node.value.lineno, "subprocess with shell=True", "Pass an argument list and drop shell=True."))
    return out
