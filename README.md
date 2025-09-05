# Game Automation Framework

A Python-based automation tool to capture and process game screenshots for multiple games, languages, and modes.

---

## Prerequisites

* Python 3.11+
* [Poetry](https://python-poetry.org/docs/#installation) (for dependency management)
* VSCode recommended

---

## Setup

1. **Clone the repo:**

```bash
git clone <repo-url>
cd <repo-folder>
```

2. **Install dependencies with Poetry:**

```bash
poetry install
```

3. **Activate virtual environment:**

```bash
poetry shell
```

---

## Run Automation

Use the Makefile shortcut:

```bash
make run
```

Or directly via Python:

```bash
poetry run python src/main.py
```

### User Inputs

The script will ask for:

* Delete previous reports?
* Environment (`dev`, `sandbox`, `production`)
* Game selection
* Language
* Currency
* Execution mode (`manual` or `automatic`)
* Game modes to check

---

## Outputs

* **Reports:** `_output-reports/<token>_<language>/report.csv`
* **Logs:** `_output-reports/<token>_<language>/log_activity.log`
* **Screenshots:** `captures/<gameCode>_<language>.png`

> Each game folder in `_output-reports` contains detailed CSV report and logs.

---

## Notes

* Ensure you are inside the Poetry environment (`poetry shell`) before running.
* Screenshots are stored separately in the `captures/` folder.
* CSV reports summarize success/failure per mode.
