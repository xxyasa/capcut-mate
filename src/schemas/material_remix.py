from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class MaterialInput(BaseModel):
    """素材输入，支持远程 URL 或服务端本地路径。"""

    type: Literal["url", "local"] = Field(default="url", description="素材类型")
    url: Optional[HttpUrl] = Field(default=None, description="http/https 素材地址")
    path: Optional[str] = Field(default=None, description="服务端本地素材路径")

    @model_validator(mode="after")
    def validate_source(self):
        if self.type == "url" and self.url is None:
            raise ValueError("url material requires url")
        if self.type == "local" and not self.path:
            raise ValueError("local material requires path")
        return self


class CaptionRemixConfig(BaseModel):
    """字幕扩展预留配置。"""

    enabled: bool = Field(default=False, description="是否启用字幕")
    items: List[dict] = Field(default_factory=list, description="字幕项，兼容 add_captions captions")


class VoiceoverRemixConfig(BaseModel):
    """口播扩展预留配置。"""

    enabled: bool = Field(default=False, description="是否启用口播")
    audio_url: Optional[HttpUrl] = Field(default=None, description="口播音频 URL")


class MaterialRemixRequest(BaseModel):
    """素材混剪请求参数。"""

    videos: List[MaterialInput] = Field(default_factory=list, description="原始视频素材输入")
    video_urls: List[HttpUrl] = Field(default_factory=list, description="已 URL 化的视频素材")
    output_count: int = Field(default=1, ge=1, le=20, description="生成草稿数量")
    width: int = Field(default=1080, ge=1, description="草稿宽度")
    height: int = Field(default=1920, ge=1, description="草稿高度")
    target_duration: int = Field(default=30_000_000, ge=1_000_000, description="目标时长，微秒")
    clip_min_duration: int = Field(default=2_000_000, ge=100_000, description="单片段最短时长，微秒")
    clip_max_duration: int = Field(default=5_000_000, ge=100_000, description="单片段最长时长，微秒")
    bgms: List[MaterialInput] = Field(default_factory=list, description="原始 BGM 输入")
    bgm_urls: List[HttpUrl] = Field(default_factory=list, description="已 URL 化的 BGM 素材")
    style: Literal["auto", "fast", "smooth"] = Field(default="auto", description="混剪风格")
    mute_original: bool = Field(default=True, description="是否静音原视频")
    seed: Optional[int] = Field(default=None, description="随机种子")
    caption: CaptionRemixConfig = Field(default_factory=CaptionRemixConfig, description="字幕配置")
    voiceover: VoiceoverRemixConfig = Field(default_factory=VoiceoverRemixConfig, description="口播配置")

    @model_validator(mode="after")
    def validate_materials(self):
        if not self.videos and not self.video_urls:
            raise ValueError("videos or video_urls is required")
        if self.clip_max_duration < self.clip_min_duration:
            raise ValueError("clip_max_duration must be greater than or equal to clip_min_duration")
        return self


class MaterialRemixDraft(BaseModel):
    """单个混剪草稿结果。"""

    draft_url: str = Field(default="", description="草稿 URL")
    duration: int = Field(default=0, description="草稿时长，微秒")
    seed: int = Field(default=0, description="本草稿使用的随机种子")
    selected_videos: List[str] = Field(default_factory=list, description="本草稿选中的视频 URL")
    bgm_url: str = Field(default="", description="选中的 BGM URL")
    segment_ids: List[str] = Field(default_factory=list, description="视频片段 ID")


class MaterialRemixResponse(BaseModel):
    """素材混剪响应。"""

    drafts: List[MaterialRemixDraft] = Field(default_factory=list, description="生成的草稿列表")
