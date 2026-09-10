@echo off
echo ---- %date% %time% ---- >> "%~dp0..\log.txt"
"C:\Users\artti\tools\node\node.exe" "%~dp0atualizar-semana.js" >> "%~dp0..\log.txt" 2>&1
