# Windows 最终打包 Runbook

本文档是 `capcut-mate` 当前 Windows 版的最终发包流程。目标产物只有两个：

- `desktop-client/dist/capcut-mate-windows-x64-green.zip`
- `desktop-client/dist/capcut-mate-windows-x64-installer.exe`

这份流程按“素材包 -> 后端 -> 前端 -> 桌面包 -> 验收”执行。只要其中任一环节变更，就重新从对应步骤开始，不要跳步。

## 1. 环境前提

建议在 Windows 10/11 x64 上执行，工具链如下：

- Node.js 20+
- Python 3.11+
- `uv`
- Git

进入仓库根目录：

```powershell
cd F:\workCode\capcut-mate
```

发包前先确认关键资源存在：

```powershell
Test-Path .\template
Test-Path .\config
Test-Path .\assets
Test-Path .\smart-assets\manifest.json
Test-Path .\tools\ffmpeg.exe
Test-Path .\tools\ffprobe.exe
Test-Path .\src\pyJianYingDraft\assets\draft_content_template.json
```

## 2. 素材包导出

只要 `文字模板2`、`音效库2`、剪映缓存或素材版本有变化，就先重导 `smart-assets/`。

常用命令：

```powershell
python .\scripts\export-smart-assets.py `
  --projects-dir "C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft" `
  --cache-dir "C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Cache" `
  --text-template-draft "文字模板2" `
  --sound-draft "音效库2" `
  --output smart-assets `
  --version 2026.06.17
```

导出后必须检查：

```powershell
Test-Path .\smart-assets\manifest.json
Test-Path .\smart-assets\text_templates\文字模板2\key_value.json
Test-Path .\smart-assets\sound_effects\音效库2\key_value.json
Test-Path .\smart-assets\music\downLoadcfg
```

`manifest.json` 里应能看到模板、音效、缺失项统计，缺项不能带包。

## 3. 后端打包

后端由 `main.py` 打成目录包。建议用 `uv` 执行 PyInstaller：

```powershell
uv sync
uv pip install pyinstaller
uv run pyinstaller -y `
  --name capcut-mate-backend `
  --onedir `
  --add-data "template;template" `
  --add-data "config;config" `
  --add-data "assets;assets" `
  --add-data "tools;tools" `
  --add-data "src/pyJianYingDraft/assets;src/pyJianYingDraft/assets" `
  main.py
```

输出目录是：

```text
dist\capcut-mate-backend\
```

打完必须检查：

```powershell
Test-Path .\dist\capcut-mate-backend\capcut-mate-backend.exe
Test-Path .\dist\capcut-mate-backend\_internal\tools\ffmpeg.exe
Test-Path .\dist\capcut-mate-backend\_internal\tools\ffprobe.exe
Test-Path .\dist\capcut-mate-backend\_internal\src\pyJianYingDraft\assets\draft_content_template.json
```

这四项都要是 `True`。

## 4. 后端 Smoke

当前 Electron 主进程会在打包后自动启动后端，端口从 `30000-30020` 里挑一个可用的，并把日志写到：

```text
%APPDATA%\CapCut-Mate\logs\backend.log
```

如果只验证后端 exe，可用独立数据目录启动：

```powershell
$env:CAPCUT_MATE_HOST='127.0.0.1'
$env:CAPCUT_MATE_PORT='30019'
$env:CAPCUT_MATE_DATA_DIR='F:\workCode\capcut-mate\temp\backend-smoke'
$env:SMART_PACKAGING_ASSETS_DIR='F:\workCode\capcut-mate\smart-assets'
Start-Process -FilePath 'F:\workCode\capcut-mate\dist\capcut-mate-backend\capcut-mate-backend.exe' `
  -WorkingDirectory 'F:\workCode\capcut-mate' `
  -WindowStyle Hidden `
  -PassThru
```

验证时至少跑通这类请求：

- `POST /openapi/capcut-mate/v1/create_draft`
- `POST /openapi/capcut-mate/v1/add_audios`

如果 `add_audios` 失败，先看 `backend.log`，再看是否缺 `ffprobe.exe`、`draft_content_template.json` 或 `smart-assets`。

## 5. 前端构建

进入前端目录：

```powershell
cd F:\workCode\capcut-mate\desktop-client
npm run web:build
```

构建产物会落到：

```text
desktop-client\ui\
```

如果只改了前端，这一步后直接重新打桌面包即可。改过后端或素材包，必须回到第 2、3 步。

## 6. 桌面包打包

`desktop-client/scripts/electron-builder.config.js` 和 `desktop-client/scripts/electron-builder-green.config.js` 都已经把下面两项作为 `extraResources`：

- `../dist/capcut-mate-backend -> backend`
- `../smart-assets -> smart-assets`

最终打包命令：

```powershell
cd F:\workCode\capcut-mate\desktop-client
npm ci
npm run build-win-green
npm run build-win-installer
```

输出文件：

```text
desktop-client\dist\capcut-mate-windows-x64-green.zip
desktop-client\dist\capcut-mate-windows-x64-installer.exe
```

## 7. 最终验收

回到仓库根目录：

```powershell
cd F:\workCode\capcut-mate
```

先确认产物存在：

```powershell
Test-Path .\desktop-client\dist\capcut-mate-windows-x64-green.zip
Test-Path .\desktop-client\dist\capcut-mate-windows-x64-installer.exe
```

再确认安装包内资源齐全：

```powershell
Test-Path .\desktop-client\dist\win-unpacked\resources\backend\capcut-mate-backend.exe
Test-Path .\desktop-client\dist\win-unpacked\resources\backend\_internal\tools\ffmpeg.exe
Test-Path .\desktop-client\dist\win-unpacked\resources\backend\_internal\tools\ffprobe.exe
Test-Path .\desktop-client\dist\win-unpacked\resources\backend\_internal\src\pyJianYingDraft\assets\draft_content_template.json
Test-Path .\desktop-client\dist\win-unpacked\resources\smart-assets\manifest.json
```

最后用真实剪映草稿做一次打开验证，确保：

- 后端自动启动
- 本地视频可导入
- 字幕、花字、音效能正常写入
- 生成的草稿能被剪映专业版正常打开

## 8. 当前版本的关键约定

当前代码已经固定了这些行为：

- Electron 打包后自动启动本地后端
- 后端端口自动避让 `30000-30020`
- 运行时配置通过主进程传给前端
- 后端日志写入用户目录
- `smart-assets` 随桌面包一起发布
- 音频文件允许带封面 video stream，只要确实包含 audio stream

## 9. 清理

打包完成后，可清理临时目录：

```powershell
$root = (Resolve-Path -LiteralPath 'F:\workCode\capcut-mate').Path
$targets = @(
  'F:\workCode\capcut-mate\build',
  'F:\workCode\capcut-mate\capcut-mate-backend.spec',
  'F:\workCode\capcut-mate\src\pyJianYingDraft\__pycache__'
)
foreach ($item in $targets) {
  if (Test-Path -LiteralPath $item) {
    $resolved = (Resolve-Path -LiteralPath $item).Path
    if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
      Remove-Item -LiteralPath $resolved -Recurse -Force
    } else {
      throw "Refusing to delete outside workspace: $resolved"
    }
  }
}
```

## 10. 一句话版顺序

```text
导出 smart-assets -> 打后端 -> smoke 后端 -> build web -> 打绿色包 -> 打安装包 -> 检查产物 -> 真实草稿验证
```
