# Firmware Regression Intelligence (FRI)

> FRI automatically analyzes the commits between a known-good and known-bad firmware build and intelligently prioritizes the commits and firmware modules most likely responsible for a regression.

An intelligent firmware regression investigation framework that analyzes Git commit history, firmware domains, code changes, and failure profiles to identify the commits and firmware modules most likely responsible for a regression.

---

# Overview

Firmware regression investigation can be time-consuming, especially when a regression occurs between two builds containing multiple commits.

Engineers typically need to:

- Identify the known good build
- Identify the known bad build
- Review all commits between the builds
- Analyze commit messages
- Check Jira references
- Review modified files
- Analyze code changes
- Identify affected firmware modules
- Prioritize suspicious commits
- Perform manual debugging or Git bisect

**Firmware Regression Intelligence (FRI)** automates the initial investigation and helps engineers quickly identify the most likely regression candidates.

FRI combines:

- Git commit metadata
- Commit messages
- Jira references
- Firmware domain classification
- Failure profiles (firmware boot **and** OS boot / OS handoff)
- Diff analysis and high-risk hazard detection
- Firmware keywords and path patterns
- Change size
- Commit intent
- Merge commit information

The result is a ranked list of potential regression commits along with supporting evidence and affected firmware modules.

---

# Problem Statement

Consider the following scenario:

```text
Known Good Build
       |
       |  Multiple commits
       |
       v
Known Bad Build
```

A regression is detected, for example:

```text
Boot Failure
OS Boot Failure (Linux / Windows / LinuxBoot)
```

The engineer must determine:

> Which commit introduced the regression?

Traditionally, this requires manually investigating every commit between the good and bad builds.

FRI helps reduce this investigation effort by automatically ranking commits based on firmware-aware evidence.

---

# How FRI Works

```text
                 User Input
                     |
                     v
          +---------------------+
          | Good Build / SHA    |
          | Bad Build / SHA     |
          | Failure Type        |
          +---------------------+
                     |
                     v
          +---------------------+
          | Investigation Engine|
          +---------------------+
                     |
                     v
          +---------------------+
          | Git Collector       |
          +---------------------+
                     |
                     v
          +---------------------+
          | Commit Parser       |
          +---------------------+
                     |
                     v
          +---------------------+
          | Firmware Classifier |
          +---------------------+
                     |
                     v
          +---------------------+
          | Diff Analyzer       |
          | Hazard Detector     |
          +---------------------+
                     |
                     v
          +---------------------+
          | Candidate Engine    |
          +---------------------+
                     |
                     v
          +---------------------+
          | Regression Scoring  |
          +---------------------+
                     |
                     v
          +---------------------+
          | Module Analyzer     |
          | Bisect Planner      |
          +---------------------+
                     |
                     v
          +---------------------+
          | Reports             |
          | Console             |
          | HTML                |
          | JSON                |
          +---------------------+
```

---

# Architecture

The project is organized into independent layers.

```text
fri/
│
├── analyzer/
│   ├── bisect_planner.py
│   ├── candidate_engine.py
│   ├── diff_analyzer.py
│   ├── hazard_detector.py
│   └── module_analyzer.py
│
├── classifier/
│   └── classifier.py
│
├── collector/
│   ├── build_resolver.py
│   └── git_collector.py
│
├── engine/
│   └── investigation_engine.py
│
├── parser/
│   └── commit_parser.py
│
├── report/
│   ├── console_report.py
│   ├── html_report.py
│   └── json_report.py
│
├── scorer/
│   └── regression_scorer.py
│
├── utils/
│   └── helpers.py
│
├── cli.py
├── config.py
├── constants.py
├── logger.py
├── main.py
└── models.py
```

Configuration lives under `config/`. HTML templates live under `templates/`.

---

# Key Components

## Investigation Engine

The `InvestigationEngine` orchestrates the complete regression investigation.

It coordinates:

- Git collection
- Commit parsing
- Firmware classification
- Diff analysis
- Candidate evaluation
- Candidate ranking
- Module aggregation
- Bisect / validation planning

The engine itself does not contain firmware-specific analysis logic.

---

## Git Collector

The Git Collector communicates with the firmware Git repository.

It is responsible for:

- Opening the repository
- Resolving Git references
- Resolving short SHA values
- Resolving `HEAD`
- Collecting commits between two builds
- Retrieving commit diffs

Example:

```text
Good Build : 13b5128
Bad Build  : HEAD
```

FRI resolves these references and collects all commits in the regression range.

---

## Commit Parser

The Commit Parser extracts useful metadata from commit messages.

It can identify information such as:

- Jira IDs
- Merge references
- Commit intent
- Firmware feature keywords

Examples of commit intent include:

```text
Fix
Revert
Enable
Disable
Hang
Unknown
```

---

## Firmware Classifier

The Firmware Classifier maps commits and modified files to firmware domains using `config/component_map.yaml` and commit keywords.

Example domains include:

```text
Platform
FIT
Memory
PCIe
Storage
Network
Security
Power
Boot
PEI
DXE
BDS
ACPI
OSLoader
LinuxBoot
IOMMU
```

A commit may belong to multiple domains.

Example:

```text
Primary Domain : FIT

Domains :
FIT
Platform
```

---

## Diff Analyzer and Hazard Detector

The Diff Analyzer examines the actual code changes associated with a commit.

It identifies firmware-related evidence such as:

- Firmware keywords
- Modified files, functions, and macros
- PCD / UPD symbols
- Protocol / PPI GUIDs
- Boot-services APIs
- Diff complexity

The Hazard Detector looks for high-risk change patterns that commonly *cause* regressions, for example:

```text
ExitBootServices
GetMemoryMap
SetVirtualAddressMap
ACPI tables (DSDT, MADT, SRAT, DMAR, …)
IOMMU / VT-d
PCD / UPD defaults
Timeouts / stalls
Secure Boot policy
TPM / PCR
SMM / SMI
```

This provides additional evidence beyond commit messages.

---

## Candidate Engine

The Candidate Engine combines:

```text
Commit Metadata
       +
Firmware Classification
       +
Failure Profile
       +
Diff Evidence
       +
Hazards
       |
       v
Regression Candidate
```

Each commit is converted into a `RegressionCandidate`.

The candidate contains:

- Confidence score
- Evidence
- Matching domains
- Matching files and paths
- Firmware keywords
- Hazards
- Reasons for ranking

---

# Regression Scoring

FRI uses a rule-based, multi-signal scoring system to prioritize suspicious commits.

The score is generated using independent signals so a small but precise OS-boot change can outrank a large unrelated edit.

Examples include:

| Evidence | Example |
| --- | --- |
| Failure profile match | Boot / OS-boot failure + relevant firmware domain |
| Path pattern match | `BdsDxe`, `LinuxBoot`, `AcpiTable`, `IntelVTd` |
| Profile keywords | ExitBootServices, FIT, PEI, DDR, PCD, IOMMU |
| High-risk hazards | ExitBootServices, PCD/UPD default, ACPI table, VT-d |
| Boot / OS-handoff APIs | `gBS->ExitBootServices`, `GetMemoryMap` |
| Commit intent | Fix, Revert, Enable, Disable, Hang |
| Merge commit | Commit contains multiple integrated changes |
| Jira reference | Associated tracked issue |
| Change size | Large or medium code modification |
| Diff complexity | Complexity of the code changes |
| Noise reduction | Documentation-only and comment-only diffs are down-ranked |

The final confidence score is limited to:

```text
0% - 100%
```

FRI does not claim that the highest-ranked commit is automatically the root cause.

Instead, it provides an **intelligent investigation starting point**.

---

# Example Candidate

```text
[1] 70e2e4be

Confidence : 99%

Author     : Saurabh Mishra

Jira       : UEFIRM-78402

Intent     : Unknown

Domain     : FIT

Domains    : FIT, Platform
```

Evidence:

```text
✓ Firmware keyword: FIT
✓ Firmware keyword: PLATFORM
✓ Merge commit
✓ Jira UEFIRM-78402
✓ Medium code change
```

OS-boot example:

```text
[1] 9f9435c4

Confidence : 100%

Subject    : BIOS-42: Linux OS boot hangs in ExitBootServices

Domain     : BDS

Hazards    : HIGH hazard: ExitBootServices
```

---

# Module Analysis

FRI also aggregates regression candidates into firmware modules.

Instead of only answering:

> Which commit is suspicious?

FRI also answers:

> Which firmware area is most likely affected?

Example:

```text
MOST AFFECTED MODULES

FIT                  94%
   Commits : 4
   Jira    : UEFIRM-78402

Platform             78%
   Commits : 8
   Jira    : UEFIRM-78140, UEFIRM-78324, UEFIRM-78402
```

This is useful because firmware development and debugging are often organized around module ownership.

---

# Boot phases (CPU reset → OS)

FRI triages the firmware Git window from a **good SHA** to a **failing SHA** against the real server UEFI sequence. It does not ingest OS logs.

```text
reset          CPU out of reset, microcode, FIT / AMD BIOS directory / PSP
sec            SEC, TempRamInit, FSP-T, Cache-as-RAM
pei            PEI core, PEIMs, HOBs, PPIs
memory_init    Intel FSP-M / MRC  |  AMD AGESA AmdInitPost / UMC
silicon_init   Intel FSP-S / PCH / IIO  |  AMD NBIO / DF / SMU / FCH
dxe            DXE dispatcher, firmware volumes
bds            Boot manager, consoles, ReadyToBoot
os_handoff     ExitBootServices, ACPI/SMBIOS/IOMMU, OS loader
runtime        UEFI runtime after the OS is running
resume         S3 / S0ix boot script
recovery       Recovery FV / dual-bank / capsule
```

When the hang is “no boot after flashing” and the phase is unknown:

```bash
fri phases

fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure from_reset \
    --html --json
```

The report’s **Boot Phase Triage** block says where to start (for example memory_init on Intel FSP-M vs AGESA on AMD). Narrow with `--failure memory_init`, `sec`, `amd_psp`, `intel_bootguard`, and so on.

---

# Supported Failure Types

Use `fri topics` to list every profile. Built-in `--failure` values include:

```text
boot            Firmware boot (SEC / PEI / DXE / BDS / FSP / FIT)
os_boot         Firmware changes whose *symptom* is OS handoff failure:
                ExitBootServices, memory map, ACPI, GRUB, Linux, Windows
                bootmgr, LinuxBoot. FRI still only reads the firmware Git
                repo — it does not ingest dmesg, journalctl, or kernel source.
linuxboot       LinuxBoot / u-root / kexec payload
acpi            DSDT / SSDT / MADT / SRAT / DMAR and related tables
iommu           VT-d / AMD-Vi / DMAR programming
memory          MRC / FSP memory init, DIMM, NUMA
pcie            Link training, BARs, resource allocation
network         PXE, HTTP boot, UNDI/SNP
storage         NVMe, SATA, RAID, boot disk
security        Secure Boot, Boot Guard, authenticated variables
secure_boot     OS loader verification, shim, db/dbx
measured_boot   TCG event log / PCR policy
tpm             TPM 2.0 device and measurements
smm             SMM / SMI / SMRAM
variable        NVRAM, BootOrder, FTW
capsule         Capsule / ESRT / FMP update
cpu             MP init, microcode, MADT topology
numa            SRAT / SLIT / HMAT / SNC
cxl             CXL device and HDM decoder
ras             MCE / AER / firmware-first RAS
graphics        GOP / console / framebuffer handoff
serial          UART / SOL / earlyprintk
usb             USB host and USB boot
csm             Legacy BIOS / option ROM boot
bmc / ipmi / me Out-of-band manageability
watchdog        TCO / WDT reboot during boot
thermal / gpio / power / resume
smbios / fit / fsp
generic         Unknown failure class
```

Example:

```bash
--failure boot
--failure os_boot
```

The failure type influences how commits are evaluated and ranked.

Additional domains and topics are **config-only**. Add a domain (paths + keywords) in `config/component_map.yaml` and a profile in `config/failure_profiles.yaml`. The CLI reads `--failure` choices from the YAML; you do not need to edit Python constants or keyword sets.

---

# Installation

## Prerequisites

FRI requires:

```text
Python 3.10 or newer
Git
```

---

## Clone or Navigate to the Project

```bash
git clone <repository-url>
cd Firmware_Regression_Intelligence
```

---

## Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Or use the project setup script:

```bash
./setup.sh
```

---

## Install FRI

Install the project in editable mode:

```bash
pip install -e .
```

Development extras:

```bash
pip install -e ".[dev]"
```

Verify installation:

```bash
fri --help
fri doctor
fri topics
```

---

# Quick Start

Firmware / BIOS boot regression (single Git repo):

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure boot \
    --html \
    --json
```

OS boot / firmware-to-OS handoff regression (Linux, Windows, LinuxBoot, GRUB, EFI stub):

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure os_boot \
    --html \
    --json
```

---

# Multi-repo BIOS workspaces (edk2 + Intel + platforms)

A UEFI BIOS **build is a pin-set**, not one SHA. The binary that left the factory is the joint of:

- the platform / board repo
- `edk2`
- `edk2-platforms`
- Intel silicon (FSP, ME/CSME blobs, Boot Guard, IIO/PCH) **or** AMD AGESA / PSP
- any other Git submodule your tree vendors

A “good build” and a “bad build” are therefore **two complete pin tables**. Ranking only the platform repo will miss an FSP-M change in the Intel tree, and ranking only edk2 will miss a board ACPI DSDT.

## 1. See what moved

Point FRI at the **superproject** (the tree that has `.gitmodules`) and the two BIOS tags you already flash:

```bash
fri pins \
    --workspace ~/BHS_2026/birchstream-rv \
    --good GOOD_BUILD_TAG \
    --bad BAD_BUILD_TAG
```

FRI reads each revision’s gitlinks (and nested submodules) and prints `changed` / `unchanged` / `missing` for every pin. Unchanged Intel/EDK trees are skipped. Missing means that checkout is not cloned (or the object is not in `.git/modules/...`), so FRI cannot walk that repo until you sync it.

## 2. Investigate the joint window

```bash
fri investigate \
    --workspace ~/BHS_2026/birchstream-rv \
    --good GOOD_BUILD_TAG \
    --bad BAD_BUILD_TAG \
    --failure from_reset \
    --html --json
```

FRI walks **every moved repo**, tags each candidate with the repository name, ranks them on one list, and groups modules as `edk2 / ACPI` vs `Intel / FSP`. Bisect hints are **per moved repo** (`git -C edk2 bisect start <bad-pin> <good-pin>`). Do not bisect the superproject SHA as if the whole BIOS were one Git history.

## 3. Explicit pin manifest

When repos are siblings (not submodules), or you already know the SHAs from a build database:

```bash
fri investigate --manifest bios-pins.yaml --failure os_boot
```

See `config/workspace.example.yaml`. Each entry is `{name, path, good?, bad?}`. Top-level `good`/`bad` apply unless a repo overrides them.

Single-repo `--repo` still works for a tree that really is one Git history.

---

# Command Line Arguments

## Repository sources (pick one)

```bash
--repo         Single Git repository
--workspace    BIOS superproject; FRI expands .gitmodules pins
--manifest     YAML pin-set (see config/workspace.example.yaml)
```

`--good` and `--bad` are required with `--repo` and `--workspace`. They are the superproject tags/SHAs (the BIOS builds you flash). FRI then resolves each submodule pin at those two revisions.

```bash
fri pins --workspace ~/firmware --good GOOD --bad BAD
```

---

## Good Build

```bash
--good
```

Known working commit or build SHA.

Example:

```bash
--good 13b5128
```

---

## Bad Build

```bash
--bad
```

Known failing commit or build SHA.

Example:

```bash
--bad HEAD
```

---

## Failure Type

```bash
--failure
```

Regression failure category.

Example:

```bash
--failure boot
--failure os_boot
```

---

## HTML Report

```bash
--html
```

Generates:

```text
output/report.html
```

---

## JSON Report

```bash
--json
```

Generates:

```text
output/report.json
```

---

## Top Candidates

```bash
--top 10
```

Limits how many ranked candidates are shown in reports.

---

# Example Commands

## Console Investigation

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure boot
```

---

## Generate HTML Report

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure boot \
    --html
```

---

## Generate JSON Report

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure boot \
    --json
```

---

## Generate Both Reports

```bash
fri investigate \
    --repo ~/BHS_2026/birchstream-rv \
    --good 13b5128 \
    --bad HEAD \
    --failure boot \
    --html \
    --json
```

---

## List All Regression Topics

```bash
fri topics
```

---

# Output

FRI supports three report formats.

## Console Report

Provides immediate investigation results in the terminal.

Includes:

- Ranked regression candidates
- Confidence scores
- Authors
- Jira IDs
- Commit intent
- Firmware domains
- Hazards and evidence
- Affected modules
- Git bisect commands
- Covered regression topics

---

## HTML Report

Generated at:

```text
output/report.html
```

The HTML dashboard provides a visual representation of:

- Investigation summary
- Top firmware modules
- Confidence levels
- Regression candidates
- Commit metadata
- High-risk hazards
- Evidence
- Git bisect plan
- Covered regression topics

---

## JSON Report

Generated at:

```text
output/report.json
```

The JSON report can be used for:

- Automation
- CI/CD integration
- External dashboards
- Future analytics
- Machine learning pipelines

---

# Configuration

FRI uses configuration files stored under:

```text
config/
├── component_map.yaml
├── config.yaml
└── failure_profiles.yaml
```

---

## Component Mapping

`component_map.yaml` maps repository components and paths to firmware domains.

Example concept:

```text
Memory Path
      ↓
Memory Domain

PCI Path
      ↓
PCIe Domain

FIT Path
      ↓
FIT Domain

BdsDxe Path
      ↓
BDS Domain
```

---

## Failure Profiles

`failure_profiles.yaml` defines which firmware domains, keywords, path patterns, and risk signals are relevant to each failure type.

Example concept:

```text
Boot Failure
      ↓
Platform, FIT, PEI, DXE, BDS, FSP

OS Boot Failure
      ↓
BDS, ACPI, SMBIOS, OSLoader, LinuxBoot, IOMMU, Variable
```

This information is used during regression candidate scoring.

---

# Development

## Install Development Dependencies

```bash
make dev
```

---

## Format Code

```bash
make format
```

This runs:

```text
black
ruff
```

---

## Static Analysis

```bash
make lint
```

This runs:

```text
ruff
mypy
```

---

## Run Tests

```bash
make test
```

or:

```bash
pytest
```

---

## Run Coverage

```bash
make coverage
```

---

## Run Full Validation

```bash
make ci
```

---

# Makefile Commands

```text
make install
make dev
make format
make lint
make test
make coverage
make clean
make run
make html
make json
make build
make tree
make ci
```

Example:

```bash
make run REPO=~/BHS_2026/birchstream-rv GOOD=13b5128 BAD=HEAD FAILURE=os_boot
```

---

# Project Goals

The primary goal of FRI is to reduce the time required for firmware regression investigation.

Instead of manually reviewing a large number of commits:

```text
100 Commits
     |
     v
Manual Investigation
     |
     v
Several Hours / Days
```

FRI provides:

```text
100 Commits
     |
     v
Automated Analysis
     |
     v
Top Regression Candidates
     |
     v
Focused Investigation
```

---

# Important Disclaimer

FRI is an **investigation assistant**.

It does not automatically prove that a commit caused a regression.

The confidence score represents the likelihood that a commit deserves investigation based on available evidence.

The final root cause must still be validated by firmware engineers through:

- Code review
- Reproduction
- Debug logs
- Build testing
- Git bisect
- Hardware validation

---

# Future Roadmap

FRI is currently implemented as a Proof of Concept.

Future improvements include:

## Firmware Semantic Analysis

Understand firmware-specific entities such as:

```text
Functions
Protocols
PPIs
GUIDs
PCDs
HOBs
Libraries
Drivers
Packages
Setup Variables
ACPI Tables
```

---

## Firmware Phase Awareness

Automatically identify firmware execution phases:

```text
SEC
PEI
DXE
BDS
SMM
Runtime
OS Handoff
```

---

## Firmware Knowledge Base

Build a knowledge base connecting:

```text
PCD
   ↓
Subsystem

Protocol
   ↓
Subsystem

Library
   ↓
Subsystem

Driver
   ↓
Subsystem

Firmware Phase
```

---

## Improved Regression Scoring

Use semantic firmware evidence instead of relying primarily on keyword matching.

---

## GitLab Integration

Potential integration with:

- Merge Requests
- Reviewers
- Labels
- Pipeline status
- CI results

---

## Jira Integration

Potential integration with:

- Jira summary
- Components
- Priority
- Labels
- Related issues

---

## Git Bisect Assistant

Automatically recommend an optimized regression investigation path using Git bisect.

---

## CI/CD Integration

FRI can eventually be integrated into firmware validation pipelines.

Example:

```text
Regression Detected
        |
        v
FRI Automatically Runs
        |
        v
Top Suspect Commits
        |
        v
Engineer Notification
```

---

# Vision

The long-term vision of FRI is to build an intelligent firmware investigation assistant that understands both:

```text
Git History
```

and

```text
Firmware Architecture
```

The goal is to help firmware engineers answer:

> What changed?

> Which firmware module is affected?

> Which commits are most suspicious?

> Why are these commits suspicious?

> Where should investigation begin?

---

# Author

**Saurabh Mishra**

Firmware Engineer | UEFI | BIOS | Firmware Development

Firmware | UEFI | Coreboot | LinuxBoot | Datacenter Infrastructure

---

# License

MIT License

---

# Status

Proof of Concept / Active Development

FRI is currently under active development and focused on improving the accuracy and intelligence of firmware regression investigation.
