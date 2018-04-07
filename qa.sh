#!/bin/bash
python -m flake8 plugin/ --output-file ./pages_out/flake8_report.txt
nosetests
