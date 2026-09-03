# Firmware Regression Intelligence (FRI)

Firmware Regression Intelligence (FRI) is an intelligent firmware regression analysis framework that helps BIOS and firmware engineers identify the most probable commits responsible for regressions between a known-good and a known-bad build.

Instead of manually reviewing hundreds of commits, FRI combines Git history, commit metadata, firmware-aware classification, diff analysis, and configurable failure profiles to rank the most likely regression candidates.

---

# Features

- Analyze firmware regressions between two Git revisions
- Parse firmware commit metadata (Jira, Merge Requests, intent)
- Firmware-aware subsystem classification
- Diff analysis with firmware-specific heuristics
- Candidate scoring and ranking
- Module-level aggregation
- Interactive HTML dashboard
- JSON export for automation and CI
- Git bisect recommendations
- Extensible YAML-based configuration

---

# Project Architecture

```
CLI
 ¦
 ?
Investigation Engine
 ¦
 +-- Git Collector
 +-- Commit Parser
 +-- Firmware Classifier
 +-- Diff Analyzer
 +-- Regression Scorer
 +-- Candidate Engine
 +-- Module Analyzer
 ¦
 ?
Regression Report
 ¦
 +-- Console Report
 +-- HTML Report
 +-- JSON Report
```

---

# Installation

Clone the repository:

```bash
git clone <repository-url>

cd fri
```

Create the development environment:

```bash
./setup.sh
```

Or install manually:

```bash
python3 -m venv venv

source venv/bin/activate

pip install -e .

pip install -e ".[dev]"
```

---

# Verify Installation

```bash
fri --help
```

Expected output:

```text
Firmware Regression Intelligence

Commands

    investigate

    doctor

    config
```

---

# Basic Usage

Investigate a firmware regression:

```bash
fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure boot
```

Generate an HTML dashboard:

```bash
fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure boot \
    --html
```

Generate a JSON report:

```bash
fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure boot \
    --json
```

Generate both reports:

```bash
fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure boot \
    --html \
    --json
```

---

# Example Workflow

```
Known Good Build
        ¦
        ?
Known Bad Build
        ¦
        ?
Collect Commits
        ¦
        ?
Parse Metadata
        ¦
        ?
Classify Firmware Domains
        ¦
        ?
Analyze Git Diffs
        ¦
        ?
Score Regression Candidates
        ¦
        ?
Aggregate Firmware Modules
        ¦
        ?
Generate Reports
```

---

# Output

FRI can generate:

- Console summary
- HTML dashboard
- JSON report

The HTML dashboard includes:

- Investigation summary
- Firmware module ranking
- Regression candidate ranking
- Evidence collected
- Git bisect recommendations
- Investigation statistics

---

# Configuration

FRI uses YAML configuration files to customize analysis.

Typical configuration includes:

- Component mapping
- Failure profiles
- Scoring rules
- Firmware domain mappings

---

# Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Useful commands:

```bash
make format

make lint

make test

make coverage

make build
```

---

# Running Tests

```bash
pytest
```

Coverage:

```bash
pytest --cov=fri
```

---

# Supported Firmware Domains

FRI currently recognizes domains such as:

- Platform
- Memory
- Boot
- PCIe
- ACPI
- Security
- RAS
- CXL
- TPM
- FIT
- PEI
- DXE
- SMM
- Networking
- Storage

Additional domains can be added through configuration.

---

# Roadmap

Future releases will include:

- GitLab integration
- Jira integration
- Jenkins integration
- REST API
- Machine learning-based scoring
- Web UI
- Plugin architecture
- Regression history database

---

# License

MIT License

---

# Author

**Saurabh Mishra**

Firmware Engineer

Firmware | UEFI | Coreboot | LinuxBoot | Datacenter Infrastructure