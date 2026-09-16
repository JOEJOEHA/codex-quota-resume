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

本机是 Windows，尚未连接用户的 Mac。已询问用户是否可提供 Mac 连接方式；不能把未回复当成已有设备或授权。

下一步在已登录 Codex 的目标 Mac 执行 `--doctor`，确认 CLI 路径、App Server 实验接口及 queue 支持；再验收真实菜单点击、截图权限、Retina/多显示器、重启后后台调度，最后完成“明确额度中断 → 额度恢复 → 原任务验收 → 后续任务发送”的真实完整周期。CI 使用模拟 Codex 响应，不能替代这个验收。

详细构建和测试说明见 `docs/macos.md`。未改变当前 Windows 监控、用户任务、附件或打开的草稿。
