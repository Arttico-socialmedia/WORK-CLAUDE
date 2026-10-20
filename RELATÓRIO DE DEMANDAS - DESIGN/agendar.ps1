# Cria (ou atualiza) a tarefa no Agendador do Windows: toda sexta as 19h, sem abrir janela.
# Se o computador estiver desligado nesse horario, roda assim que ele for ligado.
$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw = "C:\Users\artti\AppData\Local\Programs\Python\Python312\pythonw.exe"
$acao = New-ScheduledTaskAction -Execute $pythonw -Argument "relatorio.py --agendado" -WorkingDirectory $pasta
$gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At "19:00"
$opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "Relatorio Demandas Design" -Action $acao -Trigger $gatilho -Settings $opcoes -Description "Relatorio semanal de demandas de clientes Tastto do kanban DESIGN (ClickUp) para o GitHub" -Force
