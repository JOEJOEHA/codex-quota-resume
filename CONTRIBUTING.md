# Contributing / 贡献指南

[简体中文 README](README.md) · [English README](README.en.md) · [macOS Codex Prompt](docs/macos-handoff.md)

## 中文

欢迎以自己的 GitHub 账号参与。无需共享维护者账号，也无需先取得仓库写权限：Fork 本项目，在自己的分支提交，再向上游发 Pull Request（PR）。**Contributor（贡献者）与 Collaborator（有仓库权限的协作者）不同**；前者不需要邀请，后者需维护者单独授权。

macOS 目前在 `macos-port`，PR #1 尚未合并。Fork 即使只复制了 `main`，也可以从上游获取 `macos-port`。在尚无本地克隆时执行以下示例，先把 `YOUR_GITHUB_USERNAME` 替换为自己的账号；已有克隆应先检查 remote、分支及未提交修改，不重复克隆或覆盖：

```sh
git clone https://github.com/YOUR_GITHUB_USERNAME/codex-quota-resume.git
cd codex-quota-resume
git remote add upstream https://github.com/JOEJOEHA/codex-quota-resume.git
git fetch upstream
git switch -c macos/continue-development upstream/macos-port
```

提交前检查 `git config user.name`、`git config user.email`，使用自己的真实作者身份，以及自己 GitHub 已关联的邮箱或 GitHub 提供的 noreply 邮箱；不要沿用 JOEJOEHA 身份。完成后 push 到自己的 `origin`，向 `JOEJOEHA/codex-quota-resume` 的 `macos-port` 提 PR。若移植已合并，则以最新 `main` 为起点并向 `main` 提 PR。未验收工作使用 Draft PR，保留未完成清单。

贡献记录来自实际提交，不是人为给账号添加“Contributor”标签。提交被合并到默认分支、作者邮箱关联到账号后，GitHub 才能按其规则显示贡献，可能存在刷新延迟；仅进入 `macos-port` 不等于已进入默认分支。参见 [GitHub 贡献记录规则](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference)。维护者合并时应保留实际作者归属。

## English

Use your own GitHub account: fork the project, work on a feature branch, push to your fork and open an upstream pull request. Contributor credit does not require collaborator/write access. Never share the maintainer's credentials.

The macOS port currently lives on `macos-port` in draft PR #1. The commands above fetch it from upstream even if your fork only copied `main`; replace `YOUR_GITHUB_USERNAME` first. With an existing checkout, inspect remotes, branches and uncommitted changes before changing anything. If the port has since merged, start from current upstream `main` instead.

Use your own Git author name and a verified/associated GitHub email or your GitHub noreply address. Push to your fork and target upstream `macos-port` until the port merges; target `main` afterward. Keep incomplete work as a draft PR. Commit credit depends on GitHub's rules, including associated author email and inclusion in the default branch; it is not an access role that the owner manually assigns. See [GitHub's contribution reference](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference). Preserve the actual author when merging.

## Names and explanations / 命名与说明

- Keep code identifiers, filenames, branches and asset names in stable English/ASCII: `macos/fix-menu-bar`, `CodexQuotaResume-macOS-arm64-preview.zip`. 保持程序标识符与下载文件名稳定，避免因翻译破坏链接。
- Use bilingual commit/PR/release titles, e.g. `fix(macos): Restore menu-bar window / 修复菜单栏窗口恢复`。提交、PR、发布标题使用英文与中文。
- PR and release bodies must include Chinese and English explanations of the change, validation and remaining limits. PR 与发布正文分别说明改动、验证和未完成项；不只翻译标题。
- Keep Chinese and English README behavior/status in sync. Documentation translation does not imply the application UI has been localized. 中英文文档同步更新；文档双语不代表软件界面已实现多语言。
- Keep changes small; reuse Python/Tkinter/Pillow and native OS facilities. Preserve Windows behavior, existing monitoring, saved tasks, attachments and drafts. 不做无关重构，不强杀含草稿的窗口。
- Run checks relevant to the change and record real device/OS/architecture, command results and unresolved items. Never equate simulated CI tests with a real quota recovery cycle. 根据改动运行测试并记录证据，不伪造实机验收。
- Do not commit tokens, personal Codex logs, saved task contents, screenshots containing private data or generated bundles. 不提交密钥、个人日志、任务附件和构建目录。
