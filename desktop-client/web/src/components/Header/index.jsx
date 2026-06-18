import "./index.less";

// 顶部导航组件
function TopHeader({ onTabChange, selectedTab, userInfo, onLogout }) {
  const handleTabClick = (tab) => {
    onTabChange(tab);
  };
  const displayName = userInfo?.realName || userInfo?.name || userInfo?.nickname || "已登录";

  return (
    <div className="top-header">
      <div className="top-nav">
        <div
          className={`top-nav-item logo`}
          onClick={() => handleTabClick("download")}
        >
          极易智能包装小助手
        </div>
        <div className="top-nav-group">
          <div
            className={`top-nav-item ${selectedTab === "history" ? "active" : ""}`}
            onClick={() => handleTabClick("history")}
          >
            草稿历史
          </div>
          <div
            className={`top-nav-item ${selectedTab === "smartPackaging" ? "active" : ""}`}
            onClick={() => handleTabClick("smartPackaging")}
          >
            智能包装
          </div>
          <div
            className={`top-nav-item ${selectedTab === "remix" ? "active" : ""}`}
            onClick={() => handleTabClick("remix")}
          >
            素材混剪
          </div>
          <div
            className={`top-nav-item ${selectedTab === "config" ? "active" : ""}`}
            onClick={() => handleTabClick("config")}
          >
            配置中心
          </div>
          <div className="top-user" title={displayName}>
            {displayName}
          </div>
          <button className="top-logout" type="button" onClick={onLogout}>
            退出
          </button>
        </div>
      </div>
    </div>
  );
}
export default TopHeader;
