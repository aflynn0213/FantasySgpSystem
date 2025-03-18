#!/bin/bash

python refresh_excel_projections.py
python main.py -b atc -p atc
python main.py -b atc -p oopsy -a atc
python main.py -b batx -p oopsy -a atc
