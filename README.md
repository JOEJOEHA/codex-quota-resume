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



监控器会缓存未变化的会话日志，并检查全部本机会话。发送后五分钟仍未观察到新回合时，状态为 `dispatch-unconfirmed`，不会盲目重复发送。使用 `python scripts/quota_watcher.py --status` 查看状态。每分钟本地检查仍保留。

验证：实际 `codex queue` 已触发独立监督任务并收到 `QUOTA_RESUME_TEST_OK`；`python scripts/test_watcher.py` 验证等待、去重、再次耗尽及取消。真实账户耗尽后恢复仍未实际经历。


## 后续任务弹窗

检测到明确额度耗尽中断并进入等待恢复时，自动弹出“续跑后还想跑什么任务”，同一次中断只提示一次。填写后点击“保存后续任务”，需求仅保存在本机，绑定对应对话。可关闭弹窗而不安排任务。手动编辑：`python scripts/quota_watcher.py --plan <任务UUID>`。

原任务恢复并在最终回复末尾写出 `[QUOTA_RESUME_GOAL_COMPLETE]` 后，监控器才向同一对话发送保存的需求原文。该标记只允许在所有原目标验收完成时输出，不能用于等待用户、登录、批准或失败状态。普通回合结束不会触发后续任务。发送结果不确定时不会自动重复发送，可查看本机 followups 目录状态。

弹窗不调用模型。当前基于日志额度错误发现中断，受一分钟轮询与两分钟静默判断影响，并非余额数字变成 0 的瞬间弹出；锁屏时需解锁后填写。运行记录和填写内容不包含在分享包中。
