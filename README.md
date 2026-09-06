# Codex Quota Resume · 额度恢复自动续跑

<img src="icon.png" alt="Codex Quota Resume icon" width="160">

Resume unfinished Codex tasks after usage limits reset. Read the actual five-hour and weekly reset times, schedule one check five minutes after recovery, then schedule the next check from fresh account data. No hourly polling during normal operation.

在实际额度重置后五分钟检查一次，续跑明确因额度耗尽而中断的原任务，并自动根据最新重置时间预约下一次检查。正常情况下不按小时轮询。

## Download and install / 下载与安装

**[Download the ready-to-install ZIP / 下载技能包](https://github.com/JOEJOEHA/codex-quota-resume/raw/refs/heads/main/codex-quota-resume.zip)**

Extract the ZIP and put its `codex-quota-resume` folder in your Codex skills directory:

- Windows: `%USERPROFILE%\.codex\skills\`
- macOS / Linux: `~/.codex/skills/`
- Custom `CODEX_HOME`: use its `skills/` subdirectory.

The final path should be `skills/codex-quota-resume/SKILL.md`. Reopen Codex or start a new conversation to discover the skill. Installing does not start monitoring; ask Codex to enable it.

解压后将 `codex-quota-resume` 文件夹放入上述技能目录，确认没有重复嵌套同名文件夹，然后重新打开 Codex 或新建对话。安装本身不会启动自动任务。

## Enable / 启用

```text
Use $codex-quota-resume to automatically resume my unfinished Codex tasks
that stopped because of usage limits. Check five minutes after the actual
reset time, then schedule the next check from fresh quota data. Do not poll hourly.
```

```text
使用 $codex-quota-resume，为我启用额度恢复后自动续跑。
自动发现因额度耗尽中断、尚未完成的 Codex 任务；
在实际重置后五分钟检查，读取新的重置时间并预约下一次，不按小时轮询。
```

Specify individual tasks if you want a narrower scope. Ask the skill to show the next check and last dispatch, or to stop monitoring at any time.

如只希望管理特定任务，请明确指定。可随时要求查看下次检查时间、上次续跑结果或停止监控。

## Behavior / 工作方式

- Reads actual account limits; weekly exhaustion waits for weekly recovery.
- Updates the same scheduled follow-up rather than creating duplicate tasks.
- Resumes only tasks with explicit quota-interruption evidence, in their original conversations.
- Skips completed, canceled, actively running, manually paused, or user-blocked tasks.
- Records dispatches to avoid duplicate messages and requests stage-level `PROGRESS.md` checkpoints.
- Does not buy credits, redeem resets, change models, or expand task permissions.

读取实际额度、等待对应窗口恢复、复用同一个计划、保留原对话上下文，并通过派发记录防止重复催跑。不会把空闲对话都当成未完成任务，也不会购买额度或扩大权限。

## Requirements and validation / 环境与验证

Requires a Codex host exposing account-usage, scheduling, task-history and task-messaging tools. It is an instruction skill, not a standalone daemon or an API quota bypass. Ordinary CLI or web environments may lack these tools. Local work requires the computer, network and app to remain available.

Single-run scheduling and rescheduling depend on the host version. Missing or stale reset data triggers only bounded exception retries. Configuration and package validation have passed; end-to-end recovery across actual quota exhaustion has not yet been verified. Check the first real run before relying on unattended operation.

需要宿主提供额度读取、定时任务、任务历史和向原任务发送消息的工具。本技能不是独立后台程序，也不增加额度。本地执行需要电脑、网络和应用可用；单次调度及续订能力取决于宿主版本。已验证技能格式和打包，尚未完成真实额度耗尽后的端到端续跑验证。

No personal account data, conversation IDs, credentials or runtime state are included. The icon was generated with OpenAI ImageGen. This is a community project, not an official OpenAI product.

分享内容不包含个人账户数据、对话 ID、凭据或运行状态。图标由 OpenAI ImageGen 生成。本项目为社区技能，并非 OpenAI 官方产品。

## License

[MIT](LICENSE)
