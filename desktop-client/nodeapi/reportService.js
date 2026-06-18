const https = require('https');
const os = require('os');
const { app } = require('electron');
const logger = require('./logger');
const auth = require('./authService');

const REPORT_URL = 'https://dataapi.ecmax.cn/rpa/rpa/pushRpaLog';
const APPLICATION_NAME = '极易智能包装小助手';

function formatDateTime(date = new Date()) {
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function getLocalIp() {
  const interfaces = os.networkInterfaces();
  for (const list of Object.values(interfaces)) {
    for (const item of list || []) {
      if (item.family === 'IPv4' && !item.internal) {
        return item.address;
      }
    }
  }
  return '';
}

function postJson(url, body) {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const payload = JSON.stringify(body);
    const req = https.request({
      hostname: target.hostname,
      port: target.port || 443,
      path: `${target.pathname}${target.search}`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
        'User-Agent': `CapCutMate/${app.getVersion()}`,
      },
      timeout: 15000,
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
          return;
        }
        reject(new Error(`HTTP ${res.statusCode}: ${data}`));
      });
    });

    req.on('timeout', () => {
      req.destroy(new Error('report request timeout'));
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

function resolveBrandName(userInfo = null, fallback = '') {
  const currentUser = userInfo || auth.getUserInfo() || {};
  return currentUser.realName
    || currentUser.name
    || currentUser.nickname
    || currentUser.mobile
    || fallback
    || '';
}

function buildRemark(eventName, remark) {
  const segments = [];
  if (eventName) {
    segments.push(`event=${eventName}`);
  }
  if (remark) {
    segments.push(String(remark));
  }
  return segments.join('; ');
}

async function pushRpaLog({
  eventName = '',
  applicationName = APPLICATION_NAME,
  brandName = '',
  startTime,
  endTime,
  executionQuantity = 1,
  executionResult = '成功',
  remark = '',
  userInfo = null,
} = {}) {
  const startedAt = startTime ? new Date(startTime) : new Date();
  const endedAt = endTime ? new Date(endTime) : new Date();
  const durationSeconds = Math.max(0, Math.round((endedAt.getTime() - startedAt.getTime()) / 1000));

  const formBody = [{
    applicationDuration: durationSeconds,
    applicationName,
    brandName: resolveBrandName(userInfo, brandName),
    endTime: formatDateTime(endedAt),
    executionQuantity: Number(executionQuantity || 0),
    executionResult,
    ip: getLocalIp(),
    startTime: formatDateTime(startedAt),
    remark: buildRemark(eventName, remark),
  }];

  try {
    await postJson(REPORT_URL, formBody);
    logger.info('[Report] RPA log pushed:', JSON.stringify(formBody));
    return { success: true };
  } catch (error) {
    logger.warn('[Report] RPA log failed:', error.message);
    return { success: false, error: error.message };
  }
}

module.exports = {
  pushRpaLog,
};
