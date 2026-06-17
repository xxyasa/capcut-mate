const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const net = require('net');
const path = require('path');
const logger = require('./nodeapi/logger');

// 引入IPC处理程序模块
const { setupIpcHandlers } = require('./nodeapi/ipcHandlers');

let mainWindow;
let ipcHandlersInitialized = false;
let backendProcess = null;
let runtimeConfig = {
  apiBase: process.env.CAPCUT_MATE_API_BASE || 'http://localhost:30000/openapi/capcut-mate/v1',
  assetsVersion: ''
};

function getResourcePath(...parts) {
  return app.isPackaged
    ? path.join(process.resourcesPath, ...parts)
    : path.join(__dirname, '..', ...parts);
}

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

async function chooseBackendPort() {
  for (let port = 30000; port <= 30020; port += 1) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error('端口 30000-30020 均不可用');
}

function getPythonBackendCommand() {
  if (app.isPackaged) {
    const backendFileName = process.platform === 'win32'
      ? 'capcut-mate-backend.exe'
      : 'capcut-mate-backend';
    return {
      command: getResourcePath('backend', backendFileName),
      args: []
    };
  }

  const windowsPython = path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe');
  const posixPython = path.join(__dirname, '..', '.venv', 'bin', 'python');
  const command = fs.existsSync(windowsPython)
    ? windowsPython
    : fs.existsSync(posixPython)
      ? posixPython
      : 'python3';
  return {
    command,
    args: [path.join(__dirname, '..', 'main.py')]
  };
}

function readAssetsVersion(assetsDir) {
  const manifestPath = path.join(assetsDir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    return '';
  }
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    return String(manifest.version || '');
  } catch (error) {
    logger.warn('读取素材 manifest 失败:', error);
    return '';
  }
}

function pipeBackendLogs(logPath) {
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  return fs.createWriteStream(logPath, { flags: 'a' });
}

async function startBackend() {
  if (backendProcess) {
    return runtimeConfig;
  }

  const port = await chooseBackendPort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const assetsDir = getResourcePath('smart-assets');
  const { command, args } = getPythonBackendCommand();
  const backendLog = pipeBackendLogs(path.join(app.getPath('userData'), 'logs', 'backend.log'));

  runtimeConfig = {
    apiBase: `${baseUrl}/openapi/capcut-mate/v1`,
    assetsVersion: readAssetsVersion(assetsDir)
  };

  backendProcess = spawn(command, args, {
    cwd: path.join(__dirname, '..'),
    env: {
      ...process.env,
      SMART_PACKAGING_ASSETS_DIR: assetsDir,
      JIANYING_TEXT_TEMPLATE_DRAFT_DIR: path.join(assetsDir, 'text_templates', '文字模板2'),
      JIANYING_ARTIST_EFFECT_CACHE_DIR: path.join(assetsDir, 'artistEffect'),
      JIANYING_SOUND_DRAFT_DIR: path.join(assetsDir, 'sound_effects', '音效库2'),
      JIANYING_MUSIC_CACHE_DIR: path.join(assetsDir, 'music'),
      CAPCUT_MATE_HOST: '127.0.0.1',
      CAPCUT_MATE_PORT: String(port),
      DRAFT_URL: `${baseUrl}/openapi/capcut-mate/v1/get_draft`,
      DOWNLOAD_URL: `${baseUrl}/`
    },
    windowsHide: true
  });

  backendProcess.stdout.pipe(backendLog);
  backendProcess.stderr.pipe(backendLog);
  backendProcess.on('exit', (code, signal) => {
    logger.info(`后端进程退出 code=${code} signal=${signal}`);
    backendProcess = null;
    backendLog.end();
  });
  backendProcess.on('error', (error) => {
    logger.error('后端进程启动失败:', error);
  });

  logger.info(`后端服务已启动: ${runtimeConfig.apiBase}`);
  return runtimeConfig;
}

function stopBackend() {
  if (!backendProcess) {
    return;
  }
  backendProcess.kill();
  backendProcess = null;
}

function createWindow() {
  // 避免重复创建窗口
  if (mainWindow) {
    mainWindow.show();
    return mainWindow;
  }

  // 根据平台选择合适的图标格式
  let iconPath;
  if (process.platform === 'darwin') {
    iconPath = path.join(__dirname, './assets/icons/logo.icns');
  } else if (process.platform === 'win32') {
    iconPath = path.join(__dirname, './assets/icons/logo.ico');
  } else {
    iconPath = path.join(__dirname, './assets/icons/logo.png');
  }

  mainWindow = new BrowserWindow({
    width: 1366,
    height: 868,
    icon: iconPath,
    show: false, // 创建窗口但先隐藏，等页面加载完成后再显示
    webPreferences: {
      nodeIntegration: false, // 禁用 Node.js 集成（出于安全考虑，强烈推荐）
      contextIsolation: true, // 启用上下文隔离（Electron 12 后默认 true，推荐开启）
      preload: path.join(__dirname, 'preload.js'), // 指定预加载脚本的绝对路径
      // webSecurity: false, // 禁用web安全策略（可选，根据需求调整）
      disableBlinkFeatures: 'OutOfBlinkCors', // 禁用某些Blink特性以提高性能
      hardwareAcceleration: true // 启用硬件加速
    }
  });

  // 在 macOS 上设置 Dock 图标
  if (process.platform === 'darwin') {
    app.dock.setIcon(path.join(__dirname, './assets/icons/logo.png'));
  }

  // 判断是否为开发模式
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  
  // 加载React应用
  if (isDev) {
    // 开发模式下加载本地web服务
    mainWindow.loadURL('http://localhost:9000');
    // 开发模式下打开开发者工具
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式下加载构建后的文件
    mainWindow.loadFile(path.join(__dirname, 'ui', 'index.html'));
  }

  // 当页面加载完成后显示窗口
  mainWindow.webContents.on('ready-to-show', () => {
    mainWindow.show();
  });

  // 只初始化一次IPC处理程序
  if (!ipcHandlersInitialized) {
    setupIpcHandlers(mainWindow, {
      getRuntimeConfig: () => runtimeConfig
    });
    ipcHandlersInitialized = true;
  }

  mainWindow.on('closed', function () {
    mainWindow = null;
  });

  return mainWindow;
}

// 处理未捕获的异常，特别是与文件权限相关的错误
process.on('uncaughtException', (error) => {
  logger.error('未捕获的异常:', error);
  
  // 在 macOS 沙箱环境下，某些权限错误可能在这里捕获
  if (process.platform === 'darwin' && error.message && 
      (error.message.includes('Operation not permitted') || error.message.includes('EPERM'))) {
    dialog.showMessageBoxSync({
      type: 'error',
      title: '权限错误',
      message: '应用缺少必要的文件访问权限，请检查系统偏好设置中的隐私与安全性设置。',
      detail: '请在 系统偏好设置 > 安全性与隐私 > 隐私 > 文件夹访问 中允许本应用访问相关文件夹。',
      buttons: ['确定']
    });
  }
});

// 判断是否为需要外跳系统浏览器的外部链接
function isExternalUrl(url) {
  return url && (url.startsWith('http://') || url.startsWith('https://'));
}

// 全局拦截所有 webContents 的新窗口打开行为
app.on('web-contents-created', (event, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    if (isExternalUrl(url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
});

// 兜底：任何新窗口被创建时直接销毁并甩到系统浏览器
app.on('browser-window-created', (event, window) => {
  // 用 getAllWindows 判断：如果当前只有这一个窗口，说明是主窗口，放过
  if (BrowserWindow.getAllWindows().length === 1) return;
  // 检测不是外部链接则放过
  const url = window.webContents.getURL();
  if (!isExternalUrl(url)) return;

  window.webContents.once('did-finish-load', () => {
    shell.openExternal(url);
    window.destroy();
  });
});

// 当Electron完成初始化并准备创建浏览器窗口时调用此方法
app.whenReady().then(async () => {
  try {
    await startBackend();
  } catch (error) {
    logger.error('启动本地后端失败:', error);
    dialog.showMessageBoxSync({
      type: 'error',
      title: '本地服务启动失败',
      message: error.message || '本地服务启动失败，请联系技术同学。',
      buttons: ['确定']
    });
  }
  createWindow();
});

app.on('before-quit', () => {
  stopBackend();
});

// 当所有窗口都关闭时退出应用
app.on('window-all-closed', () => {
  // 在macOS上，应用及其菜单栏通常保持活动状态，直到用户使用Cmd + Q明确退出
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // 在macOS上，当单击dock图标时，如果没有任何窗口打开则创建一个，
  // 否则显示已存在的窗口
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  } else {
    // 如果已有窗口，确保它被显示和聚焦
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  }
});
