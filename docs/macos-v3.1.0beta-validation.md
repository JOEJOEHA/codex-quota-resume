# v3.1.0beta · macOS Developer Preview

第二轮修正与当前安装结果见 [UI QA 记录](macos-v3.1.0beta-ui-qa.md)。以下结果保留第一轮验证历史。

开发分支：`MacOS-version`。本轮不修改 `main`，不发布稳定版。

## 架构与修改范围

GUI 仍为 Tkinter + Pillow，macOS 菜单栏使用 PyObjC / NSStatusItem。只进行小范围表现层拆分，业务操作继续通过已有回调调用。新增 `macos_main_ui.py` 管理主窗口布局，`macos_appearance.py` 管理语义颜色、系统外观检测与原生标题栏同步。

| 文件 | 改动 |
| --- | --- |
| `scripts/macos_main_ui.py` | 状态胶囊、后续任务卡片、已保存要求预览、按钮层级、底部工具栏 |
| `scripts/macos_appearance.py` | Light / Dark 调色板，打开期间跟随系统主题，原生窗口外观同步 |
| `scripts/window_ui.py` | macOS 原生标题栏与系统圆角，可调整窗口尺寸；任务名称省略、菜单尺寸与焦点兼容性；Windows 保留原路径 |
| `scripts/app.py` | macOS 布局接线，复用原有监控、编辑、保存反馈和立即发送回调；退出程序复用暂停接口 |
| `scripts/plan_dialog.py` | macOS 统一主题编辑器，取消 / 保存 / 发送层级，统一附件入口，文件移除，固定高度可滚动的附件预览 |
| `scripts/tray_macos.py` | 原生菜单栏恢复；退出程序并暂停监控；保留仅退出界面选项 |
| `scripts/updater.py` | 唯一版本源 `3.1.0beta`，兼容新版本格式及历史 `bata` 拼写；更新元数据检查 |
| `scripts/build_macos.py` | 从同一版本源设置 metadata；Apple 合法数字版本为 `3.1.0`，预览身份记录为 `v3.1.0beta` |
| `.github/workflows/macos.yml` | 保留 arm64 / Intel 构建矩阵，增加重构回归及两套外观截图 |
| `scripts/test_macos_redesign.py`、`scripts/test_macos_actions.py` | 新增外观、状态、卡片、缩放布局、混合附件、保存 / 重开 / 发送回归 |
| `scripts/test_macos_ui.py`、`test_file_attachments.py`、`test_placeholder.py`、`test_macos_updater.py` | 根据用户可见文案、原生标题栏及统一附件入口更新断言；保留原有功能验证 |
| `README.md`、`README.en.md` | 更新 v3.1.0beta 特性与 Developer Preview 定位 |

## 业务逻辑

未修改 `quota_watcher.py`、`codex_status.py`、`macos.py` 的额度判断、自动续跑、任务识别、延迟投递、防重复、保存和附件数据格式。

“立即发送”仍调用 `request_plan_send`，受原有原任务状态与额度检查约束，不绕过安全投递条件。编辑窗口“发送”仍保存 `sendRequested=True`。附件仍保存为持久副本，移除只移出列表，不删除已有保存的来源文件。

macOS 关闭主窗口仅隐藏，菜单栏可恢复。“退出程序并暂停监控”调用已有暂停接口，再执行已有草稿保护退出逻辑；正在执行的 Codex 任务不取消，独立 LaunchAgent 不被删除或强制终止。可选择“仅退出界面”继续后台。Windows 的退出行为不改动。

## 验证边界

本机终端沙箱阻止 Tk 图形会话初始化，也阻止 LaunchServices 启动独立 GUI 测试应用；本地真实 LaunchAgent bootstrap 被拒绝。这些不记为通过。原生 UI 与 LaunchAgent 测试改由现有 GitHub macOS CI 执行，使用临时文件及模拟 Codex 响应，不操作用户真实任务。

系统主题变化采用每 1.5 秒在 Tk 主线程检查 AppKit effectiveAppearance 的保守方案，主题切换可能有短暂延迟。`QUOTA_RESUME_THEME=light|dark` 仅供隔离开发测试，正常用户不必设置。截图中的任务名称及后续要求是模拟内容。

## 发布前人工验收

- 在真实 Apple Silicon / Intel 目标设备检查 Retina、多显示器、较小工作区、原生最小化 / 恢复与窗口尺寸。
- 在系统设置中实际切换 Light / Dark，确认主窗口、编辑窗口、文件选择器、提示弹窗和菜单栏统一，输入内容保持。
- 实际登录的 Codex 执行额度耗尽 → 恢复 → 自动续跑 → 延迟投递；检查普通文件、图片、输入法与 Finder 剪贴板。
- 检查关闭后后台继续、菜单栏恢复、暂停 / 恢复、退出时草稿保护；已开始的 Codex 任务不被取消。
- 用真实 GitHub 发布元数据检查更新和 GitHub 入口。模拟链接回调通过不等于真实浏览器下载端到端通过。
- 本版仍采用 ad-hoc 签名，尚无 Developer ID 签名与 Apple 公证；继续标记 Developer Preview。


## 最终验证结果（2026-09-18）

已验证代码提交：`14b57157c39a38bef2efa6bf11cb2856abec0556`。

- [macOS CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35355307151)：`macos-14` arm64、`macos-15-intel` x86_64 两项均通过。包括离线业务回归、原生 GUI、临时 LaunchAgent、打包、冻结程序自检与构建附件上传。
- [Windows CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35355307270)：通过现有 Windows 业务、任务配置和更新回归。
- 本地业务回归、版本排序、布局检查、compileall 和 git diff --check 通过。
- 本地产物严格 codesign 校验、自检通过，版本 metadata 为 `3.1.0` / `v3.1.0beta · macOS Developer Preview`。
- 已安装最终包至 `~/Applications/CodexQuotaResume.app`。替换前版本备份至 `~/Applications/.quota-resume-backup-20260918-221956/CodexQuotaResume.app`。不修改真实监控配置，不发送真实任务，不强制结束用户进程。
- arm64 ZIP SHA256：`e68c2de748833a5e2f2b28082ed80739fb2f4fe22037e9b801bd3ab20c1416f0`。本地 ZIP 名称：`CodexQuotaResume-v3.1.0beta-macOS-arm64-preview.zip`。

### 验收覆盖

| 检查项 | 自动验证及边界 |
| --- | --- |
| 1. 正常启动 | 原生源代码应用启动及 arm64 / x86_64 冻结产物自检通过；本机 Finder 启动仍需人工检查 |
| 2. 主窗口显示 | CI 实际原生窗口及截图通过 |
| 3–4. Light / Dark | 主窗口与编辑器切换、语义颜色和两套截图通过；系统设置真实切换待目标设备验收 |
| 5. 自动监控启动 | 临时 LaunchAgent 执行通过；真实用户监控配置不操作 |
| 6. 暂停 / 恢复 | UI 操作与暂停文件、恢复回调通过；真实恢复后的额度周期待验收 |
| 7. 任务列表 | 模拟 Codex 响应、选择、长名称、菜单重复开关 / Esc / 外部点击 / 隐藏通过 |
| 8–9. 添加 / 编辑 | 编辑器打开、重复编辑窗复用、已保存卡片与重新加载通过 |
| 10. 保存 | 文字及图片 / 文件持久副本往返通过 |
| 11. 立即发送 | 主窗口请求回调和编辑器 sendRequested 标志通过；业务条件检查沿用已有回归 |
| 12–13. 图片 / 普通文件 | 混合选择、七张图片、缩略图移除、文件单独移除、来源删除后副本保留通过 |
| 14–15. 关闭后后台 / 菜单栏恢复 | 隐藏与原生菜单栏回调恢复、草稿保护通过；后台任务与 UI 进程分离维持 |
| 16–17. 更新 / GitHub | 离线版本元数据及正确链接回调通过；实际浏览器 / 发布下载路径待验收 |
| 18. 不明显重叠 | 布局边界断言、调整大小、两套截图人工读取通过 |
| 19. 两种 Mac 架构 | 两项 CI 的原生 UI、打包及冻结自检均通过 |
| 20. Windows 回归 | 现有 Windows CI 通过，macOS 绘制及标题栏路径以平台条件隔离 |

README 的图片是 CI 中使用模拟任务生成的真实 Tk 窗口截图，裁剪为应用窗口区域。截图不表示真实额度流程已经验收。
