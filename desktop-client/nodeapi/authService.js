const https = require('https');
const { URLSearchParams } = require('url');
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const config = {
  MODE: 'production',
  PACKAGENAME: '混剪助手',
  WXLOGIN_URL: 'https://idaas-auth.ecmax.cn/sso/render?thirdOAuthType=WORK_WECHAT_SCAN&state=browser_plugin',
  QYWX_APPID: 'wwb2cb4085b19e32d4',
  AGENTID: '1000023',
  BASE_URL: 'https://idaas-auth.ecmax.cn',
  CLIENT_AUTHORIZATION: 'Basic YnJvd3Nlcl9wbHVnaW46c2VjcmV0',
  APP_DESK_ID: '2067450522575937538',
  APP_DESK_VERSION: 'v1.0',
  PLATFORM_CLIENT_ID: 'platform',
  MAC_ID: 'auto_cut_mix_mac_id',
  get isDevelopment() {
    return !app.isPackaged;
  },
};

let loginState = {
  isLoggedIn: false,
  token: null,
  userInfo: null,
  expiresAt: null,
};

function getLoginStateFile() {
  return path.join(app.getPath('userData'), 'login-state.json');
}

function loadLoginState() {
  try {
    const filePath = getLoginStateFile();
    if (!fs.existsSync(filePath)) {
      return false;
    }
    loginState = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return isLoginValid();
  } catch (error) {
    console.error('加载登录状态失败:', error);
    return false;
  }
}

function saveLoginState() {
  try {
    const filePath = getLoginStateFile();
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(loginState, null, 2));
  } catch (error) {
    console.error('保存登录状态失败:', error);
  }
}

function clearLoginState() {
  loginState = {
    isLoggedIn: false,
    token: null,
    userInfo: null,
    expiresAt: null,
  };

  try {
    const filePath = getLoginStateFile();
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  } catch (error) {
    console.error('清除登录状态失败:', error);
  }
}

function makeLoginRequest(loginData) {
  return new Promise((resolve, reject) => {
    const url = new URL(`${config.BASE_URL}/oauth2/token`);
    const postData = new URLSearchParams();

    Object.keys(loginData || {}).forEach((key) => {
      postData.append(key, loginData[key]);
    });

    const postDataString = postData.toString();
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(postDataString),
        'User-Agent': 'MixCutAssistant/1.0.0',
        Authorization: config.CLIENT_AUTHORIZATION,
        Accept: '*/*',
        Connection: 'keep-alive',
      },
      rejectUnauthorized: !config.isDevelopment,
      timeout: 30000,
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        if (!data || data.trim() === '') {
          resolve({
            success: false,
            message: res.statusCode === 404
              ? 'API接口不存在 (404)'
              : res.statusCode === 401
                ? '认证失败 (401)'
                : res.statusCode >= 500
                  ? `服务器内部错误 (${res.statusCode})`
                  : '服务器返回空响应',
            statusCode: res.statusCode,
          });
          return;
        }

        try {
          const result = JSON.parse(data);
          if (res.statusCode === 200 && result.access_token) {
            resolve({ success: true, data: result });
            return;
          }

          resolve({
            success: false,
            message: result.msg || result.error_description || result.message || '登录失败',
            code: result.code,
            statusCode: res.statusCode,
          });
        } catch (error) {
          resolve({
            success: false,
            message: `响应数据格式错误: ${error.message}`,
          });
        }
      });
    });

    req.on('error', (error) => {
      reject(new Error(`网络请求失败: ${error.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });

    req.write(postDataString);
    req.end();
  });
}

function setLoginState(tokenData) {
  loginState = {
    isLoggedIn: true,
    token: tokenData.access_token,
    userInfo: tokenData.user_info || { realName: tokenData.realName, username: tokenData.username },
    expiresAt: Date.now() + (tokenData.expires_in || 7200) * 1000,
  };
  saveLoginState();
}

function isLoginValid() {
  if (!loginState.isLoggedIn || !loginState.token) {
    return false;
  }

  if (loginState.expiresAt && Date.now() > loginState.expiresAt) {
    clearLoginState();
    return false;
  }

  return true;
}

function getUserInfo() {
  return loginState.userInfo;
}

function getAccessToken() {
  return loginState.token;
}

function logout() {
  clearLoginState();
}

module.exports = {
  config,
  makeLoginRequest,
  setLoginState,
  isLoginValid,
  loadLoginState,
  getUserInfo,
  getAccessToken,
  logout,
  clearLoginState,
};
