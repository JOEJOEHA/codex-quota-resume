# macOS 移植进度（2026-09-16）

当前阶段：开发预览已构建，尚未完成目标 Mac 和真实额度恢复验收。不得输出整体完成标记。

## 源码与交付

- 基线：Windows v3.0.0-beta.15 / `4edb3cd`。
- 分支：`macos-port`；草稿 PR：https://github.com/JOEJOEHA/codex-quota-resume/pull/1 。未合并、未覆盖 Windows 发布版。
- 本轮已验证的程序源码提交：`eae49ce`。
- 成功的 macOS CI：https://github.com/JOEJOEHA/codex-quota-resume/actions/runs/35065360614 。包含 arm64 / x86_64 `.app` 预览 ZIP、SHA256、界面截图。
- 预览包为开发用 ad-hoc 签名，没有 Developer ID、公证或正式 DMG。

## 已实现与验证

- 复用监控业务逻辑，保留明确额度错误、实时额度、完成标记、原会话续跑、写入者冲突回退和发送去重。
- macOS 用户路径、CLI 查找与只读 doctor、主备 LaunchAgent（60 / 300 秒）、共享 flock、暂停标记。
- 安装更新共用监控锁，避免覆盖发送记录；不卸载或终止正在执行的任务。
- 原生菜单栏通过事件队列交给 Tk 主循环处理，关闭/恢复窗口，退出时保留草稿。
- macOS 字体、窗口摆放、截图工具、Finder 文件/图片粘贴、Command 快捷键、展开编辑器。
- Aqua 缩略图改为 Canvas 直接绘制；窗口布局后标记 Cocoa backing view 重绘。原生截图检查验证缩略图及主窗口文字实际显示，并允许小范围显示色差。
- Windows 本地界面/附件/草稿回归及 CI 通过。
- macOS 14 arm64、macOS 15 Intel 的业务回归、跨进程锁、临时 LaunchAgent 后台启动、原生窗口测试、PyInstaller 构建、签名检查、打包后自检通过。

## 仍需外部条件

用户已确认没有 Mac；后续由朋友在自己的 Mac 上通过 Fork / PR 继续开发和验收。完整中英文交接 prompt 见 [macOS Development Handoff / macOS 开发交接](docs/macos-handoff.md)，贡献身份与流程见 [Contributing / 贡献指南](CONTRIBUTING.md)。

The owner has no Mac. A contributor will continue on their own Mac through a fork and PR. Native CI builds exist, but signed-in target-device and real quota-recovery acceptance remain pending. See the bilingual handoff above; do not report full completion.

下一步在已登录 Codex 的目标 Mac 执行 `--doctor`，确认 CLI 路径、App Server 实验接口及 queue 支持；再验收真实菜单点击、截图权限、Retina/多显示器、重启后后台调度，最后完成“明确额度中断 → 额度恢复 → 原任务验收 → 后续任务发送”的真实完整周期。CI 使用模拟 Codex 响应，不能替代这个验收。

详细构建和测试说明见 `docs/macos.md`。未改变当前 Windows 监控、用户任务、附件或打开的草稿。

## Windows 应用内更新（2026-09-17） / Windows in-app updates

- Windows 主分支 `49f9949`，发布 [v3.0.0-beta.18](https://github.com/joejoeha/codex-quota-resume/releases/tag/v3.0.0-beta.18)。左下版本号、右下检查更新；GitHub 下载、SHA256 校验、分版本安装与新界面启动。
- 实测发现 GitHub API 403 限流和公开 latest 地址缓存旧标签；已增加公开页面备用检查并刷新缓存。
- 自动更新从 GitHub 实际下载 beta.18 并安装成功。桌面快捷方式、主备监控均指向 `%LOCALAPPDATA%\CodexQuotaWatcher\versions\v3.0.0-beta.18\CodexQuotaResume.exe`；原监控 enabled 状态不变。未删除任务、附件或强制结束草稿窗口。
- 已安装 EXE 窗口渲染检查：430×535，底部版本号与更新按钮均可见。更新逻辑、校验失败阻止执行、版本排序、限流备用路径、输入窗口及监控业务回归通过；Windows CI 35128368435 成功。
- Upgrade download/install verified against the real GitHub release with a simulated older client version. The installed EXE, shortcut and both monitor targets were checked; open drafts and monitor state are preserved.
- macOS 分支同步 Windows 更新代码并保留平台限制；macOS 预览暂不支持自动安装。前述目标 Mac 与真实额度恢复验收仍待朋友完成。

## 2026-09-17 最新用户要求 / Latest request

- 已恢复明确额度中断时自动打开任务输入窗：GUI 约 5 秒检测，同进程复用草稿；独占领取文件保证同一中断只弹一次。GUI 未运行时在下次后台检查打开。零额度快照、网络错误及正常完成不触发。
- Windows beta.24 已安装；源码 main `6386c95`，Windows CI `35163568163` 通过。
- macOS 分支已同步主分支更新；菜单栏采用第三版奶油色小猫，构建包含图片资源。候选构建提交 `2a38b21`，CI `35163669146`。
- Release `v3.0.0-beta.24` 正在汇总 Windows 与 macOS 两种架构附件；以最终 Release 页面和 CI 结论为准。
- macOS 仍为开发预览：应用内自动安装尚未移植，使用手动下载替换；目标 Mac 登录及真实额度恢复周期验收仍待完成，不宣称全功能验收。

The latest Windows changes are synchronized to macos-port. macOS packages remain developer previews; in-app automatic installation and signed-in target-device acceptance remain pending. Windows auto-update and quota-popup behavior were locally tested.
