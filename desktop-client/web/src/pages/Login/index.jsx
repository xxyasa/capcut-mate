import { useEffect, useRef, useState } from "react";
import "./index.less";

const APP_DESK_ID = "2067450522575937538";
const APP_DESK_VERSION = "v1.0";
const MAC_ID_KEY = "auto_cut_mix_mac_id";

function getElectronAPI() {
  return window.electronAPI;
}

function generateMacId() {
  const existed = localStorage.getItem(MAC_ID_KEY);
  if (existed) {
    return existed;
  }

  const macId = `${Date.now()}_${Math.random().toString(36).slice(2, 15)}`;
  localStorage.setItem(MAC_ID_KEY, macId);
  return macId;
}

function LoginPage({ onLoginSuccess }) {
  const [activeTab, setActiveTab] = useState("qrcode");
  const [authCode, setAuthCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  const usernameInputRef = useRef(null);
  const authCodeInputRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (activeTab === "password") {
        usernameInputRef.current?.focus();
      }
      if (activeTab === "authcode") {
        authCodeInputRef.current?.focus();
      }
    }, 80);

    return () => clearTimeout(timer);
  }, [activeTab]);

  const showMessage = (text, type = "info") => {
    setMessage({ text, type });
  };

  const doLogin = async (loginData) => {
    const electronAPI = getElectronAPI();
    if (!electronAPI?.login) {
      showMessage("当前环境不支持登录，请在桌面端中打开。", "error");
      return;
    }

    setLoading(true);
    setMessage({ text: "", type: "" });

    try {
      const result = await electronAPI.login(loginData);
      if (result.success) {
        showMessage("登录成功", "success");
        setTimeout(() => onLoginSuccess(result.data), 500);
        return;
      }
      showMessage(`登录失败：${result.message || "未知错误"}`, "error");
    } catch (error) {
      showMessage(`登录错误：${error.message}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const buildBasePayload = () => ({
    scope: "ALL",
    app_desk_id: APP_DESK_ID,
    app_desk_version: APP_DESK_VERSION,
    platform_client_id: "platform",
    mac: generateMacId(),
  });

  const handleQrcodeLogin = () => {
    setMessage({ text: "", type: "" });
    const loginUrl = "https://idaas-auth.ecmax.cn/sso/render?thirdOAuthType=WORK_WECHAT_SCAN&state=browser_plugin";
    const loginWindow = window.open(loginUrl, "wxLogin", "width=600,height=680,resizable=yes,scrollbars=yes");

    if (!loginWindow) {
      showMessage("无法打开登录窗口，请检查弹窗设置。", "error");
      return;
    }

    const handleMessage = async (event) => {
      const uuid = event?.data?.uuid;
      if (!uuid) {
        return;
      }

      if (!loginWindow.closed) {
        loginWindow.close();
      }
      window.removeEventListener("message", handleMessage);

      await doLogin({
        ...buildBasePayload(),
        grant_type: "app_desk",
        username: uuid,
        app_desk_user_type: "INNER",
      });
    };

    window.addEventListener("message", handleMessage);

    const checkClosed = setInterval(() => {
      if (loginWindow.closed) {
        clearInterval(checkClosed);
        window.removeEventListener("message", handleMessage);
      }
    }, 1000);
  };

  const handlePasswordLogin = async (event) => {
    event.preventDefault();

    if (!username || !password) {
      showMessage("请输入用户名和密码", "error");
      return;
    }

    await doLogin({
      ...buildBasePayload(),
      grant_type: "password",
      username,
      password,
    });
  };

  const handleAuthCodeLogin = async (event) => {
    event.preventDefault();

    if (!authCode) {
      showMessage("请输入授权码", "error");
      return;
    }

    await doLogin({
      ...buildBasePayload(),
      grant_type: "app_desk",
      username: authCode,
      app_desk_user_type: "OUTER",
    });
  };

  return (
    <div className="login-page">
      <section className="login-panel">
        <div className="login-title">
          <h1>极易智能包装小助手</h1>
          <p>登录后继续使用智能包装与草稿工具</p>
        </div>

        <div className="login-tabs">
          <button className={activeTab === "qrcode" ? "active" : ""} onClick={() => setActiveTab("qrcode")}>
            企微扫码
          </button>
          <button className={activeTab === "password" ? "active" : ""} onClick={() => setActiveTab("password")}>
            账号密码
          </button>
          <button className={activeTab === "authcode" ? "active" : ""} onClick={() => setActiveTab("authcode")}>
            授权码
          </button>
        </div>

        {activeTab === "qrcode" && (
          <div className="login-form">
            <div className="login-hint">
              使用此工具需要账号授权。申请路径：企微工作台-审批-极易自研系统-账号权限申请。
            </div>
            <button className="login-primary" onClick={handleQrcodeLogin} disabled={loading}>
              {loading ? "登录中..." : "企业微信扫码登录"}
            </button>
          </div>
        )}

        {activeTab === "password" && (
          <form className="login-form" onSubmit={handlePasswordLogin}>
            <label>
              用户名
              <input
                ref={usernameInputRef}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="请输入用户名"
                disabled={loading}
              />
            </label>
            <label>
              密码
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="请输入密码"
                disabled={loading}
              />
            </label>
            <button className="login-primary" type="submit" disabled={loading}>
              {loading ? "登录中..." : "登录"}
            </button>
          </form>
        )}

        {activeTab === "authcode" && (
          <form className="login-form" onSubmit={handleAuthCodeLogin}>
            <label>
              授权码
              <input
                ref={authCodeInputRef}
                value={authCode}
                onChange={(event) => setAuthCode(event.target.value)}
                placeholder="请输入授权码"
                disabled={loading}
              />
            </label>
            <button className="login-primary" type="submit" disabled={loading}>
              {loading ? "登录中..." : "登录"}
            </button>
          </form>
        )}

        {message.text && <div className={`login-message ${message.type}`}>{message.text}</div>}
      </section>
    </div>
  );
}

export default LoginPage;
