#!/bin/bash

set -e

echo "========================================="
echo "FRI v1.0 Repository Restructure"
echo "========================================="

ROOT=$(pwd)

echo ""
echo "Working Directory : $ROOT"

############################################
# Create directories
############################################

mkdir -p config
mkdir -p output
mkdir -p logs
mkdir -p tests
mkdir -p docs

mkdir -p fri/utils

############################################
# Move top-level files
############################################

if [ -f fri/README.md ]; then
    mv fri/README.md .
fi

if [ -f fri/requirements.txt ]; then
    mv fri/requirements.txt .
fi

if [ -f fri/setup.sh ]; then
    mv fri/setup.sh .
fi

############################################
# Create package init files
############################################

touch fri/__init__.py
touch fri/analyzer/__init__.py
touch fri/classifier/__init__.py
touch fri/collector/__init__.py
touch fri/engine/__init__.py
touch fri/parser/__init__.py
touch fri/report/__init__.py
touch fri/utils/__init__.py

############################################
# Configuration templates
############################################

if [ ! -f config/config.yaml ]; then

cat > config/config.yaml <<EOF
debug: false

analysis:
  minimum_confidence: 25

report:
  top_candidates: 10

html:
  theme: light
EOF

fi

############################################

if [ ! -f config/component_map.yaml ]; then

cat > config/component_map.yaml <<EOF
Platform:
  - Lenovo/Platform
  - PlatformPkg

Memory:
  - Memory
  - Mrc

FIT:
  - fit

Security:
  - SecureBoot
  - TPM

PCIe:
  - PCIe
  - Pcie

Network:
  - PXE
  - Network

Storage:
  - NVMe
  - Storage
EOF

fi

############################################

if [ ! -f config/failure_profiles.yaml ]; then

cat > config/failure_profiles.yaml <<EOF
boot:
  subsystems:
    - Platform
    - FIT
    - Security

memory:
  subsystems:
    - Memory

pcie:
  subsystems:
    - PCIe

network:
  subsystems:
    - Network

storage:
  subsystems:
    - Storage

security:
  subsystems:
    - Security

power:
  subsystems:
    - Platform
EOF

fi

############################################
# Git ignore
############################################

if [ ! -f .gitignore ]; then

cat > .gitignore <<EOF
__pycache__/
*.pyc
*.pyo

venv/
.env/

logs/
output/

.idea/
.vscode/

*.swp
EOF

fi

############################################
# Utils helper
############################################

if [ ! -f fri/utils/helpers.py ]; then

cat > fri/utils/helpers.py <<EOF
"""
Common helper functions.
"""

def short_sha(sha: str) -> str:
    return sha[:8]
EOF

fi

############################################

echo ""
echo "Repository successfully restructured."

echo ""
echo "Final tree:"
echo ""

tree -L 3
