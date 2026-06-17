# Windows 智能包装桌面版内部打包方案

本文档描述如何把“批量智能包装”能力打包成 Windows 业务可用的桌面应用。目标是业务同学安装一个 Windows 应用后，即可选择本地视频或 OSS 视频，自动 ASR/LLM 生成字幕，添加文字模板花字、音效、贴纸，并输出可在剪映专业版中打开的工程草稿。

适用范围：

- 仅公司内部业务同学使用。
- 第一版以内测/灰度分发为目标，不上架应用商店。
- 不做 Windows 代码签名；如遇 Windows Defender、SmartScreen 或企业杀软提示，由内部 IT 白名单、企业网盘说明或绿色包方式处理。
- 不把生产 ASR/LLM Key 写入安装包。

## 1. 推荐结论

第一版建议采用“Electron 桌面端 + 本地后端 + 内置素材包”的单机方案，不建议把草稿生成后端单独部署到服务器。

内部版推荐先交付两个产物：

- 安装包：`capcut-mate-windows-x64-installer.exe`
- 绿色包：`capcut-mate-windows-x64-green.zip`

安装包适合普通业务同学使用；绿色包适合被杀软拦截、没有安装权限、或需要快速替换内测版本的场景。

推荐形态：

```text
CapCut-Mate-Setup.exe
  安装后：
  CapCut-Mate/
    CapCut-Mate.exe
    resources/
      app.asar 或 app/
      backend/
        capcut-mate-backend.exe
        template/
        config/
      smart-assets/
        text_templates/
          文字模板2/
        artistEffect/
          7583185273840897342/
          ...
        sound_effects/
          音效库2/
        music/
          *.mp3
          downLoadcfg
        manifest.json
```

原因：

- 本地视频不需要上传服务器，速度和隐私都更好。
- 生成剪映草稿是本机文件操作，天然适合放在桌面端。
- 文字模板和音效依赖剪映缓存资源，内置素材包比要求业务电脑提前下载素材更稳定。
- 云端只适合做账号、配置、ASR/LLM 代理、素材版本更新，不适合第一版承担草稿生成。

## 2. 当前项目现状

当前已有能力：

- Electron 桌面端在 `desktop-client/`。
- Web 前端通过 `npm run web:build` 构建到 `desktop-client/ui/`。
- Windows 安装包脚本已存在：
  - `npm run build-win-installer`
  - `npm run build-win-green`
- 后端是 Python/FastAPI，入口是 `main.py`。
- 智能包装当前使用：
  - 文字模板草稿：`文字模板2`
  - 音效草稿：`音效库2`
  - 文字模板缓存：剪映 `Cache/artistEffect`
  - 音效缓存：剪映 `Cache/music`

当前缺口：

- Electron 主进程还没有自动拉起本地 Python 后端。
- 后端还没有打成 Windows 可执行文件。
- `electron-builder` 配置还没有把后端和素材包作为 `extraResources` 打进去。
- 后端默认路径目前仍主要面向开发机，需要改成支持环境变量或启动参数。

## 3. 目标运行流程

业务用户视角：

1. 安装 `CapCut-Mate-Setup.exe`。
2. 打开桌面应用。
3. 应用自动启动本地后端，例如 `127.0.0.1:30000`。
4. 业务选择本地视频或填写 OSS 视频 URL。
5. 点击生成，后端调用 ASR/LLM，并使用内置的 `文字模板2` 和 `音效库2`。
6. 生成剪映草稿。
7. 点击保存或打开，草稿落到业务电脑的剪映草稿目录。

## 4. Windows 目录约定

Windows 剪映草稿目录通常是：

```text
C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft
```

项目里已有探测逻辑：

```text
desktop-client/nodeapi/draftPathDetect.js
```

打包版应继续使用自动探测。如果探测失败，界面要允许用户手动选择剪映草稿目录。

## 5. 后端打包方案

建议使用 PyInstaller 把后端打成单文件或目录模式。

推荐先用目录模式，稳定性更好。最小命令如下：

```powershell
uv pip install pyinstaller
pyinstaller ^
  --name capcut-mate-backend ^
  --onedir ^
  --add-data "template;template" ^
  --add-data "config;config" ^
  --add-data "assets;assets" ^
  main.py
```

输出目录：

```text
dist/
  capcut-mate-backend/
    capcut-mate-backend.exe
    _internal/
```

如果确认依赖都稳定，再考虑 `--onefile`。第一版不建议直接 `--onefile`，因为视频、模板、字体、动态库和 mediainfo 相关依赖排查成本更高。

### 5.1 推荐维护 PyInstaller spec

上面的命令适合第一次验证。正式内部打包建议提交一个固定的 spec 文件，例如：

```text
scripts/pyinstaller/capcut-mate-backend.spec
```

原因：

- FastAPI/uvicorn、媒体处理库、剪映草稿库可能存在动态导入，spec 更容易补 `hiddenimports`。
- 后续如果要带 ffmpeg、mediainfo、字体、默认配置，spec 更容易维护。
- 构建机每次打包命令固定为 `pyinstaller scripts/pyinstaller/capcut-mate-backend.spec`，减少人为差异。

建议 spec 至少覆盖：

- `main.py`
- `src/`
- `config.py`
- `template/`
- `config/`
- `assets/`
- 运行时需要的动态库或二进制工具

### 5.2 后端启动参数

打包后的后端 exe 不应该固定监听 `30000`。建议 `main.py` 支持环境变量：

```python
host = os.getenv("CAPCUT_MATE_HOST", "127.0.0.1")
port = int(os.getenv("CAPCUT_MATE_PORT", "30000"))
uvicorn.run(app, host=host, port=port, log_config=None, log_level="info")
```

这样 Electron 可以在 `30000` 被占用时切换到 `30001`、`30002` 等备用端口。

## 6. 后端路径配置化

后端不能依赖开发机路径，例如：

```text
/Users/xinyu/Movies/JianyingPro/User Data/...
```

Windows 打包版启动后端时应注入以下环境变量：

```text
SMART_PACKAGING_ASSETS_DIR=<resources>\smart-assets
JIANYING_TEXT_TEMPLATE_DRAFT_DIR=<resources>\smart-assets\text_templates\文字模板2
JIANYING_ARTIST_EFFECT_CACHE_DIR=<resources>\smart-assets\artistEffect
JIANYING_SOUND_DRAFT_DIR=<resources>\smart-assets\sound_effects\音效库2
JIANYING_MUSIC_CACHE_DIR=<resources>\smart-assets\music
DRAFT_URL=http://127.0.0.1:30000/openapi/capcut-mate/v1/get_draft
DOWNLOAD_URL=http://127.0.0.1:30000/
CAPCUT_MATE_HOST=127.0.0.1
CAPCUT_MATE_PORT=30000
```

后端代码需要优先读取这些环境变量，没有环境变量时再回退到开发机默认路径。

建议修改点：

```text
src/service/smart_packaging.py
```

涉及默认值：

- `DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR`
- `DEFAULT_JIANYING_ARTIST_EFFECT_CACHE_DIR`
- `DEFAULT_JIANYING_SOUND_DRAFT_DIR`
- `DEFAULT_JIANYING_MUSIC_CACHE_DIR`

推荐实现方式：

```python
DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR = os.getenv(
    "JIANYING_TEXT_TEMPLATE_DRAFT_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/文字模板2"),
)
DEFAULT_JIANYING_ARTIST_EFFECT_CACHE_DIR = os.getenv(
    "JIANYING_ARTIST_EFFECT_CACHE_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Cache/artistEffect"),
)
DEFAULT_JIANYING_SOUND_DRAFT_DIR = os.getenv(
    "JIANYING_SOUND_DRAFT_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/音效库2"),
)
DEFAULT_JIANYING_MUSIC_CACHE_DIR = os.getenv(
    "JIANYING_MUSIC_CACHE_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Cache/music"),
)
```

注意：Electron 里传入的路径必须是绝对路径，不能依赖当前工作目录。

## 7. 素材包导出方案

需要把当前可用的模板和音效做成固定素材包，随安装包发布。

不要手工复制素材作为长期流程。第一版可以手工验证一次，但正式内测包建议提供导出脚本，例如：

```text
scripts/export-smart-assets.py
```

建议参数：

```powershell
python scripts/export-smart-assets.py ^
  --projects-dir "C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft" ^
  --cache-dir "C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Cache" ^
  --text-template-draft "文字模板2" ^
  --sound-draft "音效库2" ^
  --output smart-assets
```

脚本职责：

- 清理并重建 `smart-assets/`。
- 复制 `文字模板2` 到 `smart-assets/text_templates/文字模板2/`。
- 从 `文字模板2/key_value.json` 解析所有 `materialId`。
- 复制对应 `Cache/artistEffect/<materialId>/`。
- 复制 `音效库2` 到 `smart-assets/sound_effects/音效库2/`。
- 从 `音效库2/key_value.json` 解析音效 `materialId`。
- 根据当前代码使用的 `materialId -> md5(materialId) -> downLoadcfg.hex -> mp3` 规则复制实际音频文件。
- 复制 `Cache/music/downLoadcfg`。
- 生成 `manifest.json`。
- 输出自检结果：模板数量、音效数量、缺失 artistEffect 数量、缺失 mp3 数量。

### 7.1 文字模板

源目录：

```text
剪映草稿目录\文字模板2
```

需要打入：

```text
smart-assets/text_templates/文字模板2/
  key_value.json
  common_attachment/
  ...
```

还需要根据 `key_value.json` 中的 `materialId`，把对应缓存包复制出来：

```text
剪映缓存目录\Cache\artistEffect\<materialId>\
```

放到：

```text
smart-assets/artistEffect/<materialId>/
```

当前 `文字模板2` 至少包括这些模板：

- 好用单品
- 电商-热销爆款
- 好物体验官
- 穿搭-宝藏单品
- 带货-超级福利日
- 双11带货 引导 推荐购买
- 热搜第一
- 美食-吃喝最重要
- 惊喜福利
- 重点来啦

### 7.2 音效

源目录：

```text
剪映草稿目录\音效库2
```

需要打入：

```text
smart-assets/sound_effects/音效库2/
  key_value.json
  common_attachment/
  ...
```

还需要复制音频缓存：

```text
剪映缓存目录\Cache\music\
```

只复制当前 `音效库2` 中用到的 mp3 即可，放到：

```text
smart-assets/music/
```

注意：当前代码通过 `materialId -> md5(materialId) -> downLoadcfg.hex -> mp3` 建立映射，所以 `music/downLoadcfg` 也要一起打入。

### 7.3 manifest.json

建议生成一个素材清单：

```json
{
  "version": "2026.06.17",
  "text_template_draft": "文字模板2",
  "sound_draft": "音效库2",
  "text_templates": [
    {
      "name": "好用单品",
      "material_id": "7583185273840897342"
    }
  ],
  "sound_effects": [
    {
      "name": "滴，提示音",
      "material_id": "6896679333541285133"
    }
  ]
}
```

启动时可以读取 `manifest.json` 做自检。

### 7.4 素材自检规则

启动后端时建议检查：

- `smart-assets/manifest.json` 存在。
- `text_templates/文字模板2/key_value.json` 存在。
- `sound_effects/音效库2/key_value.json` 存在。
- `artistEffect/` 下至少存在一个素材包。
- `music/downLoadcfg` 存在。
- `music/` 下至少存在一个可用音频文件。

建议增加接口：

```text
GET /openapi/capcut-mate/v1/smart-packaging/assets/check
```

返回示例：

```json
{
  "ok": true,
  "version": "2026.06.17",
  "text_template_count": 10,
  "sound_effect_count": 9,
  "missing_artist_effects": [],
  "missing_audio_files": []
}
```

如果 `ok=false`，前端应显示“素材包不完整，请联系技术同学重新发包”，不要让业务继续生成。

## 8. Electron 打包配置

建议使用 `electron-builder`，安装包使用 NSIS，绿色包使用 zip。

需要在 `desktop-client/scripts/electron-builder.config.js` 和 `desktop-client/scripts/electron-builder-green.config.js` 中都增加 `extraResources`：

```js
extraResources: [
  {
    from: "../dist/capcut-mate-backend",
    to: "backend"
  },
  {
    from: "../smart-assets",
    to: "smart-assets"
  }
]
```

注意路径是相对于 `desktop-client/` 目录执行 `electron-builder` 时的路径。如果后端输出目录调整，需要同步修改。

Windows 目标：

```js
win: {
  icon: "assets/icons/logo.ico",
  target: "nsis",
  artifactName: "capcut-mate-windows-x64-installer.exe"
}
```

NSIS 建议：

```js
nsis: {
  oneClick: false,
  allowToChangeInstallationDirectory: true,
  perMachine: false,
  createDesktopShortcut: true,
  createStartMenuShortcut: true
}
```

内部版不做代码签名，因此不配置证书。保留当前 `signingHashAlgorithms: []` 即可；如果 electron-builder 或 Windows 环境仍尝试签名，可显式确认没有设置 `CSC_LINK`、`CSC_KEY_PASSWORD` 等签名环境变量。

## 9. Electron 自动启动后端

需要在 `desktop-client/main.js` 增加后端进程管理。

核心逻辑：

```js
const { spawn } = require("child_process");
const path = require("path");
const { app } = require("electron");

let backendProcess = null;

function getResourcePath(...parts) {
  return app.isPackaged
    ? path.join(process.resourcesPath, ...parts)
    : path.join(__dirname, "..", ...parts);
}

function startBackend() {
  const backendExe = app.isPackaged
    ? getResourcePath("backend", "capcut-mate-backend.exe")
    : path.join(__dirname, "..", ".venv", "Scripts", "python.exe");

  const backendArgs = app.isPackaged
    ? []
    : [path.join(__dirname, "..", "main.py")];

  const assetsDir = getResourcePath("smart-assets");

  backendProcess = spawn(backendExe, backendArgs, {
    env: {
      ...process.env,
      SMART_PACKAGING_ASSETS_DIR: assetsDir,
      JIANYING_TEXT_TEMPLATE_DRAFT_DIR: path.join(assetsDir, "text_templates", "文字模板2"),
      JIANYING_ARTIST_EFFECT_CACHE_DIR: path.join(assetsDir, "artistEffect"),
      JIANYING_SOUND_DRAFT_DIR: path.join(assetsDir, "sound_effects", "音效库2"),
      JIANYING_MUSIC_CACHE_DIR: path.join(assetsDir, "music"),
      CAPCUT_MATE_HOST: "127.0.0.1",
      CAPCUT_MATE_PORT: "30000",
      DRAFT_URL: "http://127.0.0.1:30000/openapi/capcut-mate/v1/get_draft",
      DOWNLOAD_URL: "http://127.0.0.1:30000/"
    },
    windowsHide: true
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
```

建议补充：

- 启动后轮询 `http://127.0.0.1:<port>/docs` 或健康检查接口。
- 如果端口被占用，自动切换到备用端口，并把前端 `apiBase` 改成新端口。
- 后端日志写到 `app.getPath("userData")/logs/backend.log`。

### 9.1 端口选择

推荐端口策略：

```text
优先：30000
备用：30001-30020
```

Electron 启动时先检测端口是否可用，选择一个空闲端口后注入：

```text
CAPCUT_MATE_PORT=<selected_port>
DRAFT_URL=http://127.0.0.1:<selected_port>/openapi/capcut-mate/v1/get_draft
DOWNLOAD_URL=http://127.0.0.1:<selected_port>/
```

如果所有端口都不可用，弹窗提示：

```text
本地服务启动失败：端口 30000-30020 均不可用。请关闭占用端口的程序后重试，或联系技术同学。
```

### 9.2 日志

后端日志建议写入：

```text
%APPDATA%\CapCut-Mate\logs\backend.log
```

Electron 主进程日志建议写入：

```text
%APPDATA%\CapCut-Mate\logs\main.log
```

内部版排障时，业务同学只需要把 `logs/` 目录压缩发给技术同学。

### 9.3 退出清理

Electron 退出时需要杀掉后端子进程：

- `before-quit` 中调用 `backendProcess.kill()`。
- Windows 下如果后端又拉起了子进程，必要时使用 `taskkill` 兜底。
- 避免用户关闭窗口后后端残留占用端口。

## 10. 前端配置

生产包默认 API 地址：

```text
http://127.0.0.1:30000/openapi/capcut-mate/v1
```

如果实现动态端口，前端不能把端口写死。推荐方式：

- Electron 主进程选定端口后保存运行时配置。
- preload 暴露 `window.capcutMate.getRuntimeConfig()`。
- 前端启动时读取：

```json
{
  "apiBase": "http://127.0.0.1:30000/openapi/capcut-mate/v1",
  "assetsVersion": "2026.06.17"
}
```

开发模式下可以继续使用 `.env` 或默认 `http://localhost:30000/openapi/capcut-mate/v1`。

业务版建议保留可编辑入口，但默认隐藏高级配置：

- ASR 地址
- LLM 地址
- ASR/LLM Key
- 剪映草稿目录
- 文字模板目录
- 音效目录

如果业务只负责使用，不建议让他们改模板和音效路径。

当前前端还有开发机默认路径，例如：

```text
/Users/xinyu/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/文字模板2
```

打包前必须改为：

- 默认不展示模板/音效路径。
- 请求后端时如果用户没有手动配置，传空值，让后端使用环境变量里的内置素材包路径。
- 如果要展示调试信息，只在“高级设置”或“诊断信息”中展示。

## 11. ASR/LLM Key 处理

不要把生产 key 写死进安装包。

推荐两种方式：

1. 公司后端代理 ASR/LLM  
   桌面端只请求公司服务，不暴露模型 key。

2. 首次启动配置 key  
   key 写入本机用户配置目录：

```text
%APPDATA%\CapCut-Mate\config.json
```

第一版内测可以用第二种，正式给业务建议用第一种。

内部版建议：

- 不把 key 写进源码、前端构建产物、PyInstaller 包或 `smart-assets`。
- 内测阶段可由用户首次启动时配置。
- 配置文件只放在用户目录，例如 `%APPDATA%\CapCut-Mate\config.json`。
- 日志里不要打印完整 key，只保留前后 3-4 位用于排查。

## 12. 构建流水线建议

Windows 构建机要求：

- Windows 10/11 x64
- Node.js 18+ 或 20+
- Python 3.11+
- uv
- Git
- 剪映专业版，至少用于验证草稿打开

构建步骤：

```powershell
# 1. 安装 Python 依赖
uv sync
uv pip install pyinstaller

# 2. 构建后端
pyinstaller --name capcut-mate-backend --onedir --add-data "template;template" --add-data "config;config" --add-data "assets;assets" main.py
# 或使用固定 spec：
# pyinstaller scripts/pyinstaller/capcut-mate-backend.spec

# 3. 准备素材包
python scripts/export-smart-assets.py --projects-dir "<剪映草稿目录>" --cache-dir "<剪映缓存目录>" --output smart-assets

# 4. 构建前端
cd desktop-client
npm ci
npm run web:build

# 5. 打安装包
npm run build-win-installer

# 6. 可选：打绿色包
npm run build-win-green
```

产物：

```text
desktop-client/dist/capcut-mate-windows-x64-installer.exe
desktop-client/dist/capcut-mate-windows-x64-green.zip
```

### 12.1 内部分发建议

建议每次内测包同时附带：

- 安装包或绿色包。
- 版本号，例如 `0.0.100-internal.1`。
- 素材包版本，例如 `smart-assets 2026.06.17`。
- 更新说明。
- 已知问题。
- 日志收集说明：`%APPDATA%\CapCut-Mate\logs\`。

内部包不做代码签名，分发时需要提前说明：

- Windows 可能提示未知发布者。
- 如被企业杀软拦截，先使用绿色包或联系 IT 加白。
- 不要从非公司渠道转发安装包。

### 12.2 GitHub Actions 打包

如果没有 Windows 机器，可以使用 GitHub Actions 的 `windows-latest` runner 打包。

当前仓库提供：

```text
.github/workflows/build-windows.yml
```

出于内部素材安全考虑，`smart-assets/` 不提交到 GitHub 仓库。需要先在本地生成并压缩素材包：

```powershell
Compress-Archive -Path smart-assets -DestinationPath smart-assets.zip -Force
```

或在 macOS/Linux 上：

```bash
zip -r smart-assets.zip smart-assets
```

然后把 `smart-assets.zip` 上传到公司内部可访问地址，例如：

- 私有对象存储临时下载链接。
- 私有 GitHub Release asset。
- 公司网盘直链。
- 内部制品库。

在 GitHub 仓库中配置 Secret：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
Name: SMART_ASSETS_URL
Value: <smart-assets.zip 的私有下载地址>
```

配置完成后手动触发：

```text
Actions -> Build Windows Desktop -> Run workflow
```

构建完成后下载 artifact：

```text
capcut-mate-windows
```

里面包含：

```text
capcut-mate-windows-x64-installer.exe
capcut-mate-windows-x64-green.zip
```

## 13. 验收清单

### 13.1 安装启动

- Windows 10/11 可安装。
- 桌面快捷方式可启动。
- 启动后本地后端自动运行。
- 打开页面不白屏。
- `http://127.0.0.1:<port>/docs` 可访问，或健康检查正常。

### 13.2 素材自检

- 文字模板数量大于 0。
- 音效数量大于 0。
- `文字模板2` 的模板能展开文字层、贴纸层、动画层。
- 音效可以预览。
- 音效实际文件和界面名称一致。

### 13.3 生成草稿

- 本地视频可选择。
- ASR 可生成字幕。
- LLM 可校准字幕和提取重点词。
- 底部字幕位置正确。
- 文字模板花字在画面上方左右区域。
- 花字音效不重复，除非音效池用完。
- 生成草稿能保存到剪映草稿目录。
- 剪映打开后不要求重新链接本地视频。

### 13.4 异常场景

- 未安装剪映时有明确提示。
- 剪映草稿目录探测失败时可以手动选择。
- ASR/LLM 失败时错误提示可读。
- 后端端口被占用时有提示或自动换端口。
- 素材包缺失时有自检提示。

## 14. 常见风险

### 14.1 剪映素材授权/VIP

模板和音效如果是 VIP 素材，业务电脑打开草稿时可能仍受剪映账号授权影响。内测前需要用业务账号验证。

### 14.2 素材缓存不完整

只复制 `文字模板2` 草稿目录不够，还必须复制 `artistEffect` 缓存包。只复制 `音效库2` 草稿目录也不够，还必须复制 `music` 中的真实 mp3 和 `downLoadcfg`。

### 14.3 Windows 路径和权限

Windows 路径包含中文和空格时，后端和 Electron 都必须使用绝对路径，不要拼 shell 命令字符串。启动后端建议使用 `spawn(file, args, { env })`，不要用一整段命令。

### 14.4 杀毒软件误报

PyInstaller + Electron 打出的内部包可能被 Windows Defender 或企业杀软误报。本项目仅公司内部使用，第一版不做代码签名；如遇拦截，优先使用绿色包、企业网盘可信分发、IT 加白或内部说明处理。

### 14.5 端口冲突

默认端口 `30000` 可能被占用。生产包建议支持动态端口，并把端口写入前端运行配置。

## 15. 建议开发排期

### 第一期：可发内测包

- 后端支持环境变量读取素材路径。
- PyInstaller 打 Windows 后端。
- Electron 自动启动/关闭后端。
- `electron-builder` 打入 backend 和 smart-assets。
- 提供安装包和绿色包。
- 做素材自检接口。

### 第二期：稳定业务分发

- ASR/LLM Key 改为公司服务代理。
- 增加自动更新。
- 增加素材包版本管理。
- 增加日志导出按钮。
- 增加端口冲突自动切换。
- 增加内部版本检查和强制升级提示。

## 16. 最小可用版本标准

满足以下条件即可给业务试用：

- 业务电脑不需要安装 Python。
- 业务电脑不需要手动启动后端。
- 业务电脑不需要手动复制文字模板和音效缓存。
- 业务只需要安装应用、配置 key、选择视频、点击生成。
- 生成的剪映草稿能在业务电脑剪映专业版里打开，文字模板和音效正常。
