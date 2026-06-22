from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class SmartPackagingVideoInput(BaseModel):
    """单个待包装视频。"""

    video_url: Optional[HttpUrl] = Field(default=None, description="视频素材 URL")
    local_video_path: Optional[str] = Field(default=None, description="本地视频文件路径，仅桌面应用/本机服务可用")
    duration: Optional[int] = Field(default=None, ge=100_000, description="视频时长，微秒；不传则自动识别完整视频时长")
    title: Optional[str] = Field(default=None, description="视频标题，可用于自动字幕")
    captions: List[dict] = Field(default_factory=list, description="字幕项，兼容 add_captions captions")
    caption_texts: List[str] = Field(default_factory=list, description="自动均分生成字幕的文本列表")

    @model_validator(mode="after")
    def validate_source(self):
        if not self.video_url and not self.local_video_path:
            raise ValueError("video_url or local_video_path is required")
        return self


class SmartPackagingCaptionConfig(BaseModel):
    """字幕/花字包装配置。"""

    enabled: bool = Field(default=True, description="是否添加字幕")
    source: Literal["asr", "manual", "auto"] = Field(default="auto", description="字幕来源：ASR、手动或自动兜底")
    text_color: str = Field(default="#ffffff", description="字幕颜色")
    border_color: Optional[str] = Field(default="#000000", description="字幕描边颜色")
    font: Optional[str] = Field(default=None, description="字体名称")
    font_size: int = Field(default=12, ge=1, description="字幕字号")
    transform_y: float = Field(default=-1500.0, description="字幕 Y 轴位置，像素偏移；剪映文本坐标中负值更靠底部")
    keyword_color: str = Field(default="#ffe600", description="底部字幕中重点词高亮颜色")
    keyword_border_color: Optional[str] = Field(default=None, description="底部字幕中重点词描边颜色；不填则沿用字幕描边")
    text_effects: List[str] = Field(default_factory=list, description="花字效果池")
    in_animations: List[str] = Field(default_factory=list, description="字幕入场动画池")
    loop_animations: List[str] = Field(default_factory=list, description="字幕循环动画池")
    caption_duration: int = Field(default=2_000_000, ge=100_000, description="自动字幕单句默认时长")
    max_chars_per_caption: int = Field(default=10, ge=1, le=30, description="单条字幕最大字数，断句会优先选择语义边界")
    highlight_enabled: bool = Field(default=True, description="是否只把重点词/金句做成花字")
    highlight_style_mode: Literal["template", "effect"] = Field(default="template", description="重点花字样式模式：template 为干净文字模板，effect 为剪映花字效果")
    jianying_text_template_draft_dir: Optional[str] = Field(default=None, description="剪映文字模板素材库草稿目录")
    text_template_names: List[str] = Field(default_factory=list, description="剪映文字模板名称池")
    highlight_max_count: int = Field(default=30, ge=0, le=30, description="单个视频最多生成重点花字数量上限")
    highlight_max_chars: int = Field(default=4, ge=1, le=4, description="单条重点花字最大字数")
    highlight_font_size: int = Field(default=28, ge=1, description="重点花字字号")
    text_template_scale: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=2.0,
        description="剪映文字模板整体缩放；不填则按底部字幕字号自动缩放",
    )
    highlight_transform_x_min: float = Field(default=-782.0, description="重点花字随机 X 轴最小位置，像素偏移")
    highlight_transform_x_max: float = Field(default=780.0, description="重点花字随机 X 轴最大位置，像素偏移")
    highlight_transform_y_min: float = Field(default=520.0, description="重点花字随机 Y 轴最小位置，像素偏移；正值更靠上")
    highlight_transform_y_max: float = Field(default=820.0, description="重点花字随机 Y 轴最大位置，像素偏移；正值更靠上")

    @model_validator(mode="after")
    def validate_highlight_position_range(self):
        if self.highlight_transform_x_min > self.highlight_transform_x_max:
            raise ValueError("highlight_transform_x_min must be <= highlight_transform_x_max")
        if self.highlight_transform_y_min > self.highlight_transform_y_max:
            raise ValueError("highlight_transform_y_min must be <= highlight_transform_y_max")
        return self


class SmartPackagingAsrConfig(BaseModel):
    """ASR 字幕识别配置。"""

    enabled: bool = Field(default=False, description="是否启用 ASR 自动字幕")
    provider: Literal["custom_json", "openai_compatible"] = Field(
        default="custom_json",
        description="ASR 服务类型",
    )
    endpoint: Optional[str] = Field(default=None, description="ASR 接口地址")
    api_key: Optional[str] = Field(default=None, description="ASR API Key，可选")
    model: Optional[str] = Field(default=None, description="ASR 模型名称，可选")
    language: Optional[str] = Field(default="zh", description="识别语言，可选")
    timestamp_granularities: List[Literal["word", "segment"]] = Field(
        default_factory=lambda: ["segment"],
        description="时间戳粒度，兼容 OpenAI verbose_json",
    )
    timeout: int = Field(default=180, ge=1, le=1800, description="ASR 请求超时秒数")


class SmartPackagingLlmCaptionConfig(BaseModel):
    """LLM 字幕校验/纠错配置。"""

    enabled: bool = Field(default=False, description="是否启用 LLM 字幕纠错")
    endpoint: Optional[str] = Field(default=None, description="LLM chat/completions 接口地址")
    api_key: Optional[str] = Field(default=None, description="LLM API Key，可选；不填时复用 ASR Key")
    model: str = Field(default="deepseek-v4-flash", description="LLM 模型名称")
    domain_terms: List[str] = Field(default_factory=list, description="专有名词标准词库，供 LLM 校准 ASR 同音误识别")
    timeout: int = Field(default=180, ge=1, le=1800, description="LLM 请求超时秒数")


class SmartPackagingEffectConfig(BaseModel):
    """视频特效配置。"""

    enabled: bool = Field(default=True, description="是否添加视频特效")
    effect_titles: List[str] = Field(default_factory=list, description="特效名称池")
    count: int = Field(default=2, ge=0, le=20, description="单个草稿添加特效数量")
    duration: int = Field(default=1_200_000, ge=100_000, description="单个特效时长，微秒")


class SmartPackagingFilterConfig(BaseModel):
    """滤镜配置。"""

    enabled: bool = Field(default=True, description="是否添加滤镜")
    filter_titles: List[str] = Field(default_factory=list, description="滤镜名称池")
    intensity: float = Field(default=80.0, ge=0.0, le=100.0, description="滤镜强度")


class SmartPackagingSoundEffectConfig(BaseModel):
    """音效配置。"""

    enabled: bool = Field(default=True, description="是否添加音效")
    audio_urls: List[HttpUrl] = Field(default_factory=list, description="音效 URL 池")
    highlight_sound_effects: List[str] = Field(default_factory=list, description="花字出场音效名称池")
    use_jianying_cache: bool = Field(default=True, description="是否优先使用本机剪映缓存中的真实音效文件")
    jianying_cache_dir: Optional[str] = Field(default=None, description="剪映音效缓存目录，不填则使用默认目录")
    jianying_sound_draft_dir: Optional[str] = Field(default=None, description="剪映音效素材库草稿目录，不填则尝试读取默认“音效”草稿")
    count: int = Field(default=2, ge=0, le=20, description="单个草稿添加音效数量")
    duration: int = Field(default=360_000, ge=100_000, description="单个音效时长，微秒")
    volume: float = Field(default=0.55, ge=0.0, le=10.0, description="音效音量")
    auto_for_highlights: bool = Field(default=True, description="是否为重点花字自动添加出场音效")


class SmartPackagingBgmConfig(BaseModel):
    """BGM 配置。"""

    enabled: bool = Field(default=False, description="是否添加 BGM")
    audio_urls: List[HttpUrl] = Field(default_factory=list, description="BGM URL 池")
    volume: float = Field(default=0.35, ge=0.0, le=10.0, description="BGM 音量")


class SmartPackagingStickerConfig(BaseModel):
    """贴纸配置。"""

    enabled: bool = Field(default=False, description="是否结合语境自动添加贴纸")
    count: int = Field(default=0, ge=0, le=20, description="单个视频最多添加贴纸数量")
    duration: int = Field(default=900_000, ge=100_000, description="单个贴纸显示时长，微秒")
    scale_min: float = Field(default=0.32, ge=0.05, le=5.0, description="贴纸随机最小缩放")
    scale_max: float = Field(default=0.52, ge=0.05, le=5.0, description="贴纸随机最大缩放")
    keywords: List[str] = Field(default_factory=list, description="自定义贴纸搜索关键词池")

    @model_validator(mode="after")
    def validate_scale_range(self):
        if self.scale_min > self.scale_max:
            raise ValueError("scale_min must be <= scale_max")
        return self


class SmartPackagingRequest(BaseModel):
    """批量智能包装请求。"""

    videos: List[SmartPackagingVideoInput] = Field(default_factory=list, description="待包装视频列表")
    width: int = Field(default=1080, ge=1, description="草稿宽度")
    height: int = Field(default=1920, ge=1, description="草稿高度")
    style: Literal["auto", "clean", "dynamic", "vlog"] = Field(default="auto", description="包装风格")
    mute_original: bool = Field(default=False, description="是否静音原视频")
    seed: Optional[int] = Field(default=None, description="随机种子")
    caption: SmartPackagingCaptionConfig = Field(default_factory=SmartPackagingCaptionConfig, description="字幕配置")
    asr: SmartPackagingAsrConfig = Field(default_factory=SmartPackagingAsrConfig, description="ASR 配置")
    llm_caption: SmartPackagingLlmCaptionConfig = Field(
        default_factory=SmartPackagingLlmCaptionConfig,
        description="LLM 字幕校验配置",
    )
    effects: SmartPackagingEffectConfig = Field(default_factory=SmartPackagingEffectConfig, description="特效配置")
    filters: SmartPackagingFilterConfig = Field(default_factory=SmartPackagingFilterConfig, description="滤镜配置")
    sound_effects: SmartPackagingSoundEffectConfig = Field(
        default_factory=SmartPackagingSoundEffectConfig,
        description="音效配置",
    )
    bgm: SmartPackagingBgmConfig = Field(default_factory=SmartPackagingBgmConfig, description="BGM 配置")
    stickers: SmartPackagingStickerConfig = Field(default_factory=SmartPackagingStickerConfig, description="贴纸配置")

    @model_validator(mode="after")
    def validate_videos(self):
        if not self.videos:
            raise ValueError("videos is required")
        return self


class SmartPackagingDraft(BaseModel):
    """单个包装草稿结果。"""

    draft_url: str = Field(default="", description="草稿 URL")
    source_video_url: str = Field(default="", description="源视频 URL")
    duration: int = Field(default=0, description="草稿时长，微秒")
    seed: int = Field(default=0, description="本草稿使用的随机种子")
    video_segment_ids: List[str] = Field(default_factory=list, description="视频片段 ID")
    caption_segment_ids: List[str] = Field(default_factory=list, description="字幕片段 ID")
    highlight_segment_ids: List[str] = Field(default_factory=list, description="重点花字片段 ID")
    effect_segment_ids: List[str] = Field(default_factory=list, description="特效片段 ID")
    filter_segment_ids: List[str] = Field(default_factory=list, description="滤镜片段 ID")
    sticker_segment_ids: List[str] = Field(default_factory=list, description="贴纸片段 ID")
    audio_ids: List[str] = Field(default_factory=list, description="音频素材 ID")
    applied: List[str] = Field(default_factory=list, description="已应用的包装能力")


class SmartPackagingResponse(BaseModel):
    """批量智能包装响应。"""

    drafts: List[SmartPackagingDraft] = Field(default_factory=list, description="生成的草稿列表")


class SmartPackagingSoundEffectsRequest(BaseModel):
    """剪映音效素材库请求。"""

    jianying_sound_draft_dir: Optional[str] = Field(default=None, description="剪映音效素材库草稿目录")
    jianying_cache_dir: Optional[str] = Field(default=None, description="剪映音效缓存目录")


class SmartPackagingSoundEffectItem(BaseModel):
    """单个可预览音效。"""

    name: str = Field(default="", description="音效名称")
    material_id: str = Field(default="", description="剪映素材 ID")
    preview_url: str = Field(default="", description="音效预览 URL")
    duration: int = Field(default=0, description="音效真实时长，微秒")


class SmartPackagingSoundEffectsResponse(BaseModel):
    """剪映音效素材库响应。"""

    sound_effects: List[SmartPackagingSoundEffectItem] = Field(default_factory=list, description="可用音效列表")


class SmartPackagingTextTemplatesRequest(BaseModel):
    """剪映文字模板素材库请求。"""

    jianying_text_template_draft_dir: Optional[str] = Field(default=None, description="剪映文字模板素材库草稿目录")
    jianying_artist_effect_cache_dir: Optional[str] = Field(default=None, description="剪映 artistEffect 缓存目录")


class SmartPackagingTextTemplateItem(BaseModel):
    """单个可用文字模板。"""

    name: str = Field(default="", description="模板名称")
    material_id: str = Field(default="", description="剪映文字模板素材 ID")
    segment_id: str = Field(default="", description="模板草稿中的片段 ID")
    effect_id: str = Field(default="", description="模板内部文字 effectStyle ID")
    is_vip: bool = Field(default=False, description="是否 VIP")
    rank: int = Field(default=9999, description="模板排序")
    default_texts: List[str] = Field(default_factory=list, description="模板默认文本")


class SmartPackagingTextTemplatesResponse(BaseModel):
    """剪映文字模板素材库响应。"""

    text_templates: List[SmartPackagingTextTemplateItem] = Field(default_factory=list, description="可用文字模板列表")
