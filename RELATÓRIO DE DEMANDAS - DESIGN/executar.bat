@echo off
rem Para gerar o relatorio na hora (dois cliques). O agendamento de sexta 19h roda escondido pelo pythonw.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist logs mkdir logs
"C:\Users\artti\AppData\Local\Programs\Python\Python312\python.exe" relatorio.py >> logs\execucao.log 2>&1
