@echo off
rem Version: v2026.07.25.2
cd /d C:\keiba
if not exist C:\keiba\shadow_jra\logs mkdir C:\keiba\shadow_jra\logs
C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe -X utf8 ^
  C:\keiba\shadow_jra\jra_standalone_live.py ^
  --mode live --data-dir C:\keiba\data ^
  --pedigree C:\keiba\data\pedigree_jra.json ^
  --training C:\keiba\data\training_jra.json ^
  --webhook-file C:\keiba\shadow_jra\discord_webhook.txt ^
  --state C:\keiba\data\jra_standalone_live.json ^
  > C:\keiba\shadow_jra\logs\jra_standalone_live.log 2>&1
