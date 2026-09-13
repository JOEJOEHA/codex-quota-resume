[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$taskName = 'Codex Quota Resume Watcher'
$source = Join-Path $PSScriptRoot 'quota_watcher.py'
$installDir = Join-Path $env:LOCALAPPDATA 'CodexQuotaWatcher'
$installed = Join-Path $installDir 'quota_watcher.py'

$pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pythonw) {
    throw 'Python 3 with pythonw.exe is required. Install Python, then run this script again.'
}

$python = Join-Path (Split-Path $pythonw.Source) 'python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = $pythonw.Source
}
& $python -X utf8 $source --self-test
if ($LASTEXITCODE -ne 0) {
    throw 'Watcher self-test failed.'
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $installed -Force

$action = New-ScheduledTaskAction -Execute $pythonw.Source -Argument "`"$installed`"" -WorkingDirectory $installDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description 'Zero-token local watcher: resumes a Codex task only after a recorded quota reset.'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3

$info = Get-ScheduledTaskInfo -TaskName $taskName
if ($info.LastTaskResult -ne 0) {
    throw "Scheduled watcher failed with result $($info.LastTaskResult)."
}
Write-Output "INSTALLED: $taskName; next run $($info.NextRunTime)"
