# macOS 开发预览

此分支基于 Windows v3.0.0-beta.15（4edb3cd）移植。不是已完成实机验收的正式版本。

## 构建与安装

在 macOS 上使用包含 Tk 的 Python 3.12（例如 python.org 安装包）：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pyinstaller
python scripts/build_macos.py
```

生成 `dist/CodexQuotaResume.app` 与对应架构的预览 ZIP / SHA256。GitHub Actions 分别在 Apple Silicon 和 Intel runner 构建，并提供 artifacts。只生成开发用 ad-hoc 签名；没有 Developer ID 签名、公证或正式安装包。不要关闭 Gatekeeper；如系统阻止运行，按 macOS 的“隐私与安全性”流程处理可信的本地构建。

把 `.app` 放入 `/Applications` 或 `~/Applications`，双击打开，然后点击“启用 / 更新监控”。这一步检查已有 Codex 登录与额度接口，并注册当前用户的两个 LaunchAgent；无需管理员权限。移动应用后需更新监控路径。也可以从固定源码目录运行 `python scripts/app.py`。

## 平台行为

- 状态与附件：`~/Library/Application Support/CodexQuotaWatcher`。
- 调度：`~/Library/LaunchAgents/com.codexquota.watcher.plist`（60 秒）及 `com.codexquota.backup.plist`（300 秒）。用户登录后运行，睡眠期间不承诺定时执行。
- 两层共用 `flock` 和发送记录。暂停写入标记，后续检查直接返回，正在执行的任务继续；退出界面不暂停监控。
- 菜单栏左键恢复，右键打开菜单；原生回调只入队，Tk 主循环执行界面操作。退出时保留打开的草稿，手动关闭有修改的草稿时可保存、丢弃或取消。
- `⌘V` 粘贴图片或 Finder 文件，`⌘Enter` 保存；截图调用系统交互截图工具，完成后粘贴。系统可能要求屏幕录制权限。
- 普通窗口 430 × 535，展开编辑器 760 × 620，苹方字体；多屏使用 `NSScreen.visibleFrame` 计算工作区。

## Codex 兼容检查

```sh
python scripts/app.py --doctor
```

只读取版本、命令帮助、当前额度、任务列表与最近回合；不会发送任务。输出包含 `resume`、`queue` 和 `turnsAPI` 是否可用。没有任务时无法验证回合查询。CLI 可通过 `CODEX_EXECUTABLE` 指定；否则检查 PATH、Codex.app、Homebrew 和 `~/.local/bin`。自定义 `CODEX_HOME` 会保存在 LaunchAgent 环境中。

官方 [CLI 文档](https://developers.openai.com/codex/cli/reference) 与 [App Server 文档](https://developers.openai.com/codex/app-server) 用于核对接口。目标 Mac 上仍必须执行 doctor；`queue` 和实验回合接口不能仅凭 Windows 版本推断。写入者冲突才尝试 queue，缺失则记录失败；入队仍保留启动确认。

## 验证范围

本地 Windows 可运行共享业务回归及 `test_macos.py` 的模拟平台测试。macOS CI 运行相同业务测试、真实进程锁测试、原生 Tk / 菜单栏冒烟测试、构建及签名检查。CI 无已登录的用户 Codex，不证明真实额度恢复与任务发送已验收。

交付前还需在目标 Mac 逐项验收：

- 登录状态、实时额度、exec resume、桌面写入者冲突时 queue 的真实支持。
- 菜单栏实际点击、系统退出、最小化恢复、多个草稿与展开窗口的保留。
- 深色圆角布局、红旗闪动与重启恢复、中文输入和 Command 快捷键。
- 图片 / 文件粘贴、截图权限允许和拒绝、取消截图、删除原文件后仍能读取副本。
- Retina、多个显示器及负坐标、工作区不足时的摆放。
- LaunchAgent 安装、登录后恢复、暂停与继续、共享锁、防重复。
- 真实“明确额度中断 → 恢复 → 原任务完成验收 → 后续任务发送”，每条只发送一次。

没有完成这些检查前，不宣称 macOS 版本已可用。发布 DMG、Developer ID 签名和 Apple 公证留待实际证书与验收条件满足后执行。
