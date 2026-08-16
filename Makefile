.PHONY: verify validate snapshot no-todos
verify:
	python scripts/verify.py
validate:
	python scripts/validate_curriculum.py
snapshot:
	python scripts/context_snapshot.py
no-todos:
	python scripts/check_no_todos.py
