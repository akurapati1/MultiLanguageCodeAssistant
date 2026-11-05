# PolyReview

A fast, dependency-free **code reviewer for Python, JavaScript/TypeScript, Java and Go** that you can run locally or as a CI gate. It finds the problems
reviewers flag most - security smells, error-handling mistakes, complexity - gives a **0-100 score per file** and a concrete fix for every finding.

```text
$ python -m polyreview samples/bad.js
## samples/bad.js (javascript, 9 lines) - score 0/100
- **MEDIUM** `JS010` line 1: `var` has function scope and hoisting surprises -> Use const/let.
- **MEDIUM** `JS010` line 3: `var` has function scope and hoisting surprises -> Use const/let.
- **MEDIUM** `JS020` line 4: Loose equality (==/!=) coerces types -> Use === / !==.
- **LOW** `JS040` line 4: console.log left in code -> Use a logger or remove before shipping.
- **MEDIUM** `JS050` line 6: Empty catch block hides failures -> Handle or at least log the error.
- **HIGH** `JS060` line 7: Assigning innerHTML can enable XSS -> Use textContent or sanitise input.
- **HIGH** `JS030` line 8: Dynamic code execution -> Avoid eval/new Function; parse data with JSON.parse.
...
```
(`python -m polyreview samples` on the four bundled bad-code samples: **29 findings - 11 high, 11 medium, 7 low**.)

## Rule coverage
| Language | How | Examples |
| --- | --- | --- |
| **Python** | real AST analysis | cyclomatic complexity, nesting depth, function length/parameters, mutable default args, bare/empty `except`, `eval/exec`, `os.system`, `shell=True`, `== None`, star imports, shadowed builtins, missing docstrings, syntax errors |
| **JS / TS** | patterns + brace matching | `var`, loose `==`, `eval`, `innerHTML` (XSS), empty `catch`, `console.log`, `any`, long functions |
| **Java** | patterns + brace matching | string `==`, SQL built with `+`, broad/empty `catch`, `printStackTrace`, mutable `public static`, long methods |
| **Go** | patterns + brace matching | discarded errors (`_ =`), `panic`, inline goroutines, `sh -c`, long funcs |
| **All** | | hard-coded secrets (AWS keys, private keys, `password = "..."`, `sk-...`, GitHub tokens) with placeholder/env-var suppression, long lines, TODO markers |

Findings are de-duplicated per rule and line; the score weighs severity (high 10 / medium 4 / low 1) by file size.

## Use
```bash
python -m polyreview src/                       # Markdown report, worst files first
python -m polyreview src/ --format json         # machine-readable
python -m polyreview src/ --fail-under 70       # exit code 1 -> CI gate
python -m unittest discover -s tests -t . -v    # 12 tests
```

## Optional AI explanations
`polyreview.review.explain(finding, source)` asks a model (Anthropic / OpenAI-compatible / Ollama via env vars) why the finding matters *in that code*, sending only the
surrounding lines. The deterministic rules decide what is a finding; the model never invents issues. The Ollama `Modelfile` for a local "code teacher" persona and the original Gradio script are kept in
[`ollama/`](ollama/) and [`legacy/`](legacy/).

> Static heuristics have false positives and negatives; treat the output as a reviewer's checklist, not a verdict.
