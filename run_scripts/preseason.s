#!/bin/bash

#python update_scripts/refresh_excel_projections.py
#python ../preseason_main.py -b atc_pre -p atc_pre
#python ../preseason_main.py -b atc_pre -p oopsy_pre -a atc
python main.py -b atc_pre -p oopsy_pre -a atc
python main.py -b atc_pre -p oopsy_pre -a atc -m points -sb
