# macOS beta.36 本地更新与验证

日期：2026-09-17。状态：在原有 Mac 版本上完成的 Apple Silicon 本地开发预览。

## 更新内容

上游 `macos-port` 从 `6f48493`（beta.25）快进到 `736567164502f4c08e03d1b0e76f9397da68e6d2`（beta.36），本地分支仍为 `macos/device-validation`。保留此前的 CLI 查找、结构化 doctor、失败退出码、原生界面测试以及构建签名修复。

本轮新增四项改进：

1. 延迟投递前检测任务取消；即使取消后又开始新回合，旧需求也不自动重发。取消状态持久保存，保留文字和附件，支持用户手动重新保存或发送。额度查询返回后再次检查取消与暂停。已经交给 Codex 的队列不能通过此逻辑撤回。
2. 恢复编辑器的原生鼠标定位和拖动选字行为。
3. 输入时持续显示任务名称及保存/发送规则；展开编辑窗口也显示任务名称。取消的草稿有明确提示。
4. Mac 的“检查更新”读取 GitHub 发布信息，显示版本和发布说明，并可打开下载页。API 限流时回退到正式发布页并标明检查范围；未确认架构附件时不会声称已有可用 Mac 安装包。安装仍需手动进行。

工作区修改和新文件已备份到 `work`，合并前的 Git stash 仍保留。没有向远端推送或发布。

## 交付包

- 文件：`CodexQuotaResume-v3.0.0-beta.36-macOS-arm64-local.zip`
- 大小：19,136,342 bytes
- SHA256：`da107fe4daab064b71857088f5ec70f3f34960fae051a34afeca551f3df8c7fb`
- 配套校验文件：`CodexQuotaResume-v3.0.0-beta.36-macOS-arm64-local.sha256`
- 签名：ad-hoc；未进行 Developer ID 签名或 Apple 公证。

这是包含本地修复的构建，不是上游原版二进制。没有更改用户监控、草稿或登录状态，也没有向真实任务发送内容。标准系统和用户 Applications 目录均未发现同名安装，因此本轮交付更新包，没有替换其它路径下的程序。

## 构建环境

| 项目 | 结果 |
| --- | --- |
| 设备 | MacBook Air，Apple M2，arm64，8 GB |
| 系统 | macOS 26.3（25D125） |
| 运行时 | Python 3.14.5，Tk 9.0.3 |
| 打包依赖 | PyInstaller 6.22.3，Pillow 12.3.0，PyObjC 12.2.2 |

```sh
.venv/bin/python scripts/build_macos.py --dist-dir /private/tmp/codex-quota-resume-beta36-local-20260917
```

Documents 的 File Provider 会给 bundle 重附 FinderInfo。本轮在非同步临时目录完成签名，再将 ZIP 放回交付目录。交付 ZIP 另行解压后通过严格签名校验和冻结程序自检。

## 已通过的验证

- `quota_watcher.py --self-test`。
- `test_watcher.py`、`test_delayed_followup.py`、`test_backup.py`、`test_live_status.py`、`test_popup.py`、`test_placement.py`。
- `test_cancelled_followup.py`：7 项回归，包括取消后又开始、截止前取消、旧格式草稿、额度查询期间取消/暂停、历史取消隔离、记录缺失及显式重新发送。
- `test_macos_updater.py`：7 项离线测试，包括版本筛选、架构附件、下载 URL 校验、限流回退和错误处理。没有下载或执行安装程序。
- `test_macos.py` 与 `test_macos_doctor.py`（8 项 doctor 测试）。
- 独立临时测试 `.app` 在正常桌面会话运行 `test_macos_ui.py`、`test_file_attachments.py`、`test_placeholder.py`、`test_macos_update_ui.py`，全部通过。
- 原生功能覆盖：菜单回调、隐藏/恢复、多草稿保护、展开编辑、七张模拟图片、附件副本、保存、鼠标定位及选字、任务名称常驻、取消草稿恢复、更新检查后保持窗口，以及下载页入口。Codex 响应与更新元数据均为模拟；浏览器打开动作亦被模拟。
- `compileall`、`pip check`、`git diff --check`。
- 对最终 ZIP 解压产物执行 `codesign --verify --deep --strict` 及 `CodexQuotaResume --self-test`，结果通过。

## 验证边界

- 原生测试显式设置 `QUOTA_RESUME_SKIP_SCREEN_CAPTURE=1`：屏幕录制权限不可用，像素检查跳过。功能通过不等于像素截图验收通过；CI 默认仍检查截图。
- 新增回归已加入 macOS CI 配置，但此次本地修改尚未在远端 CI 或 Intel 实机运行。
- 本轮未实测真实额度耗尽→恢复→续跑→延迟投递，也未启用/更新用户的持久 LaunchAgent。登录后恢复、实际输入法/Finder 剪贴板、多显示器仍待实机验收。
- 先前 shell 沙箱阻止 App Server 初始化与 LaunchAgent bootstrap；本次未将这两项标为通过。
- Mac 更新逻辑和界面已用隔离元数据验证；本轮没有通过实际 GitHub 网络请求完成端到端升级，也未自动安装更新。


## 后续原位安装（2026-09-17）

用户要求直接更新后，已定位正在使用的 `outputs/CodexQuotaResume.app`（界面 beta.25），正常退出界面，将旧版备份到 `work/installed-beta25-backup-20260917-211610/CodexQuotaResume.app`，并用已校验的 beta.36 ZIP 在原位置替换。清理生成 bundle 中影响签名的 FinderInfo / ResourceFork 后，严格签名校验和程序自检通过。通过桌面重新启动后，实际界面显示 `v3.0.0-beta.36`，任务列表成功更新。原有监控处于未启用状态，本次保持该状态。用户保存数据未修改。


原位运行后复查发现 Documents 同步服务会重新附加 FinderInfo。获得用户 Applications 目录写入权限后，最终将同一已验证 ZIP 安装到 `~/Applications/CodexQuotaResume.app`；`outputs/CodexQuotaResume.app` 现在是指向该应用的符号链接，原入口仍可使用。最终安装经过严格签名检查、自检及桌面启动，界面显示 beta.36、任务列表已更新。退出再启动与运行后的严格签名复查均正常；未改变监控启用状态。


## 2026-09-18：重复启用监控误报修复

`macos.compatible_agent` 对已加载任务进行语义比较：明确指定绝对 CLI 路径时忽略继承 PATH 差异，规范化应用/CLI 符号链接及默认 CODEX_HOME；其余环境、命令参数、账户目录、调度与数据目录差异仍拒绝覆盖。复用加载中的配置，不 bootout、kill 或 bootstrap 现有任务。

5 项新增回归通过，涵盖环境差异、符号链接、真实配置差异、相对 CLI 的 PATH 保护，以及重复安装保持 plist 和发送记录。测试已加入 macOS CI。修复版重新构建后通过签名、自检，安装到 `~/Applications/CodexQuotaResume.app`；旧版保存在 `~/Applications/.quota-resume-backup-20260918-101919/CodexQuotaResume.app`。

通过桌面实际点击“启用 / 更新监控”，界面显示“已启用主备监控（每分钟 / 每五分钟）”，指示灯变绿，无原报错。随后用户操作令界面回到暂停状态，已保留。测试未主动发送任务消息。交付 ZIP 为 `CodexQuotaResume-v3.0.0-beta.36-macOS-arm64-agent-fix.zip`，版本显示仍为 beta.36。
