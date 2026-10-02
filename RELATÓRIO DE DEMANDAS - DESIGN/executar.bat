@echo off
rem Chamado pelo Agendador de Tarefas do Windows toda sexta as 18h.
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist logs mkdir logs
"C:\Users\artti\AppData\Local\Programs\Python\Python312\python.exe" relatorio.py >> logs\execucao.log 2>&1
