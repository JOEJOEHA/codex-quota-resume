# macOS Development Handoff / macOS 开发交接

[贡献指南 / Contributing](../CONTRIBUTING.md) · [中文说明](../README.md) · [English README](../README.en.md)

把下方中文或英文 prompt **任选一份完整复制**给朋友 Mac 上的 Codex。朋友使用自己的 GitHub 和 Codex 账号；首次 GitHub 登录或系统权限弹窗由朋友完成。Codex 应自行检查工具与源码，再继续开发。

Copy either complete prompt below into Codex on the contributor's Mac. Use the contributor's own GitHub and Codex accounts. The contributor handles initial sign-in and OS permission dialogs; the agent handles repository inspection and development.

## 中文 Prompt（复制下面代码框内全文）

```text
你是这台 Mac 上的 Codex 开发 agent。请帮助我作为贡献者继续开发 JOEJOEHA/codex-quota-resume 的 macOS 版本，并提交可审阅的贡献。请实际完成工作，不只输出方案；减少重复确认，按实际源码和最新用户要求推进。

仓库：https://github.com/JOEJOEHA/codex-quota-resume
交接日期：2026-09-16。先核实远端最新状态，不把以下快照当作永远有效。

一、接手与贡献身份
1. 检查当前目录、未提交修改、macOS/芯片架构、Git、Python/Tk、GitHub 登录和 Codex CLI。使用我的 GitHub 账号和我自己的提交作者身份，不使用项目所有者的身份或凭据。缺少登录、作者邮箱或系统权限时，只向我索取实际缺少的信息；不泄露令牌。
2. 阅读适用的 AGENTS.md、README.md、README.en.md、CONTRIBUTING.md，再读取 macOS 开发分支上的 PROGRESS.md、docs/macos.md、实际源码与测试。不要把 Windows 安装 Skill 当成 Mac 安装步骤运行。
3. 当前 macOS 源码在上游 macos-port，草稿 PR #1：https://github.com/JOEJOEHA/codex-quota-resume/pull/1 。main 目前仍是 Windows 程序。最新已发布预览标签 desktop-preview-2026-09-16 对应 cbaa818；Windows 基线 v3.0.0-beta.15 / 4edb3cd。必须 fetch 后从最新开发代码接手，不退回基线重写。
4. 默认使用我的 Fork；检查已有 Fork/remote 后再创建或复用，origin 指向我的 Fork，upstream 指向 JOEJOEHA/codex-quota-resume。若 PR #1 未合并，从 upstream/macos-port 创建 macos/<简短英文主题> 分支；若已合并，检查实际文件后从 upstream/main 开始。Fork 只有 main 时仍须 fetch 上游 macos-port。不覆盖现有修改、不 force push。
5. 我授权本任务范围内的源码修改、本地隔离测试、构建、向我的 Fork push，以及向原仓库创建/更新贡献 PR；不授权直接合并上游、发布正式版本、购买额度或使用他人凭据。仅 Contributor 贡献流程不需要仓库写权限。保留我的真实作者归属；GitHub 贡献图还取决于合并默认分支等条件。

二、当前状态：继续验收和修复，不从零移植
已有 macOS CLI 查找、只读 doctor、用户数据路径、主备 LaunchAgent（60/300 秒）、flock 去重、原生菜单栏、Command 快捷键、截图/Finder 粘贴、窗口摆放、草稿保护和 PyInstaller .app 构建。
macOS 14 arm64 / macOS 15 Intel CI 已验证模拟业务逻辑、进程锁、临时 LaunchAgent、原生 UI、构建签名与打包后自检；成功构建记录：https://github.com/JOEJOEHA/codex-quota-resume/actions/runs/35065533139 。CI 没有真实登录账户，不是实际额度恢复验收。
M1/M2/M3 使用 arm64 包，Intel 使用 x86_64 包；不能声称每种芯片均已实机测试。当前仅 ad-hoc 签名，没有 Developer ID、公证、正式 DMG。原维护者没有 Mac，目标设备验收由我这边继续。
核心文件：scripts/app.py、plan_dialog.py、window_ui.py、quota_watcher.py、codex_status.py、macos.py、tray_macos.py、build_macos.py，以及 .github/workflows/macos.yml。原生事件回调必须入队交给 Tk 主循环，不能直接重入 GUI。现有 Cocoa 重绘和 Canvas 缩略图修复应保留，除非证据证明需要替换。

三、不得改变的业务及界面要求
- 仅恢复明确因额度耗尽中断、仍未完成的原任务；发送前读实时额度。仅额度为零、普通网络错误、正常完成都不能触发。继续原会话，不新建任务、不改模型、不买额度。
- 主备监控共享锁和发送记录，防止重复发送。默认 exec resume；仅桌面写入者冲突才尝试 queue。入队不等于启动或完成，必须保留后续状态确认。
- 后续文字/图片/文件只是保存，不立即发送；被恢复的原任务完成验收并出现 [QUOTA_RESUME_GOAL_COMPLETE] 且额度可用，才允许发送后续任务。附件复制到本地，原文件移走后仍可用；图片不设固定六张上限，横向滚动，点击移除；文件双击/Delete 移除。
- 深色圆角主窗/输入窗 430×535，展开编辑器 760×620；主标题16、说明11，合适的 macOS 字体。显示任务名称而非 UUID，任务按钮/菜单固定等宽。状态圆点只有确认主备均启用才为绿色，否则红色。
- 保存后红旗红绿闪五次，保持红色到任务交给 Codex，重启后按保存状态恢复。展开/关闭完整带回文字。同进程复用同任务草稿；输入窗贴主窗右侧，空间不足放左侧，顶对齐、间隔6像素。
- 主窗关闭/最小化后菜单栏常驻，点击恢复，菜单支持打开/退出界面。退出界面不停止监控，不丢草稿。不停止现有监控、不删除用户任务附件、不强杀可能有未保存内容的窗口。

四、在本机自主完成的工作
1. 使用带 Tk 的 Python 3.13 建立项目 .venv，安装 requirements.txt 和 PyInstaller。先运行 python scripts/app.py --doctor，检查已登录 CLI 的路径、resume/queue、App Server 实时额度与回合接口；doctor 只读不发送任务。无任务导致无法验证 turnsAPI 时如实记录。不要把 queue 支持从 Windows 推断到 Mac。
2. 复用 .github/workflows/macos.yml 中的测试命令，运行共享逻辑、Mac 原生 UI、跨进程锁、临时 LaunchAgent 测试并检查截图。根据实际问题做最小修复，复测相应路径，并保持 Windows CI 通过。
3. 运行 python scripts/build_macos.py，检查 dist/CodexQuotaResume.app、架构、签名与 SHA256，再运行 dist/CodexQuotaResume.app/Contents/MacOS/CodexQuotaResume --self-test。实际打开 .app 验证；不能仅凭打包成功断言可用。
4. 在这台 Mac 验证菜单栏实际点击、隐藏/恢复/最小化/退出、多个草稿、展开编辑器、中文输入、Command 快捷键、红旗闪动及重启恢复、七张以上图片、普通文件、Finder/剪贴板粘贴、截图允许/拒绝/取消、删除原文件后附件副本可用。可使用 computer use；需要人工系统操作时给我一个简单步骤。
5. 验证 Retina、多显示器/负坐标/边缘摆放。只有单屏或单一架构时明确哪些场景没测，不伪造覆盖。真实安装、持久监控启用、重启登录以及会消费额度的测试，先列出具体影响，由我确认适当测试会话与时机；隔离测试使用临时名称/目录，只清理自己创建的测试数据，不动用户现有监控。
6. 在我明确选定的测试任务上验证真实“明确额度耗尽中断 → 恢复额度 → 继续原任务 → 原任务完成验收 → 发送保存后续任务”，确认主备同时检查仍只发送一次。不得为制造额度耗尽而故意大量消耗额度，不兑换重置券/购买额度，不冒用真实用户任务。若没有真实额度事件、登录、权限、硬件或签名证书，完成其他可执行步骤并记录具体剩余验收，不用模拟通过冒充完成，也不无限空等。
7. 更新 PROGRESS.md 与中英文文档，记录设备/系统/芯片、实际命令结果、构建文件、已验收与未验收项。不要把账户令牌、个人日志、任务正文、附件或隐私截图提交 GitHub。

五、提交和交付
代码标识符、文件、分支和资产名保持英文/ASCII；提交、PR、发布说明使用中英文标题与正文，例如 fix(macos): Restore menu-bar window / 修复菜单栏窗口恢复。同步 README.md 与 README.en.md 的状态。
向我的 Fork push，向上游 macos-port 提贡献 PR（移植已合并才以 main 为 base），避免重复提交整个已有移植。用文件传递多行 PR 正文，包含中文/English 的改动、验证、待验收项。任何必要验收缺失时保持 Draft；不自行合并 PR 或发布稳定版。
最后给我 PR 链接、构建产物位置、通过的测试、仍需人工条件。只有原任务全部目标验收完成才能在最终回复末尾单独输出 [QUOTA_RESUME_GOAL_COMPLETE]；等待权限/信息/设备或实测未完成时绝不输出。完成当前可执行交付后停止，不另建后台自动任务。
```

## English prompt (copy the entire block)

```text
You are the Codex development agent on my Mac. Help me contribute to the macOS version of JOEJOEHA/codex-quota-resume. Do the implementation, validation and reviewable contribution, not just planning. Work autonomously within scope and avoid repeated confirmations.

Repository: https://github.com/JOEJOEHA/codex-quota-resume
Handoff snapshot: 2026-09-16. Fetch and inspect current remote state before relying on this snapshot.

1. Repository and identity
Inspect the current checkout, uncommitted changes, macOS/chip architecture, Git, Python/Tk, GitHub authentication and Codex CLI. Use MY GitHub account and actual author identity, never the owner's credentials or identity. Ask only for missing sign-in, author information or OS interaction; never expose tokens.
Read applicable AGENTS.md, both READMEs, CONTRIBUTING.md, then PROGRESS.md, docs/macos.md, actual source and tests on the development branch. Do not execute the Windows installation Skill on macOS.
The port currently lives on upstream macos-port in draft PR #1: https://github.com/JOEJOEHA/codex-quota-resume/pull/1 . main still contains the Windows application. Preview tag desktop-preview-2026-09-16 points to cbaa818; the Windows baseline is v3.0.0-beta.15 / 4edb3cd. Continue from current code rather than restarting the port.
Create or reuse MY fork after checking existing remotes: origin is my fork; upstream is JOEJOEHA/codex-quota-resume. Fetch upstream/macos-port even if the fork only copied main. Create macos/<short-topic> from upstream/macos-port while PR #1 is unmerged; if merged, inspect files and start from current upstream/main. Preserve existing changes; do not force-push.
I authorize scoped source changes, isolated local tests/builds, pushing to my fork and creating/updating an upstream contribution PR. This does not authorize merging upstream, publishing stable releases, purchasing quota or using another person's credentials. Contributor work does not require collaborator access. Preserve my authorship; GitHub credit also depends on its default-branch/email rules.

2. Existing implementation
The port already includes CLI discovery, a read-only doctor, macOS data paths, primary/backup LaunchAgents (60/300 seconds), flock deduplication, native menu-bar integration, Command shortcuts, screenshots/Finder paste, window placement, draft protection and PyInstaller .app builds.
CI passed on macOS 14 arm64 and macOS 15 Intel for simulated business logic, process locking, temporary LaunchAgents, native UI, packaging/signature checks and frozen self-tests: https://github.com/JOEJOEHA/codex-quota-resume/actions/runs/35065533139 . CI lacks a signed-in personal Codex account and does not prove real quota recovery.
M1/M2/M3 use arm64; Intel uses x86_64. Individual chip models have not all been tested. Builds are only ad-hoc signed, without Developer ID, notarization or a final DMG. The original maintainer has no Mac; continue target-device validation here.
Key files under scripts/: app.py, plan_dialog.py, window_ui.py, quota_watcher.py, codex_status.py, macos.py, tray_macos.py, build_macos.py. Also read .github/workflows/macos.yml. Native callbacks must enqueue actions for Tk's main loop, never reenter GUI code directly. Keep existing Cocoa repaint and Canvas thumbnail fixes unless evidence justifies changing them.

3. Required behavior
Resume only explicitly quota-interrupted, unfinished original work after checking live quota. Zero quota alone, normal completion and ordinary network errors must not trigger resumption. Keep the same session; do not create sessions, change models or buy quota.
Both watchers share locking and send records. Use exec resume by default; queue only on desktop writer conflict. Queue acceptance is neither startup nor completion; retain subsequent confirmation.
Saving follow-up text/images/files must not send immediately. Send only after the watcher-resumed original goal is accepted as complete with [QUOTA_RESUME_GOAL_COMPLETE] and quota is available. Copy attachments into local storage; moving/deleting originals must not break them. No fixed six-image limit; horizontal previews, click-to-remove images, double-click/Delete for ordinary files.
Preserve the dark rounded 430x535 main/composer windows, 760x620 expanded editor, title size 16/body size 11 and suitable macOS fonts. Show task names, not UUIDs; keep selector/menu widths consistent. The status dot is green only when both monitors are confirmed enabled, otherwise red.
Saved flags flash red/green five times, stay red until handed to Codex and restore from saved state after restart. Expanded editing returns all text. Reuse same-process drafts per task. Place the composer 6 pixels beside the main window, right first/left if needed, top-aligned.
Closing/minimizing the main window keeps menu-bar residency; clicking restores it, and the menu opens/exits the interface. Exiting UI must not stop monitoring or lose drafts. Do not stop existing monitors, delete user tasks/attachments or force-kill windows containing unsaved work.

4. Execute on this Mac
Create a project .venv with Python 3.13 including Tk, then install requirements.txt and PyInstaller. Run python scripts/app.py --doctor: verify signed-in CLI discovery, resume/queue support, App Server quota and turn APIs. Doctor is read-only. Record when no history prevents turnsAPI validation; do not infer Mac support from Windows.
Run applicable commands from .github/workflows/macos.yml, including business regressions, native UI, process locking and temporary LaunchAgents; inspect screenshots. Fix observed issues minimally, rerun affected checks and preserve Windows CI.
Run python scripts/build_macos.py. Inspect dist/CodexQuotaResume.app, architecture, signing and SHA256. Run dist/CodexQuotaResume.app/Contents/MacOS/CodexQuotaResume --self-test and actually launch the app; successful packaging alone is insufficient.
Validate real menu clicks, hide/restore/minimize/exit, multiple drafts, expanded editing, Chinese input, Command shortcuts, flags and restart persistence, more than seven image attachments, ordinary files, Finder/clipboard paste, screenshot permission allow/deny/cancel and retained copies after originals are deleted. Use computer use when helpful; give one clear step for necessary human OS interaction.
Validate Retina, multiple displays/negative coordinates and edge placement. Record untested hardware scenarios honestly. Before installing persistent monitoring, reboot/login checks or quota-consuming tests, explain the concrete effect and obtain my confirmation of the test session and timing. Isolated tests use temporary names/directories and clean up only their own data, preserving existing monitoring.
With my explicitly selected test task, validate a REAL explicit quota interruption -> quota recovery -> original session resumption -> accepted goal completion -> saved follow-up delivery, exactly once under both watchers. Do not deliberately burn quota, redeem resets, purchase quota or use unrelated real tasks. If quota events, login, permissions, hardware or certificates are unavailable, finish other actionable work and list the specific remaining acceptance items. Do not substitute mock tests for real acceptance or wait indefinitely.
Update PROGRESS.md and Chinese/English docs with device, OS/chip, commands/results, artifacts and passed/pending acceptance. Never commit credentials, personal logs, task contents, attachments or private screenshots.

5. Contribution and delivery
Keep identifiers, filenames, branches and asset names in English/ASCII. Use Chinese AND English commit/PR/release titles and explanations, e.g. fix(macos): Restore menu-bar window / 修复菜单栏窗口恢复. Keep README.md and README.en.md status aligned.
Push to my fork and open/update an upstream PR targeting macos-port until the port is merged, then main. Avoid duplicating the existing port in the contribution diff. Supply multiline PR bodies through a file, including Chinese/English changes, validation and remaining work. Keep it draft if required acceptance is missing. Do not self-merge or publish a stable release.
Deliver the PR URL, local artifacts, passed checks and remaining external requirements. Only append [QUOTA_RESUME_GOAL_COMPLETE] as the final standalone line when ALL original goals have passed acceptance; never while waiting for information/permission/hardware or missing real validation. Stop after the actionable handoff; do not create extra background automations.
```
