# v3.1.0beta 第二轮 UI QA

本轮仅修正表现层与交互反馈，不新增功能。开发分支 `MacOS-version`，版本保持 `3.1.0beta`，继续标记 Developer Preview。

## 逐项检查与修复

| 区域 | 发现 / 复核 | 本轮处理 |
| --- | --- | --- |
| 任务选择窗口 | 透明 Tk 弹窗可能出现黑色直角底板与边缘残留，风格偏离系统菜单 | macOS 改用 NSMenu，系统管理圆角、阴影、关闭与滚动；不再创建透明 Tk 弹窗；选择回调经队列交回 Tk |
| 主窗口 | 默认高度与内容不匹配；窗口放大后编辑窗无法排放 | 默认 / 最小 480×620；空间不足时编辑窗在主窗附近显示，不阻止打开；保留系统标题栏、交通灯与系统圆角 |
| 任务选择区域 | 长标题容易挤占菜单；无任务时下一步不明确；列表加载后按钮短暂不可用 | 按实际字体宽度省略，完整标题保留 tooltip；空态提示刷新 / 选择；加载后立即同步按钮 |
| 状态区域 | 旧运行状态可能掩盖监控未启用状态 | 已暂停、异常、未启用 / 读取中等状态明确排序；只使用必要语义色，不增加装饰 |
| 后续任务区域 | 过长预览挤占按钮；缩小时主要操作空间不稳定 | 预览限制 96 字符，底部操作先保留空间；保存摘要、预览与按钮层级统一 |
| 需求编辑窗口 | 按钮字号不一致；展开图标含义不明确；文案偏技术化 | 主窗与编辑窗动作字号统一 11；使用“展开”；说明改为任务 / 额度检查语言；保留取消、保存、发送层级 |
| 附件区域 | 固定按钮容器使按钮高度不一致 | macOS 使用自然按钮高度与一致内边距；附件预览与文件列表保持有界滚动，不改变数据格式 |
| 底部栏 | 主动作与工具动作应有区别 | 更新 / GitHub 保持紧凑次级动作，版本与反馈保持辅助文字；不增加重复窗口控制 |
| Light Mode | 复核窗口、卡片、输入、按钮、标题栏 | 使用共享语义调色板，原生菜单采用 Aqua 外观 |
| Dark Mode | 复核窗口、卡片、输入、按钮、标题栏 | 使用同一布局与字号，原生菜单采用 Dark Aqua 外观，无渐变、玻璃或动画 |

## 业务影响

`quota_watcher.py`、`codex_status.py`、`macos.py` 未修改。任务选择继续返回同一列表索引；保存、附件持久副本、立即发送与延迟投递仍走原有回调。`app.py` 只增加任务加载后立即同步已保存摘要和按钮状态。Windows 保留原弹窗与原窗口路径。

## 验证与限制

本机图形会话受到终端沙箱限制，不能把当前用户桌面当作已完成实机观察。原生 GUI 检查与截图由 GitHub macOS CI 执行，使用模拟任务和临时数据；不触碰真实任务。目标设备上的多显示器、Retina、系统设置真实切换 Light / Dark，以及实际鼠标 / Esc 关闭原生菜单仍需人工验收。

系统标题栏和菜单圆角由 AppKit 管理。相关 API：[NSMenu](https://developer.apple.com/documentation/appkit/nsmenu)、[cancelTracking](https://developer.apple.com/documentation/appkit/nsmenu/canceltracking())。

本版仍为 ad-hoc 签名，没有 Developer ID 与 Apple 公证；不作为正式稳定版。

## 最终验证结果（2026-09-18）

验证提交：`a7b35377c689d38da881b2f0a8525cf06e2cba2e`。

- [macOS CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35358228259)：arm64 与 Intel 均通过，包含已有业务回归、原生主窗 / 编辑窗、图片与文件往返、缩放与大窗口排放、菜单数据与选择回调、临时 LaunchAgent、打包与冻结自检。
- [Windows CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35358228213)：通过已有回归。
- 本地已有 watcher、延迟投递、取消、备份、实时状态、弹出、macOS 合同、doctor 与 updater 测试通过；compileall 与差异空白检查通过。
- 原生 NSMenu 的条目、选择回调、队列与主题参数已自动测试；弹出追踪入口在 CI 使用替身，避免无人值守菜单阻塞。菜单真实黑边消除、Esc、外部点击及多显示器定位必须由实际桌面检查，当前不宣称已完成物理操作验收。
- 已人工读取 CI 浅色 / 深色截图：主窗与编辑窗没有重复窗口控制；字体、动作层级、颜色与留白一致。截图为模拟任务，不表示实际业务端到端验收。
- 本地包严格签名检查与 `--self-test` 通过，安装至 `/Users/zhantaorui/Applications/CodexQuotaResume.app`。原安装备份至 `/Users/zhantaorui/Applications/.quota-resume-qa2-backup-20260918-224837/CodexQuotaResume.app`。
- 安装包 `CodexQuotaResume-v3.1.0beta-macOS-arm64-preview-ui-qa2.zip`，SHA256：`e85d007c50be21df6eabdf767d58331c6ab57f122e7a60e75042004ff3bcf955`。

最终状态：第二轮代码修正完成，自动回归通过，已安装与推送 `MacOS-version`。版本仍为 `v3.1.0beta · Developer Preview`，目标设备人工验收未完成。安装不会替换已运行进程的界面；需退出旧界面后重新打开应用才能看到本轮改动。

## 任务选择闪退修复（2026-09-19）

用户在本机点击任务选择时闪退。系统崩溃报告 `CodexQuotaResume-2026-09-18-225151.ips` 指向 `PyEval_RestoreThread`：Python 3.14 / Tk 9 的按钮回调进入 PyObjC `NSMenu.popUpMenuPositioningItem...`，AppKit 菜单跟踪期间又重入 Tcl/Tk 事件，触发进程 `SIGABRT`。第二轮 QA 中直接调用 AppKit 菜单的方案已撤回。

现在通过 Tk `Menu.tk_popup` 打开 macOS Aqua 菜单，由 Tcl/Tk 自己管理系统菜单跟踪与 Python 回调；不再从 Tk 回调进入 PyObjC 的嵌套菜单事件循环。菜单沿用任务索引与现有选择行为，未改动监控、保存或发送业务逻辑。长任务名称继续按字体宽度省略。CI 的菜单条目与选择回调用有界测试；无人值守 CI 不能模拟真实鼠标跟踪，因此本机物理点击是否仍崩溃必须在重新打开新包后验收。

已验证提交 `48fa558d6f17fd97044ca3ed00ea889beae53a58`：

- [macOS CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35426698536)：macOS arm64 / Python 3.13、arm64 / Python 3.14、Intel / Python 3.13 均通过，包括原生 GUI 与冻结程序自检。
- [Windows CI](https://github.com/joejoeha/codex-quota-resume/actions/runs/35426698550)：通过。
- 本地已有 macOS 合同、版本、排放、延迟投递、取消回归通过；构建包严格签名检查与冻结自检通过。
- 已安装至 `/Users/zhantaorui/Applications/CodexQuotaResume.app`；旧安装备份至 `/Users/zhantaorui/Applications/.quota-menu-crash-backup-20260919-143131/CodexQuotaResume.app`。
- 修复包 SHA256：`164681ba9caf2dee57e5ad29a8061e6cd669f05317a9a5630417a9a4e9108946`。版本仍为 `v3.1.0beta` Developer Preview。

此前文档中的 NSMenu 说明保留为第二轮历史记录，以上修复取代了该实现。安装后的新界面需要退出旧进程再重新打开；本次未强制结束用户进程或触碰真实监控配置。
