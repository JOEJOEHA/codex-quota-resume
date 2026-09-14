---
name: codex-quota-resume
description: 设置、检查、更新或停止 Windows Codex 额度中断后的自动续跑。主监控与独立备用监控读取实时额度，有额度就继续原任务。仅询问方案时不启用。
---

# Codex 额度恢复续跑

阅读 README.md 的环境要求与限制。此 Skill 提供 Windows 本地 EXE、Python 源码和计划任务；仅复制 Skill 不会启用后台监控。其他平台不安装本程序。

## 安装与更新

优先下载 README 中的 Windows EXE，运行 `CodexQuotaResume.exe --install` 并核验主备任务和桌面快捷方式；EXE 内置 Python/Pillow。源码安装时，检查 Python 3.11+、Tkinter、Pillow、已登录的兼容 Codex CLI。安装依赖 `python -m pip install -r requirements.txt`，运行 `scripts/install_windows.ps1`。复用现有同名计划任务，不创建重复监控。使用自定义 CODEX_HOME 时，确保计划任务继承相同的用户环境变量。

核对两个计划任务、LastTaskResult、安装文件与源文件，以及本机 state.json 和 watcher.log。运行 scripts 中的自检和三个 test_*.py；它们不向真实任务发送消息。弹窗启动后必须收到可见窗口确认才算已提示。需要真实续跑验收时，先取得对测试任务的发送授权。

## 续跑规则

- 只处理监控启用后、最后回合明确因 usage_limit_exceeded 失败的原任务。
- 主层每分钟读取会话日志；备用层每五分钟通过官方 App Server 独立发现额度失败任务。
- 发送前读取实时额度并核对最后回合。额度可用就续跑；不要求旧快照达到 100%，不额外等五分钟。
- 使用 codex exec resume 继续原任务；遇到明确 active writer 冲突时，使用 codex queue 交给桌面端，核验真实开始，入队不等于执行成功；共享文件锁和发送记录，避免重复发送。不用仅入队且无法验证启动的替代路径。
- 正常完成、取消、等待用户、状态不明时不续跑。不购买额度、兑换重置券或改变模型、审批、沙箱设置。
- 后续需求和图片只在原任务明确完成、末尾输出 [QUOTA_RESUME_GOAL_COMPLETE] 后发送。任务未完成、等待登录或批准时不得输出此标记。

## 查看与停止

运行 `scripts/manage_windows.ps1 status|pause|resume|uninstall`，每次只传一个操作。暂停必须同时停用主备两层；不会终止正在执行的原任务。卸载保留用户需求、图片和状态。不要修改其他自动任务。

真实恢复周期与离线模拟测试分开报告；不要声称永不故障。不得将本机日志、状态、需求截图、凭据或个人会话内容加入公开分享包。
