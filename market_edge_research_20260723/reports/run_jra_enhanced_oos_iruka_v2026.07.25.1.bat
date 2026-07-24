@echo off
cd /d C:\keiba\shadow_jra
C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe walkforward_jra_pedigree_training.py --data-dir C:\keiba\data --pedigree C:\keiba\data\pedigree_jra.json --training C:\keiba\data\training_jra.json --output C:\keiba\codex_display_test\jra_enhanced_iruka_report.json --oos-output C:\keiba\codex_display_test\jra_enhanced_iruka_oos.csv --years 2024 2025
