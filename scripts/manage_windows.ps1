[CmdletBinding()]
param([Parameter(Mandatory)][ValidateSet('status','pause','resume','uninstall')][string]$Action)
$ErrorActionPreference = 'Stop'
$taskNames = 'Codex Quota Resume Watcher','Codex Quota Resume Backup'
switch ($Action) {
    'status' {
        foreach ($taskName in $taskNames) {
            Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Select-Object TaskName,State
            Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue | Select-Object LastRunTime,LastTaskResult,NextRunTime
        }
        $statePath = Join-Path $env:LOCALAPPDATA 'CodexQuotaWatcher\state.json'
        if (Test-Path -LiteralPath $statePath) { Get-Content -LiteralPath $statePath }
    }
    'pause' {
        foreach ($taskName in $taskNames) { Disable-ScheduledTask -TaskName $taskName | Out-Null }
        Write-Output 'Future monitoring paused. Already-running work is not interrupted.'
    }
    'resume' {
        foreach ($taskName in $taskNames) {
            Enable-ScheduledTask -TaskName $taskName | Out-Null
            Start-ScheduledTask -TaskName $taskName
        }
        Write-Output 'Both monitors enabled.'
    }
    'uninstall' {
        $tasks = @($taskNames | ForEach-Object { Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue })
        if ($tasks | Where-Object State -eq 'Running') {
            throw 'A monitor is running. Pause future checks and wait for current work to finish before uninstalling.'
        }
        foreach ($task in $tasks) { Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false }
        Write-Output 'Both scheduled tasks removed. Local plans, images and program files are retained in LOCALAPPDATA\CodexQuotaWatcher.'
    }
}
