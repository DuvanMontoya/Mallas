from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_domain_contexts_are_present() -> None:
    expected = {
        "identity",
        "institutions",
        "curriculum",
        "rules",
        "audit",
        "student_records",
        "offerings",
        "planning",
        "optimization",
        "governance",
        "imports",
        "notifications",
        "analytics",
    }
    assert {path.name for path in (ROOT / "modules").iterdir() if path.is_dir()} >= expected
