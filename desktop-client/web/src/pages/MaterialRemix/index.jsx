import { useState } from "react";
import axios from "axios";
import { toast } from "react-toastify";
import electronService from "../../services/electronService";

import "./index.less";

const DEFAULT_API_BASE = "http://localhost:30000/openapi/capcut-mate/v1";

function splitLines(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function MaterialRemixPage() {
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [videoUrls, setVideoUrls] = useState("");
  const [bgmUrls, setBgmUrls] = useState("");
  const [outputCount, setOutputCount] = useState(3);
  const [targetSeconds, setTargetSeconds] = useState(30);
  const [style, setStyle] = useState("auto");
  const [isGenerating, setIsGenerating] = useState(false);
  const [drafts, setDrafts] = useState([]);

  const buildPayload = () => ({
    video_urls: splitLines(videoUrls),
    bgm_urls: splitLines(bgmUrls),
    output_count: Number(outputCount),
    target_duration: Number(targetSeconds) * 1000000,
    style,
    width: 1080,
    height: 1920,
    mute_original: true,
  });

  const handleGenerate = async () => {
    const payload = buildPayload();
    if (payload.video_urls.length === 0) {
      toast.warn("请至少输入一个视频素材 URL");
      return;
    }

    setIsGenerating(true);
    try {
      const response = await axios.post(`${apiBase}/material_remix`, payload, {
        timeout: 120000,
      });
      if (response.data?.code !== 0 || !Array.isArray(response.data?.drafts)) {
        toast.error(response.data?.message || "混剪生成失败");
        return;
      }
      setDrafts(response.data.drafts);
      toast.success(`已生成 ${response.data.drafts.length} 个草稿`);
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || "混剪生成失败");
    } finally {
      setIsGenerating(false);
    }
  };

  const importDraft = async (draftUrl) => {
    try {
      const jsonData = await electronService.getUrlJsonData(draftUrl);
      if (jsonData?.code !== 0 || !jsonData?.files) {
        toast.error("获取草稿文件列表失败");
        return;
      }
      const urlParams = new URLSearchParams(draftUrl.includes("?") ? draftUrl.split("?")[1] : "");
      const targetId = urlParams.get("draft_id");
      if (!targetId) {
        toast.error("草稿地址缺少 draft_id");
        return;
      }
      const remoteFileUrls = jsonData.files.filter((fileUrl) => fileUrl.includes(targetId));
      await electronService.saveFile({
        sourceUrl: draftUrl,
        remoteFileUrls,
        targetId,
        isOpenDir: true,
      });
      toast.success("草稿已写入剪映目录");
    } catch (error) {
      toast.error(error.message || "写入剪映失败");
    }
  };

  return (
    <div className="material-remix-page">
      <div className="container">
        <div className="card">
          <div className="card-body">
            <div className="section-title">素材混剪</div>
            <div className="remix-grid">
              <label className="remix-field remix-field-wide">
                <span>后端服务地址</span>
                <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
              </label>
              <label className="remix-field remix-field-wide">
                <span>视频素材 URL，每行一个</span>
                <textarea
                  value={videoUrls}
                  onChange={(e) => setVideoUrls(e.target.value)}
                  placeholder="https://example.com/video-a.mp4"
                />
              </label>
              <label className="remix-field remix-field-wide">
                <span>BGM URL，可选，每行一个</span>
                <textarea
                  value={bgmUrls}
                  onChange={(e) => setBgmUrls(e.target.value)}
                  placeholder="https://example.com/bgm.mp3"
                />
              </label>
              <label className="remix-field">
                <span>生成数量</span>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={outputCount}
                  onChange={(e) => setOutputCount(e.target.value)}
                />
              </label>
              <label className="remix-field">
                <span>单条时长（秒）</span>
                <input
                  type="number"
                  min="1"
                  value={targetSeconds}
                  onChange={(e) => setTargetSeconds(e.target.value)}
                />
              </label>
              <label className="remix-field">
                <span>风格</span>
                <select value={style} onChange={(e) => setStyle(e.target.value)}>
                  <option value="auto">自动</option>
                  <option value="fast">快节奏</option>
                  <option value="smooth">平滑</option>
                </select>
              </label>
            </div>
            <div className="remix-note">
              系统会按风格自动给非首段素材添加转场。
            </div>
            <button className="btn btn-download" disabled={isGenerating} onClick={handleGenerate}>
              {isGenerating ? "生成中..." : "生成混剪草稿"}
            </button>
          </div>
        </div>

        {drafts.length > 0 && (
          <div className="remix-result-list">
            {drafts.map((draft, index) => (
              <div className="remix-result" key={draft.draft_url}>
                <div>
                  <div className="remix-result-title">草稿 {index + 1}</div>
                  <div className="remix-result-url">{draft.draft_url}</div>
                </div>
                <button className="btn btn-small" onClick={() => importDraft(draft.draft_url)}>
                  写入剪映
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default MaterialRemixPage;
