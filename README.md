# Codex Quota Resume · Windows Beta

为因额度耗尽而中断的 Codex 任务提供本地自动续跑。主监控读取日志，备用监控直接读取 Codex 任务状态；发送前检查**实时可用额度**，不要求旧日志显示 100%，也不固定多等五分钟。

**这是测试版，不保证所有 Codex 版本和异常场景都能自动恢复。** 已测试实时查询、后台直接续跑、失败处理及防重复；尚未完成新版在真实额度耗尽—恢复周期中的验收。

## 它包含什么

- 主监控每分钟检查，备用监控每五分钟独立检查。
- 两层共用进程锁和发送记录，避免重复启动。
- 通过 `codex exec resume` 继续原任务；若桌面端已有写入者，使用 `codex queue` 交给现有桌面任务执行。入队后仍需观察启动，不把入队当作完成。不新建任务，不主动更改模型或购买额度。
- 深色圆角后续任务输入框，显示任务名称，支持图片、文件、粘贴截图和 Windows 截图工具；图片不设固定数量上限，缩略图可横向滚动。
- 输入框右下角的 ↗ 可展开为独立大窗口，关闭大窗口会带回文字。保存后，任务选择框显示红旗并红绿闪动五次，红旗保留至任务已交给 Codex。
- 监控查询不调用模型；真正续跑会正常消耗 Codex 额度。

提供 **Windows 本地 EXE + Windows 计划任务 + 可选 Codex Skill**。EXE 已包含 Python、Tkinter 和 Pillow，无需另外安装 Python。

## 下载本地软件（推荐）

[下载 CodexQuotaResume.exe](https://github.com/JOEJOEHA/codex-quota-resume/releases/download/v3.0.0-beta.13/CodexQuotaResume.exe) · [发布说明](https://github.com/JOEJOEHA/codex-quota-resume/releases/tag/v3.0.0-beta.13)

主界面与输入框右上角仅保留最小化和关闭按钮，可从任务栏恢复；软件、快捷方式及任务栏使用循环箭头图标。

主界面与输入框采用统一深色圆角外观、标题字号和任务菜单宽度，可拖动标题栏或空白边缘移动窗口。绿色圆点代表主备监控均已启用，红色代表未全部启用或无法确认；状态每五秒读取实际计划任务。

双击打开，点击 **启用 / 更新监控**。程序会安装到 `%LOCALAPPDATA%\CodexQuotaWatcher`，复用主备计划任务并创建桌面快捷方式。在软件中选择任务，再点“打开需求输入框”即可填写文字、加入截图。关闭主界面不会停止后台计划任务；暂停使用“暂停监控”。

## 环境要求

- Windows 10/11；电脑开机、用户保持登录、网络可用。
- 仅源码安装需要 Python 3.11+，包含 Tkinter；`python`、`pythonw` 可从终端调用。
- 仅源码安装需要 Pillow 图片库。
- 已登录的 Codex CLI，支持 `exec resume`、`app-server --stdio`、`account/rateLimits/read` 和 `thread/turns/list`。最后一项属于实验接口，Codex 更新可能影响兼容性。

## 源码 / Skill 安装

[下载可安装的技能包](https://github.com/JOEJOEHA/codex-quota-resume/raw/refs/heads/main/codex-quota-resume.zip) · [源代码](https://github.com/JOEJOEHA/codex-quota-resume)

下载本仓库 ZIP 并解压，或用 Git 克隆。在仓库目录打开 PowerShell：

```powershell
python -m pip install -r requirements.txt
& .\scripts\install_windows.ps1
```

如果系统策略禁止运行脚本，请遵循你的设备或组织策略；本项目不修改系统执行策略。

也可以把仓库链接发给 Codex：

> 请阅读这个仓库的 README 和 SKILL.md，检查 Windows 和 Codex CLI 兼容性，然后安装自动续跑并验证两个计划任务。

若需要在 Codex 中直接使用 Skill，将本仓库解压为 Codex Skills 目录下的 `codex-quota-resume` 文件夹（其中应直接包含 `SKILL.md`）。仅复制 Skill 不会启用后台监控，仍需运行安装脚本。

安装后会创建：

| 项目 | 位置或名称 |
|---|---|
| 程序与运行状态 | `%LOCALAPPDATA%\CodexQuotaWatcher` |
| 主计划任务 | `Codex Quota Resume Watcher` |
| 备用计划任务 | `Codex Quota Resume Backup` |

默认只处理监控启用后发生的额度中断，不自动重启历史遗留任务。

## 查看、暂停、恢复、卸载

```powershell
& .\scripts\manage_windows.ps1 status
& .\scripts\manage_windows.ps1 pause
& .\scripts\manage_windows.ps1 resume
& .\scripts\manage_windows.ps1 uninstall
```

暂停会禁用两层的后续调度，不中止已经执行的任务。卸载保留本机需求、图片和运行记录；确认不再需要后可自行删除上述安装目录。不要只停用主层，否则备用层仍会工作。

## 后续任务与截图

额度中断时可填写后续任务。手动打开：

```powershell
& "$env:LOCALAPPDATA\CodexQuotaWatcher\CodexQuotaResume.exe" --plan <任务UUID>
```

`Ctrl+V` 粘贴截图，`Ctrl+Enter` 保存。截图按钮打开 Windows 截图工具，截图后回到输入框粘贴。每个计划最多六张图片。

后续任务只有在被监控器恢复的原任务明确完成，并输出 `[QUOTA_RESUME_GOAL_COMPLETE]` 后才发送；普通回合结束、取消或等待用户不会触发它。它不是通用任务队列。

## 数据与边界

弹窗只有在窗口已显示并发回确认后才标记为已提示；启动失败会留下记录并在后续检查重试。

程序读取本机 Codex 日志、官方本地 App Server 状态及当前账户额度，使用已有 Codex 登录。它不读取或上传登录令牌，不兑换重置券，不购买额度。保存的文字、截图和状态留在本机；实际发送任务及图片时会交给 Codex 按正常服务流程处理。

不要把安装目录、日志、状态文件或截图提交到 GitHub。报告问题时只提供脱敏错误和版本信息。

关机、断网、登录失效、需要人工批准、接口变化或监控进程卡住都可能影响续跑。备用层有独立的任务发现路径，但仍共享 Windows、Python、Codex 和网络，并非完全独立的系统。无法确认是否已启动时，优先防止重复执行。

## 开发验证

```powershell
python scripts/quota_watcher.py --self-test
python scripts/test_watcher.py
python scripts/test_backup.py
python scripts/test_live_status.py
python scripts/test_popup.py
python scripts/test_app.py
```

这些测试使用临时目录和模拟响应，不会向真实任务发送消息。Windows CI 运行相同测试。测试通过不等于已完成真实额度恢复验收。

## 构建 EXE

```powershell
python -m pip install -r requirements.txt pyinstaller
& .\scripts\build_windows.ps1
```

生成 `dist/CodexQuotaResume.exe`。构建产物及运行记录不提交到源代码仓库。

## English

Windows-only beta: a local primary watcher and an independent App Server-based backup resume Codex tasks stopped by explicit quota errors when live quota becomes available. Monitoring makes no model calls; resumed work uses normal Codex quota. The EXE bundles Python and Pillow; a compatible signed-in Codex CLI is still required. No guaranteed recovery; experimental APIs may change. See the commands above for installation, lifecycle controls and offline tests.

MIT licensed. This is an independent community project, not an official OpenAI product.

文件附件：在需求弹窗点击“+ 添加 → 添加文件”。文件复制保存到本机，续跑时将本地路径随需求提供给 Codex。双击文件名或选中后按 Delete 移除附件。

主界面直接在当前进程打开需求弹窗，同一任务重复点击会唤回已有草稿。关闭主窗口会保留仍在编辑的弹窗；后台监控在主程序关闭时仍可用同一个 EXE 单独显示弹窗。

需求弹窗打开或唤回时优先贴靠主窗口右侧，空间不足则放左侧，顶部对齐，间距 6 像素。根据当前显示器工作区定位，避免遮住主窗口。
