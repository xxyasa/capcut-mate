import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "react-toastify";
import electronService from "../../services/electronService";

import "./index.less";

const DEFAULT_API_BASE = "http://localhost:30000/openapi/capcut-mate/v1";
const DEFAULT_ASR_ENDPOINT = "https://model-api.ecmax.cn/v1/audio/transcriptions";
const DEFAULT_ASR_MODEL = "whisper-large-v3";
const DEFAULT_LLM_ENDPOINT = "https://model-api.ecmax.cn/v1/chat/completions";
const DEFAULT_LLM_MODEL = "deepseek-v4-flash";
const DEFAULT_DOMAIN_TERMS = [
  "格兰芬多",
  "斯莱特林",
  "赫奇帕奇",
  "拉文克劳",
  "霍格沃茨",
  "魔杖",
  "宝剑",
  "格兰芬多宝剑",
];
const HIGHLIGHT_TRANSFORM_X_MIN = -782;
const HIGHLIGHT_TRANSFORM_X_MAX = 780;
const HIGHLIGHT_TRANSFORM_Y_MIN = 520;
const HIGHLIGHT_TRANSFORM_Y_MAX = 820;
const PLAIN_CAPTION_TRANSFORM_Y = -1500;
const DEFAULT_JIANYING_SOUND_DRAFT_DIR = "";
const DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR = "";
const DEFAULT_HIGHLIGHT_SOUND_EFFECTS = [
  "滴，提示音",
  "叮叮叮",
  "哇呜",
  "啵1",
  "唰",
  "Ding，可爱提示音",
  "魔法音效",
  "正确",
  "叮",
];
const EXCLUDED_TEXT_TEMPLATE_KEYWORDS = ["疯狂安利", "实用满分", "超值好物", "简约盐系穿搭"];

function splitLines(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeApiKey(value) {
  let cleaned = String(value || "").trim().replace(/\u3000/g, " ");
  if (/^authorization\s*:/i.test(cleaned)) {
    cleaned = cleaned.replace(/^authorization\s*:/i, "").trim();
  }
  if (/^bearer\s+/i.test(cleaned)) {
    cleaned = cleaned.replace(/^bearer\s+/i, "").trim();
  }
  return cleaned.replace(/\s+/g, "");
}

function buildVideoItems(videoUrls, localVideoPaths, captionLines) {
  const remoteItems = videoUrls.map((videoUrl) => ({ video_url: videoUrl }));
  const localItems = localVideoPaths.map((localVideoPath) => ({ local_video_path: localVideoPath }));
  return [...remoteItems, ...localItems].map((item, index) => ({
    ...item,
    caption_texts: captionLines[index]
      ? captionLines[index].split("|").map((item) => item.trim()).filter(Boolean)
      : [],
  }));
}

function SmartPackagingPage() {
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [videoUrls, setVideoUrls] = useState("");
  const [localVideoPaths, setLocalVideoPaths] = useState([]);
  const [captionTexts, setCaptionTexts] = useState("");
  const [enableAsr, setEnableAsr] = useState(true);
  const [asrEndpoint, setAsrEndpoint] = useState(DEFAULT_ASR_ENDPOINT);
  const [asrApiKey, setAsrApiKey] = useState("");
  const [asrModel, setAsrModel] = useState(DEFAULT_ASR_MODEL);
  const [asrLanguage, setAsrLanguage] = useState("zh");
  const [timestampGranularity, setTimestampGranularity] = useState("word_segment");
  const [enableLlmCaption, setEnableLlmCaption] = useState(true);
  const [llmEndpoint, setLlmEndpoint] = useState(DEFAULT_LLM_ENDPOINT);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [domainTerms, setDomainTerms] = useState(DEFAULT_DOMAIN_TERMS.join("\n"));
  const [style, setStyle] = useState("dynamic");
  const [muteOriginal, setMuteOriginal] = useState(false);
  const [fontSize, setFontSize] = useState(12);
  const [captionTransformY, setCaptionTransformY] = useState(PLAIN_CAPTION_TRANSFORM_Y);
  const [captionKeywordColor, setCaptionKeywordColor] = useState("#ffe600");
  const [maxCaptionChars, setMaxCaptionChars] = useState(10);
  const [highlightEnabled, setHighlightEnabled] = useState(true);
  const [highlightFontSize, setHighlightFontSize] = useState(28);
  const [jianyingTextTemplateDraftDir, setJianyingTextTemplateDraftDir] = useState(DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR);
  const [textTemplateNames, setTextTemplateNames] = useState("");
  const [textTemplateCatalog, setTextTemplateCatalog] = useState([]);
  const [isLoadingTextTemplates, setIsLoadingTextTemplates] = useState(false);
  const [textEffects, setTextEffects] = useState("黄字橙光花字\n动感黄色发光故障风花字\n红金立体发光花字");
  const [textEffectCatalog, setTextEffectCatalog] = useState([]);
  const [textEffectQuery, setTextEffectQuery] = useState("");
  const [isLoadingTextEffects, setIsLoadingTextEffects] = useState(false);
  const [captionAnimations, setCaptionAnimations] = useState("弹入\n向上滑动");
  const [loopAnimations, setLoopAnimations] = useState("");
  const [effectTitles, setEffectTitles] = useState("抖动\n模糊\n复古DV");
  const [effectCount, setEffectCount] = useState(0);
  const [enableStickers, setEnableStickers] = useState(true);
  const [stickerCount, setStickerCount] = useState(0);
  const [stickerKeywords, setStickerKeywords] = useState("");
  const [filterTitles, setFilterTitles] = useState("亮夏\n初恋\n清透自然");
  const [filterIntensity, setFilterIntensity] = useState(80);
  const [bgmUrls, setBgmUrls] = useState("");
  const [soundEffectUrls, setSoundEffectUrls] = useState("");
  const [jianyingSoundDraftDir, setJianyingSoundDraftDir] = useState(DEFAULT_JIANYING_SOUND_DRAFT_DIR);
  const [highlightSoundEffects, setHighlightSoundEffects] = useState(DEFAULT_HIGHLIGHT_SOUND_EFFECTS.join("\n"));
  const [soundEffectCatalog, setSoundEffectCatalog] = useState([]);
  const [isLoadingSoundEffects, setIsLoadingSoundEffects] = useState(false);
  const [playingSoundName, setPlayingSoundName] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [drafts, setDrafts] = useState([]);

  const remoteVideoCount = useMemo(() => splitLines(videoUrls).length, [videoUrls]);
  const videoCount = remoteVideoCount + localVideoPaths.length;
  const captionCount = useMemo(() => splitLines(captionTexts).length, [captionTexts]);
  const selectedTextEffects = useMemo(() => splitLines(textEffects), [textEffects]);
  const selectedTextTemplateNames = useMemo(() => splitLines(textTemplateNames), [textTemplateNames]);
  const selectedHighlightSoundEffects = useMemo(() => splitLines(highlightSoundEffects), [highlightSoundEffects]);
  const soundEffectOptions = useMemo(() => (
    soundEffectCatalog.length > 0
      ? soundEffectCatalog
      : DEFAULT_HIGHLIGHT_SOUND_EFFECTS.map((name) => ({ name, preview_url: "", duration: 0 }))
  ), [soundEffectCatalog]);
  const visibleTextEffects = useMemo(() => {
    const query = textEffectQuery.trim().toLowerCase();
    return textEffectCatalog
      .filter((item) => {
        const title = String(item.title || "");
        return !query || title.toLowerCase().includes(query);
      })
      .slice(0, 48);
  }, [textEffectCatalog, textEffectQuery]);

  const loadTextEffectCatalog = async () => {
    setIsLoadingTextEffects(true);
    try {
      const response = await axios.post(`${apiBase}/get_text_effects`, { mode: 0 }, { timeout: 30000 });
      const effects = response.data?.text_effects || [];
      if (!Array.isArray(effects)) {
        toast.error(response.data?.message || "加载花字样式失败");
        return;
      }
      setTextEffectCatalog(effects);
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || "加载花字样式失败");
    } finally {
      setIsLoadingTextEffects(false);
    }
  };

  const loadTextTemplateCatalog = async () => {
    setIsLoadingTextTemplates(true);
    try {
      const response = await axios.post(`${apiBase}/smart_packaging/text_templates`, {
        jianying_text_template_draft_dir: jianyingTextTemplateDraftDir.trim() || undefined,
      }, { timeout: 30000 });
      const templates = response.data?.text_templates || [];
      if (!Array.isArray(templates)) {
        toast.error(response.data?.message || "加载文字模板库失败");
        return;
      }
      setTextTemplateCatalog(templates);
      setTextTemplateNames(templates
        .filter((item) => !EXCLUDED_TEXT_TEMPLATE_KEYWORDS.some((keyword) => item.name.includes(keyword)))
        .map((item) => item.name)
        .join("\n"));
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || "加载文字模板库失败");
    } finally {
      setIsLoadingTextTemplates(false);
    }
  };

  const loadSoundEffectCatalog = async () => {
    setIsLoadingSoundEffects(true);
    try {
      const response = await axios.post(`${apiBase}/smart_packaging/sound_effects`, {
        jianying_sound_draft_dir: jianyingSoundDraftDir.trim() || undefined,
      }, { timeout: 30000 });
      const effects = response.data?.sound_effects || [];
      if (!Array.isArray(effects)) {
        toast.error(response.data?.message || "加载音效库失败");
        return;
      }
      setSoundEffectCatalog(effects);
      setHighlightSoundEffects(effects.length > 0
        ? effects.map((item) => item.name).filter(Boolean).join("\n")
        : DEFAULT_HIGHLIGHT_SOUND_EFFECTS.join("\n"));
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || "加载音效库失败");
    } finally {
      setIsLoadingSoundEffects(false);
    }
  };

  useEffect(() => {
    const loadRuntimeConfig = async () => {
      try {
        const config = await window.electronAPI?.getRuntimeConfig?.();
        if (config?.apiBase) {
          setApiBase(config.apiBase);
        }
      } catch (error) {
        // Browser mode keeps using DEFAULT_API_BASE.
      }
    };
    loadRuntimeConfig();
  }, []);

  useEffect(() => {
    loadTextEffectCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  useEffect(() => {
    loadTextTemplateCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  useEffect(() => {
    loadSoundEffectCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const toggleTextEffect = (title) => {
    const current = selectedTextEffects;
    const next = current.includes(title)
      ? current.filter((item) => item !== title)
      : [...current, title];
    setTextEffects(next.join("\n"));
  };

  const toggleTextTemplate = (name) => {
    const current = selectedTextTemplateNames;
    const next = current.includes(name)
      ? current.filter((item) => item !== name)
      : [...current, name];
    setTextTemplateNames(next.join("\n"));
  };

  const toggleHighlightSoundEffect = (title) => {
    const current = selectedHighlightSoundEffects;
    const next = current.includes(title)
      ? current.filter((item) => item !== title)
      : [...current, title];
    setHighlightSoundEffects(next.join("\n"));
  };

  const playHighlightSoundEffect = async (item) => {
    if (!item?.preview_url) {
      toast.warn("这个音效还没有可播放的缓存文件");
      return;
    }
    try {
      setPlayingSoundName(item.name);
      const audio = new Audio(item.preview_url);
      audio.volume = 0.8;
      audio.onended = () => setPlayingSoundName("");
      audio.onerror = () => {
        setPlayingSoundName("");
        toast.error("音效播放失败");
      };
      await audio.play();
    } catch (error) {
      setPlayingSoundName("");
      toast.error(error.message || "音效播放失败");
    }
  };

  const handleSoundEffectClick = (item) => {
    playHighlightSoundEffect(item);
    toggleHighlightSoundEffect(item.name);
  };

  const timestampGranularities = () => {
    if (timestampGranularity === "word_segment") {
      return ["word", "segment"];
    }
    return [timestampGranularity];
  };

  const buildPayload = () => {
    const videos = buildVideoItems(splitLines(videoUrls), localVideoPaths, splitLines(captionTexts));
    const bgmList = splitLines(bgmUrls);
    const soundList = splitLines(soundEffectUrls);
    const normalizedAsrApiKey = normalizeApiKey(asrApiKey);

    return {
      videos,
      width: 1080,
      height: 1920,
      style,
      mute_original: muteOriginal,
      caption: {
        enabled: true,
        source: enableAsr ? "asr" : "manual",
        font_size: Number(fontSize),
        transform_y: Number(captionTransformY),
        keyword_color: captionKeywordColor.trim() || "#ffe600",
        max_chars_per_caption: Number(maxCaptionChars),
        highlight_enabled: highlightEnabled,
        highlight_style_mode: "template",
        jianying_text_template_draft_dir: jianyingTextTemplateDraftDir.trim() || undefined,
        text_template_names: selectedTextTemplateNames,
        highlight_max_count: 30,
        highlight_max_chars: 5,
        highlight_font_size: Number(highlightFontSize),
        highlight_transform_x_min: HIGHLIGHT_TRANSFORM_X_MIN,
        highlight_transform_x_max: HIGHLIGHT_TRANSFORM_X_MAX,
        highlight_transform_y_min: HIGHLIGHT_TRANSFORM_Y_MIN,
        highlight_transform_y_max: HIGHLIGHT_TRANSFORM_Y_MAX,
        text_effects: selectedTextEffects,
        in_animations: splitLines(captionAnimations),
        loop_animations: splitLines(loopAnimations),
      },
      asr: {
        enabled: enableAsr,
        provider: "openai_compatible",
        endpoint: asrEndpoint.trim() || undefined,
        api_key: normalizedAsrApiKey || undefined,
        model: asrModel.trim() || DEFAULT_ASR_MODEL,
        language: asrLanguage.trim() || undefined,
        timestamp_granularities: timestampGranularities(),
        timeout: 180,
      },
      llm_caption: {
        enabled: enableLlmCaption,
        endpoint: llmEndpoint.trim() || undefined,
        model: llmModel.trim() || DEFAULT_LLM_MODEL,
        domain_terms: splitLines(domainTerms),
        timeout: 180,
      },
      effects: {
        enabled: splitLines(effectTitles).length > 0 && Number(effectCount) > 0,
        effect_titles: splitLines(effectTitles),
        count: Number(effectCount),
        duration: 1200000,
      },
      filters: {
        enabled: splitLines(filterTitles).length > 0,
        filter_titles: splitLines(filterTitles),
        intensity: Number(filterIntensity),
      },
      stickers: {
        enabled: enableStickers && Number(stickerCount) > 0,
        count: Number(stickerCount),
        duration: 900000,
        scale_min: 0.32,
        scale_max: 0.52,
        keywords: splitLines(stickerKeywords),
      },
      bgm: {
        enabled: bgmList.length > 0,
        audio_urls: bgmList,
        volume: 0.35,
      },
      sound_effects: {
        enabled: highlightEnabled || soundList.length > 0,
        audio_urls: soundList,
        highlight_sound_effects: selectedHighlightSoundEffects,
        use_jianying_cache: true,
        jianying_sound_draft_dir: jianyingSoundDraftDir.trim() || undefined,
        count: 0,
        duration: 360000,
        volume: 0.55,
        auto_for_highlights: true,
      },
    };
  };

  const handleGenerate = async () => {
    const payload = buildPayload();
    if (payload.videos.length === 0) {
      toast.warn("请至少输入一个视频 URL 或选择一个本地视频");
      return;
    }
    if (enableAsr && !asrEndpoint.trim()) {
      toast.warn("请填写 ASR 接口地址");
      return;
    }
    if (enableAsr && !asrApiKey.trim()) {
      toast.warn("请填写 ASR API Key");
      return;
    }
    if (enableLlmCaption && !llmEndpoint.trim()) {
      toast.warn("请填写 LLM 接口地址");
      return;
    }

    setIsGenerating(true);
    try {
      const response = await axios.post(`${apiBase}/smart_packaging`, payload, {
        timeout: 180000,
      });
      if (response.data?.code !== 0 || !Array.isArray(response.data?.drafts)) {
        toast.error(response.data?.message || "智能包装失败");
        return;
      }
      setDrafts(response.data.drafts);
      toast.success(`已生成 ${response.data.drafts.length} 个包装草稿`);
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || "智能包装失败");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectLocalVideos = async () => {
    try {
      const paths = await electronService.selectLocalVideos();
      if (Array.isArray(paths) && paths.length > 0) {
        setLocalVideoPaths((current) => Array.from(new Set([...current, ...paths])));
        toast.success(`已选择 ${paths.length} 个本地视频`);
      }
    } catch (error) {
      toast.error(error.message || "选择本地视频失败");
    }
  };

  const removeLocalVideo = (targetPath) => {
    setLocalVideoPaths((current) => current.filter((item) => item !== targetPath));
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
    <div className="smart-packaging-page">
      <div className="container">
        <div className="smart-toolbar">
          <div>
            <div className="section-title">批量智能包装</div>
            <div className="smart-summary">
              视频 {videoCount} 条，{enableAsr ? "ASR 自动字幕" : `手动字幕行 ${captionCount} 条`}
            </div>
          </div>
          <button className="btn btn-download" disabled={isGenerating} onClick={handleGenerate}>
            {isGenerating ? "包装中..." : "生成包装草稿"}
          </button>
        </div>

        <div className="smart-layout">
          <div className="smart-panel smart-panel-main">
            <label className="smart-field">
              <span>后端服务地址</span>
              <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
            </label>

            <label className="smart-field">
              <span>远程视频 URL，每行一个</span>
              <textarea
                value={videoUrls}
                onChange={(e) => setVideoUrls(e.target.value)}
                placeholder="https://example.com/video-a.mp4"
              />
            </label>

            <div className="smart-field">
              <span>本地视频文件</span>
              <button type="button" className="btn btn-download smart-secondary-btn" onClick={handleSelectLocalVideos}>
                选择本地视频
              </button>
              {localVideoPaths.length > 0 && (
                <div className="smart-local-list">
                  {localVideoPaths.map((item) => (
                    <div className="smart-local-item" key={item}>
                      <span title={item}>{item}</span>
                      <button type="button" onClick={() => removeLocalVideo(item)}>移除</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <label className="smart-field">
              <span>手动字幕兜底，每行对应一个视频，多句用 | 分隔</span>
              <textarea
                value={captionTexts}
                onChange={(e) => setCaptionTexts(e.target.value)}
                placeholder="开场钩子|核心卖点|立即行动"
              />
            </label>
          </div>

          <div className="smart-panel">
            <div className="smart-grid">
              <label className="smart-toggle">
                <input
                  type="checkbox"
                  checked={enableAsr}
                  onChange={(e) => setEnableAsr(e.target.checked)}
                />
                <span>启用 ASR 自动字幕</span>
              </label>
              <label className="smart-field">
                <span>包装风格</span>
                <select value={style} onChange={(e) => setStyle(e.target.value)}>
                  <option value="auto">自动</option>
                  <option value="dynamic">动感</option>
                  <option value="vlog">Vlog</option>
                  <option value="clean">干净</option>
                </select>
              </label>
              <label className="smart-field">
                <span>字幕字号</span>
                <input
                  type="number"
                  min="1"
                  value={fontSize}
                  onChange={(e) => setFontSize(e.target.value)}
                />
              </label>
              <label className="smart-field">
                <span>底部重点词颜色</span>
                <div className="smart-color-input">
                  <input
                    type="color"
                    value={captionKeywordColor}
                    onChange={(e) => setCaptionKeywordColor(e.target.value)}
                  />
                  <input
                    value={captionKeywordColor}
                    onChange={(e) => setCaptionKeywordColor(e.target.value)}
                    placeholder="#ffe600"
                  />
                </div>
              </label>
              <label className="smart-field">
                <span>字幕垂直位置</span>
                <input
                  type="number"
                  step="50"
                  value={captionTransformY}
                  onChange={(e) => setCaptionTransformY(e.target.value)}
                />
              </label>
              <label className="smart-field">
                <span>单条字幕最多字数</span>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={maxCaptionChars}
                  onChange={(e) => setMaxCaptionChars(e.target.value)}
                />
              </label>
              <label className="smart-toggle">
                <input
                  type="checkbox"
                  checked={muteOriginal}
                  onChange={(e) => setMuteOriginal(e.target.checked)}
                />
                <span>静音原视频</span>
              </label>
            </div>
          </div>

          {enableAsr && (
            <div className="smart-panel smart-panel-main">
              <div className="smart-grid smart-grid-two">
                <label className="smart-field">
                  <span>ASR 接口地址</span>
                  <input value={asrEndpoint} onChange={(e) => setAsrEndpoint(e.target.value)} />
                </label>
                <label className="smart-field">
                  <span>ASR API Key</span>
                  <input
                    type="password"
                    value={asrApiKey}
                    onChange={(e) => setAsrApiKey(e.target.value)}
                    placeholder="sk-xxxxxxxxxxxxxxxxxx"
                  />
                </label>
                <label className="smart-field">
                  <span>ASR 模型</span>
                  <input value={asrModel} onChange={(e) => setAsrModel(e.target.value)} />
                </label>
                <label className="smart-field">
                  <span>识别语言</span>
                  <input value={asrLanguage} onChange={(e) => setAsrLanguage(e.target.value)} />
                </label>
                <label className="smart-field">
                  <span>时间戳粒度</span>
                  <select value={timestampGranularity} onChange={(e) => setTimestampGranularity(e.target.value)}>
                    <option value="word_segment">词级 + 分段</option>
                    <option value="segment">分段</option>
                    <option value="word">词级</option>
                  </select>
                </label>
                <label className="smart-toggle">
                  <input
                    type="checkbox"
                    checked={enableLlmCaption}
                    onChange={(e) => setEnableLlmCaption(e.target.checked)}
                  />
                  <span>LLM 校验字幕文本</span>
                </label>
                {enableLlmCaption && (
                  <>
                    <label className="smart-field">
                      <span>LLM 接口地址</span>
                      <input value={llmEndpoint} onChange={(e) => setLlmEndpoint(e.target.value)} />
                    </label>
                    <label className="smart-field">
                      <span>LLM 模型</span>
                      <input value={llmModel} onChange={(e) => setLlmModel(e.target.value)} />
                    </label>
                    <label className="smart-field smart-field-wide">
                      <span>专有名词标准词库，每行一个</span>
                      <textarea
                        value={domainTerms}
                        onChange={(e) => setDomainTerms(e.target.value)}
                        placeholder="格兰芬多&#10;霍格沃茨&#10;品牌名&#10;产品名"
                      />
                    </label>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="smart-panel smart-panel-main">
            <div className="smart-grid smart-grid-two">
              <div className="smart-template-picker smart-field-wide">
                <div className="smart-effect-head">
                  <div>
                    <div className="smart-effect-title">剪映电商文字模板</div>
                    <div className="smart-effect-subtitle">
                      从模板草稿读取名称，生成重点词时展开模板中的文字层、贴纸层和动画层
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-small"
                    disabled={isLoadingTextTemplates}
                    onClick={loadTextTemplateCatalog}
                  >
                    {isLoadingTextTemplates ? "加载中..." : "刷新模板库"}
                  </button>
                </div>
                <label className="smart-field">
                  <span>剪映文字模板草稿目录</span>
                  <input
                    value={jianyingTextTemplateDraftDir}
                    onChange={(e) => setJianyingTextTemplateDraftDir(e.target.value)}
                    placeholder={DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR}
                  />
                </label>
                <div className="smart-template-list">
                  {textTemplateCatalog.map((item) => {
                    const selected = selectedTextTemplateNames.includes(item.name);
                    return (
                      <button
                        type="button"
                        className={`smart-template-card ${selected ? "selected" : ""}`}
                        key={`${item.material_id}-${item.name}`}
                        onClick={() => toggleTextTemplate(item.name)}
                        title={item.name}
                      >
                        <span>{item.name}</span>
                        <small>{item.effect_id ? "可展开模板" : "可用模板"}</small>
                      </button>
                    );
                  })}
                  {!isLoadingTextTemplates && textTemplateCatalog.length === 0 && (
                    <div className="smart-effect-empty">没有读取到文字模板</div>
                  )}
                </div>
              </div>
              <label className="smart-field smart-field-wide">
                <span>已选剪映文字模板，可手动编辑，每行一个</span>
                <textarea
                  value={textTemplateNames}
                  onChange={(e) => setTextTemplateNames(e.target.value)}
                  placeholder="电商-新品首发"
                />
              </label>
              <label className="smart-toggle">
                <input
                  type="checkbox"
                  checked={highlightEnabled}
                  onChange={(e) => setHighlightEnabled(e.target.checked)}
                />
                <span>仅重点词/金句使用花字</span>
              </label>
              <label className="smart-field">
                <span>备用花字字号（文字模板自动缩放）</span>
                <input
                  type="number"
                  min="1"
                  value={highlightFontSize}
                  onChange={(e) => setHighlightFontSize(e.target.value)}
                />
              </label>
              <label className="smart-field">
                <span>重点花字入场动画池，每行一个</span>
                <textarea value={captionAnimations} onChange={(e) => setCaptionAnimations(e.target.value)} />
              </label>
              <label className="smart-field">
                <span>重点花字循环动画池，可选，每行一个</span>
                <textarea
                  value={loopAnimations}
                  onChange={(e) => setLoopAnimations(e.target.value)}
                  placeholder="轻微放大"
                />
              </label>
              <label className="smart-field">
                <span>视频特效池，每行一个</span>
                <textarea value={effectTitles} onChange={(e) => setEffectTitles(e.target.value)} />
              </label>
            </div>
          </div>

          <div className="smart-panel">
            <div className="smart-grid">
              <label className="smart-toggle">
                <input
                  type="checkbox"
                  checked={enableStickers}
                  onChange={(e) => setEnableStickers(e.target.checked)}
                />
                <span>结合语境添加随机贴纸</span>
              </label>
              <label className="smart-field">
                <span>贴纸数量</span>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={stickerCount}
                  onChange={(e) => setStickerCount(e.target.value)}
                />
              </label>
              <label className="smart-field">
                <span>特效数量</span>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={effectCount}
                  onChange={(e) => setEffectCount(e.target.value)}
                />
              </label>
              <label className="smart-field">
                <span>滤镜强度</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={filterIntensity}
                  onChange={(e) => setFilterIntensity(e.target.value)}
                />
              </label>
              <label className="smart-field smart-field-wide">
                <span>滤镜池，每行一个</span>
                <textarea value={filterTitles} onChange={(e) => setFilterTitles(e.target.value)} />
              </label>
              <label className="smart-field smart-field-wide">
                <span>贴纸搜索关键词，可选；不填则按字幕语境自动选择</span>
                <textarea
                  value={stickerKeywords}
                  onChange={(e) => setStickerKeywords(e.target.value)}
                  placeholder={"闪光\n星星\n箭头\n重点"}
                />
              </label>
            </div>
          </div>

          <div className="smart-panel smart-panel-main">
            <div className="smart-grid smart-grid-two">
              <label className="smart-field">
                <span>BGM URL，可选，每行一个</span>
                <textarea
                  value={bgmUrls}
                  onChange={(e) => setBgmUrls(e.target.value)}
                  placeholder="https://example.com/bgm.mp3"
                />
              </label>
              <div className="smart-sound-picker">
                <div className="smart-effect-head">
                  <div>
                    <div className="smart-effect-title">花字出场音效池</div>
                    <div className="smart-effect-subtitle">
                      按花字内容自动挑选，已选 {selectedHighlightSoundEffects.length} 个
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-small"
                    disabled={isLoadingSoundEffects}
                    onClick={loadSoundEffectCatalog}
                  >
                    {isLoadingSoundEffects ? "加载中..." : "刷新音效库"}
                  </button>
                </div>
                <div className="smart-sound-list">
                  {soundEffectOptions.map((item) => {
                    const title = item.name;
                    const selected = selectedHighlightSoundEffects.includes(title);
                    return (
                      <button
                        type="button"
                        className={`smart-sound-card ${selected ? "selected" : ""} ${playingSoundName === title ? "playing" : ""}`}
                        key={title}
                        onClick={() => handleSoundEffectClick(item)}
                        title={title}
                      >
                        <span>{title}</span>
                        {item.duration > 0 && (
                          <small>{(item.duration / 1000000).toFixed(1)}s</small>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
              <label className="smart-field">
                <span>已选花字出场音效，可手动编辑，每行一个</span>
                <textarea
                  value={highlightSoundEffects}
                  onChange={(e) => setHighlightSoundEffects(e.target.value)}
                  placeholder="噔1"
                />
              </label>
              <label className="smart-field">
                <span>剪映音效草稿目录</span>
                <input
                  value={jianyingSoundDraftDir}
                  onChange={(e) => setJianyingSoundDraftDir(e.target.value)}
                  placeholder={DEFAULT_JIANYING_SOUND_DRAFT_DIR}
                />
              </label>
              <label className="smart-field">
                <span>自定义音效 URL，可选，每行一个（填写后优先使用）</span>
                <textarea
                  value={soundEffectUrls}
                  onChange={(e) => setSoundEffectUrls(e.target.value)}
                  placeholder="https://example.com/sfx.mp3"
                />
              </label>
            </div>
          </div>
        </div>

        {drafts.length > 0 && (
          <div className="smart-result-list">
            {drafts.map((draft, index) => (
              <div className="smart-result" key={draft.draft_url}>
                <div className="smart-result-body">
                  <div className="smart-result-title">包装草稿 {index + 1}</div>
                  <div className="smart-result-url">{draft.draft_url}</div>
                  <div className="smart-result-meta">
                    {(draft.applied || []).join(" / ")}
                  </div>
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

export default SmartPackagingPage;
