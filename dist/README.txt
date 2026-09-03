Unpack this archive on the machine that has your BIOS tree.

    tar -xzf Firmware_Regression_Intelligence-2.4.0.tar.gz
    cd Firmware_Regression_Intelligence
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
    fri doctor
