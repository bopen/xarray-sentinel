COV_REPORT = html


default: fix-code-style unit-test doc-test

fix-code-style:
	black .
	isort .

unit-test:
	python -m pytest --cov=. --cov-report=$(COV_REPORT) tests/

doc-test:
	python -m pytest --cov=. --cov-report=$(COV_REPORT) README.md

code-quality:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy --strict .

code-style:
	black --check .
	isort --check .
