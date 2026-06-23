#!/bin/bash
# Run this on your Mac to update Anima: bash ~/update-anima.sh
cd ~
curl -sL https://github.com/PalakB1/anima/archive/refs/heads/master.zip -o anima.zip
unzip -o anima.zip > /dev/null 2>&1
cd anima-master
pip3.11 install -e . -q > /dev/null 2>&1
echo "Updated. Running Anima..."
python3.11 -m anima.cli
