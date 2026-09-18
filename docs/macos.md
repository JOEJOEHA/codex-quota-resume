# macOS 开发预览

此分支最初基于 Windows v3.0.0-beta.15（4edb3cd）移植；当前本地更新已合入 beta.36。不是已完成实机验收的正式版本。

## 构建与安装

在 macOS 上使用包含 Tk 的 Python 3.13 最新维护版（例如 python.org 安装包）：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pyinstaller
python scripts/build_macos.py
```

生成 `dist/CodexQuotaResume.app` 与对应架构的预览 ZIP / SHA256。GitHub Actions 分别在 Apple Silicon 和 Intel runner 构建，并提供 artifacts。只生成开发用 ad-hoc 签名；没有 Developer ID 签名、公证或正式安装包。不要关闭 Gatekeeper；如系统阻止运行，按 macOS 的“隐私与安全性”流程处理可信的本地构建。

如果源码位于 iCloud / File Provider 管理的目录，系统可能不断给 `.app` 或内嵌 framework 添加 Finder 元数据，导致签名失败。可以把构建输出放在非同步目录：

```sh
python scripts/build_macos.py --dist-dir /private/tmp/codex-quota-preview
```

脚本只清理生成应用中的 `com.apple.FinderInfo` / `com.apple.ResourceFork`，再签名并严格验证；不会清除 quarantine 或关闭 Gatekeeper。若同步服务重新添加属性，改用上述输出目录。将验证成功的 ZIP 复制回工作目录即可；使用时解压到非同步目录，再移入应用程序文件夹。参见 [Apple QA1940](https://developer.apple.com/library/archive/qa/qa1940/_index.html)。

把 `.app` 放入 `/Applications` 或 `~/Applications`，双击打开，然后点击“启用 / 更新监控”。这一步检查已有 Codex 登录与额度接口，并注册当前用户的两个 LaunchAgent；无需管理员权限。更新使用相同安装路径；已加载的路径或环境不同时，程序会拒绝覆盖，避免中止执行中的任务。更换路径需先确认任务结束，再手动重新注册 LaunchAgent。也可以从固定源码目录运行 `python scripts/app.py`。

## 平台行为

- 状态与附件：`~/Library/Application Support/CodexQuotaWatcher`。
- 调度：`~/Library/LaunchAgents/com.codexquota.watcher.plist`（60 秒）及 `com.codexquota.backup.plist`（300 秒）。用户登录后运行，睡眠期间不承诺定时执行。
- 两层共用 `flock` 和发送记录。暂停写入标记，后续检查直接返回，正在执行的任务继续；退出界面不暂停监控。
- 菜单栏左键恢复，右键打开菜单；原生回调只入队，Tk 主循环执行界面操作。退出时保留打开的草稿，手动关闭有修改的草稿时可保存、丢弃或取消。
- `⌘V` 粘贴图片或 Finder 文件，`⌘Enter` 保存；使用系统截图工具后粘贴。系统可能要求屏幕录制权限。
- 普通窗口 430 × 535，展开编辑器 760 × 620，苹方字体；多屏使用 `NSScreen.visibleFrame` 计算工作区。

## Codex 兼容检查

```sh
python scripts/app.py --doctor
```

只读取版本、命令帮助、当前额度、任务列表与最近回合；不会发送任务。输出包含 `resume`、`queue` 和 `turnsAPI` 是否可用。没有任务时无法验证回合查询。CLI 可通过 `CODEX_EXECUTABLE` 指定；否则检查 PATH、系统或用户应用程序目录下的 Codex.app / ChatGPT.app、Homebrew 和 `~/.local/bin`。ChatGPT.app 仅在实际包含可执行的 Codex CLI 时作为候选。自定义 `CODEX_HOME` 会保存在 LaunchAgent 环境中。

诊断输出使用 JSON。`ok` 表示是否已完成全部兼容性检查，`errors` 说明未通过的环节；未能读取的项目不会假装为“不支持”。额度已耗尽是成功读到的账户状态，`quotaAvailable: false` 本身不代表兼容性失败。检查失败或没有任务可验证回合接口时，命令返回退出码 1，仍保留已完成的结果。诊断不会写入本工具的监控状态；Codex App Server 自身仍可能更新本地 SQLite 运行状态，因此受限沙箱可能阻止检查。

官方 [CLI 文档](https://developers.openai.com/codex/cli/reference) 与 [App Server 文档](https://developers.openai.com/codex/app-server) 用于核对接口。目标 Mac 上仍必须执行 doctor；`queue` 和实验回合接口不能仅凭 Windows 版本推断。写入者冲突才尝试 queue，缺失则记录失败；入队仍保留启动确认。

## 验证范围

本机 beta.36 更新记录及明确的未验收项见 [macOS 本地验证](macos-local-validation.md)。没有屏幕录制权限时，可使用 `QUOTA_RESUME_SKIP_SCREEN_CAPTURE=1 python scripts/test_macos_ui.py` 仅验证原生功能；该模式会明确输出像素检查已跳过，不替代默认截图验收。

本地 Windows 可运行共享业务回归及 `test_macos.py` 的模拟平台测试。macOS CI 运行相同业务测试、真实进程锁测试、原生 Tk / 菜单栏冒烟测试、构建及签名检查。CI 无已登录的用户 Codex，不证明真实额度恢复与任务发送已验收。

2026-09-16：Apple Silicon（macOS 14）与 Intel（macOS 15）CI 均已完成上述检查并生成 `.app` 预览产物。已检查原生窗口截图；另用临时 LaunchAgent 验证加载和后台启动，测试结束移除自己的测试任务。没有改动用户机器的 Windows 监控或保存数据。

交付前还需在目标 Mac 逐项验收：

- 登录状态、实时额度、exec resume、桌面写入者冲突时 queue 的真实支持。
- 菜单栏实际点击、系统退出、最小化恢复、多个草稿与展开窗口的保留。
- 深色圆角布局、红旗闪动与重启恢复、中文输入和 Command 快捷键。
- 图片 / 文件粘贴、截图权限允许和拒绝、取消截图、删除原文件后仍能读取副本。
- Retina、多个显示器及负坐标、工作区不足时的摆放。
- LaunchAgent 安装、登录后恢复、暂停与继续、共享锁、防重复。
- 真实“明确额度中断 → 恢复 → 续跑被接受 → 至少 10 秒后投递后续需求”，每条只发送一次。

没有完成这些检查前，不宣称 macOS 版本已可用。发布 DMG、Developer ID 签名和 Apple 公证留待实际证书与验收条件满足后执行。

## beta.36 本地更新

- “检查更新”读取 GitHub Releases，显示版本及发布说明，并可打开下载页；当前窗口和草稿继续保留。只检查版本，不自动替换 `.app`。API 限流时回退到最新正式发布页，界面明确提示无法完整检查预览版。
- 输入框顶部持续显示任务名称和保存/发送规则。鼠标单击可定位光标，拖动可选中文字。
- 延迟投递期间检测到 `turn_aborted`，待发需求转为取消状态，文字和附件保留。重启监控、后续新回合不会自动重发；用户重新保存或“发送已存任务”后才重新提交。已经交给 Codex 的队列不属于此处可撤回的待发需求。
- 等待额度期间暂停监控，也会阻止本工具继续投递。

新增离线回归：`test_cancelled_followup.py`、`test_macos_updater.py`；原生回归：`test_placeholder.py`、`test_macos_update_ui.py`。
