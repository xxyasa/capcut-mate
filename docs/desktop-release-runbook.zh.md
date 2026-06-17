# CapCut Mate 桌面版打包发布流程

本文档是内部发包操作手册，覆盖从更新代码、准备素材、GitHub Actions 打包、发布 Release、下载安装验证，到 Windows 本地打包的完整流程。

适用场景：

- 需要发布 Windows 安装包和绿色包。
- 需要发布 macOS arm64 安装包和绿色包。
- 公司内部使用，不做 Windows/macOS 代码签名。
- `smart-assets/` 直接提交到仓库，随包一起发布。

## 1. 产物说明

GitHub Actions 成功后会生成一个 prerelease，包含：

```text
capcut-mate-windows-x64-installer.exe
capcut-mate-windows-x64-green.zip
capcut-mate-macos-arm64-installer.dmg
capcut-mate-macos-arm64-green.zip
```

推荐使用：

- Windows 用户优先下载 `capcut-mate-windows-x64-installer.exe`。
- Windows 如果被安装权限或杀软拦截，再下载 `capcut-mate-windows-x64-green.zip`。
- Apple Silicon Mac 用户下载 `capcut-mate-macos-arm64-installer.dmg`。
- macOS 绿色包仅用于快速验证。

## 2. 发包前检查

### 2.1 确认当前代码已提交

GitHub Actions 只会使用已经 push 到 GitHub 的代码。本地未提交文件不会进入打包产物。

查看本地状态：

```bash
git status --short
```

如果看到业务代码改动，例如：

```text
M src/service/smart_packaging.py
M src/service/asr_captions.py
M src/service/llm_caption_polish.py
M src/schemas/smart_packaging.py
```

并且这些改动需要进入新包，就必须提交：

```bash
git add src/schemas/smart_packaging.py \
  src/service/asr_captions.py \
  src/service/llm_caption_polish.py \
  src/service/smart_packaging.py \
  tests/test_asr_captions.py \
  tests/test_smart_packaging.py

git commit -m "Update smart packaging behavior"
```

不要提交：

```text
.DS_Store
desktop-client/dist/
dist/
output/
temp/
logs/
```

### 2.2 确认素材包存在

仓库中必须存在：

```text
smart-assets/manifest.json
smart-assets/text_templates/文字模板2/key_value.json
smart-assets/sound_effects/音效库2/key_value.json
smart-assets/music/downLoadcfg
```

快速检查：

```bash
test -f smart-assets/manifest.json
test -f "smart-assets/text_templates/文字模板2/key_value.json"
test -f "smart-assets/sound_effects/音效库2/key_value.json"
test -f smart-assets/music/downLoadcfg
```

如果素材变了，需要重新导出。

## 3. 更新 smart-assets

### 3.1 macOS 导出素材

在已经下载好剪映模板和音效的 Mac 上执行：

```bash
python3 scripts/export-smart-assets.py \
  --projects-dir "$HOME/Movies/JianyingPro/User Data/Projects/com.lveditor.draft" \
  --cache-dir "$HOME/Movies/JianyingPro/User Data/Cache" \
  --text-template-draft "文字模板2" \
  --sound-draft "音效库2" \
  --output smart-assets
```

成功示例：

```text
smart-assets: /path/to/capcut-mate/smart-assets
text templates: 11, missing artistEffect: 0
sound effects: 9, missing audio: 0
```

如果 `missing artistEffect` 或 `missing audio` 大于 0，需要先在剪映里重新打开/下载对应模板或音效，再重新导出。

### 3.2 Windows 导出素材

在 Windows PowerShell 中执行：

```powershell
python scripts/export-smart-assets.py `
  --projects-dir "$env:LOCALAPPDATA\JianyingPro\User Data\Projects\com.lveditor.draft" `
  --cache-dir "$env:LOCALAPPDATA\JianyingPro\User Data\Cache" `
  --text-template-draft "文字模板2" `
  --sound-draft "音效库2" `
  --output smart-assets
```

### 3.3 提交素材

```bash
git add smart-assets scripts/export-smart-assets.py
git commit -m "Update smart packaging assets"
```

## 4. 推送到 GitHub

推送前确认提交图：

```bash
git log --oneline --decorate -5
```

推送：

```bash
git push https://github.com/xxyasa/capcut-mate.git main
```

如果提示 `non-fast-forward`，说明远端有本地没有的提交。先执行：

```bash
git fetch https://github.com/xxyasa/capcut-mate.git main:refs/remotes/origin/main
```

再根据情况 rebase 或合并。不要直接裸 `git push --force`。

## 5. GitHub Actions 打包并发布 Release

打开仓库：

```text
https://github.com/xxyasa/capcut-mate
```

进入：

```text
Actions -> Build Desktop Release -> Run workflow
```

建议填写版本号：

```text
v0.0.100-internal.1
```

如果不填，workflow 会自动使用：

```text
internal-<run_number>
```

Actions 会执行：

1. Windows runner 构建 Python 后端 exe。
2. Windows runner 构建前端。
3. Windows runner 打安装包和绿色包。
4. macOS runner 构建 Python 后端。
5. macOS runner 构建前端。
6. macOS runner 打 dmg 和绿色包。
7. 汇总所有产物。
8. 创建或更新 GitHub prerelease。

## 6. 下载产物

推荐从 Release 下载，不从 Actions Artifact 下载。

路径：

```text
GitHub -> Releases -> 最新 prerelease -> Assets
```

只看 Windows 效果时，先下载：

```text
capcut-mate-windows-x64-installer.exe
```

不要一开始下载绿色包。绿色包通常更大，GitHub 下载也可能更慢。

如果浏览器下载慢，使用断点续传：

```bash
curl -L -C - -o capcut-mate-windows-x64-installer.exe "<Release asset 下载链接>"
```

下载中断后重复执行同一条命令即可续传。

如果 GitHub 下载持续很慢，建议把 Release 里的文件同步到公司网盘、阿里云 OSS、腾讯 COS 或其他国内制品库。

## 7. Windows 验证流程

### 7.1 安装包验证

在 Windows 10/11 x64 上运行：

```text
capcut-mate-windows-x64-installer.exe
```

安装完成后打开桌面快捷方式。

### 7.2 绿色包验证

解压：

```text
capcut-mate-windows-x64-green.zip
```

运行：

```text
剪映小助手.exe
```

### 7.3 必测项

启动后检查：

- 应用能打开，不白屏。
- 进入“批量智能包装”页面。
- 后端服务地址是 `http://127.0.0.1:<port>/openapi/capcut-mate/v1`。
- 刷新模板库能读到 `文字模板2` 中的模板。
- 刷新音效库能读到 `音效库2` 中的音效。
- 选择本地视频。
- 配置 ASR/LLM Key。
- 点击生成包装草稿。
- 生成的草稿能保存到剪映草稿目录。
- 剪映专业版能打开草稿，文字模板和音效正常。

### 7.4 日志位置

如果启动失败或生成失败，收集日志：

```text
%APPDATA%\剪映小助手\logs\
%APPDATA%\CapCut-Mate\logs\
```

重点看：

```text
backend.log
app.log
```

## 8. macOS 验证流程

下载：

```text
capcut-mate-macos-arm64-installer.dmg
```

打开 dmg 并拖入 Applications。

首次打开未签名内部包时，macOS 可能提示无法验证开发者。内部验证可在系统设置中允许打开，或在终端执行：

```bash
xattr -dr com.apple.quarantine "/Applications/剪映小助手.app"
```

macOS 包当前主要用于内部验证桌面端功能。剪映草稿路径、素材缓存路径、剪映打开行为仍需以业务实际机器验证为准。

## 9. Windows 本地打包流程

如果 GitHub 下载很慢，或需要快速反复试包，推荐使用一台 Windows 10/11 x64 机器本地打包。

### 9.1 安装工具

安装：

```text
Git
Node.js 20
Python 3.11
uv
剪映专业版
```

### 9.2 拉代码

```powershell
git clone https://github.com/xxyasa/capcut-mate.git
cd capcut-mate
```

### 9.3 安装 Python 依赖

```powershell
uv sync
uv pip install pyinstaller
```

### 9.4 导出或确认素材

如果仓库里已经有 `smart-assets/`，可以直接使用。

如果要使用当前 Windows 机器上的素材，执行：

```powershell
python scripts/export-smart-assets.py `
  --projects-dir "$env:LOCALAPPDATA\JianyingPro\User Data\Projects\com.lveditor.draft" `
  --cache-dir "$env:LOCALAPPDATA\JianyingPro\User Data\Cache" `
  --text-template-draft "文字模板2" `
  --sound-draft "音效库2" `
  --output smart-assets
```

### 9.5 构建后端

```powershell
uv run pyinstaller `
  --name capcut-mate-backend `
  --onedir `
  --add-data "template;template" `
  --add-data "config;config" `
  --add-data "assets;assets" `
  main.py
```

输出：

```text
dist/capcut-mate-backend/capcut-mate-backend.exe
```

### 9.6 构建前端和桌面包

```powershell
cd desktop-client
npm ci
npm --prefix web ci
npm run web:build
npm run build-win-installer
npm run build-win-green
```

输出：

```text
desktop-client/dist/capcut-mate-windows-x64-installer.exe
desktop-client/dist/capcut-mate-windows-x64-green.zip
```

## 10. 常见问题

### 10.1 Actions 成功但下载很慢

优先从 Release 下载，不从 Actions Artifact 下载。

只下载安装包，不先下载绿色包：

```text
capcut-mate-windows-x64-installer.exe
```

仍然很慢时，用断点续传：

```bash
curl -L -C - -o capcut-mate-windows-x64-installer.exe "<Release asset 下载链接>"
```

### 10.2 Actions 找不到 smart-assets

确认 `smart-assets/` 已提交并 push。

检查：

```bash
git ls-files smart-assets/manifest.json
```

如果没有输出，需要：

```bash
git add smart-assets
git commit -m "Add smart packaging assets"
git push https://github.com/xxyasa/capcut-mate.git main
```

### 10.3 Windows 启动后没有模板或音效

检查安装目录里是否存在：

```text
resources/smart-assets/manifest.json
resources/smart-assets/text_templates/文字模板2/key_value.json
resources/smart-assets/sound_effects/音效库2/key_value.json
resources/smart-assets/music/downLoadcfg
```

如果不存在，说明 `electron-builder` 没有打入 `smart-assets`，检查：

```text
desktop-client/scripts/electron-builder.config.js
desktop-client/scripts/electron-builder-green.config.js
```

### 10.4 后端没有启动

检查日志：

```text
%APPDATA%\剪映小助手\logs\backend.log
```

常见原因：

- 后端 exe 没被打进 `resources/backend/`。
- 端口 `30000-30020` 都被占用。
- PyInstaller 缺少依赖。
- 杀软拦截后端 exe。

### 10.5 杀软或系统提示未知发布者

当前是内部包，不做代码签名。处理方式：

- 使用公司内部可信渠道分发。
- 联系 IT 加白。
- 优先给业务同学安装包，不直接散发绿色包目录。

## 11. 推荐发布节奏

每次发包建议记录：

- Git commit。
- Release tag。
- 素材版本。
- 业务变更说明。
- 已知问题。
- 验证人和验证机器。

示例：

```text
Release: v0.0.100-internal.1
Commit: <commit sha>
Assets: smart-assets 2026.06.17
验证：Windows 11 x64 + 剪映专业版
```
