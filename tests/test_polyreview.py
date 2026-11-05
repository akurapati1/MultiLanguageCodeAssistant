import tempfile
import unittest
from pathlib import Path

from polyreview.llm import MockLLM
from polyreview.python_rules import check, complexity
from polyreview.review import explain, review_path, review_text, to_json, to_markdown
from polyreview.rules import Finding, detect_language

S = Path(__file__).parents[1] / "samples"
rules = lambda fs: {f.rule for f in fs}


class Language(unittest.TestCase):
    def test_detection(self):
        self.assertEqual([detect_language(p) for p in ("a.py", "b.tsx", "C.java", "d.go", "e.rb")], ["python", "javascript", "java", "go", None])
        self.assertEqual(detect_language("noext", "def f(x):\n    return x"), "python")
        self.assertEqual(detect_language("noext", "package main\nfunc main() {}"), "go")


class PythonRules(unittest.TestCase):
    def test_sample_triggers_expected_rules(self):
        r = review_text((S / "bad.py").read_text(), "bad.py")
        self.assertEqual(rules(r.findings), {"PY070", "SEC001", "PY012", "PY013", "PY020", "PY030", "PY080", "PY060", "PY040", "PY090", "PY091", "PY050"})
        self.assertEqual(len([f for f in r.findings if f.rule == "SEC001"]), 1)   # deduplicated per line
        self.assertEqual(r.score, 0)

    def test_complexity_counts_branches_and_boolops(self):
        import ast
        fn = ast.parse("def f(x):\n    if x and x > 1 or x < -1:\n        return [i for i in x if i]\n    for a in x:\n        pass\n").body[0]
        self.assertEqual(complexity(fn), 1 + 1 + 2 + 1 + 1)   # base, if, and+or (2), comprehension (its inline `if` is part of it), for

    def test_clean_code_scores_100_and_syntax_errors_reported(self):
        clean = review_text('def add(a, b):\n    """Add."""\n    return a + b\n', "ok.py")
        self.assertEqual((clean.findings, clean.score), ([], 100))
        self.assertEqual(check("def broken(:\n")[0].rule, "PY000")

    def test_safe_patterns_not_flagged(self):
        r = review_text('import os\nKEY = os.environ["API_KEY"]\npassword = "example-placeholder-value"\nx = 1\nif x is None:\n    pass\n', "s.py")
        self.assertEqual(r.findings, [])


class OtherLanguages(unittest.TestCase):
    def test_javascript(self):
        self.assertEqual(rules(review_text((S / "bad.js").read_text(), "bad.js").findings), {"JS010", "JS020", "JS030", "JS040", "JS050", "JS060"})
        self.assertNotIn("JS020", rules(review_text("if (a === b && c !== d) {}\n", "x.js").findings))

    def test_java(self):
        self.assertEqual(rules(review_text((S / "Bad.java").read_text(), "Bad.java").findings), {"JV010", "JV020", "JV030", "JV040", "JV060", "JV070"})

    def test_go(self):
        self.assertEqual(rules(review_text((S / "bad.go").read_text(), "bad.go").findings), {"GO010", "GO020", "GO030", "GO040"})

    def test_long_functions_found_in_brace_languages(self):
        body = "\n".join(f"  x{i} = {i};" for i in range(70))
        self.assertIn("JS011", rules(review_text(f"function big() {{\n{body}\n}}\n", "big.js").findings))

    def test_generic_secrets(self):
        r = review_text('const k = "AKIAABCDEFGHIJKLMNOP";\n', "k.js")
        self.assertEqual(rules(r.findings), {"SEC001"})
        self.assertEqual(review_text("// password = 'hunter2hunter2'\n", "c.js").findings[0].rule, "SEC001")


class Directory(unittest.TestCase):
    def test_scan_skips_vendor_dirs_and_formats(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "node_modules").mkdir()
            (Path(d) / "node_modules" / "x.js").write_text("var a = 1;")
            (Path(d) / "src").mkdir()
            (Path(d) / "src" / "a.js").write_text("var a = 1;\n")
            (Path(d) / "notes.txt").write_text("var a")
            reports = review_path(d)
            self.assertEqual([Path(r.path).name for r in reports], ["a.js"])
            self.assertIn("JS010", to_markdown(reports))
            self.assertIn('"rule": "JS010"', to_json(reports))


class Explain(unittest.TestCase):
    def test_llm_explanation_uses_code_context(self):
        llm = MockLLM(lambda s, p: "It matters because...")
        f = Finding("JS010", "medium", 2, "`var` has function scope", "Use const/let.")
        self.assertEqual(explain(f, "a\nvar x = 1;\nb", llm), "It matters because...")
        self.assertIn("var x = 1;", llm.calls[0][1])
        self.assertIsNone(explain(f, "x", MockLLM()))


if __name__ == "__main__":
    unittest.main()
