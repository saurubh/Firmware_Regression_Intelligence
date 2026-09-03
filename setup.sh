#!/usr/bin/env bash

#
# Firmware Regression Intelligence (FRI)
#
# Development environment setup
#

set -euo pipefail

echo "============================================================"
echo "Firmware Regression Intelligence (FRI)"
echo "Development Environment Setup"
echo "============================================================"
echo

#
# Check Python
#
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

echo "Python Version : ${PYTHON_VERSION}"
echo

#
# Create virtual environment
#
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

#
# Activate
#
echo "Activating virtual environment..."
source venv/bin/activate

#
# Upgrade pip
#
echo "Upgrading pip..."
python -m pip install --upgrade pip

#
# Install project
#
if [ -f "pyproject.toml" ]; then

    echo "Installing FRI (editable mode)..."

    pip install -e .

elif [ -f "requirements.txt" ]; then

    echo "Installing dependencies..."

    pip install -r requirements.txt

else

    echo "ERROR: Neither pyproject.toml nor requirements.txt found."

    exit 1

fi

echo
echo "============================================================"
echo "Setup Complete"
echo "============================================================"
echo
echo "Activate the environment:"
echo
echo "    source venv/bin/activate"
echo
echo "Verify the installation:"
echo
echo "    fri --version"
echo
echo "Show available commands:"
echo
echo "    fri --help"
echo
echo "Run an investigation:"
echo
echo "    fri investigate \\"
echo "        --repo <repository> \\"
echo "        --good <good-build> \\"
echo "        --bad <bad-build> \\"
echo "        --failure boot"
echo
