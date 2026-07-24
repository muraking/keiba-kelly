@echo off
rem Version: v2026.07.24.1
cd /d C:\keiba
if not exist C:\keiba\shadow_jra\logs mkdir C:\keiba\shadow_jra\logs
C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe -X utf8 ^
  C:\keiba\shadow_jra\jra_shadow_service.py ^
  --mode run --workdir C:\keiba --data-dir C:\keiba\data ^
  --state C:\keiba\data\jra_shadow_state.json ^
  > C:\keiba\shadow_jra\logs\jra_shadow_live.log 2>&1
