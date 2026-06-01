PROJECT := xarray-sentinel
CONDA := conda
CONDAFLAGS :=
COV_REPORT := html
PYTHON := uv run --frozen

default: qa unit-tests type-check

qa:
	$(PYTHON) -m pre_commit run --all-files

unit-tests:
	$(PYTHON) -m pytest -vv --cov=. --cov-report=$(COV_REPORT)

type-check:
	$(PYTHON) -m mypy --strict .

conda-env-update:
	$(CONDA) install -y -c conda-forge conda-merge
	$(CONDA) run conda-merge environment.yml ci/environment-ci.yml > ci/combined-environment-ci.yml
	$(CONDA) env update $(CONDAFLAGS) -f ci/combined-environment-ci.yml

docker-build:
	docker build -t $(PROJECT) .

docker-run:
	docker run --rm -ti -v $(PWD):/srv $(PROJECT)

docs-build:
	cp README.md docs/. && cd docs && rm -fr _api && make clean && make html

doc-tests:
	$(PYTHON) -m pytest -vv --doctest-glob="*.md" --doctest-glob="*.rst" README.md

integration-tests:
	$(PYTHON) -m pytest -vv --cov=. --cov-report=$(COV_REPORT) --log-cli-level=INFO tests/integration*.py
