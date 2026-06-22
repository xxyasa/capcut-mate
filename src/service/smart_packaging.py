import asyncio
import hashlib
import json
import math
import os
import pathlib
import random
import re
import shutil
import struct
import wave
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import config
import src.pyJianYingDraft as draft
from src.pyJianYingDraft.animation import SegmentAnimations
from src.pyJianYingDraft.segment import ClipSettings
from src.pyJianYingDraft.text_segment import TextBorder, TextEffect, TextSegment, TextStyle
from src.pyJianYingDraft.time_util import Timerange
from src.pyJianYingDraft.video_segment import StickerSegment
from src.schemas.smart_packaging import (
    SmartPackagingDraft,
    SmartPackagingRequest,
    SmartPackagingResponse,
    SmartPackagingSoundEffectsRequest,
    SmartPackagingSoundEffectsResponse,
    SmartPackagingSoundEffectItem,
    SmartPackagingTextTemplatesRequest,
    SmartPackagingTextTemplatesResponse,
    SmartPackagingTextTemplateItem,
    SmartPackagingVideoInput,
)
from src.service.asr_captions import transcribe_video_to_captions
from src.service.llm_caption_polish import polish_captions_with_llm
from src.service.add_audios import add_audios_async
from src.service.add_captions import add_captions_async
from src.service.add_effects import add_effects_async
from src.service.add_filters import add_filters_async
from src.service.add_sticker import add_sticker_async
from src.service.add_videos import add_videos_async
from src.service.create_draft import create_draft
from src.service.save_draft import save_draft_async
from src.utils.download import cleanup_temp_file, download
from src.utils import helper
from src.utils.draft_cache import DRAFT_CACHE
from src.utils.jianying_cache import (
    install_smart_packaging_cache_assets,
    localize_jianying_cache_path,
)
from src.utils.logger import logger
from src.utils.media import get_media_duration


STYLE_PRESETS = {
    "clean": {
        "text_effects": [],
        "caption_in_animations": ["渐显"],
        "caption_loop_animations": [],
        "effects": [],
        "filters": [],
    },
    "dynamic": {
        "text_effects": ["黄字橙光花字", "动感黄色发光故障风花字", "红金立体发光花字"],
        "caption_in_animations": ["弹入", "向上滑动"],
        "caption_loop_animations": [],
        "effects": ["抖动", "模糊", "复古DV"],
        "filters": ["亮夏", "初恋", "清透自然"],
    },
    "vlog": {
        "text_effects": ["蓝白渐变立体花字", "白色蓝边立体花字", "黄色渐变描边花字"],
        "caption_in_animations": ["渐显", "向上滑动"],
        "caption_loop_animations": [],
        "effects": ["复古DV", "复古发光", "模糊"],
        "filters": ["初恋", "清透自然", "鲜亮食光"],
    },
}

HIGHLIGHT_STOPWORDS = {
    "这个",
    "那个",
    "就是",
    "然后",
    "因为",
    "所以",
    "可以",
    "我们",
    "你们",
    "大家",
    "今天",
    "一个",
}

HIGHLIGHT_WEAK_WORDS = {
    "一个", "一种", "一款", "这款", "这一款", "这个", "那个", "我们", "你们", "他们", "大家",
    "今天", "然后", "可以", "继续", "来看", "那里", "这里", "这边", "那边", "前方", "后方",
    "还做了", "做了", "是可以",
}

HIGHLIGHT_WEAK_PREFIXES = (
    "一个", "一种", "一款", "这个", "那个", "这一个", "这一款", "这款", "然后", "可以", "继续", "来看",
    "那里", "这里", "这边", "那边", "前方", "后方", "欢这一款", "喜欢到", "到这一款", "到这款",
)

HIGHLIGHT_BAD_SUBSTRINGS = (
    "我们", "你们", "他们", "大家", "这边", "那边", "可以", "做了", "还是", "还做",
    "这一款", "这一个", "这款", "一款", "这个", "那个", "喜欢到", "有到",
)

STICKER_KEYWORD_RULES = (
    (("魔法", "格兰芬多", "斯莱特林", "赫奇帕奇", "拉文克劳", "宝剑", "勇气"), ("魔法", "闪光", "星星")),
    (("橘黄", "橙黄", "铁锈红", "红色", "黄色", "蓝色", "白色", "黑色", "金色", "银色", "棕色"), ("闪光", "彩色", "星星")),
    (("拉链", "隔层", "压纹", "包身", "包包", "设计"), ("重点", "箭头", "放大镜")),
    (("赠送", "礼物", "直播间"), ("礼物", "爱心", "闪光")),
    (("喜欢", "开心", "哈哈", "笑"), ("开心", "笑", "爱心")),
    (("重点", "关键", "核心", "本质", "一定", "必须"), ("重点", "注意", "箭头")),
)

DEFAULT_STICKER_KEYWORDS = ("闪光", "星星", "箭头", "重点", "可爱", "气泡")

_STICKER_DATA_CACHE: List[dict] | None = None

HIGHLIGHT_KEYWORDS = (
    "格兰芬多",
    "斯莱特林",
    "赫奇帕奇",
    "拉文克劳",
    "橘黄色",
    "橙黄色",
    "橘红色",
    "铁锈红",
    "铁锈",
    "红色",
    "黄色",
    "蓝色",
    "白色",
    "黑色",
    "金色",
    "银色",
    "棕色",
    "包身",
    "包包",
    "拉链",
    "隔层",
    "宝剑",
    "勇气",
    "压纹",
    "学院",
    "赠送",
    "直播间",
    "本质",
    "核心",
    "关键",
    "重点",
    "机会",
    "价值",
    "信任",
    "智慧",
    "方法",
    "策略",
    "增长",
    "成交",
    "优势",
    "秘密",
    "答案",
    "结果",
    "改变",
    "第一",
    "必须",
    "一定",
    "不要",
    "真正",
)

PRODUCT_HIGHLIGHT_TERMS = (
    "格兰芬多",
    "斯莱特林",
    "赫奇帕奇",
    "拉文克劳",
    "橘黄色",
    "橙黄色",
    "铁锈红",
    "铁锈",
    "红色",
    "黄色",
    "蓝色",
    "白色",
    "黑色",
    "金色",
    "银色",
    "棕色",
    "包身",
    "包包",
    "小隔层",
    "隔层",
    "拉链",
    "宝剑",
    "勇气",
    "压纹",
    "学院",
    "赠送",
    "魔杖",
    "设计",
)

COLOR_TERMS = ("橘黄色", "橙黄色", "铁锈红", "红色", "黄色", "蓝色", "白色", "黑色", "金色", "银色", "棕色")
IMPACT_TERMS = ("勇气", "宝剑", "魔杖", "格兰芬多", "斯莱特林", "赫奇帕奇", "拉文克劳")
DETAIL_TERMS = ("压纹", "拉链", "隔层", "包身", "包包", "学院", "设计")
HIGH_PRIORITY_HIGHLIGHT_TERMS = (
    "格兰芬多",
    "斯莱特林",
    "赫奇帕奇",
    "拉文克劳",
    "橘黄色",
    "橙黄色",
    "铁锈红",
    "红色",
    "黄色",
    "蓝色",
    "白色",
    "黑色",
    "金色",
    "银色",
    "棕色",
    "勇气",
    "宝剑",
    "魔杖",
    "压纹",
    "拉链",
    "隔层",
)
HIGHLIGHT_TEXT_TEMPLATES = (
    {
        "text_color": "#fff2c7",
        "border_color": "#472000",
        "shadow_info": {"shadow_alpha": 0.55, "shadow_color": "#000000", "shadow_diffuse": 18.0, "shadow_distance": 4.0, "shadow_angle": -45.0},
    },
    {
        "text_color": "#ffffff",
        "border_color": "#174b8f",
        "shadow_info": {"shadow_alpha": 0.48, "shadow_color": "#0b1d3a", "shadow_diffuse": 16.0, "shadow_distance": 5.0, "shadow_angle": -35.0},
    },
    {
        "text_color": "#ffe66d",
        "border_color": "#7a2332",
        "shadow_info": {"shadow_alpha": 0.5, "shadow_color": "#2b0d12", "shadow_diffuse": 16.0, "shadow_distance": 4.0, "shadow_angle": -45.0},
    },
    {
        "text_color": "#eafff5",
        "border_color": "#16725f",
        "shadow_info": {"shadow_alpha": 0.46, "shadow_color": "#082d26", "shadow_diffuse": 14.0, "shadow_distance": 4.0, "shadow_angle": -40.0},
    },
)
DEFAULT_HIGHLIGHT_SOUND_EFFECTS = (
    "滴，提示音",
    "叮叮叮",
    "哇呜",
    "啵1",
    "唰",
    "Ding，可爱提示音",
    "魔法音效",
    "正确",
    "叮",
)
TEXT_TEMPLATE_SAFE_MARGIN_X = 54.0
TEXT_TEMPLATE_SAFE_MARGIN_Y = 96.0
HIGHLIGHT_SOUND_EFFECT_TONES = {
    "啵1": "pop",
    "任务完成": "shine",
    "叮叮叮": "shine",
    "滴，提示音": "tick",
    "啾": "pop",
    "“呼”的转场音效": "whoosh",
    "唰": "whoosh",
    "Ding，可爱提示音": "shine",
    "叮铃~魔法音效": "magic",
    "叮铃～魔法音效": "magic",
    "魔法音效": "magic",
    "闪亮登场音效": "shine",
    "正确": "shine",
    "叮": "shine",
    "哇呜": "pop",
    "砰，拳击声": "impact",
    "匕首": "impact",
    "呵呵": "laugh",
    "情景剧笑": "laugh",
    "嘟咚，提示音1": "pop",
    "Magic reveal": "magic",
}
HIGHLIGHT_TONE_ALIASES = {
    "砰": "impact",
    "拳击": "impact",
    "冲击": "impact",
    "仙尘": "shine",
    "完成": "shine",
    "Ding": "shine",
    "叮叮": "shine",
    "Magic": "magic",
    "魔法": "magic",
    "提示": "tick",
    "滴": "tick",
    "转场": "whoosh",
    "加速": "whoosh",
    "呼": "whoosh",
    "笑": "laugh",
    "疑问": "question",
    "啊?": "question",
}
DEFAULT_JIANYING_MUSIC_CACHE_DIR = os.getenv(
    "JIANYING_MUSIC_CACHE_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Cache/music"),
)
DEFAULT_JIANYING_SOUND_DRAFT_DIR = os.getenv(
    "JIANYING_SOUND_DRAFT_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/音效库2"),
)
DEFAULT_JIANYING_PROJECTS_DIR = os.path.expanduser(
    "~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
)
DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR = os.getenv(
    "JIANYING_TEXT_TEMPLATE_DRAFT_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/文字模板2"),
)
DEFAULT_JIANYING_ARTIST_EFFECT_CACHE_DIR = os.getenv(
    "JIANYING_ARTIST_EFFECT_CACHE_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Cache/artistEffect"),
)
DEFAULT_JIANYING_EFFECT_CACHE_DIR = os.getenv(
    "JIANYING_EFFECT_CACHE_DIR",
    os.path.expanduser("~/Movies/JianyingPro/User Data/Cache/effect"),
)
TEXT_TEMPLATE_BASE_WIDTH = 1080.0
TEXT_TEMPLATE_BASE_HEIGHT = 1920.0
EXCLUDED_JIANYING_TEXT_TEMPLATE_KEYWORDS = ("疯狂安利", "实用满分", "超值好物", "简约盐系穿搭")
TEXT_TEMPLATE_MIN_DISPLAY_DURATION = 2_400_000
TEXT_TEMPLATE_MAX_DISPLAY_DURATION = 3_200_000
TEXT_TEMPLATE_AUTO_SCALE_MIN = 0.7
TEXT_TEMPLATE_AUTO_SCALE_MAX = 1.0
HIGHLIGHT_TIME_LEAD = 260_000
HIGHLIGHT_TIME_TAIL = 260_000
SUPPORTED_JIANYING_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac"}
SOUND_EFFECT_PREVIEW_DIR = os.path.join(config.PROJECT_ROOT, "output", "sound_effect_previews")
SMART_PACKAGING_ASSETS_DIR = os.getenv(
    "SMART_PACKAGING_ASSETS_DIR",
    os.path.join(config.APP_ROOT, "smart-assets"),
)


@dataclass
class PreparedVideo:
    input: SmartPackagingVideoInput
    duration: int
    local_video_path: str | None = None
    cleanup_local_file: bool = False


def _style_preset(style: str) -> dict:
    if style == "auto":
        return STYLE_PRESETS["dynamic"]
    return STYLE_PRESETS.get(style, STYLE_PRESETS["dynamic"])


def _stringify(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _choose_optional(candidates: Sequence[str], randomizer: random.Random) -> str | None:
    if not candidates:
        return None
    return randomizer.choice(list(candidates))


def _spread_starts(duration: int, count: int, item_duration: int) -> List[int]:
    if count <= 0 or duration <= 0:
        return []

    latest_start = max(0, duration - item_duration)
    if count == 1:
        return [0 if latest_start == 0 else latest_start // 2]

    step = latest_start / max(1, count - 1)
    return [int(round(step * index)) for index in range(count)]


def _merge_candidates(explicit: Iterable[str], preset: Iterable[str]) -> List[str]:
    values = [item for item in explicit if item]
    return values or [item for item in preset if item]


def _visible_char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _split_long_text(text: str, max_chars: int) -> List[str]:
    normalized = re.sub(r"\s+", "", text.strip())
    if _visible_char_count(normalized) <= max_chars:
        return [normalized] if normalized else []

    lead_match = re.match(r"^((?:下方|上方|这里|画面里|镜头里|前面|后面).{0,4}?)(一把|一个|一只|一件|这把|这个|这只|这件)", normalized)
    if lead_match:
        first = lead_match.group(1)
        rest = normalized[len(first):]
        if 3 <= _visible_char_count(first) <= max_chars and rest:
            return [first] + _split_long_text(rest, max_chars)

    name_markers = ("格兰芬多", "斯莱特林", "赫奇帕奇", "拉文克劳")
    for marker in name_markers:
        index = normalized.find(marker)
        if 0 < index <= len(normalized) - len(marker):
            left = normalized[:index]
            right = normalized[index:]
            if _visible_char_count(left) <= max_chars:
                return [left] + _split_long_text(right, max_chars)

    soft_limit = max_chars
    hard_limit = max_chars
    protected_suffixes = ("的", "着", "了", "过", "在", "有", "到", "把", "被", "和", "与", "及")
    protected_prefixes = ("的", "着", "了", "过", "和", "与", "及", "是")
    phrase_markers = (
        "然后",
        "但是",
        "而且",
        "如果",
        "所以",
        "因为",
        "就是",
        "可以",
        "对应到",
        "这里",
        "下方",
        "上方",
        "接着",
        "同时",
        "其实",
        "喜欢",
    )
    protected_phrases = (
        "这一款",
        "这一只",
        "这一件",
        "这一个",
        "这一把",
        "一款包包",
        "一只包包",
        "一个包包",
        "这款包包",
        "这只包包",
        "直播间",
        "看一看",
        "瞧一瞧",
        "了解一下",
        "咒语",
        "一个咒语",
        "对应到一个咒语",
    )
    natural_right_starts = (
        "喜欢",
        "对应到",
        "对应到一个",
        "直播间",
        "来直播间",
        "看一看",
        "瞧一瞧",
        "了解一下",
    )
    natural_left_ends = ("有", "来", "看", "是", "的话")

    def boundary_score(text_value: str, index: int, target: int) -> int:
        left = text_value[:index]
        right = text_value[index:]
        if not left or not right:
            return -1000

        score = 0
        distance = abs(_visible_char_count(left) - target)
        score -= distance * 2

        prev_char = text_value[index - 1]
        next_char = text_value[index]
        if prev_char in "。！？!?；;，,、：:":
            score += 80
        if next_char in "。！？!?；;，,、：:":
            score += 20

        for marker in phrase_markers:
            if right.startswith(marker):
                score += 45
            if left.endswith(marker):
                score += 25

        for marker in natural_right_starts:
            if right.startswith(marker):
                score += 70
        for marker in natural_left_ends:
            if left.endswith(marker):
                score += 35
        if left.endswith("可以") and right.startswith(("来", "去", "看", "试")):
            score += 75

        if prev_char in protected_suffixes:
            score -= 35
        if next_char in protected_prefixes:
            score -= 25
        if re.search(r"(象征着|勇气的|格兰芬多|直播间|看一看)$", left):
            score -= 45
        if re.match(r"^(象征着|勇气的|格兰芬多|直播间|看一看)", right):
            score -= 45

        for phrase in protected_phrases:
            phrase_index = text_value.find(phrase)
            while phrase_index != -1:
                if phrase_index < index < phrase_index + len(phrase):
                    score -= 180
                phrase_index = text_value.find(phrase, phrase_index + 1)

        for term in PRODUCT_HIGHLIGHT_TERMS:
            term_index = text_value.find(term)
            while term_index != -1:
                if term_index < index < term_index + len(term):
                    score -= 120
                term_index = text_value.find(term, term_index + 1)

        return score

    def split_once(text_value: str) -> tuple[str, str] | None:
        if _visible_char_count(text_value) <= hard_limit:
            return None

        preferred_start = max(2, soft_limit - 6)
        preferred_end = min(len(text_value) - 1, hard_limit)
        candidates = list(range(preferred_start, preferred_end + 1))
        if not candidates:
            return text_value[:soft_limit], text_value[soft_limit:]

        split_at = max(candidates, key=lambda idx: boundary_score(text_value, idx, soft_limit))
        if split_at <= 0 or split_at >= len(text_value):
            split_at = min(len(text_value) - 1, soft_limit)
        return text_value[:split_at], text_value[split_at:]

    chunks: List[str] = []
    pending = normalized
    while pending:
        result = split_once(pending)
        if result is None:
            chunks.append(pending)
            break
        left, pending = result
        if left:
            chunks.append(left.strip("，,。！？!?；;、"))
        pending = pending.strip("，,。！？!?；;、")

    return [item for item in chunks if item]


def _split_caption_by_max_chars(caption: dict, max_chars: int, source_index: int | None = None) -> List[dict]:
    text = str(caption.get("text", "")).strip()
    pieces = _split_long_text(text, max_chars)
    original_source_index = caption.get("_source_caption_index", source_index)
    if len(pieces) <= 1:
        next_caption = dict(caption)
        if original_source_index is not None:
            next_caption["_source_caption_index"] = original_source_index
        return [next_caption]

    start = int(caption["start"])
    end = int(caption["end"])
    duration = max(1, end - start)
    weights = [max(1, _visible_char_count(piece)) for piece in pieces]
    total_weight = sum(weights)

    result: List[dict] = []
    cursor = start
    for index, piece in enumerate(pieces):
        if index == len(pieces) - 1:
            piece_end = end
        else:
            piece_duration = max(1, round(duration * weights[index] / total_weight))
            piece_end = min(end, cursor + piece_duration)
        next_caption = dict(caption)
        next_caption["start"] = cursor
        next_caption["end"] = piece_end
        next_caption["text"] = piece
        if original_source_index is not None:
            next_caption["_source_caption_index"] = original_source_index
        if caption.get("highlights"):
            piece_highlights = [
                highlight
                for highlight in caption.get("highlights", [])
                if str(highlight) and str(highlight) in piece
            ]
            if piece_highlights:
                next_caption["highlights"] = piece_highlights
                next_caption["highlight"] = "|".join(piece_highlights)
            else:
                next_caption.pop("highlights", None)
                next_caption.pop("highlight", None)
        if piece_end > cursor:
            result.append(next_caption)
        cursor = piece_end
    return result


def _split_captions_by_max_chars(captions: List[dict], max_chars: int) -> List[dict]:
    result: List[dict] = []
    for index, caption in enumerate(captions):
        result.extend(_split_caption_by_max_chars(caption, max_chars, index))
    return result


def _prepare_video(video: SmartPackagingVideoInput) -> PreparedVideo:
    if video.duration:
        return PreparedVideo(input=video, duration=video.duration, local_video_path=video.local_video_path)

    if video.local_video_path:
        if not os.path.isfile(video.local_video_path):
            raise ValueError(f"Local video file does not exist: {video.local_video_path}")
        local_video_path = video.local_video_path
        cleanup_local_file = False
    else:
        logger.info(
            "smart_packaging remote video download start, timeout=%ss, retry=%s, url=%s",
            config.SMART_PACKAGING_VIDEO_DOWNLOAD_TIMEOUT,
            config.SMART_PACKAGING_VIDEO_DOWNLOAD_RETRY,
            video.video_url,
        )
        local_video_path = download(
            str(video.video_url),
            config.TEMP_DIR,
            timeout=config.SMART_PACKAGING_VIDEO_DOWNLOAD_TIMEOUT,
            retry=config.SMART_PACKAGING_VIDEO_DOWNLOAD_RETRY,
        )
        cleanup_local_file = True

    duration = get_media_duration(local_video_path)
    if duration is None or duration <= 0:
        if cleanup_local_file:
            cleanup_temp_file(local_video_path)
        raise ValueError(f"Failed to detect video duration: {video.local_video_path or video.video_url}")
    return PreparedVideo(input=video, duration=duration, local_video_path=local_video_path, cleanup_local_file=cleanup_local_file)


def _build_video_infos(prepared: PreparedVideo, mute_original: bool) -> List[dict]:
    info = {
        "video_url": str(prepared.input.video_url or prepared.input.local_video_path),
        "start": 0,
        "end": prepared.duration,
        "duration": prepared.duration,
        "volume": 0.0 if mute_original else 1.0,
    }
    if prepared.local_video_path:
        info["local_video_path"] = prepared.local_video_path
    return [info]


def _build_captions(
    video: SmartPackagingVideoInput,
    video_duration: int,
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    if video.captions:
        captions = [dict(item) for item in video.captions]
    else:
        texts = video.caption_texts or ([video.title] if video.title else [])
        captions = []
        if texts:
            caption_duration = min(req.caption.caption_duration, video_duration)
            starts = _spread_starts(video_duration, len(texts), caption_duration)
            for index, text in enumerate(texts):
                start = starts[index]
                captions.append(
                    {
                        "start": start,
                        "end": min(video_duration, start + caption_duration),
                        "text": text,
                    }
                )

    return captions


def _apply_caption_style(
    captions: List[dict],
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    if not captions:
        return []

    preset = _style_preset(req.style)
    text_effects = _merge_candidates(req.caption.text_effects, preset["text_effects"])
    in_animations = _merge_candidates(req.caption.in_animations, preset["caption_in_animations"])
    loop_animations = _merge_candidates(req.caption.loop_animations, preset["caption_loop_animations"])

    styled = [dict(caption) for caption in captions]
    for caption in styled:
        caption.setdefault("font_size", req.caption.font_size)
        caption.setdefault("text_effect", _choose_optional(text_effects, randomizer))
        caption.setdefault("in_animation", _choose_optional(in_animations, randomizer))
        caption.setdefault("loop_animation", _choose_optional(loop_animations, randomizer))
    return styled


def _apply_plain_caption_style(
    captions: List[dict],
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    preset = _style_preset(req.style)
    in_animations = _merge_candidates(req.caption.in_animations, preset["caption_in_animations"])
    loop_animations = _merge_candidates(req.caption.loop_animations, preset["caption_loop_animations"])

    styled = [dict(caption) for caption in captions]
    for caption in styled:
        caption.setdefault("font_size", req.caption.font_size)
        caption.pop("text_effect", None)
        if in_animations:
            caption.setdefault("in_animation", _choose_optional(in_animations, randomizer))
        else:
            caption.pop("in_animation", None)
        if loop_animations:
            caption.setdefault("loop_animation", _choose_optional(loop_animations, randomizer))
        else:
            caption.pop("loop_animation", None)
    return styled


def _offset_timed_items(items: List[dict], offset: int, source_index_offset: int = 0) -> List[dict]:
    if offset == 0 and source_index_offset == 0:
        return [dict(item) for item in items]

    result: List[dict] = []
    for item in items:
        next_item = dict(item)
        for key in ("start", "end", "_source_caption_start", "_source_caption_end"):
            if key in next_item and next_item[key] is not None:
                next_item[key] = int(next_item[key]) + offset
        if "_source_caption_index" in next_item and next_item["_source_caption_index"] is not None:
            next_item["_source_caption_index"] = int(next_item["_source_caption_index"]) + source_index_offset
        result.append(next_item)
    return result


def _append_applied(applied: List[str], name: str) -> None:
    if name not in applied:
        applied.append(name)


def _caption_source_index_map(captions: List[dict], source_index_offset: int) -> tuple[dict[int, int], int]:
    if not captions:
        return {}, 0

    local_source_indexes = sorted(
        {int(caption.get("_source_caption_index", index)) for index, caption in enumerate(captions)}
    )
    return {
        source_index: source_index_offset + index
        for index, source_index in enumerate(local_source_indexes)
    }, len(local_source_indexes)


def _globalize_caption_source_indexes(
    captions: List[dict],
    source_index_map: dict[int, int],
) -> List[dict]:
    result: List[dict] = []
    for caption_index, caption in enumerate(captions):
        source_index = int(caption.get("_source_caption_index", caption_index))
        next_caption = dict(caption)
        next_caption["_source_caption_index"] = source_index_map.get(source_index, source_index)
        result.append(next_caption)
    return result


def _normalize_highlight_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", "", str(text or ""))
    cleaned = re.sub(r"[，,。！？!?；;：:“”\"'、（）()\[\]【】《》<>]", "", cleaned)
    cleaned = re.sub(r"的+$", "", cleaned)
    return cleaned[:max_chars]


def _highlight_core_term(text: str, max_chars: int) -> str:
    cleaned = _normalize_highlight_text(text, max(30, max_chars))
    if not cleaned:
        return ""

    exact_terms = list(dict.fromkeys(PRODUCT_HIGHLIGHT_TERMS + COLOR_TERMS + IMPACT_TERMS + DETAIL_TERMS + HIGHLIGHT_KEYWORDS))
    exact_matches = [
        term
        for term in exact_terms
        if term in cleaned and _visible_char_count(term) <= max_chars
    ]
    if exact_matches:
        exact_matches.sort(key=lambda term: (_highlight_term_score(term, cleaned, 0), len(term)), reverse=True)
        return exact_matches[0]

    suffix_pattern = r"[\u4e00-\u9fff]{1,4}(?:色|红|黄|蓝|白|黑|金|银|棕|包|剑|纹|层|链)"
    suffix_matches = [
        match.group(0)
        for match in re.finditer(suffix_pattern, cleaned)
        if _visible_char_count(match.group(0)) <= max_chars
    ]
    if suffix_matches:
        suffix_matches.sort(key=lambda term: (len(term), cleaned.rfind(term)), reverse=True)
        return suffix_matches[0]

    return cleaned[:max_chars]


def _is_valid_highlight_term(text: str) -> bool:
    cleaned = str(text or "")
    if not 2 <= _visible_char_count(cleaned) <= 4:
        return False
    if cleaned in HIGHLIGHT_WEAK_WORDS:
        return False
    if cleaned.startswith(HIGHLIGHT_WEAK_PREFIXES):
        return False
    if any(word in cleaned for word in HIGHLIGHT_BAD_SUBSTRINGS):
        return False
    if cleaned.endswith(("的一个", "的一款", "的这个", "的那个")):
        return False
    if re.search(r"的.{1,3}的", cleaned):
        return False
    if "的" in cleaned:
        return False
    if cleaned.count("的") >= 2:
        return False
    if re.search(r"(有|到|放|看|来|去|做|带|是|在|把|给|让|会|能|要|就)", cleaned):
        known_terms = set(PRODUCT_HIGHLIGHT_TERMS + COLOR_TERMS + IMPACT_TERMS + DETAIL_TERMS + HIGHLIGHT_KEYWORDS)
        if cleaned not in known_terms:
            return False
    if cleaned.endswith(("有", "到", "放", "看", "来", "去", "做", "带", "是", "在", "把", "给", "让")):
        return False
    return True


def _normalize_highlight_candidate(text: str, max_chars: int) -> str:
    cleaned = _normalize_highlight_text(text, max(30, max_chars))
    if not cleaned:
        return ""
    if _is_valid_highlight_term(cleaned):
        return cleaned
    core = _highlight_core_term(cleaned, max_chars)
    if core != cleaned and _is_valid_highlight_term(core):
        return core
    return ""


def _dedupe_highlight_candidates(candidates: Sequence[tuple[int, str]], caption_text: str, max_chars: int) -> List[tuple[int, str]]:
    deduped: List[tuple[int, str]] = []
    for score, raw_term in sorted(candidates, key=lambda item: (-item[0], -len(item[1]))):
        term = _normalize_highlight_candidate(raw_term, max_chars)
        if not term or term in HIGHLIGHT_STOPWORDS:
            continue
        normalized_score = score
        if term != raw_term:
            normalized_score += _highlight_term_score(term, caption_text, 0) + 4

        replaced = False
        should_skip = False
        for index, (kept_score, kept_term) in enumerate(deduped):
            if term == kept_term:
                should_skip = True
                break
            if term in kept_term or kept_term in term:
                term_score = _highlight_term_score(term, caption_text, 0)
                kept_term_score = _highlight_term_score(kept_term, caption_text, 0)
                if (term_score, len(term), normalized_score) > (kept_term_score, len(kept_term), kept_score):
                    deduped[index] = (normalized_score, term)
                    replaced = True
                else:
                    should_skip = True
                break
        if should_skip or replaced:
            continue
        deduped.append((normalized_score, term))
    deduped.sort(key=lambda item: (-item[0], -len(item[1])))
    return deduped


def _highlight_term_score(term: str, caption_text: str, caption_index: int) -> int:
    score = 0
    if term in PRODUCT_HIGHLIGHT_TERMS:
        score += 12
    if term in COLOR_TERMS:
        score += 12 + min(4, len(term))
    if term in IMPACT_TERMS:
        score += 7
    if term in DETAIL_TERMS:
        score += 8
    if term in ("压纹", "拉链", "隔层", "宝剑"):
        score += 5
    if term in ("包身", "设计"):
        score -= 3
    if term == "学院":
        score -= 4
    if term in caption_text[: max(5, len(caption_text) // 2)]:
        score += 2
    score += min(4, max(0, len(term) - 1))
    score -= caption_index // 8
    return score


def _is_high_priority_highlight(term: str, score: int) -> bool:
    return term in HIGH_PRIORITY_HIGHLIGHT_TERMS


def _highlight_score(text: str, index: int) -> int:
    cleaned = _normalize_highlight_text(text, 30)
    if not cleaned or cleaned in HIGHLIGHT_STOPWORDS:
        return -100

    visible_count = _visible_char_count(cleaned)
    score = 0
    if 3 <= visible_count <= 10:
        score += 6
    elif visible_count <= 2:
        score -= 6
    elif visible_count <= 14:
        score += 2
    else:
        score -= 4

    for keyword in HIGHLIGHT_KEYWORDS:
        if keyword in cleaned:
            score += 4
    if re.search(r"[0-9一二三四五六七八九十百千万亿]+", cleaned):
        score += 2
    if any(marker in cleaned for marker in ("的本质", "的核心", "的方法", "的关键")):
        score += 3
    score -= index // 8
    return score


def _extract_terms_from_text(text: str, max_chars: int, caption_index: int) -> List[tuple[int, str]]:
    cleaned = _normalize_highlight_text(text, 80)
    if not cleaned:
        return []

    candidates: List[tuple[int, str]] = []
    for term in PRODUCT_HIGHLIGHT_TERMS:
        if term in cleaned and _visible_char_count(term) <= max_chars and _is_valid_highlight_term(term):
            candidates.append((_highlight_term_score(term, cleaned, caption_index), term))

    for term in HIGHLIGHT_KEYWORDS:
        if term in cleaned and _visible_char_count(term) <= max_chars and _is_valid_highlight_term(term):
            candidates.append((_highlight_term_score(term, cleaned, caption_index), term))

    suffix_pattern = r"[\u4e00-\u9fff]{1,4}(?:色|红|黄|蓝|白|黑|金|银|棕|包|剑|纹|层|链)"
    for match in re.finditer(suffix_pattern, cleaned):
        term = match.group(0)
        if any(term != existing and term in existing for existing in PRODUCT_HIGHLIGHT_TERMS if existing in cleaned):
            continue
        if _is_valid_highlight_term(term) and term not in HIGHLIGHT_STOPWORDS:
            candidates.append((_highlight_term_score(term, cleaned, caption_index) - 1, term))

    return _dedupe_highlight_candidates(candidates, cleaned, max_chars)


def _extract_highlight_text(caption: dict, max_chars: int) -> str:
    explicit = caption.get("highlight") or caption.get("highlight_text") or caption.get("keyword")
    if explicit:
        return _normalize_highlight_text(str(explicit).split("|")[0], max_chars)

    terms = _extract_terms_from_text(str(caption.get("text", "")), max_chars, 0)
    if terms:
        return terms[0][1]
    return ""


def _extract_explicit_highlight_terms(caption: dict, max_chars: int) -> List[str]:
    raw_highlights = caption.get("highlights") or caption.get("highlight_terms")
    if raw_highlights is None:
        raw_highlights = caption.get("highlight") or caption.get("highlight_text") or caption.get("keyword")

    if isinstance(raw_highlights, str):
        candidates = re.split(r"[|,，、\n]+", raw_highlights)
    elif isinstance(raw_highlights, list):
        candidates = [str(item) for item in raw_highlights]
    else:
        candidates = []

    terms: List[str] = []
    normalized_candidates: List[tuple[int, str]] = []
    for candidate in candidates:
        normalized = _normalize_highlight_candidate(candidate, max_chars)
        if not normalized:
            continue
        normalized_candidates.append((_highlight_score(normalized, len(normalized_candidates)) + 20, normalized))
    for _, term in _dedupe_highlight_candidates(normalized_candidates, str(raw_highlights), max_chars):
        terms.append(term)
    return terms


def _random_between(min_value: float, max_value: float, randomizer: random.Random) -> float:
    if min_value == max_value:
        return min_value
    return round(randomizer.uniform(min_value, max_value), 2)


def _clamp_position(value: float, min_value: float, max_value: float) -> float:
    return round(max(min_value, min(max_value, value)), 2)


def _highlight_text_bounds(x: float, y: float, text: str, font_size: int) -> tuple[float, float, float, float]:
    text_width = max(220.0, min(680.0, len(str(text)) * font_size * 3.4))
    text_height = max(180.0, font_size * 5.6)
    return (
        x - text_width / 2,
        y - text_height / 2,
        x + text_width / 2,
        y + text_height / 2,
    )


def _bounds_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    padding: float = 80.0,
) -> bool:
    return not (
        first[2] + padding <= second[0]
        or second[2] + padding <= first[0]
        or first[3] + padding <= second[1]
        or second[3] + padding <= first[1]
    )


def _template_child_original_size(child: dict, highlight: dict) -> tuple[float, float]:
    original_size = child.get("original_size")
    if isinstance(original_size, list) and len(original_size) >= 2:
        try:
            width = abs(float(original_size[0]))
            height = abs(float(original_size[1]))
            if width > 0 and height > 0:
                return width, height
        except (TypeError, ValueError):
            pass

    if child.get("type") == "text":
        text = str(highlight.get("text") or "")
        font_size = float(highlight.get("font_size", 28) or 28)
        return max(180.0, len(text) * font_size * 2.4), max(72.0, font_size * 3.2)
    return 220.0, 220.0


def _template_child_bounds(child: dict, highlight: dict) -> tuple[float, float, float, float]:
    layout_bounds = child.get("_layout_bounds")
    if isinstance(layout_bounds, (list, tuple)) and len(layout_bounds) >= 4:
        try:
            transform_x = float(highlight.get("transform_x", 0.0))
            transform_y = float(highlight.get("transform_y", 0.0))
            return (
                transform_x + float(layout_bounds[0]),
                transform_y + float(layout_bounds[1]),
                transform_x + float(layout_bounds[2]),
                transform_y + float(layout_bounds[3]),
            )
        except (TypeError, ValueError):
            pass

    position = child.get("position") if isinstance(child.get("position"), list) else [0, 0, 0]
    scale = child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1]
    width, height = _template_child_original_size(child, highlight)
    try:
        center_x = float(highlight.get("transform_x", 0.0)) + float(position[0] if position else 0.0)
        center_y = float(highlight.get("transform_y", 0.0)) + float(position[1] if len(position) > 1 else 0.0)
        scale_x = abs(float(scale[0] if scale else 1.0))
        scale_y = abs(float(scale[1] if len(scale) > 1 else scale[0] if scale else 1.0))
    except (TypeError, ValueError):
        center_x = float(highlight.get("transform_x", 0.0))
        center_y = float(highlight.get("transform_y", 0.0))
        scale_x = 1.0
        scale_y = 1.0

    half_width = max(1.0, width * scale_x / 2)
    half_height = max(1.0, height * scale_y / 2)
    return center_x - half_width, center_y - half_height, center_x + half_width, center_y + half_height


def _estimate_template_height(children: Sequence[dict], highlight: dict) -> float:
    bounds = _merge_bounds([_template_child_bounds(child, highlight) for child in children])
    if not bounds:
        return 0.0
    return max(1.0, bounds[3] - bounds[1])


def _auto_text_template_scale(randomizer: random.Random, highlight: dict) -> float:
    configured = highlight.get("text_template_scale")
    if configured is not None:
        try:
            return max(0.1, min(2.0, float(configured)))
        except (TypeError, ValueError):
            pass
    return round(randomizer.uniform(TEXT_TEMPLATE_AUTO_SCALE_MIN, TEXT_TEMPLATE_AUTO_SCALE_MAX), 3)


def _template_primary_text_scale(children: Sequence[dict]) -> tuple[float, float]:
    text_scales: List[tuple[float, float]] = []
    for child in children:
        if child.get("type") != "text":
            continue
        scale = child.get("scale") if isinstance(child.get("scale"), list) else None
        if not scale:
            continue
        try:
            scale_x = abs(float(scale[0] if scale else 1.0)) or 1.0
            scale_y = abs(float(scale[1] if len(scale) > 1 else scale[0])) or scale_x
        except (TypeError, ValueError):
            continue
        text_scales.append((scale_x, scale_y))
    if not text_scales:
        return 1.0, 1.0
    return max(text_scales, key=lambda item: item[0] * item[1])


def _template_primary_text_child_index(children: Sequence[dict]) -> int | None:
    candidates: List[tuple[float, int]] = []
    for index, child in enumerate(children):
        if child.get("type") != "text":
            continue
        original_size = child.get("original_size") if isinstance(child.get("original_size"), list) else [500, 160]
        scale = child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1]
        try:
            width = abs(float(original_size[0] if original_size else 500.0))
            height = abs(float(original_size[1] if len(original_size) > 1 else 160.0))
            scale_x = abs(float(scale[0] if scale else 1.0)) or 1.0
            scale_y = abs(float(scale[1] if len(scale) > 1 else scale[0])) or scale_x
        except (TypeError, ValueError):
            width, height, scale_x, scale_y = 500.0, 160.0, 1.0, 1.0
        order_bonus = max(0.0, 1000.0 - float(child.get("order_in_layer") or 0))
        candidates.append((width * height * scale_x * scale_y + order_bonus, index))
    if not candidates:
        return None
    return max(candidates)[1]


def _template_child_name(child: dict) -> str:
    return str(child.get("name") or child.get("id") or "").strip()


def _template_layout_ref(value: str | None) -> str:
    return str(value or "").strip().lstrip("@")


def _template_child_local_bounds(child: dict) -> tuple[float, float, float, float]:
    position = child.get("position") if isinstance(child.get("position"), list) else [0, 0, 0]
    scale = child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1]
    original_size = child.get("original_size") if isinstance(child.get("original_size"), list) else [220, 220]
    try:
        center_x = float(position[0] if position else 0.0)
        center_y = float(position[1] if len(position) > 1 else 0.0)
        width = abs(float(original_size[0] if original_size else 220.0))
        height = abs(float(original_size[1] if len(original_size) > 1 else 220.0))
        scale_x = abs(float(scale[0] if scale else 1.0)) or 1.0
        scale_y = abs(float(scale[1] if len(scale) > 1 else scale[0])) or scale_x
    except (TypeError, ValueError):
        center_x, center_y = 0.0, 0.0
        width, height = 220.0, 220.0
        scale_x, scale_y = 1.0, 1.0
    half_width = max(1.0, width * scale_x / 2)
    half_height = max(1.0, height * scale_y / 2)
    return center_x - half_width, center_y - half_height, center_x + half_width, center_y + half_height


def _template_text_target_bounds(child: dict, text: str) -> tuple[float, float, float, float]:
    left, bottom, right, top = _template_child_local_bounds(child)
    position = child.get("position") if isinstance(child.get("position"), list) else [0, 0, 0]
    scale = child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1]
    original_size = child.get("original_size") if isinstance(child.get("original_size"), list) else [right - left, top - bottom]
    center_x = float(position[0] if position else 0.0)
    center_y = float(position[1] if len(position) > 1 else 0.0)
    scale_x = abs(float(scale[0] if scale else 1.0)) or 1.0
    reference_text = _template_rich_text_plain_text(child)
    font_size = _template_text_font_size(child, 28.0)
    target_width = _estimate_text_visual_width(text, font_size, original_size, reference_text)
    try:
        original_width = abs(float(original_size[0] if original_size else target_width))
    except (TypeError, ValueError):
        original_width = target_width
    min_width = max(60.0, original_width)
    max_width = max(min_width, original_width * 1.8)
    target_width = max(min_width, min(max_width, target_width))
    half_width = target_width * scale_x / 2
    return center_x - half_width, bottom, center_x + half_width, top


def _template_bounds_center(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    return (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2


def _template_apply_bounds_to_child(child: dict, bounds: tuple[float, float, float, float]) -> dict:
    laid_out = dict(child)
    center_x, center_y = _template_bounds_center(bounds)
    position = list(child.get("position") if isinstance(child.get("position"), list) else [0, 0, 0])
    while len(position) < 3:
        position.append(0)
    position[0] = center_x
    position[1] = center_y
    laid_out["position"] = position
    laid_out["_layout_bounds"] = tuple(round(value, 4) for value in bounds)
    return laid_out


def _template_resize_child_to_bounds(child: dict, bounds: tuple[float, float, float, float]) -> dict:
    laid_out = _template_apply_bounds_to_child(child, bounds)
    original_size = child.get("original_size") if isinstance(child.get("original_size"), list) else None
    scale = list(child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1])
    if original_size and len(original_size) >= 2:
        width = max(1.0, abs(float(original_size[0] or 1.0)))
        height = max(1.0, abs(float(original_size[1] or 1.0)))
        while len(scale) < 3:
            scale.append(1)
        scale[0] = max(0.01, (bounds[2] - bounds[0]) / width)
        scale[1] = max(0.01, (bounds[3] - bounds[1]) / height)
        laid_out["scale"] = scale
    return laid_out


def _template_visible_children_for_highlight(children: Sequence[dict]) -> List[dict]:
    primary_text_index = _template_primary_text_child_index(children)
    visible_children: List[dict] = []
    for index, child in enumerate(children):
        if child.get("type") == "text" and primary_text_index is not None and index != primary_text_index:
            continue
        visible_children.append(child)
    return visible_children


def _scaled_template_children(children: Sequence[dict], target_scale: float) -> List[dict]:
    base_text_scale_x, base_text_scale_y = _template_primary_text_scale(children)
    uniform_factor = target_scale / max(base_text_scale_x, base_text_scale_y, 0.001)
    scaled_children: List[dict] = []
    for child in children:
        scaled = dict(child)
        position = child.get("position") if isinstance(child.get("position"), list) else None
        if position:
            scaled["position"] = [
                float(value) * uniform_factor if index < 2 else value
                for index, value in enumerate(position)
            ]
        scale = child.get("scale") if isinstance(child.get("scale"), list) else None
        if scale:
            scaled["scale"] = [
                float(value) * uniform_factor if index < 2 else value
                for index, value in enumerate(scale)
            ]
        layout_bounds = child.get("_layout_bounds")
        if isinstance(layout_bounds, (list, tuple)) and len(layout_bounds) >= 4:
            scaled["_layout_bounds"] = tuple(
                float(value) * uniform_factor
                for value in layout_bounds
            )
        scaled_children.append(scaled)
    return scaled_children


def _merge_bounds(bounds_list: Sequence[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    if not bounds_list:
        return None
    return (
        min(bounds[0] for bounds in bounds_list),
        min(bounds[1] for bounds in bounds_list),
        max(bounds[2] for bounds in bounds_list),
        max(bounds[3] for bounds in bounds_list),
    )


def _shift_highlight_to_keep_template_visible(script, highlight: dict, children: Sequence[dict]) -> dict:
    bounds = _merge_bounds([_template_child_bounds(child, highlight) for child in children])
    if not bounds:
        return highlight

    min_x = -script.width / 2 + TEXT_TEMPLATE_SAFE_MARGIN_X
    max_x = script.width / 2 - TEXT_TEMPLATE_SAFE_MARGIN_X
    min_y = -script.height / 2 + TEXT_TEMPLATE_SAFE_MARGIN_Y
    max_y = script.height / 2 - TEXT_TEMPLATE_SAFE_MARGIN_Y

    shift_x = 0.0
    shift_y = 0.0
    if bounds[0] < min_x:
        shift_x = min_x - bounds[0]
    elif bounds[2] > max_x:
        shift_x = max_x - bounds[2]
    if bounds[1] < min_y:
        shift_y = min_y - bounds[1]
    elif bounds[3] > max_y:
        shift_y = max_y - bounds[3]

    if shift_x == 0.0 and shift_y == 0.0:
        return highlight
    adjusted = dict(highlight)
    adjusted["transform_x"] = round(float(highlight.get("transform_x", 0.0)) + shift_x, 2)
    adjusted["transform_y"] = round(float(highlight.get("transform_y", 0.0)) + shift_y, 2)
    return adjusted


def _align_highlight_template_to_side(script, highlight: dict, children: Sequence[dict]) -> dict:
    current_x = float(highlight.get("transform_x", 0.0))
    current_y = float(highlight.get("transform_y", 0.0))
    top_y_max = script.height / 2
    top_y_min = script.height / 2 - script.height * 0.70
    side_seed = f"{highlight.get('_source_caption_index', '')}:{highlight.get('text', '')}:{current_x:.2f}:{current_y:.2f}"
    randomizer = random.Random(side_seed)
    target_x = randomizer.uniform(-782.0, -600.0) if current_x <= 0 else randomizer.uniform(600.0, 780.0)
    target_y = randomizer.uniform(top_y_min, top_y_max)
    if abs(target_x - current_x) < 1.0 and abs(target_y - current_y) < 1.0:
        return highlight

    adjusted = dict(highlight)
    adjusted["transform_x"] = round(target_x, 2)
    adjusted["transform_y"] = round(target_y, 2)
    return adjusted


def _shift_highlight_template_inside_top_regions(script, highlight: dict, children: Sequence[dict]) -> dict:
    current_x = float(highlight.get("transform_x", 0.0))
    current_y = float(highlight.get("transform_y", 0.0))
    top_y_max = script.height / 2
    top_y_min = script.height / 2 - script.height * 0.70
    x_min, x_max = (-782.0, -600.0) if current_x <= 0 else (600.0, 780.0)
    target_x = _clamp_position(current_x, x_min, x_max)
    target_y = _clamp_position(current_y, top_y_min, top_y_max)
    if abs(target_x - current_x) < 1.0 and abs(target_y - current_y) < 1.0:
        return highlight

    adjusted = dict(highlight)
    adjusted["transform_x"] = round(target_x, 2)
    adjusted["transform_y"] = round(target_y, 2)
    return adjusted


def _align_highlight_template_to_edge(script, highlight: dict, children: Sequence[dict]) -> dict:
    bounds = _merge_bounds([_template_child_bounds(child, highlight) for child in children])
    if not bounds:
        return highlight

    min_x = -script.width / 2 + TEXT_TEMPLATE_SAFE_MARGIN_X
    max_x = script.width / 2 - TEXT_TEMPLATE_SAFE_MARGIN_X
    current_x = float(highlight.get("transform_x", 0.0))
    target_edge = min_x if current_x <= 0 else max_x
    current_edge = bounds[0] if current_x <= 0 else bounds[2]
    shift_x = target_edge - current_edge
    if abs(shift_x) < 1.0:
        return highlight

    adjusted = dict(highlight)
    adjusted["transform_x"] = round(current_x + shift_x, 2)
    return adjusted


def _time_ranges_overlap(first: dict, second: dict) -> bool:
    return int(first.get("start", 0)) < int(second.get("end", 0)) and int(second.get("start", 0)) < int(first.get("end", 0))


def _slot_distance_score(position: tuple[float, float], placed_highlights: Sequence[dict]) -> float:
    if not placed_highlights:
        return 0.0
    return min(
        abs(position[1] - float(placed.get("transform_y", 0.0))) * 2.2
        + abs(position[0] - float(placed.get("transform_x", 0.0)))
        for placed in placed_highlights
    )


def _spread_highlight_position(
    offset: int,
    req: SmartPackagingRequest,
    randomizer: random.Random,
    text: str = "",
    placed_highlights: Sequence[dict] = (),
) -> tuple[float, float]:
    x_min = req.caption.highlight_transform_x_min
    x_max = req.caption.highlight_transform_x_max
    y_min = req.caption.highlight_transform_y_min
    y_max = req.caption.highlight_transform_y_max
    x_span = max(1.0, x_max - x_min)
    y_span = max(1.0, y_max - y_min)
    left_min, left_max = -782.0, -600.0
    right_min, right_max = 600.0, 780.0
    if x_min < -600.0 or x_max > 600.0:
        left_min = max(x_min, left_min)
        left_max = min(-600.0, left_max)
        right_min = max(600.0, right_min)
        right_max = min(x_max, right_max)
    if left_min > left_max:
        left_min, left_max = x_min, min(x_min + x_span * 0.25, x_max)
    if right_min > right_max:
        right_min, right_max = max(x_max - x_span * 0.25, x_min), x_max

    slots = (
        ((left_min + left_max) / 2, y_min + y_span * 0.08),
        ((right_min + right_max) / 2, y_min + y_span * 0.46),
        ((left_min + left_max) / 2, y_min + y_span * 0.42),
        ((right_min + right_max) / 2, y_min + y_span * 0.60),
        ((left_min + left_max) / 2, y_min + y_span * 0.72),
        ((right_min + right_max) / 2, y_min + y_span * 0.45),
    )
    fallback_position = None
    slot_indexes = list(range(len(slots)))
    if placed_highlights:
        slot_indexes.sort(key=lambda index: _slot_distance_score(slots[index], placed_highlights), reverse=True)
    else:
        slot_indexes = slot_indexes[offset:] + slot_indexes[:offset]

    for slot_index in slot_indexes:
        base_x, base_y = slots[slot_index]
        jitter_x = randomizer.uniform(-x_span * 0.015, x_span * 0.015)
        jitter_y = randomizer.uniform(-y_span * 0.012, y_span * 0.012)
        clamp_x_min, clamp_x_max = (left_min, left_max) if base_x < 0 else (right_min, right_max)
        position = (
            _clamp_position(base_x + jitter_x, clamp_x_min, clamp_x_max),
            _clamp_position(base_y + jitter_y, y_min, y_max),
        )
        if fallback_position is None:
            fallback_position = position
        current_bounds = _highlight_text_bounds(position[0], position[1], text, req.caption.highlight_font_size)
        if not any(
            _bounds_overlap(
                current_bounds,
                _highlight_text_bounds(
                    float(placed.get("transform_x", 0.0)),
                    float(placed.get("transform_y", 0.0)),
                    str(placed.get("text", "")),
                    int(placed.get("font_size", req.caption.highlight_font_size)),
                ),
            )
            for placed in placed_highlights
        ):
            return position

    return fallback_position or (0.0, 0.0)


def _overlapping_placed_highlights(highlight: dict, placed_highlights: Sequence[dict]) -> List[dict]:
    return [placed for placed in placed_highlights if _time_ranges_overlap(highlight, placed)]


def _choose_highlight_text_template(randomizer: random.Random) -> dict:
    return dict(randomizer.choice(HIGHLIGHT_TEXT_TEMPLATES))


def _safe_int(value, default: int = 9999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_text_template_draft_dir(path: str | None = None) -> str:
    if path:
        return os.path.expanduser(path)
    return DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR


def _resolve_artist_effect_cache_dir(path: str | None = None) -> str:
    if path:
        return os.path.expanduser(path)
    return DEFAULT_JIANYING_ARTIST_EFFECT_CACHE_DIR


def _resolve_effect_cache_dir(path: str | None = None) -> str:
    if path:
        return os.path.expanduser(path)
    return DEFAULT_JIANYING_EFFECT_CACHE_DIR


def _find_artist_effect_package(material_id: str, cache_dir: str) -> pathlib.Path | None:
    material_dir = pathlib.Path(cache_dir) / material_id
    if not material_dir.exists():
        return None

    content_candidates = sorted(material_dir.glob("*/content.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if content_candidates:
        return content_candidates[0].parent
    return None


def _extract_text_template_effect_ids(content: dict) -> List[str]:
    effect_ids: List[str] = []

    def walk(node):
        if isinstance(node, dict):
            text_params = node.get("text_params")
            if isinstance(text_params, dict):
                rich_text = str(text_params.get("richText") or "")
                for match in re.finditer(r'<effectStyle\s+id="([^"]+)"', rich_text):
                    effect_id = match.group(1).strip()
                    if effect_id and effect_id not in effect_ids:
                        effect_ids.append(effect_id)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(content)
    return effect_ids


def _load_text_template_cache_info(material_id: str, cache_dir: str) -> dict:
    package_dir = _find_artist_effect_package(material_id, cache_dir)
    if not package_dir:
        return {"effect_ids": [], "default_texts": []}

    effect_ids: List[str] = []
    default_texts: List[str] = []

    content_path = package_dir / "content.json"
    if content_path.exists():
        try:
            with content_path.open("r", encoding="utf-8") as file:
                content = json.load(file)
            effect_ids = _extract_text_template_effect_ids(content)
        except Exception as exc:
            logger.warning(f"Failed to read text template content.json, material_id={material_id}: {exc}")

    extra_path = package_dir / "extra.json"
    if extra_path.exists():
        try:
            with extra_path.open("r", encoding="utf-8") as file:
                extra = json.load(file)
            default_texts = [str(item) for item in extra.get("texts", []) if str(item).strip()]
        except Exception as exc:
            logger.warning(f"Failed to read text template extra.json, material_id={material_id}: {exc}")

    return {"package_dir": str(package_dir), "effect_ids": effect_ids, "default_texts": default_texts}


def _load_jianying_text_template_entries(
    text_template_draft_dir: str | None = None,
    artist_effect_cache_dir: str | None = None,
) -> List[dict]:
    draft_dir = _resolve_text_template_draft_dir(text_template_draft_dir)
    cache_dir = _resolve_artist_effect_cache_dir(artist_effect_cache_dir)
    key_value_path = os.path.join(draft_dir, "key_value.json")
    if not os.path.exists(key_value_path):
        logger.warning(f"Jianying text template key_value.json not found: {key_value_path}")
        return []

    try:
        with open(key_value_path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except Exception as exc:
        logger.warning(f"Failed to load Jianying text template key_value.json: {exc}")
        return []

    entries_by_material_id: dict[str, dict] = {}
    for key, value in raw_data.items():
        if not isinstance(value, dict):
            continue
        if value.get("materialSubcategory") != "text_template":
            continue

        material_id = str(value.get("materialId") or key or "").strip()
        name = str(value.get("materialName") or "").strip()
        if not material_id or not name:
            continue
        if any(keyword in name for keyword in EXCLUDED_JIANYING_TEXT_TEMPLATE_KEYWORDS):
            continue

        rank = _safe_int(value.get("rank"))
        existing = entries_by_material_id.get(material_id)
        if existing and existing["rank"] <= rank and existing.get("segment_id"):
            continue

        cache_info = _load_text_template_cache_info(material_id, cache_dir)
        effect_ids = cache_info["effect_ids"]
        entries_by_material_id[material_id] = {
            "name": name,
            "material_id": material_id,
            "segment_id": str(value.get("segmentId") or ""),
            "package_dir": cache_info.get("package_dir", ""),
            "effect_id": effect_ids[0] if effect_ids else "",
            "effect_ids": effect_ids,
            "is_vip": str(value.get("is_vip", "0")) == "1",
            "rank": rank,
            "default_texts": cache_info["default_texts"],
        }

    deduped_entries: dict[tuple[str, str, str], dict] = {}
    for entry in entries_by_material_id.values():
        dedupe_key = (
            str(entry.get("name") or "").strip(),
            str(entry.get("package_dir") or "").strip(),
            str(entry.get("effect_id") or "").strip(),
        )
        existing = deduped_entries.get(dedupe_key)
        if existing and existing["rank"] <= entry["rank"]:
            continue
        deduped_entries[dedupe_key] = entry

    return sorted(deduped_entries.values(), key=lambda item: (item["rank"], item["name"]))


def _cache_path_parts(path_value: str) -> tuple[str, str, list[str]] | None:
    if not path_value:
        return None
    parts = pathlib.Path(path_value).expanduser().parts
    for index, part in enumerate(parts):
        if part in {"artistEffect", "effect"} and index + 1 < len(parts):
            return part, parts[index + 1], list(parts[index + 2:])
    return None


def _parse_template_depends(depends_path: pathlib.Path) -> List[dict]:
    if not depends_path.is_file():
        return []
    records: dict[str, dict] = {}
    try:
        lines = depends_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        logger.warning(f"Failed to read text template depends: {depends_path}, error={exc}")
        return []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("[") or line.startswith("size="):
            continue
        if "\\" not in line or "=" not in line:
            continue
        index, rest = line.split("\\", 1)
        key, value = rest.split("=", 1)
        records.setdefault(index, {})[key.strip()] = value.strip()
    return [records[key] for key in sorted(records, key=lambda item: int(item) if item.isdigit() else item)]


def _dependency_local_path(path_value: str, artist_effect_cache_dir: str, effect_cache_dir: str) -> str:
    parsed = _cache_path_parts(path_value)
    if not parsed:
        return path_value if os.path.exists(path_value) else ""
    bucket, key, rest = parsed
    base_dir = artist_effect_cache_dir if bucket == "artistEffect" else effect_cache_dir
    candidate = pathlib.Path(base_dir) / key
    if rest:
        candidate = candidate.joinpath(*rest)
    if candidate.exists():
        return localize_jianying_cache_path(str(candidate)) or str(candidate)
    original = pathlib.Path(path_value).expanduser()
    if original.exists():
        return localize_jianying_cache_path(str(original)) or str(original)
    return ""


def _build_text_template_dependency_index(
    package_dir: str,
    artist_effect_cache_dir: str | None = None,
    effect_cache_dir: str | None = None,
) -> dict[str, dict]:
    depends_path = pathlib.Path(package_dir) / "depends"
    artist_dir = _resolve_artist_effect_cache_dir(artist_effect_cache_dir)
    effect_dir = _resolve_effect_cache_dir(effect_cache_dir)
    index: dict[str, dict] = {}
    for record in _parse_template_depends(depends_path):
        resource_id = str(record.get("id") or "").strip()
        if not resource_id:
            continue
        raw_path = str(record.get("path") or "").strip()
        panel = str(record.get("panel") or "").strip()
        index[resource_id] = {
            "id": resource_id,
            "panel": panel,
            "path": _dependency_local_path(raw_path, artist_dir, effect_dir),
            "source_path": raw_path,
        }
    return index


def _choose_jianying_text_template_effect(
    template_entries: Sequence[dict],
    selected_names: Sequence[str],
    randomizer: random.Random,
    used_effect_ids: set[str] | None = None,
) -> str | None:
    if not template_entries:
        return None

    selected = {name.strip() for name in selected_names if name.strip()}
    candidates = [
        entry for entry in template_entries
        if entry.get("effect_id") and (not selected or entry.get("name") in selected)
    ]
    if not candidates:
        candidates = [entry for entry in template_entries if entry.get("effect_id")]
    if not candidates:
        return None
    unused_candidates = [
        entry for entry in candidates
        if str(entry.get("effect_id") or "") not in (used_effect_ids or set())
    ]
    selected_entry = randomizer.choice(unused_candidates or candidates)
    effect_id = str(selected_entry.get("effect_id") or "")
    if effect_id and used_effect_ids is not None:
        used_effect_ids.add(effect_id)
    return effect_id or None


def _choose_jianying_text_template_entry(
    template_entries: Sequence[dict],
    selected_names: Sequence[str],
    randomizer: random.Random,
    used_material_ids: set[str] | None = None,
) -> dict | None:
    if not template_entries:
        return None
    selected = {name.strip() for name in selected_names if name.strip()}
    candidates = [
        entry for entry in template_entries
        if entry.get("package_dir") and (not selected or entry.get("name") in selected)
    ]
    if not candidates:
        candidates = [entry for entry in template_entries if entry.get("package_dir")]
    if not candidates:
        return None
    unused_candidates = [
        entry for entry in candidates
        if str(entry.get("material_id") or entry.get("effect_id") or entry.get("name") or "") not in (used_material_ids or set())
    ]
    selected_entry = dict(randomizer.choice(unused_candidates or candidates))
    template_key = str(selected_entry.get("material_id") or selected_entry.get("effect_id") or selected_entry.get("name") or "")
    if template_key and used_material_ids is not None:
        used_material_ids.add(template_key)
    return selected_entry


class _RawTextTemplateAnimation:
    def __init__(self, animation_data: dict, duration_scale: float, dependency_index: dict[str, dict] | None = None):
        self.name = str(animation_data.get("anim_resource_id") or "")
        self.effect_id = str(animation_data.get("anim_resource_id") or "")
        self.resource_id = str(animation_data.get("anim_resource_id") or "")
        dependency = (dependency_index or {}).get(self.resource_id, {})
        self.panel = str(dependency.get("panel") or "")
        self.path = str(dependency.get("path") or "")
        self.animation_type = _normalize_template_animation_type(animation_data.get("anim_type"))
        self.start = max(0, int(float(animation_data.get("anim_start_time") or 0) * 1_000_000 * duration_scale))
        self.duration = max(1, int(float(animation_data.get("duration") or 0) * 1_000_000 * duration_scale))

    def export_json(self) -> dict:
        data = {
            "anim_adjust_params": None,
            "platform": "all",
            "panel": self.panel,
            "material_type": "sticker",
            "name": self.name,
            "id": self.effect_id,
            "type": self.animation_type,
            "resource_id": self.resource_id,
            "start": self.start,
            "duration": self.duration,
        }
        if self.path:
            data["path"] = self.path
        return data


def _normalize_template_animation_type(anim_type) -> str:
    value = str(anim_type or "in").strip()
    if value in {"in", "out", "loop"}:
        return value
    return "loop" if "loop" in value else "in"


def _segment_animations_from_template(
    child: dict,
    duration_scale: float,
    dependency_index: dict[str, dict] | None = None,
) -> SegmentAnimations | None:
    anims = child.get("anims")
    if not isinstance(anims, list) or not anims:
        return None
    segment_animations = SegmentAnimations()
    for anim in anims:
        if not isinstance(anim, dict) or not anim.get("anim_resource_id"):
            continue
        segment_animations.animations.append(_RawTextTemplateAnimation(anim, duration_scale, dependency_index))
    if not segment_animations.animations:
        return None
    return segment_animations


def _replace_rich_text_text(rich_text: str, text: str) -> str:
    if not rich_text:
        return text
    return re.sub(r">(?:\[[^\]]+\]|[^<>]*)</font>", f">{text}</font>", rich_text, count=1)


def _extract_font_id_from_rich_text(rich_text: str) -> str:
    match = re.search(r'<font\s+id="([^"]+)"', rich_text or "")
    return match.group(1) if match else ""


def _extract_size_from_rich_text(rich_text: str) -> float | None:
    match = re.search(r"<size=([0-9]+(?:\.[0-9]+)?)>", rich_text or "")
    if not match:
        return None
    try:
        size = float(match.group(1))
    except ValueError:
        return None
    return size if size > 0 else None


def _extract_color_from_rich_text(rich_text: str) -> List[float] | None:
    match = re.search(r"<color=\(([^)]+)\)>", rich_text or "")
    if not match:
        return None
    try:
        values = [float(item.strip()) for item in match.group(1).split(",")]
    except ValueError:
        return None
    if len(values) >= 3:
        return [max(0.0, min(1.0, values[0])), max(0.0, min(1.0, values[1])), max(0.0, min(1.0, values[2]))]
    return None


def _template_text_color(child: dict, rich_text: str) -> List[float]:
    rich_text_color = _extract_color_from_rich_text(rich_text)
    if rich_text_color:
        return rich_text_color
    selected = child.get("text_params", {}).get("selectedColor")
    if isinstance(selected, list) and len(selected) >= 3 and any(float(item or 0) > 0 for item in selected[:3]):
        return [max(0.0, min(1.0, float(selected[0]))), max(0.0, min(1.0, float(selected[1]))), max(0.0, min(1.0, float(selected[2])))]
    return [1.0, 1.0, 1.0]


def _template_text_font_size(child: dict, fallback_font_size: float) -> float:
    text_params = child.get("text_params") or {}
    template_size = _extract_size_from_rich_text(str(text_params.get("richText") or ""))
    if template_size:
        return template_size
    return fallback_font_size


def _template_text_material_content(
    child: dict,
    text: str,
    font_size: float | None = None,
    dependency_index: dict[str, dict] | None = None,
) -> dict:
    text_params = child.get("text_params") or {}
    rich_text = _replace_rich_text_text(str(text_params.get("richText") or ""), text)
    effect_id = ""
    effect_match = re.search(r'<effectStyle\s+id="([^"]+)"', rich_text)
    if effect_match:
        effect_id = effect_match.group(1)
    resolved_font_size = font_size if font_size is not None else _template_text_font_size(child, 28.0)

    style = {
        "fill": {
            "alpha": float(text_params.get("globalAlpha", 1) or 1),
            "content": {
                    "render_type": "solid",
                    "solid": {
                        "alpha": 1.0,
                        "color": _template_text_color(child, rich_text),
                    },
                },
        },
        "range": [0, len(text.encode("utf-16-le"))],
        "size": resolved_font_size,
        "bold": False,
        "italic": False,
        "underline": False,
        "strokes": [],
    }
    font_id = _extract_font_id_from_rich_text(rich_text)
    if font_id:
        font_dependency = (dependency_index or {}).get(font_id, {})
        style["font"] = {"id": font_id, "path": str(font_dependency.get("path") or "")}
    if effect_id:
        effect_dependency = (dependency_index or {}).get(effect_id, {})
        style["effectStyle"] = {"id": effect_id, "path": str(effect_dependency.get("path") or "")}

    return {
        "styles": [style],
        "text": text,
    }


def _template_text_effect_ids_for_child(child: dict) -> List[str]:
    text_params = child.get("text_params") or {}
    rich_text = str(text_params.get("richText") or "")
    return [match.group(1) for match in re.finditer(r'<effectStyle\s+id="([^"]+)"', rich_text)]


def _template_rich_text_plain_text(child: dict) -> str:
    text_params = child.get("text_params") or {}
    rich_text = str(text_params.get("richText") or "")
    match = re.search(r">(?:\[([^\]]+)\]|([^<>]*))</font>", rich_text)
    if not match:
        return ""
    return str(match.group(1) or match.group(2) or "")


def _estimate_text_visual_width(
    text: str,
    font_size: float,
    original_size: Sequence[float] | None = None,
    reference_text: str = "",
) -> float:
    visible_count = max(1, _visible_char_count(str(text or "")))
    if original_size and len(original_size) >= 2:
        try:
            original_width = abs(float(original_size[0]))
        except (TypeError, ValueError):
            original_width = 0.0
        if original_width > 0:
            reference_count = max(1, _visible_char_count(str(reference_text or text or "")))
            return original_width * visible_count / reference_count
    return visible_count * max(1.0, font_size) * 1.25


def _template_child_position(child: dict) -> tuple[float, float]:
    position = child.get("position") if isinstance(child.get("position"), list) else []
    try:
        return (
            float(position[0] if len(position) > 0 else 0.0),
            float(position[1] if len(position) > 1 else 0.0),
        )
    except (TypeError, ValueError):
        return 0.0, 0.0


def _template_child_scale(child: dict) -> tuple[float, float]:
    scale = child.get("scale") if isinstance(child.get("scale"), list) else []
    try:
        scale_x = abs(float(scale[0] if len(scale) > 0 else 1.0)) or 1.0
        scale_y = abs(float(scale[1] if len(scale) > 1 else scale_x)) or scale_x
    except (TypeError, ValueError):
        scale_x, scale_y = 1.0, 1.0
    return scale_x, scale_y


def _layout_template_children_for_text(children: Sequence[dict], text: str) -> List[dict]:
    return [dict(child) for child in children]


def _find_template_child_by_name(children: Sequence[dict], name: str) -> dict:
    for child in children:
        if _template_child_name(child) == name:
            return child
    return {}


def _template_child_timerange(highlight: dict, child: dict, duration_scale: float) -> Timerange:
    base_start = int(highlight["start"])
    base_duration = max(1, int(highlight["end"]) - base_start)
    child_start = max(0, int(float(child.get("start_time") or 0) * 1_000_000 * duration_scale))
    child_duration = max(1, int(float(child.get("duration") or 0) * 1_000_000 * duration_scale))
    if child_start >= base_duration:
        child_start = 0
    child_duration = min(child_duration, base_duration - child_start)
    return Timerange(base_start + child_start, max(1, child_duration))


def _template_clip_settings(script, highlight: dict, child: dict) -> ClipSettings:
    position = child.get("position") if isinstance(child.get("position"), list) else [0, 0, 0]
    scale = child.get("scale") if isinstance(child.get("scale"), list) else [1, 1, 1]
    rotation = child.get("rotation") if isinstance(child.get("rotation"), list) else [0, 0, 0]
    transform_x = float(highlight.get("transform_x", 0.0)) + float(position[0] if position else 0.0)
    transform_y = float(highlight.get("transform_y", 0.0)) + float(position[1] if len(position) > 1 else 0.0)
    return ClipSettings(
        alpha=float(child.get("sticker_alpha", 1.0) if child.get("type") == "sticker" else 1.0),
        rotation=float(rotation[2] if len(rotation) > 2 else 0.0),
        scale_x=float(scale[0] if scale else 1.0),
        scale_y=float(scale[1] if len(scale) > 1 else scale[0] if scale else 1.0),
        transform_x=transform_x / script.width,
        transform_y=transform_y / script.height,
    )


def _load_template_content(package_dir: str) -> dict | None:
    content_path = pathlib.Path(package_dir) / "content.json"
    if not content_path.exists():
        return None
    try:
        with content_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        logger.warning(f"Failed to load text template content: {content_path}, error={exc}")
        return None


def _add_segment_animations(script, segment, animations: SegmentAnimations | None) -> None:
    if not animations:
        return
    segment.animations_instance = animations
    segment.extra_material_refs.append(animations.animation_id)
    script.materials.animations.append(animations)


def _add_template_text_effect_refs(script, segment: TextSegment, child: dict) -> None:
    for effect_id in _template_text_effect_ids_for_child(child):
        text_effect = TextEffect(effect_id, effect_id)
        segment.extra_material_refs.append(text_effect.global_id)
        script.materials.filters.append(text_effect)


def _add_template_text_effect_refs_with_paths(
    script,
    segment: TextSegment,
    child: dict,
    dependency_index: dict[str, dict] | None = None,
) -> None:
    for effect_id in _template_text_effect_ids_for_child(child):
        dependency = (dependency_index or {}).get(effect_id, {})
        text_effect = TextEffect(effect_id, effect_id)
        if dependency.get("path"):
            original_export_json = text_effect.export_json

            def export_json(original_export_json=original_export_json, path=str(dependency.get("path") or "")):
                data = original_export_json()
                data["path"] = path
                return data

            text_effect.export_json = export_json
        segment.extra_material_refs.append(text_effect.global_id)
        script.materials.filters.append(text_effect)


TEXT_TEMPLATE_TRACK_LANE_STRIDE = 1000
TEXT_TEMPLATE_TRACK_TYPE_NAMES = ("text", "sticker")


def _text_template_track_name(layer_index: int, child_type: str, lane_index: int = 0) -> str:
    suffix = "" if lane_index == 0 else f"_{lane_index + 1}"
    return f"text_template_layer_{layer_index}_{child_type}{suffix}"


def _text_template_track_render_base(script) -> int:
    render_base = getattr(script, "_smart_packaging_text_template_render_base", None)
    if render_base is None:
        render_base = script.next_track_render_index()
        setattr(script, "_smart_packaging_text_template_render_base", render_base)
    return int(render_base)


def _text_template_track_render_index(script, layer_index: int, lane_index: int = 0) -> int:
    return _text_template_track_render_base(script) + lane_index * TEXT_TEMPLATE_TRACK_LANE_STRIDE + layer_index


def _track_has_time_overlap(track, start: int, end: int) -> bool:
    return any(start < int(segment.end) and end > int(segment.start) for segment in getattr(track, "segments", []))


def _text_template_lane_has_overlap(script, lane_index: int, layer_index: int, start: int, end: int) -> bool:
    for child_type in TEXT_TEMPLATE_TRACK_TYPE_NAMES:
        track = script.tracks.get(_text_template_track_name(layer_index, child_type, lane_index))
        if track and _track_has_time_overlap(track, start, end):
            return True
    return False


def _choose_text_template_track_lane(script, layer_timeranges: Sequence[tuple[int, object]]) -> int:
    lane_index = 0
    while True:
        if all(
            not _text_template_lane_has_overlap(
                script,
                lane_index,
                layer_index,
                int(timerange.start),
                int(timerange.end),
            )
            for layer_index, timerange in layer_timeranges
        ):
            return lane_index
        lane_index += 1


def _ensure_text_template_track(script, track_type, layer_index: int, child_type: str, lane_index: int = 0) -> str:
    track_name = _text_template_track_name(layer_index, child_type, lane_index)
    if track_name not in script.tracks:
        script.add_track(
            track_type=track_type,
            track_name=track_name,
            absolute_index=_text_template_track_render_index(script, layer_index, lane_index),
        )
    return track_name


def _add_text_template_layers_to_draft(
    draft_url: str,
    highlight: dict,
    template_entry: dict,
) -> List[str]:
    draft_id = helper.get_url_param(draft_url, "draft_id")
    if not draft_id or draft_id not in DRAFT_CACHE:
        return []

    script = DRAFT_CACHE[draft_id]
    package_dir = str(template_entry.get("package_dir") or "")
    content = _load_template_content(package_dir)
    children = content.get("children") if isinstance(content, dict) else None
    if not isinstance(children, list) or not children:
        return []
    dependency_index = _build_text_template_dependency_index(package_dir)

    template_duration = max(
        [float(child.get("start_time") or 0) + float(child.get("duration") or 0) for child in children if isinstance(child, dict)] or [1.0]
    )
    highlight_start = int(highlight["start"])
    source_end = int(highlight.get("_source_caption_end", highlight["end"]))
    desired_end = max(
        int(highlight["end"]),
        min(source_end, highlight_start + TEXT_TEMPLATE_MIN_DISPLAY_DURATION),
    )
    if desired_end <= highlight_start:
        desired_end = int(highlight["end"])
    if desired_end > int(highlight["end"]):
        highlight = dict(highlight)
        highlight["end"] = min(desired_end, highlight_start + TEXT_TEMPLATE_MAX_DISPLAY_DURATION)
    highlight_duration_seconds = max(0.001, (int(highlight["end"]) - highlight_start) / 1_000_000)
    duration_scale = highlight_duration_seconds / max(0.001, template_duration)

    ordered_children = [
        child for child in children
        if isinstance(child, dict) and child.get("type") in {"text", "sticker"} and child.get("visible", True)
    ]
    ordered_children.sort(key=lambda child: int(child.get("order_in_layer") or 0))
    ordered_children = _template_visible_children_for_highlight(ordered_children)
    ordered_children = _layout_template_children_for_text(ordered_children, str(highlight.get("text") or ""))
    seed_text = f"{highlight.get('_source_caption_index', '')}:{highlight.get('text', '')}:{template_entry.get('material_id', '')}"
    template_randomizer = random.Random(seed_text)
    template_scale = _auto_text_template_scale(template_randomizer, highlight)
    ordered_children = _scaled_template_children(ordered_children, template_scale)
    highlight = _align_highlight_template_to_side(script, highlight, ordered_children)
    highlight = _shift_highlight_template_inside_top_regions(script, highlight, ordered_children)

    layer_timeranges = [
        (layer_index, _template_child_timerange(highlight, child, duration_scale))
        for layer_index, child in enumerate(ordered_children)
    ]
    track_lane = _choose_text_template_track_lane(script, layer_timeranges)

    segment_ids: List[str] = []
    for layer_index, child in enumerate(ordered_children):
        child_type = child.get("type")
        timerange = layer_timeranges[layer_index][1]
        clip_settings = _template_clip_settings(script, highlight, child)
        track_type = draft.TrackType.text if child_type == "text" else draft.TrackType.sticker
        track_name = _ensure_text_template_track(script, track_type, layer_index, str(child_type), track_lane)

        animations = _segment_animations_from_template(child, duration_scale, dependency_index)
        if child_type == "text":
            template_font_size = _template_text_font_size(child, float(highlight.get("font_size", 28)))
            text_segment = TextSegment(
                str(highlight.get("text") or ""),
                timerange,
                style=TextStyle(
                    size=template_font_size,
                    color=(1.0, 1.0, 1.0),
                    alpha=1.0,
                    align=1,
                    auto_wrapping=True,
                ),
                border=TextBorder(color=(0.0, 0.0, 0.0), width=20.0),
                clip_settings=clip_settings,
            )
            _add_template_text_effect_refs_with_paths(script, text_segment, child, dependency_index)
            text_segment.export_material = lambda child=child, text=str(highlight.get("text") or ""), material_id=text_segment.material_id, template_font_size=template_font_size, dependency_index=dependency_index: {
                "id": material_id,
                "content": json.dumps(
                    _template_text_material_content(child, text, template_font_size, dependency_index),
                    ensure_ascii=False,
                ),
                "typesetting": 0,
                "alignment": 1,
                "letter_spacing": 0,
                "line_spacing": 0.02,
                "line_feed": 1,
                "line_max_width": 1.0,
                "force_apply_line_max_width": False,
                "check_flag": 7,
                "type": "subtitle",
                "global_alpha": 1.0,
            }
            _add_segment_animations(script, text_segment, animations)
            script.add_segment(text_segment, track_name)
            segment_ids.append(text_segment.segment_id)
        else:
            sticker_resource_id = str(child.get("sticker_resource_id") or "")
            if not sticker_resource_id:
                continue
            sticker_segment = StickerSegment(
                resource_id=sticker_resource_id,
                target_timerange=timerange,
                clip_settings=clip_settings,
            )
            sticker_dependency = dependency_index.get(sticker_resource_id, {})
            if sticker_dependency.get("path"):
                sticker_segment.export_material = lambda sticker_segment=sticker_segment, path=str(sticker_dependency.get("path") or ""): {
                    "id": sticker_segment.material_id,
                    "resource_id": sticker_segment.resource_id,
                    "sticker_id": sticker_segment.resource_id,
                    "source_platform": 1,
                    "type": "sticker",
                    "path": path,
                }
            _add_segment_animations(script, sticker_segment, animations)
            script.add_segment(sticker_segment, track_name)
            segment_ids.append(sticker_segment.segment_id)

    if segment_ids:
        script.save()
    return segment_ids


def _timed_highlight_range(
    caption: dict,
    highlight_text: str,
    *,
    prefer_template_duration: bool = False,
    video_duration: int | None = None,
) -> tuple[int, int]:
    caption_start = int(caption.get("start", 0))
    caption_end = int(caption.get("end", caption_start))
    caption_duration = max(1, caption_end - caption_start)
    caption_text = re.sub(r"\s+", "", str(caption.get("text", "")))
    highlight_text = re.sub(r"\s+", "", str(highlight_text))
    if not caption_text or not highlight_text:
        return caption_start, caption_end

    match_index = caption_text.find(highlight_text)
    if match_index < 0:
        return caption_start, caption_end

    text_length = max(1, _visible_char_count(caption_text))
    term_length = max(1, _visible_char_count(highlight_text))
    term_start_ratio = min(0.92, match_index / text_length)
    term_end_ratio = min(1.0, (match_index + term_length) / text_length)
    start = caption_start + int(caption_duration * term_start_ratio)
    semantic_duration = int(caption_duration * max(0.24, term_end_ratio - term_start_ratio + 0.14))
    min_duration = TEXT_TEMPLATE_MIN_DISPLAY_DURATION if prefer_template_duration else min(caption_duration, 520_000)
    max_duration = TEXT_TEMPLATE_MAX_DISPLAY_DURATION if prefer_template_duration else min(caption_duration, 1_250_000)
    highlight_duration = max(min_duration, min(max_duration, semantic_duration))
    end = min(caption_end, start + highlight_duration)
    if prefer_template_duration and end - start < min_duration:
        start = max(caption_start, end - min_duration)
    timeline_end = max(caption_end, int(video_duration or caption_end))
    if prefer_template_duration:
        start = max(0, start - HIGHLIGHT_TIME_LEAD)
        end = min(timeline_end, max(end, start + min_duration) + HIGHLIGHT_TIME_TAIL)
        if end - start > TEXT_TEMPLATE_MAX_DISPLAY_DURATION:
            end = min(timeline_end, start + TEXT_TEMPLATE_MAX_DISPLAY_DURATION)
    if end <= start:
        end = min(caption_end, start + min_duration)
    return start, max(start + 1, end)


def _build_highlight_captions(
    captions: List[dict],
    req: SmartPackagingRequest,
    randomizer: random.Random,
    video_duration: int | None = None,
) -> List[dict]:
    if not req.caption.highlight_enabled or req.caption.highlight_max_count <= 0:
        return []

    preset = _style_preset(req.style)
    use_text_effect = req.caption.highlight_style_mode == "effect"
    text_effects = _merge_candidates(req.caption.text_effects, preset["text_effects"]) if use_text_effect else []
    enable_jianying_text_templates = req.caption.highlight_style_mode == "template"
    text_template_entries = (
        _load_jianying_text_template_entries(req.caption.jianying_text_template_draft_dir)
        if enable_jianying_text_templates
        else []
    )

    in_animations = _merge_candidates(req.caption.in_animations, preset["caption_in_animations"])
    loop_animations = _merge_candidates(req.caption.loop_animations, preset["caption_loop_animations"])
    seen = set()
    selected = []
    next_allowed_source_index = 0
    selected_source_indices: set[int] = set()
    max_highlights_per_source_caption = 2
    grouped_captions: List[tuple[int, List[tuple[int, dict]]]] = []
    for index, caption in enumerate(captions):
        source_caption_index = int(caption.get("_source_caption_index", index))
        if grouped_captions and grouped_captions[-1][0] == source_caption_index:
            grouped_captions[-1][1].append((index, caption))
        else:
            grouped_captions.append((source_caption_index, [(index, caption)]))

    for source_caption_index, caption_group in grouped_captions:
        is_cooldown_caption = (
            source_caption_index < next_allowed_source_index
            and source_caption_index not in selected_source_indices
        )

        source_candidates: List[tuple[int, int, int, dict, str]] = []
        for index, caption in caption_group:
            explicit_terms = _extract_explicit_highlight_terms(caption, req.caption.highlight_max_chars)
            if explicit_terms:
                term_candidates = [
                    (_highlight_score(term, index) + 20 - term_index, term)
                    for term_index, term in enumerate(explicit_terms)
                ]
            else:
                term_candidates = _extract_terms_from_text(str(caption.get("text", "")), req.caption.highlight_max_chars, index)
            if is_cooldown_caption:
                term_candidates = [
                    (score, term)
                    for score, term in term_candidates
                    if _is_high_priority_highlight(term, score)
                ]
            for candidate_order, (score, highlight_text) in enumerate(term_candidates[:3]):
                source_candidates.append((score, index, candidate_order, caption, highlight_text))

        deduped_source_candidates: dict[str, tuple[int, int, int, dict, str]] = {}
        for score, index, candidate_order, caption, highlight_text in source_candidates:
            if not highlight_text or highlight_text in seen:
                continue
            if score < 0:
                continue
            existing = deduped_source_candidates.get(highlight_text)
            if not existing or (score, -index, -candidate_order) > (existing[0], -existing[1], -existing[2]):
                deduped_source_candidates[highlight_text] = (score, index, candidate_order, caption, highlight_text)

        selected_from_caption = 0
        for score, index, _, caption, highlight_text in sorted(
            deduped_source_candidates.values(),
            key=lambda item: (-item[0], item[1], item[2]),
        )[:max_highlights_per_source_caption]:
            seen.add(highlight_text)
            selected.append((score, index, caption, highlight_text))
            selected_from_caption += 1
            if len(selected) >= req.caption.highlight_max_count:
                break

        if selected_from_caption:
            selected_source_indices.add(source_caption_index)
            next_allowed_source_index = source_caption_index + 2
        if len(selected) >= req.caption.highlight_max_count:
            break

    selected_offsets_by_caption: dict[int, int] = {}
    used_template_effect_ids: set[str] = set()

    highlights: List[dict] = []
    for _, caption_index, caption, highlight_text in selected:
        highlight = dict(caption)
        group_offset = selected_offsets_by_caption.get(caption_index, 0)
        selected_offsets_by_caption[caption_index] = group_offset + 1
        timed_start, timed_end = _timed_highlight_range(
            caption,
            highlight_text,
            prefer_template_duration=req.caption.highlight_style_mode == "template" and enable_jianying_text_templates,
            video_duration=video_duration,
        )
        highlight["_source_caption_index"] = int(caption.get("_source_caption_index", caption_index))
        highlight["_source_caption_start"] = int(caption.get("start", timed_start))
        highlight["_source_caption_end"] = int(caption.get("end", timed_end))
        highlight["text"] = highlight_text
        highlight["start"] = timed_start
        highlight["end"] = timed_end
        if req.caption.highlight_style_mode == "template":
            highlight["font_size"] = req.caption.font_size + 5
        else:
            highlight["font_size"] = req.caption.highlight_font_size
        highlight["template_target_font_size"] = req.caption.font_size + 5
        highlight["text_template_scale"] = req.caption.text_template_scale
        if use_text_effect:
            highlight["text_effect"] = _choose_optional(text_effects, randomizer)
        else:
            highlight.pop("text_effect", None)
            template_effect = _choose_jianying_text_template_effect(
                text_template_entries,
                req.caption.text_template_names,
                randomizer,
                used_template_effect_ids,
            )
            if template_effect:
                highlight["text_effect"] = template_effect
            else:
                template_style = _choose_highlight_text_template(randomizer)
                highlight["text_color"] = template_style["text_color"]
                highlight["border_color"] = template_style["border_color"]
                highlight["has_shadow"] = True
                highlight["shadow_info"] = template_style["shadow_info"]
        highlight["in_animation"] = _choose_optional(in_animations, randomizer)
        highlight["loop_animation"] = _choose_optional(loop_animations, randomizer)
        highlight["transform_x"], highlight["transform_y"] = _spread_highlight_position(
            group_offset,
            req,
            randomizer,
            text=highlight_text,
            placed_highlights=_overlapping_placed_highlights(highlight, highlights),
        )
        highlights.append(highlight)
    return highlights


def _sound_tone_for_name(name: str) -> str:
    normalized = name.strip()
    if normalized in HIGHLIGHT_SOUND_EFFECT_TONES:
        return HIGHLIGHT_SOUND_EFFECT_TONES[normalized]
    alternate = normalized.replace("~", "～")
    if alternate in HIGHLIGHT_SOUND_EFFECT_TONES:
        return HIGHLIGHT_SOUND_EFFECT_TONES[alternate]
    for keyword, tone in HIGHLIGHT_TONE_ALIASES.items():
        if keyword in normalized:
            return tone
    return "pop"


def _tone_for_highlight(text: str) -> str:
    if any(term in text for term in IMPACT_TERMS):
        return "impact"
    if any(term in text for term in COLOR_TERMS):
        return "magic"
    if any(term in text for term in DETAIL_TERMS):
        return "tick"
    return "pop"


def _choose_highlight_sound_name(
    text: str,
    names: Sequence[str],
    randomizer: random.Random,
    index: int | None = None,
    used_names: set[str] | None = None,
) -> str:
    candidates = [name.strip() for name in names if name.strip()] or list(DEFAULT_HIGHLIGHT_SOUND_EFFECTS)
    normalized_used = {_normalize_sound_lookup_key(name) for name in (used_names or set())}
    target_tone = _tone_for_highlight(text)
    preferred_tones = {
        "impact": ("impact", "whoosh", "pop"),
        "magic": ("magic", "shine", "tick"),
        "tick": ("tick", "shine", "pop"),
        "pop": ("pop", "shine", "question", "laugh"),
    }.get(target_tone, (target_tone,))

    matched_names = []
    for tone in preferred_tones:
        matched_names.extend([name for name in candidates if _sound_tone_for_name(name) == tone])
    unused_matched_names = [
        name for name in matched_names
        if _normalize_sound_lookup_key(name) not in normalized_used
    ]
    if unused_matched_names:
        return randomizer.choice(unused_matched_names)
    unused_candidates = [
        name for name in candidates
        if _normalize_sound_lookup_key(name) not in normalized_used
    ]
    if unused_candidates:
        return randomizer.choice(unused_candidates)
    if matched_names:
        return matched_names[index % len(matched_names)] if index is not None else randomizer.choice(matched_names)
    return candidates[index % len(candidates)] if index is not None else randomizer.choice(candidates)


def _normalize_sound_lookup_key(name: str) -> str:
    return re.sub(r"[\s\"'“”‘’~～]+", "", str(name or "")).lower()


def _key_value_has_sound_effects(key_value_path: pathlib.Path) -> bool:
    try:
        data = json.loads(key_value_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return any(
        isinstance(value, dict)
        and value.get("materialCategory") == "audio"
        and value.get("materialSubcategory") == "sound_effect"
        for value in data.values()
    )


def _default_jianying_sound_draft_dir() -> str:
    default_path = pathlib.Path(DEFAULT_JIANYING_SOUND_DRAFT_DIR).expanduser()
    if _key_value_has_sound_effects(default_path / "key_value.json"):
        return str(default_path)

    projects_path = pathlib.Path(DEFAULT_JIANYING_PROJECTS_DIR).expanduser()
    if not projects_path.is_dir():
        return str(default_path)

    candidates = []
    for item in projects_path.iterdir():
        if not item.is_dir():
            continue
        key_value_path = item / "key_value.json"
        if _key_value_has_sound_effects(key_value_path):
            candidates.append((key_value_path.stat().st_mtime, item))

    if not candidates:
        return str(default_path)

    candidates.sort(key=lambda item: item[0], reverse=True)
    return str(candidates[0][1])


def _load_jianying_sound_entries(sound_draft_dir: str | None = None) -> List[dict]:
    draft_path = pathlib.Path(sound_draft_dir or _default_jianying_sound_draft_dir()).expanduser()
    key_value_path = draft_path / "key_value.json"
    if not key_value_path.is_file():
        return []

    try:
        data = json.loads(key_value_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to read Jianying sound library: {key_value_path}, error: {exc}")
        return []

    values = []
    mapping_path = draft_path / "common_attachment" / "attachment_id_mapping.json"
    if mapping_path.is_file():
        try:
            mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
            mappings = mapping_data.get("id_mapping", {}).get("mapping", [])
            mappings = sorted(mappings, key=lambda item: int(item.get("short_id") or 0))
            values = [
                data[item["uuid"]]
                for item in mappings
                if isinstance(item, dict) and item.get("uuid") in data and isinstance(data[item["uuid"]], dict)
            ]
        except Exception as exc:
            logger.warning(f"Failed to read Jianying timeline sound order: {mapping_path}, error: {exc}")

    if not values:
        values = [
            value
            for key, value in data.items()
            if isinstance(value, dict) and str(value.get("materialId", "")) == str(key)
        ] or [value for value in data.values() if isinstance(value, dict)]

    entries: List[dict] = []
    seen_material_ids = set()
    seen_names = set()
    for value in values:
        if value.get("materialCategory") != "audio" or value.get("materialSubcategory") != "sound_effect":
            continue
        material_id = str(value.get("materialId") or "")
        name = str(value.get("materialName") or "").strip()
        name_key = _normalize_sound_lookup_key(name)
        if not name or material_id in seen_material_ids or name_key in seen_names:
            continue
        seen_material_ids.add(material_id)
        seen_names.add(name_key)
        entries.append({"name": name, "material_id": material_id})
    return entries


def _load_jianying_cache_audio_paths(cache_dir: str | None = None) -> List[str]:
    cache_path = pathlib.Path(cache_dir or DEFAULT_JIANYING_MUSIC_CACHE_DIR).expanduser()
    if not cache_path.is_dir():
        return []

    paths: List[pathlib.Path] = []
    seen = set()
    download_config_path = cache_path / "downLoadcfg"
    if download_config_path.is_file():
        try:
            config_data = json.loads(download_config_path.read_text(encoding="utf-8"))
            items = config_data.get("list", [])
            if isinstance(items, list):
                items = sorted(items, key=lambda item: int(item.get("date") or 0))
                for item in items:
                    raw_path = item.get("path") if isinstance(item, dict) else None
                    if not raw_path:
                        continue
                    audio_path = pathlib.Path(raw_path)
                    if not audio_path.is_absolute():
                        audio_path = cache_path / audio_path
                    if audio_path.suffix.lower() not in SUPPORTED_JIANYING_AUDIO_SUFFIXES:
                        continue
                    if audio_path.is_file() and str(audio_path) not in seen:
                        seen.add(str(audio_path))
                        paths.append(audio_path)
        except Exception as exc:
            logger.warning(f"Failed to read Jianying audio cache config: {download_config_path}, error: {exc}")

    extra_paths = sorted(
        (
            item
            for item in cache_path.iterdir()
            if item.is_file() and item.suffix.lower() in SUPPORTED_JIANYING_AUDIO_SUFFIXES
        ),
        key=lambda item: item.stat().st_mtime,
    )
    for audio_path in extra_paths:
        if str(audio_path) not in seen:
            seen.add(str(audio_path))
            paths.append(audio_path)

    return [str(path) for path in paths]


def _load_jianying_cache_audio_path_by_hex(cache_dir: str | None = None) -> dict[str, str]:
    cache_path = pathlib.Path(cache_dir or DEFAULT_JIANYING_MUSIC_CACHE_DIR).expanduser()
    if not cache_path.is_dir():
        return {}

    download_config_path = cache_path / "downLoadcfg"
    if not download_config_path.is_file():
        return {}

    mapping: dict[str, str] = {}
    try:
        config_data = json.loads(download_config_path.read_text(encoding="utf-8"))
        items = config_data.get("list", [])
        if not isinstance(items, list):
            return {}
        for item in items:
            if not isinstance(item, dict):
                continue
            hex_key = str(item.get("hex") or "").strip().lower()
            raw_path = item.get("path")
            if not hex_key or not raw_path:
                continue
            audio_path = pathlib.Path(str(raw_path))
            if not audio_path.is_absolute():
                audio_path = cache_path / audio_path
            if audio_path.suffix.lower() not in SUPPORTED_JIANYING_AUDIO_SUFFIXES:
                continue
            if audio_path.is_file():
                mapping[hex_key] = str(audio_path)
    except Exception as exc:
        logger.warning(f"Failed to read Jianying audio cache config: {download_config_path}, error={exc}")
    return mapping


def _jianying_material_cache_hex(material_id: str) -> str:
    return hashlib.md5(str(material_id).encode("utf-8")).hexdigest()


def _load_preview_sound_files() -> List[pathlib.Path]:
    preview_dir = pathlib.Path(SOUND_EFFECT_PREVIEW_DIR)
    if not preview_dir.is_dir():
        return []
    return sorted(
        (
            item
            for item in preview_dir.iterdir()
            if item.is_file() and item.suffix.lower() in SUPPORTED_JIANYING_AUDIO_SUFFIXES
        ),
        key=lambda item: item.stat().st_mtime,
    )


def _load_smart_assets_manifest() -> dict:
    manifest_path = pathlib.Path(SMART_PACKAGING_ASSETS_DIR) / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to read smart assets manifest: {manifest_path}, error: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_sound_entries() -> List[dict]:
    manifest = _load_smart_assets_manifest()
    items = manifest.get("sound_effects", [])
    if not isinstance(items, list):
        return []
    entries: List[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        material_id = str(item.get("material_id") or "").strip()
        if name and material_id:
            entries.append({"name": name, "material_id": material_id})
    return entries


def _manifest_sound_entry_by_preview_stem(preview_stem: str, entries: Sequence[dict]) -> dict | None:
    stem = str(preview_stem or "").strip()
    if not stem:
        return None
    stem_key = stem.lower()
    for entry in entries:
        material_id = str(entry.get("material_id") or "")
        if material_id and stem_key in {
            material_id.lower(),
            _jianying_material_cache_hex(material_id),
        }:
            return entry
    return None


def _build_jianying_sound_path_map(req: SmartPackagingRequest) -> dict[str, str]:
    use_preview_cache = not req.sound_effects.jianying_sound_draft_dir
    preview_files = _load_preview_sound_files() if use_preview_cache else []
    if use_preview_cache and preview_files:
        mapping: dict[str, str] = {}
        manifest_entries = _manifest_sound_entries()
        for audio_path in preview_files:
            manifest_entry = _manifest_sound_entry_by_preview_stem(audio_path.stem, manifest_entries)
            names = [audio_path.stem]
            if manifest_entry:
                names.extend([
                    str(manifest_entry.get("name") or ""),
                    str(manifest_entry.get("material_id") or ""),
                ])
            for name in names:
                if not name:
                    continue
                mapping[name] = str(audio_path)
                mapping[_normalize_sound_lookup_key(name)] = str(audio_path)
        return mapping

    entries = _load_jianying_sound_entries(req.sound_effects.jianying_sound_draft_dir)
    if not entries:
        return {}

    mapping: dict[str, str] = {}
    cache_paths_by_hex = _load_jianying_cache_audio_path_by_hex(req.sound_effects.jianying_cache_dir)
    for entry in entries:
        material_id = str(entry.get("material_id") or "")
        audio_path = cache_paths_by_hex.get(_jianying_material_cache_hex(material_id)) if material_id else None
        if not audio_path:
            continue
        name = entry["name"]
        mapping[name] = audio_path
        mapping[_normalize_sound_lookup_key(name)] = audio_path
        if material_id:
            mapping[material_id] = audio_path

    if mapping:
        return mapping

    audio_paths = _load_jianying_cache_audio_paths(req.sound_effects.jianying_cache_dir)
    if not audio_paths:
        return {}

    audio_paths = audio_paths[-len(entries):]
    for entry, audio_path in zip(entries, audio_paths):
        name = entry["name"]
        material_id = str(entry.get("material_id") or "")
        mapping[name] = audio_path
        mapping[_normalize_sound_lookup_key(name)] = audio_path
        if material_id:
            mapping[material_id] = audio_path
    return mapping


def _resolve_jianying_sound_path(
    sound_name: str,
    sound_path_map: dict[str, str],
) -> str | None:
    if not sound_path_map:
        return None

    if sound_name in sound_path_map:
        return sound_path_map[sound_name]

    lookup_key = _normalize_sound_lookup_key(sound_name)
    if lookup_key in sound_path_map:
        return sound_path_map[lookup_key]

    return None


def _audio_duration_or_default(audio_path: str, default_duration: int) -> int:
    actual_duration = get_media_duration(audio_path)
    if actual_duration and actual_duration > 0:
        return actual_duration
    return default_duration


def _preview_audio_path(material_id: str, audio_path: str) -> str:
    os.makedirs(SOUND_EFFECT_PREVIEW_DIR, exist_ok=True)
    _, ext = os.path.splitext(audio_path)
    safe_material_id = re.sub(r"[^0-9A-Za-z_-]+", "", material_id) or pathlib.Path(audio_path).stem
    target_path = os.path.join(SOUND_EFFECT_PREVIEW_DIR, f"{safe_material_id}{ext or '.mp3'}")
    shutil.copy2(audio_path, target_path)
    return target_path


def get_smart_packaging_sound_effects(
    req: SmartPackagingSoundEffectsRequest,
    base_url: str,
) -> SmartPackagingSoundEffectsResponse:
    use_preview_cache = not req.jianying_sound_draft_dir
    preview_files = _load_preview_sound_files() if use_preview_cache else []
    if use_preview_cache and preview_files:
        items = []
        manifest_entries = _manifest_sound_entries()
        for audio_path in preview_files:
            manifest_entry = _manifest_sound_entry_by_preview_stem(audio_path.stem, manifest_entries)
            name = manifest_entry["name"] if manifest_entry else audio_path.stem
            material_id = manifest_entry["material_id"] if manifest_entry else audio_path.stem
            preview_url = f"{base_url.rstrip('/')}/output/sound_effect_previews/{audio_path.name}"
            items.append(
                SmartPackagingSoundEffectItem(
                    name=name,
                    material_id=material_id,
                    preview_url=preview_url,
                    duration=_audio_duration_or_default(str(audio_path), 0),
                )
            )
        return SmartPackagingSoundEffectsResponse(sound_effects=items)

    entries = _load_jianying_sound_entries(req.jianying_sound_draft_dir)
    fake_req = SmartPackagingRequest(
        videos=[{"video_url": "https://example.com/placeholder.mp4", "duration": 1_000_000}],
        sound_effects={
            "jianying_sound_draft_dir": req.jianying_sound_draft_dir,
            "jianying_cache_dir": req.jianying_cache_dir,
        },
    )
    sound_path_map = _build_jianying_sound_path_map(fake_req)

    items: List[SmartPackagingSoundEffectItem] = []
    for entry in entries:
        audio_path = _resolve_jianying_sound_path(entry["name"], sound_path_map)
        if not audio_path:
            continue
        preview_path = _preview_audio_path(entry["material_id"], audio_path)
        preview_name = pathlib.Path(preview_path).name
        preview_url = f"{base_url.rstrip('/')}/output/sound_effect_previews/{preview_name}"
        items.append(
            SmartPackagingSoundEffectItem(
                name=entry["name"],
                material_id=entry["material_id"],
                preview_url=preview_url,
                duration=_audio_duration_or_default(audio_path, 0),
            )
        )
    return SmartPackagingSoundEffectsResponse(sound_effects=items)


def get_smart_packaging_text_templates(
    req: SmartPackagingTextTemplatesRequest,
) -> SmartPackagingTextTemplatesResponse:
    entries = _load_jianying_text_template_entries(
        req.jianying_text_template_draft_dir,
        req.jianying_artist_effect_cache_dir,
    )
    return SmartPackagingTextTemplatesResponse(
        text_templates=[
            SmartPackagingTextTemplateItem(
                name=entry["name"],
                material_id=entry["material_id"],
                segment_id=entry.get("segment_id", ""),
                effect_id=entry.get("effect_id", ""),
                is_vip=bool(entry.get("is_vip")),
                rank=int(entry.get("rank", 9999)),
                default_texts=list(entry.get("default_texts") or []),
            )
            for entry in entries
        ]
    )


def _write_tone_wav(path: str, tone: str, duration_seconds: float = 0.34, sample_rate: int = 44100) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frame_count = int(sample_rate * duration_seconds)
    profile = {
        "impact": (150.0, 90.0, 0.85),
        "shine": (880.0, 1320.0, 0.42),
        "tick": (520.0, 760.0, 0.32),
        "pop": (420.0, 640.0, 0.36),
        "whoosh": (260.0, 1180.0, 0.34),
        "magic": (740.0, 1480.0, 0.38),
        "laugh": (300.0, 620.0, 0.32),
        "question": (520.0, 880.0, 0.3),
    }.get(tone, (420.0, 640.0, 0.36))
    freq_a, freq_b, gain = profile

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            t = index / sample_rate
            progress = index / max(1, frame_count - 1)
            envelope = math.exp(-7.0 * progress)
            if tone == "impact":
                value = math.sin(2 * math.pi * (freq_a + (freq_b - freq_a) * progress) * t)
                value += 0.35 * math.sin(2 * math.pi * 55 * t)
            elif tone == "shine":
                value = math.sin(2 * math.pi * freq_a * t) + 0.55 * math.sin(2 * math.pi * freq_b * t)
            elif tone == "tick":
                value = math.sin(2 * math.pi * freq_a * t)
                value += 0.3 * math.sin(2 * math.pi * freq_b * t)
            elif tone == "whoosh":
                sweep = freq_a + (freq_b - freq_a) * progress
                value = math.sin(2 * math.pi * sweep * t)
                value += 0.18 * math.sin(2 * math.pi * (sweep * 0.5) * t)
            elif tone == "magic":
                sparkle = 1.0 + 0.45 * math.sin(2 * math.pi * 18 * t)
                value = math.sin(2 * math.pi * freq_a * t) + 0.55 * math.sin(2 * math.pi * freq_b * t)
                value *= sparkle
            elif tone == "laugh":
                wobble = 1.0 + 0.22 * math.sin(2 * math.pi * 9 * t)
                value = math.sin(2 * math.pi * freq_a * wobble * t)
                value += 0.45 * math.sin(2 * math.pi * freq_b * t)
            elif tone == "question":
                sweep = freq_a + (freq_b - freq_a) * progress
                value = math.sin(2 * math.pi * sweep * t)
                value += 0.25 * math.sin(2 * math.pi * freq_a * t)
            else:
                value = math.sin(2 * math.pi * freq_a * t) + 0.4 * math.sin(2 * math.pi * freq_b * t)
            sample = int(max(-1.0, min(1.0, value * envelope * gain)) * 32767)
            frames.extend(struct.pack("<h", sample))
        wav_file.writeframes(frames)


def _build_highlight_audio_infos(
    highlight_captions: List[dict],
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    if not req.sound_effects.enabled or not req.sound_effects.auto_for_highlights:
        return []

    audio_infos: List[dict] = []
    duration = req.sound_effects.duration
    generated_dir = os.path.join(config.TEMP_DIR, "smart_packaging_sfx")
    jianying_sound_path_map = (
        _build_jianying_sound_path_map(req)
        if req.sound_effects.use_jianying_cache and not req.sound_effects.audio_urls
        else {}
    )
    next_available_start = 0
    seen_source_keys = set()
    used_sound_names: set[str] = set()
    overlap_padding = 20_000

    for index, caption in enumerate(highlight_captions):
        caption_start = int(caption.get("start", 0))
        caption_end = int(caption.get("end", caption_start))
        source_key = caption.get("_source_caption_index", index)
        if source_key in seen_source_keys:
            continue
        start = max(caption_start, next_available_start)
        seen_source_keys.add(source_key)
        available_duration = max(0, caption_end - start)
        if available_duration <= 0:
            continue

        if req.sound_effects.audio_urls:
            audio_duration = min(duration, available_duration)
            end = start + audio_duration
            audio_infos.append(
                {
                    "audio_url": str(randomizer.choice(req.sound_effects.audio_urls)),
                    "start": start,
                    "end": end,
                    "duration": audio_duration,
                    "volume": req.sound_effects.volume,
                }
            )
            next_available_start = max(next_available_start, end + overlap_padding)
            continue

        sound_name = _choose_highlight_sound_name(
            str(caption.get("text", "")),
            req.sound_effects.highlight_sound_effects,
            randomizer,
            index,
            used_sound_names,
        )
        jianying_audio_path = _resolve_jianying_sound_path(sound_name, jianying_sound_path_map)
        if jianying_audio_path:
            audio_duration = min(_audio_duration_or_default(jianying_audio_path, duration), available_duration)
            end = start + audio_duration
            audio_infos.append(
                {
                    "local_audio_path": jianying_audio_path,
                    "start": start,
                    "end": end,
                    "duration": audio_duration,
                    "volume": req.sound_effects.volume,
                }
            )
            used_sound_names.add(sound_name)
            next_available_start = max(next_available_start, end + overlap_padding)
            continue

        tone = _sound_tone_for_name(sound_name)
        audio_path = os.path.join(generated_dir, f"{tone}_{randomizer.randint(1, 2**31 - 1)}.wav")
        audio_duration = min(duration, available_duration)
        _write_tone_wav(audio_path, tone, duration_seconds=audio_duration / 1_000_000)
        end = start + audio_duration
        audio_infos.append(
            {
                "local_audio_path": audio_path,
                "start": start,
                "end": end,
                "duration": audio_duration,
                "volume": req.sound_effects.volume,
            }
        )
        used_sound_names.add(sound_name)
        next_available_start = max(next_available_start, end + overlap_padding)

    return audio_infos


def _split_overlapping_items_into_tracks(items: List[dict]) -> List[List[dict]]:
    tracks: List[List[dict]] = []
    track_ends: List[int] = []

    for item in sorted(items, key=lambda item: (int(item.get("start", 0)), int(item.get("end", 0)))):
        start = int(item.get("start", 0))
        placed = False
        for index, track_end in enumerate(track_ends):
            if start >= track_end:
                tracks[index].append(item)
                track_ends[index] = int(item.get("end", start))
                placed = True
                break
        if not placed:
            tracks.append([item])
            track_ends.append(int(item.get("end", start)))

    return tracks


def _split_overlapping_captions_into_tracks(captions: List[dict]) -> List[List[dict]]:
    return _split_overlapping_items_into_tracks(captions)


def _normalize_caption_timeline_for_single_track(
    captions: List[dict],
    *,
    min_duration: int = 80_000,
) -> List[dict]:
    normalized: List[dict] = []
    previous_end = 0

    for caption in sorted(captions, key=lambda item: (int(item.get("start", 0)), int(item.get("end", 0)))):
        try:
            start = int(caption.get("start", 0))
            end = int(caption.get("end", start))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        if start < previous_end:
            start = previous_end
        if end - start < min_duration:
            continue

        next_caption = dict(caption)
        next_caption["start"] = start
        next_caption["end"] = end
        normalized.append(next_caption)
        previous_end = end

    return normalized


def _split_overlapping_audio_infos_into_tracks(audio_infos: List[dict]) -> List[List[dict]]:
    return _split_overlapping_items_into_tracks(audio_infos)


def _apply_highlight_keywords_to_plain_captions(
    captions: List[dict],
    highlight_captions: List[dict],
    req: SmartPackagingRequest,
) -> List[dict]:
    if not captions or not highlight_captions or not req.caption.keyword_color:
        return captions

    terms_by_caption_index: dict[int, List[str]] = {}
    for highlight in highlight_captions:
        try:
            caption_index = int(highlight.get("_source_caption_index"))
        except (TypeError, ValueError):
            continue
        term = str(highlight.get("text") or "").strip()
        if not term:
            continue
        terms_by_caption_index.setdefault(caption_index, [])
        if term not in terms_by_caption_index[caption_index]:
            terms_by_caption_index[caption_index].append(term)

    styled = [dict(caption) for caption in captions]
    for index, caption in enumerate(styled):
        caption_source_index = int(caption.get("_source_caption_index", index))
        terms = [
            term for term in terms_by_caption_index.get(caption_source_index, [])
            if term and term in str(caption.get("text", ""))
        ]
        if not terms:
            continue
        existing = _extract_explicit_highlight_terms(caption, req.caption.highlight_max_chars)
        merged_terms: List[str] = []
        for term in [*existing, *terms]:
            if term and term not in merged_terms and term in str(caption.get("text", "")):
                merged_terms.append(term)
        if not merged_terms:
            continue
        caption["keyword"] = "|".join(merged_terms)
        caption["keyword_color"] = req.caption.keyword_color
        if req.caption.keyword_border_color:
            caption["keyword_border_color"] = req.caption.keyword_border_color
        caption.setdefault("keyword_font_size", caption.get("font_size") or req.caption.font_size)
    return styled


def _build_plain_caption_keyword_highlights(captions: List[dict], req: SmartPackagingRequest) -> List[dict]:
    if not captions or not req.caption.keyword_color:
        return []

    keyword_highlights: List[dict] = []
    for index, caption in enumerate(captions):
        explicit_terms = _extract_explicit_highlight_terms(caption, req.caption.highlight_max_chars)
        if explicit_terms:
            terms = explicit_terms
        else:
            terms = [
                term
                for _, term in _extract_terms_from_text(
                    str(caption.get("text", "")),
                    req.caption.highlight_max_chars,
                    index,
                )[:3]
            ]

        caption_text = str(caption.get("text", ""))
        source_index = int(caption.get("_source_caption_index", index))
        seen_terms: set[str] = set()
        for term in terms:
            if not term or term in seen_terms or term not in caption_text:
                continue
            seen_terms.add(term)
            keyword_highlights.append(
                {
                    "_source_caption_index": source_index,
                    "text": term,
                }
            )
    return keyword_highlights


def _resolve_captions(
    prepared: PreparedVideo,
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    video = prepared.input
    if video.captions:
        captions = [dict(item) for item in video.captions]
    elif req.caption.source in ("asr", "auto") and req.asr.enabled:
        captions = transcribe_video_to_captions(str(video.video_url or video.local_video_path), req.asr, local_video_path=video.local_video_path)
        if not captions and req.caption.source != "asr":
            captions = _build_captions(video, prepared.duration, req, randomizer)
    else:
        captions = _build_captions(video, prepared.duration, req, randomizer)

    if captions and req.llm_caption.enabled:
        captions = polish_captions_with_llm(captions, req.llm_caption, fallback_api_key=req.asr.api_key)

    return _split_captions_by_max_chars(captions, req.caption.max_chars_per_caption)


def _build_effect_infos(
    duration: int,
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    if not req.effects.enabled or req.effects.count <= 0:
        return []

    preset = _style_preset(req.style)
    effect_titles = _merge_candidates(req.effects.effect_titles, preset["effects"])
    if not effect_titles:
        return []

    effect_duration = min(req.effects.duration, duration)
    starts = _spread_starts(duration, req.effects.count, effect_duration)
    return [
        {
            "effect_title": randomizer.choice(effect_titles),
            "start": start,
            "end": min(duration, start + effect_duration),
        }
        for start in starts
    ]


def _build_filter_infos(duration: int, req: SmartPackagingRequest, randomizer: random.Random) -> List[dict]:
    if not req.filters.enabled:
        return []

    preset = _style_preset(req.style)
    filter_titles = _merge_candidates(req.filters.filter_titles, preset["filters"])
    if not filter_titles:
        return []

    return [
        {
            "filter_title": randomizer.choice(filter_titles),
            "start": 0,
            "end": duration,
            "intensity": req.filters.intensity,
        }
    ]


def _build_audio_infos(duration: int, req: SmartPackagingRequest, randomizer: random.Random) -> List[dict]:
    audio_infos: List[dict] = []

    if req.bgm.enabled and req.bgm.audio_urls:
        audio_infos.append(
            {
                "audio_url": str(randomizer.choice(req.bgm.audio_urls)),
                "start": 0,
                "end": duration,
                "duration": duration,
                "volume": req.bgm.volume,
            }
        )

    if req.sound_effects.enabled and req.sound_effects.audio_urls and req.sound_effects.count > 0:
        sound_duration = min(req.sound_effects.duration, duration)
        starts = _spread_starts(duration, req.sound_effects.count, sound_duration)
        for start in starts:
            audio_infos.append(
                {
                    "audio_url": str(randomizer.choice(req.sound_effects.audio_urls)),
                    "start": start,
                    "end": min(duration, start + sound_duration),
                    "duration": sound_duration,
                    "volume": req.sound_effects.volume,
                }
            )

    return audio_infos


def _load_sticker_data() -> List[dict]:
    global _STICKER_DATA_CACHE
    if _STICKER_DATA_CACHE is not None:
        return _STICKER_DATA_CACHE

    try:
        with open(config.STICKER_CONFIG_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as exc:
        logger.warning(f"Failed to load sticker config: {config.STICKER_CONFIG_PATH}, error: {exc}")
        data = []

    _STICKER_DATA_CACHE = [item for item in data if isinstance(item, dict) and item.get("sticker_id")]
    return _STICKER_DATA_CACHE


def _sticker_keywords_for_text(text: str) -> List[str]:
    keywords: List[str] = []
    for triggers, sticker_keywords in STICKER_KEYWORD_RULES:
        if any(trigger in text for trigger in triggers):
            keywords.extend(sticker_keywords)
    return keywords


def _build_sticker_keyword_candidates(
    captions: List[dict],
    highlight_captions: List[dict],
    req: SmartPackagingRequest,
) -> List[dict]:
    candidates: List[dict] = []
    custom_keywords = [keyword.strip() for keyword in req.stickers.keywords if keyword.strip()]

    for caption in captions:
        start = int(caption.get("start", 0))
        end = int(caption.get("end", start))
        text = str(caption.get("text", ""))
        for keyword in custom_keywords or _sticker_keywords_for_text(text):
            candidates.append({"start": start, "end": end, "keyword": keyword, "anchor": None})

    for caption in highlight_captions:
        start = int(caption.get("start", 0))
        end = int(caption.get("end", start))
        text = str(caption.get("text", ""))
        for keyword in _sticker_keywords_for_text(text) or [text]:
            candidates.append({"start": start, "end": end, "keyword": keyword, "anchor": caption})

    if not candidates and captions:
        for caption in captions:
            start = int(caption.get("start", 0))
            end = int(caption.get("end", start))
            for keyword in DEFAULT_STICKER_KEYWORDS[:2]:
                candidates.append({"start": start, "end": end, "keyword": keyword, "anchor": None})

    return candidates


def _choose_sticker_for_keyword(keyword: str, randomizer: random.Random, used_sticker_ids: set[str]) -> dict | None:
    sticker_data = _load_sticker_data()
    if not sticker_data:
        return None

    matches = [
        item
        for item in sticker_data
        if keyword in str(item.get("title", "")) and str(item.get("sticker_id", "")) not in used_sticker_ids
    ]
    if not matches:
        matches = [
            item
            for item in sticker_data
            if any(default in str(item.get("title", "")) for default in DEFAULT_STICKER_KEYWORDS)
            and str(item.get("sticker_id", "")) not in used_sticker_ids
        ]
    if not matches:
        return None
    return randomizer.choice(matches[:80])


def _sticker_position_for_candidate(candidate: dict, fallback_index: int, randomizer: random.Random) -> tuple[int, int]:
    anchor = candidate.get("anchor")
    if isinstance(anchor, dict):
        anchor_x = float(anchor.get("transform_x", 0.0))
        anchor_y = float(anchor.get("transform_y", -260.0))
        side = -1 if anchor_x >= 0 else 1
        vertical = -1 if anchor_y > -260 else 1
        return (
            int(_clamp_position(anchor_x + side * randomizer.randint(150, 230), -420, 420)),
            int(_clamp_position(anchor_y + vertical * randomizer.randint(110, 190), -720, 180)),
        )

    positions = (
        (-360, -610),
        (360, -450),
        (-350, -250),
        (340, -80),
        (0, -600),
        (0, -220),
    )
    base_x, base_y = positions[fallback_index % len(positions)]
    return base_x + randomizer.randint(-35, 35), base_y + randomizer.randint(-35, 35)


def _build_sticker_infos(
    duration: int,
    captions: List[dict],
    highlight_captions: List[dict],
    req: SmartPackagingRequest,
    randomizer: random.Random,
) -> List[dict]:
    if not req.stickers.enabled or req.stickers.count <= 0 or duration <= 0:
        return []

    candidates = _build_sticker_keyword_candidates(captions, highlight_captions, req)
    if not candidates:
        return []

    randomizer.shuffle(candidates)
    used_sticker_ids: set[str] = set()
    used_windows: List[tuple[int, int]] = []
    sticker_infos: List[dict] = []
    sticker_duration = min(req.stickers.duration, duration)

    for candidate in candidates:
        if len(sticker_infos) >= req.stickers.count:
            break
        start = int(candidate.get("start", 0))
        end = int(candidate.get("end", start))
        keyword = str(candidate.get("keyword", ""))
        if end <= start:
            continue
        window_start = max(0, min(start, duration - 100_000))
        window_end = min(duration, max(end, window_start + 100_000))
        available_duration = max(100_000, min(sticker_duration, window_end - window_start))
        if any(window_start < used_end and used_start < window_start + available_duration for used_start, used_end in used_windows):
            continue

        sticker = _choose_sticker_for_keyword(keyword, randomizer, used_sticker_ids)
        if not sticker:
            continue

        position = _sticker_position_for_candidate(candidate, len(sticker_infos), randomizer)
        sticker_id = str(sticker.get("sticker_id"))
        used_sticker_ids.add(sticker_id)
        used_windows.append((window_start, window_start + available_duration))
        sticker_infos.append(
            {
                "sticker_id": sticker_id,
                "title": sticker.get("title", ""),
                "keyword": keyword,
                "start": window_start,
                "end": window_start + available_duration,
                "scale": round(randomizer.uniform(req.stickers.scale_min, req.stickers.scale_max), 2),
                "transform_x": position[0],
                "transform_y": position[1],
            }
        )

    return sticker_infos


async def smart_packaging(req: SmartPackagingRequest) -> SmartPackagingResponse:
    """批量智能包装视频，所有输入视频组合输出为一个剪映草稿。"""

    base_seed = req.seed if req.seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
    prepared_items: List[tuple[int, SmartPackagingVideoInput, PreparedVideo, int, random.Random]] = []
    total_duration = 0

    try:
        install_smart_packaging_cache_assets()
        for index, video in enumerate(req.videos):
            prepared = await asyncio.to_thread(_prepare_video, video)
            prepared_items.append((index, video, prepared, total_duration, random.Random(base_seed + index)))
            total_duration += prepared.duration

        draft_url = create_draft(width=req.width, height=req.height)
        applied: List[str] = []
        caption_segment_ids: List[str] = []
        highlight_segment_ids: List[str] = []
        effect_segment_ids: List[str] = []
        filter_segment_ids: List[str] = []
        sticker_segment_ids: List[str] = []
        audio_ids: List[str] = []

        video_infos: List[dict] = []
        plain_caption_infos: List[dict] = []
        fallback_highlight_infos: List[dict] = []
        highlight_audio_infos: List[dict] = []
        base_audio_infos: List[dict] = []
        sticker_infos: List[dict] = []
        effect_infos: List[dict] = []
        filter_infos: List[dict] = []
        template_highlight_infos: List[tuple[dict, dict | None]] = []
        source_index_offset = 0

        for _, _, prepared, offset, randomizer in prepared_items:
            video_info = _build_video_infos(prepared, req.mute_original)[0]
            video_info["start"] = offset
            video_info["end"] = offset + prepared.duration
            video_infos.append(video_info)

            base_audio_infos.extend(_offset_timed_items(_build_audio_infos(prepared.duration, req, randomizer), offset))

            if req.caption.enabled:
                captions = await asyncio.to_thread(_resolve_captions, prepared, req, randomizer)
                if captions:
                    plain_keyword_highlights = _build_plain_caption_keyword_highlights(captions, req)
                    highlight_captions = _build_highlight_captions(captions, req, randomizer, prepared.duration)
                    plain_captions = _apply_highlight_keywords_to_plain_captions(
                        _apply_plain_caption_style(captions, req, randomizer),
                        plain_keyword_highlights,
                        req,
                    )
                    source_index_map, local_source_count = _caption_source_index_map(captions, source_index_offset)
                    global_plain_captions = _globalize_caption_source_indexes(plain_captions, source_index_map)
                    global_highlight_captions = _globalize_caption_source_indexes(highlight_captions, source_index_map)
                    global_plain_captions = _offset_timed_items(global_plain_captions, offset)
                    global_highlight_captions = _offset_timed_items(global_highlight_captions, offset)
                    plain_caption_infos.extend(global_plain_captions)

                    if global_highlight_captions:
                        current_fallback_highlights = global_highlight_captions
                        if req.caption.highlight_style_mode == "template":
                            template_entries = _load_jianying_text_template_entries(req.caption.jianying_text_template_draft_dir)
                            current_fallback_highlights = []
                            used_template_material_ids: set[str] = set()
                            for highlight in global_highlight_captions:
                                template_entry = _choose_jianying_text_template_entry(
                                    template_entries,
                                    req.caption.text_template_names,
                                    randomizer,
                                    used_template_material_ids,
                                )
                                if template_entry:
                                    template_highlight_infos.append((highlight, template_entry))
                                else:
                                    current_fallback_highlights.append(highlight)
                        fallback_highlight_infos.extend(current_fallback_highlights)
                        highlight_audio_infos.extend(
                            _offset_timed_items(
                                _globalize_caption_source_indexes(
                                    _build_highlight_audio_infos(highlight_captions, req, randomizer),
                                    source_index_map,
                                ),
                                offset,
                            )
                        )

                    sticker_infos.extend(
                        _offset_timed_items(
                            _build_sticker_infos(prepared.duration, captions, highlight_captions, req, randomizer),
                            offset,
                        )
                    )
                    source_index_offset += local_source_count

            effect_infos.extend(_offset_timed_items(_build_effect_infos(prepared.duration, req, randomizer), offset))
            filter_infos.extend(_offset_timed_items(_build_filter_infos(prepared.duration, req, randomizer), offset))

        try:
            _, _, _, video_segment_ids, _ = await add_videos_async(
                draft_url=draft_url,
                video_infos=_stringify(video_infos),
            )
            _append_applied(applied, "video")

            if template_highlight_infos:
                for highlight, template_entry in template_highlight_infos:
                    next_ids = (
                        _add_text_template_layers_to_draft(draft_url, highlight, template_entry)
                        if template_entry
                        else []
                    )
                    if next_ids:
                        highlight_segment_ids.extend(next_ids)
                    else:
                        fallback_highlight_infos.append(highlight)

            if base_audio_infos:
                _, _, next_audio_ids = await add_audios_async(
                    draft_url=draft_url,
                    audio_infos=_stringify(base_audio_infos),
                )
                audio_ids.extend(next_audio_ids)
                _append_applied(applied, "audio")

            plain_caption_infos = _normalize_caption_timeline_for_single_track(plain_caption_infos)
            if plain_caption_infos:
                _, _, _, caption_segment_ids, _ = await add_captions_async(
                    draft_url=draft_url,
                    captions=_stringify(plain_caption_infos),
                    text_color=req.caption.text_color,
                    border_color=req.caption.border_color,
                    font=req.caption.font,
                    font_size=req.caption.font_size,
                    transform_y=req.caption.transform_y,
                )
                _append_applied(applied, "captions")

            if fallback_highlight_infos:
                for highlight_track in _split_overlapping_captions_into_tracks(fallback_highlight_infos):
                    _, _, _, next_highlight_segment_ids, _ = await add_captions_async(
                        draft_url=draft_url,
                        captions=_stringify(highlight_track),
                        text_color="#ffffff",
                        border_color=None,
                        font=req.caption.font,
                        font_size=req.caption.highlight_font_size,
                        transform_y=0.0,
                    )
                    highlight_segment_ids.extend(next_highlight_segment_ids)
            if highlight_segment_ids:
                _append_applied(applied, "highlights")

            if highlight_audio_infos:
                for highlight_audio_track in _split_overlapping_audio_infos_into_tracks(highlight_audio_infos):
                    _, _, next_highlight_audio_ids = await add_audios_async(
                        draft_url=draft_url,
                        audio_infos=_stringify(highlight_audio_track),
                    )
                    audio_ids.extend(next_highlight_audio_ids)
                _append_applied(applied, "audio")

            for sticker_info in sticker_infos:
                _, _, _, segment_id, _ = await add_sticker_async(
                    draft_url=draft_url,
                    sticker_id=sticker_info["sticker_id"],
                    start=sticker_info["start"],
                    end=sticker_info["end"],
                    scale=sticker_info["scale"],
                    transform_x=sticker_info["transform_x"],
                    transform_y=sticker_info["transform_y"],
                    in_animation=sticker_info.get("in_animation"),
                    in_animation_duration=sticker_info.get("in_animation_duration"),
                )
                sticker_segment_ids.append(segment_id)
            if sticker_segment_ids:
                _append_applied(applied, "stickers")

            if effect_infos:
                _, _, _, effect_segment_ids = await add_effects_async(
                    draft_url=draft_url,
                    effect_infos=_stringify(effect_infos),
                )
                _append_applied(applied, "effects")

            if filter_infos:
                _, _, _, filter_segment_ids = await add_filters_async(
                    draft_url=draft_url,
                    filter_infos=_stringify(filter_infos),
                )
                _append_applied(applied, "filters")

            await save_draft_async(draft_url=draft_url)
            return SmartPackagingResponse(
                drafts=[
                    SmartPackagingDraft(
                        draft_url=draft_url,
                        source_video_url="\n".join(str(video.video_url or video.local_video_path) for _, video, _, _, _ in prepared_items),
                        duration=total_duration,
                        seed=base_seed,
                        video_segment_ids=video_segment_ids,
                        caption_segment_ids=caption_segment_ids,
                        highlight_segment_ids=highlight_segment_ids,
                        effect_segment_ids=effect_segment_ids,
                        filter_segment_ids=filter_segment_ids,
                        sticker_segment_ids=sticker_segment_ids,
                        audio_ids=audio_ids,
                        applied=applied,
                    )
                ]
            )
        except Exception:
            logger.exception(f"smart_packaging failed, draft_url={draft_url}, seed={base_seed}")
            raise
    finally:
        for _, _, prepared, _, _ in prepared_items:
            if prepared.cleanup_local_file:
                cleanup_temp_file(prepared.local_video_path)
