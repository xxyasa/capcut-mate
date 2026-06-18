// import {
//   BrowserRouter as Router,
//   Routes,
//   Route,
//   Navigate,
// } from "react-router-dom";

import "bootstrap/dist/css/bootstrap.min.css";
import "react-toastify/dist/ReactToastify.css";

import "./styles/index.less";

import { ToastContainer } from "react-toastify";

import TopHeader from "./components/Header";
import HistoryPage from "./pages/History";
import MainPage from "./pages/Download";
import ConfigCenter from "./pages/ConfigCenter";
import MaterialRemixPage from "./pages/MaterialRemix";
import SmartPackagingPage from "./pages/SmartPackaging";
import { useEffect, useState } from "react";
import { fetchAppVersion } from "./utils/const";
import LoginPage from "./pages/Login";

function App() {
  const [selectedTab, setSelectedTab] = useState("download");
  const [appVersion, setAppVersion] = useState("");
  const [checkingLogin, setCheckingLogin] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    fetchAppVersion().then((version) => setAppVersion(version));
  }, []);

  useEffect(() => {
    const checkLogin = async () => {
      try {
        const result = await window.electronAPI?.checkLogin?.();
        setIsLoggedIn(Boolean(result?.isLoggedIn));
        setUserInfo(result?.userInfo || null);
      } catch (error) {
        console.error("检查登录状态失败:", error);
        setIsLoggedIn(false);
      } finally {
        setCheckingLogin(false);
      }
    };

    checkLogin();
  }, []);

  const handleLoginSuccess = (tokenData) => {
    setUserInfo(tokenData?.user_info || { realName: tokenData?.realName, username: tokenData?.username });
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    await window.electronAPI?.logout?.();
    setUserInfo(null);
    setIsLoggedIn(false);
  };

  const tabMap = {
    download: <MainPage />,
    smartPackaging: <SmartPackagingPage />,
    remix: <MaterialRemixPage />,
    history: <HistoryPage />,
    config: <ConfigCenter />,
  };

  if (checkingLogin) {
    return <div className="app app-loading">正在检查登录状态...</div>;
  }

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app">
      {/* <Router> */}
      <TopHeader
        onTabChange={setSelectedTab}
        selectedTab={selectedTab}
        userInfo={userInfo}
        onLogout={handleLogout}
      />
      <div className="main-content flex-1">
        {tabMap[selectedTab] || <MainPage />}
        {/* <Routes>
            <Route path="*" element={<Navigate replace to="/" />} />
            <Route path="/" element={<MainPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/config" element={<ConfigCenter />} />
          </Routes> */}
      </div>
      <div className="app-footer">当前版本号：v{appVersion}</div>
      <ToastContainer style={{ top: "55px" }} />
      {/* </Router> */}
    </div>
  );
}

export default App;
