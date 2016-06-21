#!/usr/bin/env bash
set -e

rm -rf vendor/
mkdir vendor/
pip3 install --download vendor/ -r requirements-native.txt --no-use-wheel
pip3 install --download vendor/ -r requirements-normal.txt

OUTPUT_REQUIREMENTS=requirements.txt
cp requirements-native.txt $OUTPUT_REQUIREMENTS
cat requirements-normal.txt >> $OUTPUT_REQUIREMENTS