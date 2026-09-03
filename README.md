# Firmware Regression Intelligence (FRI)

Firmware Regression Intelligence (FRI) is an intelligent firmware regression analysis framework that helps BIOS and firmware engineers identify the most probable commits responsible for regressions between a known-good and a known-bad build.

Instead of manually reviewing hundreds of commits, FRI combines Git history, commit metadata, firmware-aware classification, diff analysis, and configurable failure profiles to rank the most likely regression candidates.

---

# Features

- Analyze firmware **and OS boot** regressions between two Git revisions
- 36 failure profiles (SEC/PEI/DXE/BDS boot, Linux/Windows/LinuxBoot handoff, ACPI, IOMMU, memory, PCIe, CXL, Secure Boot, SMM, BMC, FSP, and more)
- Parse firmware commit metadata (Jira, Merge Requests, intent)
- Firmware-aware subsystem classification from paths **and** commit keywords
- Diff analysis with hazard detection (ExitBootServices, PCD/UPD, ACPI tables, IOMMU, timeouts)
- Multi-signal candidate scoring (domain, path, keyword, hazard, boot API)
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

    topics
```

List every regression topic:

```bash
fri topics
```

---

# Basic Usage

Investigate a firmware-to-OS boot regression (Linux, Windows, LinuxBoot, GRUB, EFI stub):

```bash
fri investigate \
    --repo ~/firmware-repo \
    --good GOOD_SHA \
    --bad BAD_SHA \
    --failure os_boot
```

Investigate a firmware/BIOS boot regression:

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

# Supported Regression Topics

Use `fri topics` or `--failure <name>`. Built-in profiles:

| Topic | What it catches |
| --- | --- |
| `boot` | Firmware boot (SEC/PEI/DXE/BDS/FSP/FIT) |
| `os_boot` | OS handoff: ExitBootServices, memory map, ACPI, GRUB, Linux, Windows bootmgr, LinuxBoot |
| `linuxboot` | LinuxBoot / u-root / kexec payload |
| `acpi` | DSDT/SSDT/MADT/SRAT/DMAR and other tables the OS consumes |
| `iommu` | VT-d / AMD-Vi / DMAR programming that hangs the kernel |
| `memory` | MRC/FSP memory init, DIMM, NUMA |
| `pcie` | Link training, BARs, resource allocation |
| `storage` / `network` | Boot disks, NVMe, PXE, HTTP boot |
| `security` / `secure_boot` / `measured_boot` / `tpm` | Authenticated boot and PCR/event log |
| `smm` / `variable` / `capsule` | Runtime, NVRAM, firmware update |
| `cpu` / `numa` / `cxl` / `ras` | Topology, CXL memory, error handling |
| `graphics` / `serial` / `usb` / `csm` | Console and legacy boot |
| `bmc` / `ipmi` / `me` / `watchdog` / `thermal` / `gpio` / `power` / `resume` | Platform manageability and sleep |
| `smbios` / `fit` / `fsp` | Inventory, Boot Guard, silicon UPD |
| `generic` | Unknown failure class |

Additional domains can be added through `config/failure_profiles.yaml` and `config/component_map.yaml`.

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