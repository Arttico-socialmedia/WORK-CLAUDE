# Cria (ou atualiza) a tarefa no Agendador do Windows: toda sexta as 18h.
# Se o computador estiver desligado nesse horario, roda assim que ele for ligado.
$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
$acao = New-ScheduledTaskAction -Execute (Join-Path $pasta "executar.bat") -WorkingDirectory $pasta
$gatilho = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At "18:00"
$opcoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "Relatorio Demandas Design" -Action $acao -Trigger $gatilho -Settings $opcoes -Description "Relatorio semanal de demandas de clientes do kanban DESIGN (ClickUp) para o GitHub" -Force
