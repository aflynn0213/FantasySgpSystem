#!/bin/bash

python refresh_excel_projections.py
python main.py -b atc_pre -p atc_pre
python main.py -b atc_pre -p oopsy_pre -a atc
python main.py -b batx_pre -p oopsy_pre -a atc
