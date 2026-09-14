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
    throw 'python.exe must be installed alongside pythonw.exe.'
}
& $python -X utf8 -c "import sys,tkinter,PIL;assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+, Tkinter and Pillow are required. Install requirements.txt with this Python.' }
& $python -X utf8 -c "import sys;sys.path.insert(0,sys.argv[1]);import quota_watcher as w,codex_status as s;s.available(w.find_codex())" $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw 'Cannot read live Codex quota. Check CLI compatibility and sign in before installing.' }
& $python -X utf8 $source --self-test
if ($LASTEXITCODE -ne 0) {
    throw 'Watcher self-test failed.'
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $installed -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "plan_dialog.py") -Destination $installDir -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "window_ui.py") -Destination $installDir -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "codex_status.py") -Destination $installDir -Force
Set-Content -LiteralPath (Join-Path $installDir 'session-cache.json') -Value '{}' -Encoding utf8
& $python -X utf8 -c "import sys,time;sys.path.insert(0,sys.argv[1]);import quota_watcher as w;s=w.load_state();s.setdefault('monitoringSince',time.time());w.save_state(s)" $installDir
if ($LASTEXITCODE -ne 0) { throw 'Failed to preserve monitoring start time.' }

$action = New-ScheduledTaskAction -Execute $pythonw.Source -Argument "`"$installed`"" -WorkingDirectory $installDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description 'Local watcher: resumes quota-failed Codex tasks when live quota is available.'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
$backupName = 'Codex Quota Resume Backup'
$backupAction = New-ScheduledTaskAction -Execute $pythonw.Source -Argument "`"$installed`" --backup" -WorkingDirectory $installDir
$backupTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$backupTask = New-ScheduledTask -Action $backupAction -Trigger $backupTrigger -Principal $principal -Settings $settings `
    -Description 'Independent zero-token fallback with shared lock and unstarted-dispatch recovery.'
Register-ScheduledTask -TaskName $backupName -InputObject $backupTask -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
$checkDeadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 2
    $info = Get-ScheduledTaskInfo -TaskName $taskName
} while ($info.LastTaskResult -eq 267009 -and (Get-Date) -lt $checkDeadline)
if ($info.LastTaskResult -ne 0 -and $info.LastTaskResult -ne 267009) {
    throw "Scheduled watcher failed with result $($info.LastTaskResult)."
}
Write-Output "INSTALLED: $taskName; next run $($info.NextRunTime)"
Start-ScheduledTask -TaskName $backupName
Write-Output "INSTALLED: $backupName; every 5 minutes"
