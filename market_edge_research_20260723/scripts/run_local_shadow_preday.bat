@echo off
rem Version: v2026.07.25.1
cd /d C:\keiba
if not exist C:\keiba\shadow_local\logs mkdir C:\keiba\shadow_local\logs
C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe -X utf8 ^
  C:\keiba\shadow_local\local_standalone_live.py ^
  --mode preday --data-dir C:\keiba\data ^
  --state C:\keiba\data\local_standalone_preday.json ^
  > C:\keiba\shadow_local\logs\local_standalone_preday.log 2>&1
