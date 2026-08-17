"""Small high-confidence SAST gate for dangerous execution and injection APIs."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_IGNORED_PARTS = {
    ".git",
    ".next",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "migrations",
    "tests",
}


def _ignored(path: Path, root: Path) -> bool:
    return bool(_IGNORED_PARTS.intersection(path.relative_to(root).parts))


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _python_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted((root / "apps" / "api").rglob("*.py")):
        if _ignored(path, root):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            findings.append(f"{path.relative_to(root).as_posix()}:parse:{type(exc).__name__}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = _name(node.func)
            if function in {"eval", "exec", "compile", "os.system", "pickle.loads"}:
                findings.append(f"{path.relative_to(root).as_posix()}:{node.lineno}:{function}")
            if function in {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call"}:
                if any(
                    keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in node.keywords
                ):
                    findings.append(f"{path.relative_to(root).as_posix()}:{node.lineno}:shell=True")
            if function in {"yaml.load", "yaml.unsafe_load"}:
                findings.append(f"{path.relative_to(root).as_posix()}:{node.lineno}:{function}")
    return findings


def _frontend_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted((root / "apps" / "web").rglob("*.tsx")):
        if _ignored(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if "dangerouslySetInnerHTML" in line or "innerHTML =" in line:
                findings.append(f"{path.relative_to(root).as_posix()}:{line_number}:raw-html")
            if "new Function(" in line or "eval(" in line:
                findings.append(f"{path.relative_to(root).as_posix()}:{line_number}:dynamic-code")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    findings = sorted(_python_findings(root) + _frontend_findings(root))
    if findings:
        print("SAST findings require review:")
        print("\n".join(findings))
        return 1
    print("SAST gate passed: no high-confidence dangerous execution/raw HTML findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
