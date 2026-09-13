# Codex Quota Resume · 额度恢复自动续跑

<img src="assets/icon.png" alt="Codex Quota Resume icon" width="160">

Resume Codex tasks after five-hour or weekly usage limits reset. **Version 2 adds a zero-token Windows watcher:** idle checks run locally and do not call a model.

在五小时或周额度恢复后继续被中断的原任务。**新版加入 Windows 零额度本地监控器：空闲检查不调用模型，不消耗 Codex 用量。**

## Download / 下载

**[Download the ready-to-install ZIP / 下载技能包](https://github.com/JOEJOEHA/codex-quota-resume/raw/refs/heads/main/codex-quota-resume.zip)**

Extract `codex-quota-resume` into:

- Windows: `%USERPROFILE%\.codex\skills\`
- macOS / Linux: `~/.codex/skills/`
- Custom `CODEX_HOME`: its `skills/` directory

The final path must be `skills/codex-quota-resume/SKILL.md`. Reopen Codex or start a new task, then send:

```text
使用 $codex-quota-resume，为我启用额度恢复后自动续跑。
优先安装零 Codex 用量的本地监控器；只续跑明确因额度耗尽而中断的原任务。
```

Windows users can also run the installer directly after extracting:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\codex-quota-resume\scripts\install_windows.ps1"
```

Windows 本地模式需要 Python 3，并使用系统任务计划程序。安装器会运行自检、注册计划任务并验证首次后台运行。已有同用途的 Codex heartbeat 应暂停，避免重复执行和额度消耗。

## How it works / 工作方式

The local watcher reads Codex's own session JSONL files. It acts only when a task ends with `usage_limit_exceeded`, preserves the last valid five-hour and weekly reset timestamps, and queues one resume message five minutes after the latest exhausted window resets.

本地监控器只认明确的额度错误，不会把空闲、普通失败、已完成、取消或等待用户输入的任务当作候选。它按“任务 + 回合 + 重置时间”去重；再次额度耗尽会进入下一轮等待。每分钟的本地检查不使用 Codex 额度，只有真正续跑原任务时才产生正常用量。

- Status / 查看：`Get-ScheduledTaskInfo -TaskName 'Codex Quota Resume Watcher'`
- Stop / 停止：`Disable-ScheduledTask -TaskName 'Codex Quota Resume Watcher'`
- Resume / 恢复：enable and start the same scheduled task
- Update / 更新：rerun `scripts/install_windows.ps1` from the new skill

On unsupported hosts, the skill can fall back to a short, isolated Codex heartbeat scheduled from the actual reset time. A heartbeat consumes Codex usage on every run, so it is a fallback rather than the preferred Windows mode.

## Requirements and limits / 条件与限制

For unattended local operation, the computer must remain powered on and awake, the user must remain logged in, and Codex plus the network must be available when the resume message is queued. Turning off or locking the display does not stop the Windows scheduled task. Queue failures retry after five minutes.

The parser and scheduler passed self-tests, a real historical quota-error replay, and a live background-task check. The next real quota exhaustion is still the final end-to-end validation.

No personal account data, conversation IDs, credentials, automation state, or local paths are included. The icon was generated with OpenAI ImageGen. This is a community project, not an official OpenAI product.

## License

[MIT](LICENSE)

