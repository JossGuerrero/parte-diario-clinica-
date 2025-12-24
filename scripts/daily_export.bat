@echo off
rem Daily export for Eqctacli reports (default: yesterday)
for /f %%i in ('powershell -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set YMD=%%i
python manage.py export_eqctacli_report --desde %YMD% --hasta %YMD%
