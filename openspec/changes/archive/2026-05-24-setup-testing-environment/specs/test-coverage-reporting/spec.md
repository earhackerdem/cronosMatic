## ADDED Requirements

### Requirement: pytest-cov plugin drives coverage collection
The project SHALL use `pytest-cov` as the coverage plugin, invoked via pytest flags, replacing the separate `coverage run` + `coverage report` shell commands.

#### Scenario: pytest-cov is listed as a dev dependency
- **WHEN** `uv sync --group dev` is run
- **THEN** `pytest-cov` is installed in the virtual environment

#### Scenario: Coverage is collected through pytest directly
- **WHEN** `backend/scripts/test.sh` is executed
- **THEN** coverage data is collected as part of the pytest invocation without a separate `coverage run` wrapper

### Requirement: Terminal report shows missing lines on every test run
The test script SHALL pass `--cov-report=term-missing` so that lines not covered by any test are printed to the terminal after each run.

#### Scenario: Terminal output includes missing-line coverage table
- **WHEN** `backend/scripts/test.sh` finishes
- **THEN** a coverage table with a "Missing" column is printed to stdout

### Requirement: HTML coverage report is generated on every test run
The test script SHALL pass `--cov-report=html` so that an HTML report is produced in `htmlcov/` after each run.

#### Scenario: htmlcov/ directory is created after test run
- **WHEN** `backend/scripts/test.sh` finishes
- **THEN** `backend/htmlcov/index.html` exists and is browsable

### Requirement: htmlcov/ directory is excluded from version control
The root `.gitignore` SHALL contain an entry for `htmlcov/` so the generated HTML report is never committed.

#### Scenario: htmlcov/ is gitignored
- **WHEN** `git status` is run after a test run that generated `htmlcov/`
- **THEN** the `htmlcov/` directory does not appear as an untracked file
