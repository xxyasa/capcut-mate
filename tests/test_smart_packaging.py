import asyncio
import hashlib
import importlib
import json
from unittest.mock import Mock

import pytest

from src.schemas.smart_packaging import SmartPackagingRequest, SmartPackagingSoundEffectsRequest
from src.schemas.smart_packaging import SmartPackagingLlmCaptionConfig
from src.service import smart_packaging as smart_packaging_func
from src.service.llm_caption_polish import polish_captions_with_llm

smart_packaging_module = importlib.import_module("src.service.smart_packaging")


def test_smart_packaging_builds_one_draft_per_video(monkeypatch):
    created = []
    video_calls = []
    audio_calls = []
    caption_calls = []
    effect_calls = []
    filter_calls = []
    sticker_calls = []
    saved = []

    def fake_create_draft(width, height):
        draft_url = f"https://example.com/get_draft?draft_id=20260101000000{len(created):08d}"
        created.append((width, height, draft_url))
        return draft_url

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        video_calls.append((draft_url, json.loads(video_infos)))
        return draft_url, "track-video", ["video-id"], [f"video-segment-{len(video_calls)}"], []

    async def fake_add_audios_async(draft_url, audio_infos, **kwargs):
        audio_calls.append((draft_url, json.loads(audio_infos)))
        return draft_url, "track-audio", [f"audio-id-{len(audio_calls)}"]

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append((draft_url, json.loads(captions), kwargs))
        return draft_url, "track-caption", ["text-id"], [f"caption-segment-{len(caption_calls)}"], []

    async def fake_add_effects_async(draft_url, effect_infos, **kwargs):
        effect_calls.append((draft_url, json.loads(effect_infos)))
        return draft_url, "track-effect", ["effect-id"], [f"effect-segment-{len(effect_calls)}"]

    async def fake_add_filters_async(draft_url, filter_infos, **kwargs):
        filter_calls.append((draft_url, json.loads(filter_infos)))
        return draft_url, "track-filter", ["filter-id"], [f"filter-segment-{len(filter_calls)}"]

    async def fake_add_sticker_async(draft_url, **kwargs):
        sticker_calls.append((draft_url, kwargs))
        return draft_url, kwargs["sticker_id"], "track-sticker", f"sticker-segment-{len(sticker_calls)}", kwargs["end"] - kwargs["start"]

    async def fake_save_draft_async(draft_url, **kwargs):
        saved.append(draft_url)
        return draft_url

    monkeypatch.setattr(smart_packaging_module, "create_draft", fake_create_draft)
    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_audios_async", fake_add_audios_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "add_effects_async", fake_add_effects_async)
    monkeypatch.setattr(smart_packaging_module, "add_filters_async", fake_add_filters_async)
    monkeypatch.setattr(smart_packaging_module, "add_sticker_async", fake_add_sticker_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_sticker_data",
        lambda: [{"sticker_id": "sticker-star", "title": "闪光星星"}],
    )

    req = SmartPackagingRequest(
        videos=[
            {
                "video_url": "https://assets.example.com/a.mp4",
                "duration": 6_000_000,
                "caption_texts": ["开场", "卖点"],
            },
            {
                "video_url": "https://assets.example.com/b.mp4",
                "duration": 8_000_000,
                "captions": [{"start": 0, "end": 2_000_000, "text": "现成字幕"}],
            },
        ],
        width=1080,
        height=1920,
        style="dynamic",
        mute_original=True,
        seed=11,
        caption={
            "enabled": True,
            "text_effects": ["花字A"],
            "in_animations": ["入场A"],
            "loop_animations": ["循环A"],
            "font_size": 18,
            "highlight_enabled": False,
        },
        effects={"enabled": True, "effect_titles": ["特效A"], "count": 2, "duration": 1_000_000},
        filters={"enabled": True, "filter_titles": ["滤镜A"], "intensity": 66},
        stickers={"enabled": True, "count": 1, "keywords": ["闪光"]},
        sound_effects={
            "enabled": True,
            "audio_urls": ["https://assets.example.com/sfx.mp3"],
            "count": 1,
            "duration": 500_000,
        },
        bgm={"enabled": True, "audio_urls": ["https://assets.example.com/bgm.mp3"], "volume": 0.4},
    )

    result = asyncio.run(smart_packaging_func(req))

    assert len(result.drafts) == 1
    assert len(created) == 1
    assert len(video_calls) == 1
    assert len(audio_calls) == 1
    assert len(caption_calls) == 1
    assert len(effect_calls) == 1
    assert len(filter_calls) == 1
    assert len(sticker_calls) == 2
    assert saved == [draft.draft_url for draft in result.drafts]

    first_video = video_calls[0][1][0]
    assert first_video["video_url"] == "https://assets.example.com/a.mp4"
    assert first_video["start"] == 0
    assert first_video["end"] == 6_000_000
    assert first_video["volume"] == 0.0
    second_video = video_calls[0][1][1]
    assert second_video["video_url"] == "https://assets.example.com/b.mp4"
    assert second_video["start"] == 6_000_000
    assert second_video["end"] == 14_000_000

    first_captions = caption_calls[0][1]
    assert [item["text"] for item in first_captions] == ["开场", "卖点", "现成字幕"]
    assert first_captions[2]["start"] == 6_000_000
    assert first_captions[2]["end"] == 8_000_000
    assert all("text_effect" not in item for item in first_captions)
    assert all(item["in_animation"] == "入场A" for item in first_captions)
    assert caption_calls[0][2]["font_size"] == 18
    assert caption_calls[0][2]["transform_y"] == -1500.0

    assert audio_calls[0][1][0]["audio_url"] == "https://assets.example.com/bgm.mp3"
    assert audio_calls[0][1][1]["audio_url"] == "https://assets.example.com/sfx.mp3"
    assert effect_calls[0][1][0]["effect_title"] == "特效A"
    assert filter_calls[0][1][0]["filter_title"] == "滤镜A"
    assert filter_calls[0][1][0]["intensity"] == 66
    assert sticker_calls[0][1]["sticker_id"] == "sticker-star"
    assert sticker_calls[0][1]["in_animation"] == "入场A"
    assert result.drafts[0].sticker_segment_ids == ["sticker-segment-1"]
    assert result.drafts[0].duration == 14_000_000
    assert result.drafts[0].applied == ["video", "audio", "captions", "stickers", "effects", "filters"]


def test_smart_packaging_uses_asr_segments_for_captions(monkeypatch):
    caption_calls = []

    def fake_create_draft(width, height):
        return "https://example.com/get_draft?draft_id=2026010100000000000001"

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append(json.loads(captions))
        return draft_url, "track-caption", ["text-id"], ["caption-segment"], []

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    def fake_transcribe_video_to_captions(video_url, asr, local_video_path=None):
        assert video_url == "https://assets.example.com/asr.mp4"
        assert asr.endpoint == "https://model-api.ecmax.cn/v1/audio/transcriptions"
        assert asr.model == "whisper-large-v3"
        assert asr.timestamp_granularities == ["word", "segment"]
        return [
            {"start": 1_000_000, "end": 2_500_000, "text": "ASR 第一段"},
            {"start": 2_500_000, "end": 4_000_000, "text": "ASR 第二段"},
        ]

    monkeypatch.setattr(smart_packaging_module, "create_draft", fake_create_draft)
    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(smart_packaging_module, "transcribe_video_to_captions", fake_transcribe_video_to_captions)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/asr.mp4", "duration": 5_000_000}],
        caption={"enabled": True, "source": "asr", "font_size": 20, "highlight_enabled": False},
        asr={
            "enabled": True,
            "provider": "openai_compatible",
            "endpoint": "https://model-api.ecmax.cn/v1/audio/transcriptions",
            "api_key": "sk-test",
            "model": "whisper-large-v3",
            "timestamp_granularities": ["word", "segment"],
        },
        effects={"enabled": False},
        filters={"enabled": False},
    )

    result = asyncio.run(smart_packaging_func(req))

    assert result.drafts[0].applied == ["video", "captions"]
    assert len(caption_calls) == 1
    assert caption_calls[0][0]["text"] == "ASR 第一段"
    assert caption_calls[0][0]["start"] == 1_000_000
    assert caption_calls[0][0]["end"] == 2_500_000
    assert caption_calls[0][0]["font_size"] == 20


def test_smart_packaging_polishes_asr_text_without_changing_timeline(monkeypatch):
    caption_calls = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000002",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append(json.loads(captions))
        return draft_url, "track-caption", ["text-id"], ["caption-segment"], []

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    def fake_transcribe_video_to_captions(video_url, asr, local_video_path=None):
        return [{"start": 0, "end": 1_200_000, "text": "周意智慧"}]

    def fake_polish_captions_with_llm(captions, llm, fallback_api_key=None):
        assert llm.endpoint == "https://model-api.ecmax.cn/v1/chat/completions"
        assert llm.model == "deepseek-v4-flash"
        assert fallback_api_key == "sk-shared"
        polished = [dict(item) for item in captions]
        polished[0]["text"] = "周易智慧"
        return polished

    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(smart_packaging_module, "transcribe_video_to_captions", fake_transcribe_video_to_captions)
    monkeypatch.setattr(smart_packaging_module, "polish_captions_with_llm", fake_polish_captions_with_llm)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/asr.mp4", "duration": 2_000_000}],
        caption={"enabled": True, "source": "asr", "highlight_enabled": False},
        asr={
            "enabled": True,
            "provider": "openai_compatible",
            "endpoint": "https://model-api.ecmax.cn/v1/audio/transcriptions",
            "api_key": "sk-shared",
            "model": "whisper-large-v3",
        },
        llm_caption={
            "enabled": True,
            "endpoint": "https://model-api.ecmax.cn/v1/chat/completions",
            "model": "deepseek-v4-flash",
        },
        effects={"enabled": False},
        filters={"enabled": False},
    )

    asyncio.run(smart_packaging_func(req))

    assert caption_calls[0][0]["text"] == "周易智慧"
    assert caption_calls[0][0]["start"] == 0
    assert caption_calls[0][0]["end"] == 1_200_000


def test_llm_caption_polish_returns_multiple_highlights(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "index": 0,
                                "text": "铁锈红的一个包身",
                                "highlights": ["铁锈红", "包身", "一个"],
                            }
                        ],
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    def fake_post(url, headers, json=None, timeout=None):
        prompt = json["messages"][0]["content"][0]["text"]
        assert "highlights" in prompt
        assert "形容词、名词、品牌名" in prompt
        assert "xx的xx的" in prompt
        assert "喜欢到这一款包包的" in prompt
        assert "只能返回“包包”" in prompt
        return response

    monkeypatch.setattr("src.service.llm_caption_polish.requests.post", fake_post)

    captions = polish_captions_with_llm(
        [{"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身"}],
        SmartPackagingLlmCaptionConfig(enabled=True, endpoint="https://example.com/chat", model="deepseek-v4-flash"),
        fallback_api_key="sk-shared",
    )

    assert captions[0]["text"] == "铁锈红的一个包身"
    assert captions[0]["highlights"] == ["铁锈红", "包身"]
    assert captions[0]["highlight"] == "铁锈红|包身"


def test_llm_caption_polish_injects_domain_terms_for_model_correction(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "index": 0,
                                "text": "这是格兰芬都宝剑",
                                "highlights": ["格兰芬都", "宝剑"],
                            }
                        ],
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    def fake_post(url, headers, json=None, timeout=None):
        prompt = json["messages"][0]["content"][0]["text"]
        assert "标准词库" in prompt
        assert '"格兰芬多"' in prompt
        assert "同音、近音或错字" in prompt
        return response

    monkeypatch.setattr("src.service.llm_caption_polish.requests.post", fake_post)

    captions = polish_captions_with_llm(
        [{"start": 0, "end": 1_000_000, "text": "这是格兰芬都宝剑"}],
        SmartPackagingLlmCaptionConfig(
            enabled=True,
            endpoint="https://example.com/chat",
            model="deepseek-v4-flash",
            domain_terms=["格兰芬多", "宝剑"],
        ),
        fallback_api_key="sk-shared",
    )

    assert captions[0]["text"] == "这是格兰芬都宝剑"
    assert captions[0]["highlights"] == ["格兰芬都", "宝剑"]
    assert captions[0]["highlight"] == "格兰芬都|宝剑"


def test_llm_caption_polish_uses_model_corrected_domain_terms(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "index": 0,
                                "text": "这是格兰芬多宝剑",
                                "highlights": ["格兰芬多", "宝剑"],
                            }
                        ],
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    monkeypatch.setattr("src.service.llm_caption_polish.requests.post", lambda *args, **kwargs: response)

    captions = polish_captions_with_llm(
        [{"start": 0, "end": 1_000_000, "text": "这是格兰芬都宝剑"}],
        SmartPackagingLlmCaptionConfig(
            enabled=True,
            endpoint="https://example.com/chat",
            model="deepseek-v4-flash",
            domain_terms=["格兰芬多", "宝剑"],
        ),
        fallback_api_key="sk-shared",
    )

    assert captions[0]["text"] == "这是格兰芬多宝剑"
    assert captions[0]["highlights"] == ["格兰芬多", "宝剑"]
    assert captions[0]["highlight"] == "格兰芬多|宝剑"


def test_llm_caption_polish_filters_bad_highlight_phrases(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "index": 0,
                                "text": "带有学院风的一个包身",
                                "highlights": ["学院风的", "一个包", "包身", "这一个", "喜欢的包的"],
                            }
                        ],
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    monkeypatch.setattr("src.service.llm_caption_polish.requests.post", lambda *args, **kwargs: response)

    captions = polish_captions_with_llm(
        [{"start": 0, "end": 1_000_000, "text": "带有学院风的一个包身"}],
        SmartPackagingLlmCaptionConfig(enabled=True, endpoint="https://example.com/chat", model="deepseek-v4-flash"),
    )

    assert captions[0]["highlights"] == ["学院风", "包身"]
    assert captions[0]["highlight"] == "学院风|包身"


def test_llm_caption_polish_filters_sticky_spoken_fragments(monkeypatch):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "index": 0,
                                "text": "如果你们要是有喜欢到这一款包包的",
                                "highlights": ["到这一款包", "包包", "喜欢到这一款包"],
                            }
                        ],
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }

    monkeypatch.setattr("src.service.llm_caption_polish.requests.post", lambda *args, **kwargs: response)

    captions = polish_captions_with_llm(
        [{"start": 0, "end": 1_000_000, "text": "如果你们要是有喜欢到这一款包包的"}],
        SmartPackagingLlmCaptionConfig(enabled=True, endpoint="https://example.com/chat", model="deepseek-v4-flash"),
    )

    assert captions[0]["highlights"] == ["包包"]
    assert captions[0]["highlight"] == "包包"


def test_highlight_filters_spoken_fragment_phrases():
    bad_terms = ["那里是可以", "前方这边还", "前方还做了", "欢这一款包", "到这一款包", "喜欢到这一款包", "下方有到"]
    for term in bad_terms:
        assert not smart_packaging_module._is_valid_highlight_term(term)


def test_smart_packaging_falls_back_to_core_product_highlight_when_llm_term_is_bad():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 3,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [
            {
                "start": 0,
                "end": 1_000_000,
                "text": "如果你们要是有喜欢到这一款包包的",
                "highlights": ["到这一款包", "包包"],
            }
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["包包"]


def test_smart_packaging_only_extracts_product_like_highlights():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 4_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 5,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [{"start": 1_000_000, "end": 2_000_000, "text": "下方有到一把象征着勇气的格兰芬多宝剑"}],
        req,
        smart_packaging_module.random.Random(1),
        4_000_000,
    )

    texts = [item["text"] for item in highlights]
    assert "下方有到" not in texts
    assert set(texts).issubset({"勇气", "格兰芬多", "宝剑"})
    assert texts


def test_smart_packaging_splits_long_captions_semantically(monkeypatch):
    caption_calls = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000003",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append(json.loads(captions))
        return draft_url, "track-caption", ["text-id"], ["caption-segment"], []

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    def fake_transcribe_video_to_captions(video_url, asr, local_video_path=None):
        return [{"start": 0, "end": 3_000_000, "text": "下方有到一把象征着勇气的格兰芬多宝剑"}]

    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(smart_packaging_module, "transcribe_video_to_captions", fake_transcribe_video_to_captions)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/asr.mp4", "duration": 3_000_000}],
        caption={"enabled": True, "source": "asr", "max_chars_per_caption": 10, "highlight_enabled": False},
        asr={"enabled": True, "endpoint": "https://example.com/asr"},
        effects={"enabled": False},
        filters={"enabled": False},
    )

    asyncio.run(smart_packaging_func(req))

    captions = caption_calls[0]
    assert [item["text"] for item in captions] == ["下方有到", "一把象征着勇气的", "格兰芬多宝剑"]
    assert captions[0]["start"] == 0
    assert captions[-1]["end"] == 3_000_000


def test_smart_packaging_adds_highlights_on_separate_track(monkeypatch):
    caption_calls = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000004",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append((json.loads(captions), kwargs))
        return draft_url, "track-caption", ["text-id"], [f"caption-segment-{len(caption_calls)}"], []

    async def fake_add_audios_async(draft_url, audio_infos, **kwargs):
        return draft_url, "track-audio", ["audio-id"]

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "add_audios_async", fake_add_audios_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(
        smart_packaging_module,
        "_write_tone_wav",
        lambda path, tone, duration_seconds=0.34, sample_rate=44100: None,
    )

    req = SmartPackagingRequest(
        videos=[
            {
                "video_url": "https://assets.example.com/manual.mp4",
                "duration": 4_000_000,
                "captions": [
                    {"start": 0, "end": 1_500_000, "text": "商业的本质是信任"},
                    {"start": 1_500_000, "end": 3_000_000, "text": "然后我们继续来看"},
                ],
            }
        ],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_style_mode": "effect",
            "text_effects": ["花字A"],
            "in_animations": ["入场A"],
            "highlight_max_count": 2,
            "highlight_max_chars": 5,
            "highlight_font_size": 30,
        },
        effects={"enabled": False},
        filters={"enabled": False},
        seed=1,
    )

    result = asyncio.run(smart_packaging_func(req))

    assert len(caption_calls) >= 2
    plain_captions, plain_kwargs = caption_calls[0]
    highlight_captions, highlight_kwargs = caption_calls[1]
    assert all("text_effect" not in item for item in plain_captions)
    assert set(plain_captions[0]["keyword"].split("|")).issubset({"本质", "信任"})
    assert plain_captions[0]["keyword"]
    assert plain_captions[0]["keyword_color"] == "#ffe600"
    assert highlight_captions[0]["text"] in {"本质", "信任"}
    assert highlight_captions[0]["text_effect"] == "花字A"
    assert highlight_captions[0]["in_animation"] == "入场A"
    assert abs(highlight_captions[0]["transform_x"]) >= 450.0
    assert 520.0 <= highlight_captions[0]["transform_y"] <= 820.0
    assert highlight_kwargs["transform_y"] == 0.0
    assert plain_kwargs["font_size"] != highlight_kwargs["font_size"]
    assert result.drafts[0].highlight_segment_ids
    assert result.drafts[0].applied == ["video", "captions", "highlights", "audio"]


def test_smart_packaging_extracts_short_product_highlight_terms(monkeypatch):
    caption_calls = []
    audio_calls = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000007",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        caption_calls.append(json.loads(captions))
        return draft_url, "track-caption", ["text-id"], [f"caption-segment-{len(caption_calls)}"], []

    async def fake_add_audios_async(draft_url, audio_infos, **kwargs):
        audio_calls.append(json.loads(audio_infos))
        return draft_url, "track-audio", [f"audio-id-{len(audio_calls)}"]

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "add_audios_async", fake_add_audios_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(
        smart_packaging_module,
        "_write_tone_wav",
        lambda path, tone, duration_seconds=0.34, sample_rate=44100: None,
    )

    req = SmartPackagingRequest(
        videos=[
            {
                "video_url": "https://assets.example.com/product.mp4",
                "duration": 6_000_000,
                "captions": [
                    {"start": 0, "end": 1_000_000, "text": "橘黄色加上这个铁锈红的一个包身"},
                    {"start": 1_000_000, "end": 2_000_000, "text": "一把象征着勇气的格兰芬多宝剑"},
                    {"start": 2_000_000, "end": 3_000_000, "text": "学院的一个压纹设计"},
                ],
            }
        ],
        caption={
            "enabled": True,
            "source": "manual",
            "text_effects": ["花字A"],
            "highlight_max_count": 8,
            "highlight_max_chars": 5,
        },
        sound_effects={"enabled": True, "count": 6, "auto_for_highlights": True, "use_jianying_cache": False},
        effects={"enabled": False},
        filters={"enabled": False},
        seed=3,
    )

    result = asyncio.run(smart_packaging_func(req))

    highlight_texts = [item["text"] for captions in caption_calls[1:] for item in captions]
    assert all(len(text) <= 5 for text in highlight_texts)
    assert "橘黄色" in highlight_texts
    assert "铁锈红" in highlight_texts
    assert "格兰芬多" in highlight_texts
    assert "宝剑" in highlight_texts
    assert "压纹" in highlight_texts
    assert audio_calls
    highlight_audio_infos = [item for audio_track in audio_calls for item in audio_track]
    source_caption_indices = {
        item.get("_source_caption_index")
        for captions in caption_calls[1:]
        for item in captions
    }
    assert source_caption_indices == {0, 1, 2}
    source_caption_count = len(source_caption_indices)
    assert len(highlight_audio_infos) == source_caption_count
    assert highlight_audio_infos[0]["start"] == caption_calls[1][0]["start"]
    assert "local_audio_path" in highlight_audio_infos[0]
    assert result.drafts[0].applied == ["video", "captions", "highlights", "audio"]


def test_smart_packaging_uses_llm_highlight_terms():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_style_mode": "effect",
            "text_effects": ["花字A"],
            "highlight_max_count": 3,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [{"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红", "包身"]}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "包身"]
    assert highlights[0]["start"] == 0
    assert highlights[1]["start"] > highlights[0]["start"]
    assert highlights[1]["end"] <= 3_000_000
    assert highlights[0]["font_size"] == req.caption.highlight_font_size
    assert highlights[0]["text_effect"] == "花字A"


def test_smart_packaging_limits_text_template_highlights_to_two_per_source_caption():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 6,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [
            {
                "start": 0,
                "end": 1_000_000,
                "text": "铁锈红包身压纹拉链",
                "highlights": ["铁锈红", "包身", "压纹", "拉链"],
            }
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "包身"]
    assert len([item for item in highlights if item["_source_caption_index"] == 0]) == 2


def test_smart_packaging_skips_next_caption_after_highlight_caption_for_normal_terms():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 6_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 6,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [
            {"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红", "包身"]},
            {"start": 1_000_000, "end": 2_000_000, "text": "整体质感很好", "highlights": ["质感"]},
            {"start": 2_000_000, "end": 3_000_000, "text": "压纹设计", "highlights": ["压纹"]},
            {"start": 3_000_000, "end": 4_000_000, "text": "整体做工不错", "highlights": ["做工"]},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "包身", "压纹"]
    assert {item["_source_caption_index"] for item in highlights} == {0, 2}


def test_smart_packaging_allows_high_priority_terms_during_caption_cooldown():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 6_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 6,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [
            {"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红", "包身"]},
            {"start": 1_000_000, "end": 2_000_000, "text": "格兰芬多宝剑", "highlights": ["格兰芬多", "宝剑", "质感"]},
            {"start": 2_000_000, "end": 3_000_000, "text": "压纹设计", "highlights": ["压纹"]},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "包身", "格兰芬多", "宝剑", "压纹"]
    assert {item["_source_caption_index"] for item in highlights} == {0, 1, 2}


def test_smart_packaging_uses_later_caption_when_cooldown_caption_has_no_highlight():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 6_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_max_count": 6,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [
            {"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红"]},
            {"start": 1_000_000, "end": 2_000_000, "text": "整体质感很好", "highlights": ["质感"]},
            {"start": 2_000_000, "end": 3_000_000, "text": "然后我们继续看"},
            {"start": 3_000_000, "end": 4_000_000, "text": "拉链隔层", "highlights": ["拉链"]},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "拉链"]
    assert {item["_source_caption_index"] for item in highlights} == {0, 3}


def test_smart_packaging_applies_highlight_terms_to_plain_caption_keywords():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "keyword_color": "#ffff00",
            "keyword_border_color": "#111111",
            "font_size": 12,
        },
    )
    plain_captions = [{"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "font_size": 12}]
    highlight_captions = [
        {"_source_caption_index": 0, "text": "铁锈红"},
        {"_source_caption_index": 0, "text": "包身"},
    ]

    styled = smart_packaging_module._apply_highlight_keywords_to_plain_captions(
        plain_captions,
        highlight_captions,
        req,
    )

    assert styled[0]["keyword"] == "铁锈红|包身"
    assert styled[0]["keyword_color"] == "#ffff00"
    assert styled[0]["keyword_border_color"] == "#111111"
    assert styled[0]["keyword_font_size"] == 12


def test_plain_caption_keywords_are_not_filtered_by_template_cooldown():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "keyword_color": "#ffff00",
            "highlight_max_count": 6,
            "highlight_max_chars": 5,
        },
    )
    captions = [
        {"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红"]},
        {"start": 1_000_000, "end": 2_000_000, "text": "整体质感很好", "highlights": ["质感"]},
    ]

    template_highlights = smart_packaging_module._build_highlight_captions(
        captions,
        req,
        smart_packaging_module.random.Random(1),
    )
    keyword_highlights = smart_packaging_module._build_plain_caption_keyword_highlights(captions, req)
    styled = smart_packaging_module._apply_highlight_keywords_to_plain_captions(
        captions,
        keyword_highlights,
        req,
    )

    assert [item["text"] for item in template_highlights] == ["铁锈红"]
    assert styled[0]["keyword"] == "铁锈红"
    assert styled[1]["keyword"] == "质感"
    assert styled[1]["keyword_color"] == "#ffff00"


def test_plain_caption_keywords_keep_more_than_two_terms_per_caption():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "keyword_color": "#ffff00",
            "highlight_max_chars": 5,
        },
    )
    captions = [
        {
            "start": 0,
            "end": 1_000_000,
            "text": "铁锈红包身压纹拉链",
            "highlights": ["铁锈红", "包身", "压纹", "拉链"],
        }
    ]

    keyword_highlights = smart_packaging_module._build_plain_caption_keyword_highlights(captions, req)
    styled = smart_packaging_module._apply_highlight_keywords_to_plain_captions(
        captions,
        keyword_highlights,
        req,
    )

    assert styled[0]["keyword"] == "铁锈红|包身|压纹|拉链"


def test_smart_packaging_can_use_text_effect_highlight_mode():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "text_effects": ["花字A"],
            "highlight_style_mode": "effect",
            "highlight_max_count": 1,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [{"start": 0, "end": 1_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红"]}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert highlights[0]["text_effect"] == "花字A"
    assert highlights[0]["font_size"] == req.caption.highlight_font_size


def test_smart_packaging_staggers_same_caption_highlights_by_text_position():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_style_mode": "effect",
            "text_effects": ["花字A"],
            "highlight_max_count": 3,
            "highlight_max_chars": 5,
        },
    )

    highlights = smart_packaging_module._build_highlight_captions(
        [{"start": 1_000_000, "end": 2_000_000, "text": "铁锈红的一个包身", "highlights": ["铁锈红", "包身"]}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert [item["text"] for item in highlights] == ["铁锈红", "包身"]
    assert highlights[0]["start"] == 1_000_000
    assert highlights[1]["start"] > highlights[0]["start"]
    assert highlights[1]["end"] <= 3_000_000


def test_smart_packaging_keeps_llm_highlights_on_matching_split_caption():
    caption = {
        "start": 0,
        "end": 2_000_000,
        "text": "一把象征着勇气的格兰芬多宝剑",
        "highlights": ["勇气", "宝剑"],
        "highlight": "勇气|宝剑",
    }

    split_captions = smart_packaging_module._split_caption_by_max_chars(caption, 10)

    assert [item["text"] for item in split_captions] == ["一把象征着勇气的", "格兰芬多宝剑"]
    assert split_captions[0]["highlights"] == ["勇气"]
    assert split_captions[1]["highlights"] == ["宝剑"]


def test_smart_packaging_builds_contextual_sticker_infos(monkeypatch):
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_sticker_data",
        lambda: [
            {"sticker_id": "magic-1", "title": "魔法闪光"},
            {"sticker_id": "arrow-1", "title": "重点箭头"},
        ],
    )
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        stickers={"enabled": True, "count": 2, "duration": 500_000},
    )

    sticker_infos = smart_packaging_module._build_sticker_infos(
        3_000_000,
        [{"start": 0, "end": 1_000_000, "text": "一把象征着勇气的格兰芬多宝剑"}],
        [{"start": 0, "end": 1_000_000, "text": "宝剑"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert sticker_infos
    assert sticker_infos[0]["keyword"] in {"魔法", "闪光", "星星", "宝剑"}
    assert sticker_infos[0]["sticker_id"] in {"magic-1", "arrow-1"}
    assert sticker_infos[0]["start"] == 0
    assert sticker_infos[0]["end"] == 500_000


def test_smart_packaging_places_sticker_near_highlight_anchor(monkeypatch):
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_sticker_data",
        lambda: [{"sticker_id": "magic-1", "title": "魔法闪光"}],
    )
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        stickers={"enabled": True, "count": 1, "duration": 500_000},
    )

    sticker_infos = smart_packaging_module._build_sticker_infos(
        3_000_000,
        [],
        [{"start": 0, "end": 1_000_000, "text": "宝剑", "transform_x": 320, "transform_y": -420}],
        req,
        smart_packaging_module.random.Random(2),
    )

    assert sticker_infos
    assert sticker_infos[0]["transform_x"] < 320
    assert -720 <= sticker_infos[0]["transform_y"] <= 180


def test_smart_packaging_allows_highlights_from_same_caption_to_overlap():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "enabled": True,
            "source": "manual",
            "highlight_style_mode": "effect",
            "text_effects": ["花字A"],
            "highlight_max_count": 3,
            "highlight_max_chars": 5,
        },
    )
    highlights = smart_packaging_module._build_highlight_captions(
        [{"start": 1_000_000, "end": 2_500_000, "text": "铁锈红的一个包身"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert len(highlights) >= 2
    assert highlights[0]["start"] == 1_000_000
    assert highlights[1]["start"] > highlights[0]["start"]
    assert highlights[0]["end"] <= highlights[1]["end"]
    assert highlights[0]["_source_caption_index"] == highlights[1]["_source_caption_index"] == 0
    assert highlights[0]["_source_caption_start"] == highlights[1]["_source_caption_start"] == 1_000_000
    assert abs(highlights[0]["transform_x"] - highlights[1]["transform_x"]) >= 120
    assert abs(highlights[0]["transform_y"] - highlights[1]["transform_y"]) >= 100
    first_bounds = smart_packaging_module._highlight_text_bounds(
        highlights[0]["transform_x"],
        highlights[0]["transform_y"],
        highlights[0]["text"],
        highlights[0]["font_size"],
    )
    second_bounds = smart_packaging_module._highlight_text_bounds(
        highlights[1]["transform_x"],
        highlights[1]["transform_y"],
        highlights[1]["text"],
        highlights[1]["font_size"],
    )
    assert not smart_packaging_module._bounds_overlap(first_bounds, second_bounds)
    assert all(1_000_000 <= item["start"] < item["end"] <= 2_500_000 for item in highlights)


def test_highlight_positions_prefer_upper_left_or_right_slots():
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        caption={
            "highlight_transform_x_min": -782,
            "highlight_transform_x_max": 780,
            "highlight_transform_y_min": 520,
            "highlight_transform_y_max": 820,
        },
    )
    randomizer = smart_packaging_module.random.Random(1)

    positions = [
        smart_packaging_module._spread_highlight_position(index, req, randomizer, text="宝剑")
        for index in range(4)
    ]

    assert all((-782 <= x <= -600) or (600 <= x <= 780) for x, _ in positions)
    assert all(520 <= y <= 820 for _, y in positions)
    assert all(y >= 540 for _, y in positions)


def test_smart_packaging_splits_overlapping_highlights_into_multiple_tracks():
    tracks = smart_packaging_module._split_overlapping_captions_into_tracks(
        [
            {"start": 1_000_000, "end": 2_000_000, "text": "铁锈红"},
            {"start": 1_000_000, "end": 2_000_000, "text": "包身"},
            {"start": 2_000_000, "end": 2_500_000, "text": "拉链"},
        ]
    )

    assert len(tracks) == 2
    assert [item["text"] for item in tracks[0]] == ["铁锈红", "拉链"]
    assert [item["text"] for item in tracks[1]] == ["包身"]


def test_smart_packaging_splits_overlapping_highlight_sounds_into_multiple_tracks():
    tracks = smart_packaging_module._split_overlapping_audio_infos_into_tracks(
        [
            {"start": 1_000_000, "end": 2_000_000, "local_audio_path": "/tmp/a.mp3"},
            {"start": 1_000_000, "end": 2_000_000, "local_audio_path": "/tmp/b.mp3"},
            {"start": 2_000_000, "end": 2_500_000, "local_audio_path": "/tmp/c.mp3"},
        ]
    )

    assert len(tracks) == 2
    assert [item["local_audio_path"] for item in tracks[0]] == ["/tmp/a.mp3", "/tmp/c.mp3"]
    assert [item["local_audio_path"] for item in tracks[1]] == ["/tmp/b.mp3"]


def test_smart_packaging_uses_selected_highlight_sound_names(monkeypatch):
    tones = []
    monkeypatch.setattr(
        smart_packaging_module,
        "_write_tone_wav",
        lambda path, tone, duration_seconds=0.34, sample_rate=44100: tones.append(tone),
    )
    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "enabled": True,
            "count": 1,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["砰，拳击声"],
            "use_jianying_cache": False,
        },
    )
    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [{"start": 0, "end": 800_000, "text": "格兰芬多"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert tones == ["impact"]
    assert len(audio_infos) == 1
    assert "local_audio_path" in audio_infos[0]


def test_text_template_selection_avoids_reuse_when_enough_entries():
    entries = [
        {"name": "模板A", "material_id": "mat-a", "effect_id": "effect-a", "package_dir": "/tmp/a"},
        {"name": "模板B", "material_id": "mat-b", "effect_id": "effect-b", "package_dir": "/tmp/b"},
        {"name": "模板C", "material_id": "mat-c", "effect_id": "effect-c", "package_dir": "/tmp/c"},
    ]
    used_effects = set()
    used_materials = set()
    randomizer = smart_packaging_module.random.Random(4)

    effects = [
        smart_packaging_module._choose_jianying_text_template_effect(entries, [], randomizer, used_effects)
        for _ in range(3)
    ]
    selected_entries = [
        smart_packaging_module._choose_jianying_text_template_entry(entries, [], randomizer, used_materials)
        for _ in range(3)
    ]

    assert len(set(effects)) == 3
    assert len({entry["material_id"] for entry in selected_entries}) == 3


def test_text_template_loader_excludes_unwanted_template_names(monkeypatch, tmp_path):
    key_value_path = tmp_path / "key_value.json"
    key_value_path.write_text(
        json.dumps(
            {
                "mat-good": {
                    "materialSubcategory": "text_template",
                    "materialId": "mat-good",
                    "materialName": "新品首发",
                    "segmentId": "seg-good",
                    "rank": 1,
                },
                "mat-bad": {
                    "materialSubcategory": "text_template",
                    "materialId": "mat-bad",
                    "materialName": "超值好物",
                    "segmentId": "seg-bad",
                    "rank": 2,
                },
                "mat-style": {
                    "materialSubcategory": "text_template",
                    "materialId": "mat-style",
                    "materialName": "简约盐系穿搭",
                    "segmentId": "seg-style",
                    "rank": 3,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_text_template_cache_info",
        lambda material_id, cache_dir: {"package_dir": "", "effect_ids": [], "default_texts": []},
    )

    entries = smart_packaging_module._load_jianying_text_template_entries(str(tmp_path), str(tmp_path))

    assert [entry["name"] for entry in entries] == ["新品首发"]


def test_text_template_loader_dedupes_same_template_name_and_package(monkeypatch, tmp_path):
    key_value_path = tmp_path / "key_value.json"
    key_value_path.write_text(
        json.dumps(
            {
                "mat-a": {
                    "materialSubcategory": "text_template",
                    "materialId": "mat-a",
                    "materialName": "新品首发",
                    "segmentId": "seg-a",
                    "rank": 2,
                },
                "mat-b": {
                    "materialSubcategory": "text_template",
                    "materialId": "mat-b",
                    "materialName": "新品首发",
                    "segmentId": "seg-b",
                    "rank": 1,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_text_template_cache_info",
        lambda material_id, cache_dir: {"package_dir": "/tmp/template-a", "effect_ids": ["effect-a"], "default_texts": []},
    )

    entries = smart_packaging_module._load_jianying_text_template_entries(str(tmp_path), str(tmp_path))

    assert len(entries) == 1
    assert entries[0]["material_id"] == "mat-b"


def test_text_template_selection_reuses_only_after_pool_exhausted():
    entries = [
        {"name": "模板A", "material_id": "mat-a", "effect_id": "effect-a", "package_dir": "/tmp/a"},
        {"name": "模板B", "material_id": "mat-b", "effect_id": "effect-b", "package_dir": "/tmp/b"},
    ]
    used = set()
    randomizer = smart_packaging_module.random.Random(6)

    selected = [
        smart_packaging_module._choose_jianying_text_template_entry(entries, [], randomizer, used)
        for _ in range(3)
    ]

    assert len({entry["material_id"] for entry in selected[:2]}) == 2
    assert selected[2]["material_id"] in {"mat-a", "mat-b"}


def test_text_template_anchor_is_shifted_inside_visible_area():
    script = type("Script", (), {"width": 1080, "height": 1920})()
    highlight = {"transform_x": 500, "transform_y": 850, "text": "包包", "font_size": 28}
    children = [
        {
            "type": "text",
            "original_size": [420, 160],
            "position": [160, 120, 0],
            "scale": [1.5, 1.5, 1],
        }
    ]

    adjusted = smart_packaging_module._shift_highlight_to_keep_template_visible(script, highlight, children)
    bounds = smart_packaging_module._merge_bounds([
        smart_packaging_module._template_child_bounds(child, adjusted) for child in children
    ])

    assert adjusted["transform_x"] < highlight["transform_x"]
    assert adjusted["transform_y"] < highlight["transform_y"]
    assert bounds[2] <= script.width / 2 - smart_packaging_module.TEXT_TEMPLATE_SAFE_MARGIN_X
    assert bounds[3] <= script.height / 2 - smart_packaging_module.TEXT_TEMPLATE_SAFE_MARGIN_Y


def test_text_template_anchor_keeps_position_when_already_visible():
    script = type("Script", (), {"width": 1080, "height": 1920})()
    highlight = {"transform_x": 0, "transform_y": 0, "text": "包包", "font_size": 28}
    children = [
        {
            "type": "text",
            "original_size": [240, 120],
            "position": [0, 0, 0],
            "scale": [1, 1, 1],
        }
    ]

    adjusted = smart_packaging_module._shift_highlight_to_keep_template_visible(script, highlight, children)

    assert adjusted is highlight


def test_text_template_aligns_transform_x_to_requested_side_ranges():
    script = type("Script", (), {"width": 1080, "height": 1920})()
    children = [
        {
            "type": "text",
            "original_size": [600, 180],
            "position": [0, 0, 0],
            "scale": [1, 1, 1],
        }
    ]

    left = smart_packaging_module._align_highlight_template_to_side(
        script,
        {"transform_x": -300, "transform_y": 700, "text": "宝剑", "font_size": 28},
        children,
    )
    right = smart_packaging_module._align_highlight_template_to_side(
        script,
        {"transform_x": 300, "transform_y": 700, "text": "宝剑", "font_size": 28},
        children,
    )
    assert -782.0 <= left["transform_x"] <= -600.0
    assert 600.0 <= right["transform_x"] <= 780.0
    assert script.height / 2 - script.height * 0.70 <= left["transform_y"] <= script.height / 2
    assert script.height / 2 - script.height * 0.70 <= right["transform_y"] <= script.height / 2


def test_text_template_transform_x_is_clamped_to_requested_side_ranges():
    script = type("Script", (), {"width": 1080, "height": 1920})()
    children = [
        {
            "type": "text",
            "original_size": [600, 180],
            "position": [0, 0, 0],
            "scale": [1, 1, 1],
        }
    ]

    adjusted = smart_packaging_module._shift_highlight_template_inside_top_regions(
        script,
        {"transform_x": 200, "transform_y": -400, "text": "宝剑", "font_size": 28},
        children,
    )
    assert 600.0 <= adjusted["transform_x"] <= 780.0
    assert script.height / 2 - script.height * 0.70 <= adjusted["transform_y"] <= script.height / 2


def test_text_template_auto_scale_uses_stable_random_range():
    randomizer = smart_packaging_module.random.Random(1)
    highlight = {"text": "宝剑", "font_size": 17}
    children = [
        {
            "type": "text",
            "position": [220, 120, 0],
            "scale": [1.6, 1.6, 1],
            "original_size": [900, 420],
        },
        {
            "type": "sticker",
            "position": [-180, -80, 0],
            "scale": [1.2, 1.2, 1],
            "original_size": [520, 360],
        },
    ]

    scale = smart_packaging_module._auto_text_template_scale(randomizer, highlight)
    scaled = smart_packaging_module._scaled_template_children(children, scale)

    assert smart_packaging_module.TEXT_TEMPLATE_AUTO_SCALE_MIN <= scale
    assert scale <= smart_packaging_module.TEXT_TEMPLATE_AUTO_SCALE_MAX
    assert scaled[0]["scale"][0] == pytest.approx(scale)
    assert scaled[1]["scale"][0] == pytest.approx(children[1]["scale"][0] * scale / children[0]["scale"][0])
    assert abs(scaled[0]["position"][0]) == pytest.approx(abs(children[0]["position"][0] * scale / 1.6))
    assert scaled[0]["scale"][0] / children[0]["scale"][0] == pytest.approx(scaled[0]["scale"][1] / children[0]["scale"][1])
    assert scaled[1]["scale"][0] / children[1]["scale"][0] == pytest.approx(scaled[1]["scale"][1] / children[1]["scale"][1])


def test_text_template_scaling_keeps_small_sticker_relative_size():
    children = [
        {"type": "text", "position": [0, 0, 0], "scale": [2.0, 2.0, 1], "original_size": [500, 160]},
        {"type": "sticker", "position": [100, 30, 0], "scale": [0.08, 0.08, 1], "original_size": [200, 200]},
    ]

    scaled = smart_packaging_module._scaled_template_children(children, 1.0)

    assert scaled[0]["scale"][0] == pytest.approx(1.0)
    assert scaled[1]["scale"][0] == pytest.approx(0.04)
    assert scaled[1]["position"][0] == pytest.approx(50)


def test_text_template_scaling_keeps_relative_positions_uniformly():
    children = [
        {"type": "text", "position": [200, 100, 0], "scale": [2.0, 2.0, 1], "original_size": [500, 160]},
        {"type": "sticker", "position": [-300, -150, 0], "scale": [0.4, 0.4, 1], "original_size": [200, 200]},
    ]

    scaled = smart_packaging_module._scaled_template_children(children, 0.5)

    assert scaled[0]["position"][0] == pytest.approx(50)
    assert scaled[0]["position"][1] == pytest.approx(25)
    assert scaled[1]["position"][0] == pytest.approx(-75)
    assert scaled[1]["position"][1] == pytest.approx(-37.5)
    assert scaled[1]["position"][0] - scaled[0]["position"][0] == pytest.approx((-300 - 200) * 0.25)
    assert scaled[1]["position"][1] - scaled[0]["position"][1] == pytest.approx((-150 - 100) * 0.25)


def test_text_template_highlight_keeps_only_primary_text_layer():
    children = [
        {"type": "text", "order_in_layer": 1, "scale": [0.8, 0.8, 1], "original_size": [300, 120]},
        {"type": "text", "order_in_layer": 2, "scale": [1.4, 1.4, 1], "original_size": [600, 180]},
        {"type": "sticker", "order_in_layer": 3, "scale": [0.2, 0.2, 1], "original_size": [120, 120]},
    ]

    visible = smart_packaging_module._template_visible_children_for_highlight(children)

    assert [item["type"] for item in visible] == ["text", "sticker"]
    assert visible[0]["original_size"] == [600, 180]


def test_text_template_uses_template_font_size_for_material_content():
    child = {
        "type": "text",
        "text_params": {
            "richText": '<effectStyle id="effect-a" path=""><size=15><font id="font-a" path="">[宝藏单品]</font></size></effectStyle>',
        },
    }

    content = smart_packaging_module._template_text_material_content(child, "铁锈红")

    assert content["styles"][0]["size"] == pytest.approx(15)
    assert content["text"] == "铁锈红"


def test_text_template_layout_preserves_original_child_positions():
    children = [
        {
            "type": "sticker",
            "position": [-300, 0, 0],
            "scale": [1, 1, 1],
            "layout_params": {"left_toLeftOf": "@text-a", "right_toRightOf": ""},
        },
        {
            "type": "text",
            "name": "text-a",
            "position": [0, 0, 0],
            "scale": [2, 2, 1],
            "original_size": [300, 90],
            "text_params": {
                "richText": '<effectStyle id="effect-a" path=""><size=15><font id="font-a" path="">[超级福利日]</font></size></effectStyle>',
            },
        },
        {
            "type": "sticker",
            "position": [300, 0, 0],
            "scale": [1, 1, 1],
            "layout_params": {"left_toLeftOf": "", "right_toRightOf": "@text-a"},
        },
    ]

    laid_out = smart_packaging_module._layout_template_children_for_text(children, "好用")

    assert laid_out[0]["position"] == children[0]["position"]
    assert laid_out[2]["position"] == children[2]["position"]


def test_text_template_layout_preserves_original_child_scale():
    children = [
        {
            "type": "text",
            "name": "text-a",
            "position": [0, 0, 0],
            "scale": [2, 2, 1],
            "original_size": [300, 90],
            "text_params": {
                "richText": '<effectStyle id="effect-a" path=""><size=15><font id="font-a" path="">[好物]</font></size></effectStyle>',
            },
        },
        {
            "type": "sticker",
            "position": [0, -90, 0],
            "scale": [1, 1, 1],
            "layout_params": {"left_toLeftOf": "@text-a", "right_toRightOf": "@text-a"},
        },
    ]

    laid_out = smart_packaging_module._layout_template_children_for_text(children, "超级福利日")

    assert laid_out[1]["scale"] == children[1]["scale"]


def test_text_template_2_layers_keep_effects_and_animations(monkeypatch, tmp_path):
    template_entries = smart_packaging_module._load_jianying_text_template_entries(
        smart_packaging_module.DEFAULT_JIANYING_TEXT_TEMPLATE_DRAFT_DIR,
    )
    template_entry = next(
        (
            entry for entry in template_entries
            if entry.get("package_dir") and entry.get("effect_ids") and entry.get("name") == "好用单品"
        ),
        None,
    )
    if not template_entry:
        pytest.skip("文字模板2 cache is not available on this machine")

    draft_dir = tmp_path / "drafts"
    monkeypatch.setattr("config.DRAFT_DIR", str(draft_dir))

    draft_url = smart_packaging_module.create_draft(1080, 1920)
    draft_id = draft_url.split("draft_id=")[-1]
    script = smart_packaging_module.DRAFT_CACHE[draft_id]
    segment_ids = smart_packaging_module._add_text_template_layers_to_draft(
        draft_url,
        {
            "text": "宝剑",
            "start": 1_000_000,
            "end": 3_800_000,
            "_source_caption_index": 0,
            "_source_caption_end": 3_800_000,
            "font_size": 17,
            "transform_x": -700,
            "transform_y": 700,
        },
        template_entry,
    )

    assert len(segment_ids) >= 2
    assert script.materials.animations
    assert any(animation.animations for animation in script.materials.animations)
    assert any(
        getattr(effect, "effect_id", "") in template_entry["effect_ids"]
        for effect in script.materials.filters
    )
    assert any(track.track_type == smart_packaging_module.draft.TrackType.sticker for track in script.tracks.values())


def test_template_highlight_range_extends_around_source_caption():
    start, end = smart_packaging_module._timed_highlight_range(
        {"start": 1_000_000, "end": 1_500_000, "text": "铁锈红包身"},
        "包身",
        prefer_template_duration=True,
        video_duration=4_000_000,
    )

    assert start < 1_500_000
    assert end > 1_500_000
    assert end - start >= smart_packaging_module.TEXT_TEMPLATE_MIN_DISPLAY_DURATION


def test_smart_packaging_prefers_jianying_cached_sound_file(monkeypatch, tmp_path):
    cached_audio = tmp_path / "impact.mp3"
    cached_audio.write_bytes(b"fake mp3")

    monkeypatch.setattr(
        smart_packaging_module,
        "_build_jianying_sound_path_map",
        lambda req: {"砰，拳击声": str(cached_audio)},
    )
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 2_400_000)
    monkeypatch.setattr(
        smart_packaging_module,
        "_write_tone_wav",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should use cached audio")),
    )

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "enabled": True,
            "count": 1,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["砰，拳击声"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [{"start": 0, "end": 800_000, "text": "格兰芬多"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert audio_infos == [
        {
            "local_audio_path": str(cached_audio),
            "start": 0,
            "end": 800_000,
            "duration": 800_000,
            "volume": 0.55,
        }
    ]


def test_smart_packaging_offsets_dense_highlight_sounds_from_different_captions(monkeypatch, tmp_path):
    cached_audio = tmp_path / "pop.mp3"
    cached_audio.write_bytes(b"fake mp3")
    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: {"啵1": str(cached_audio)})
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 360_000)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "enabled": True,
            "count": 3,
            "duration": 360_000,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["啵1"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [
            {"start": 1_000_000, "end": 1_600_000, "text": "压纹"},
            {"start": 1_100_000, "end": 1_800_000, "text": "拉链"},
            {"start": 1_800_000, "end": 2_300_000, "text": "宝剑"},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert audio_infos[0]["start"] == 1_000_000
    assert audio_infos[1]["start"] == 1_380_000
    assert audio_infos[2]["start"] == 1_800_000
    assert audio_infos[0]["end"] <= audio_infos[1]["start"]
    assert audio_infos[1]["end"] <= audio_infos[2]["start"]


def test_smart_packaging_keeps_one_sound_for_same_caption_highlights(monkeypatch, tmp_path):
    cached_audio = tmp_path / "pop.mp3"
    cached_audio.write_bytes(b"fake mp3")
    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: {"啵1": str(cached_audio)})
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 360_000)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "enabled": True,
            "count": 2,
            "duration": 360_000,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["啵1"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [
            {"start": 1_000_000, "end": 1_500_000, "text": "压纹", "_source_caption_index": 0},
            {"start": 1_260_000, "end": 1_500_000, "text": "拉链", "_source_caption_index": 0},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert len(audio_infos) == 1
    assert audio_infos[0]["start"] == 1_000_000
    assert audio_infos[0]["end"] == 1_360_000


def test_smart_packaging_avoids_reusing_highlight_sounds_when_pool_is_enough(monkeypatch, tmp_path):
    sound_paths = {}
    for name in ["啵1", "唰", "叮"]:
        path = tmp_path / f"{name}.mp3"
        path.write_bytes(b"fake mp3")
        sound_paths[name] = str(path)
    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: sound_paths)
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 200_000)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 4_000_000}],
        sound_effects={
            "enabled": True,
            "count": 3,
            "duration": 200_000,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["啵1", "唰", "叮"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [
            {"start": 0, "end": 600_000, "text": "包包"},
            {"start": 800_000, "end": 1_400_000, "text": "好物"},
            {"start": 1_600_000, "end": 2_200_000, "text": "喜欢"},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    used_paths = [item["local_audio_path"] for item in audio_infos]
    assert len(used_paths) == 3
    assert len(set(used_paths)) == 3


def test_smart_packaging_reuses_highlight_sounds_after_pool_is_exhausted(monkeypatch, tmp_path):
    sound_paths = {}
    for name in ["啵1", "唰"]:
        path = tmp_path / f"{name}.mp3"
        path.write_bytes(b"fake mp3")
        sound_paths[name] = str(path)
    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: sound_paths)
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 200_000)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 4_000_000}],
        sound_effects={
            "enabled": True,
            "count": 3,
            "duration": 200_000,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["啵1", "唰"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [
            {"start": 0, "end": 600_000, "text": "包包"},
            {"start": 800_000, "end": 1_400_000, "text": "好物"},
            {"start": 1_600_000, "end": 2_200_000, "text": "喜欢"},
        ],
        req,
        smart_packaging_module.random.Random(1),
    )

    used_paths = [item["local_audio_path"] for item in audio_infos]
    assert len(used_paths) == 3
    assert len(set(used_paths)) == 2


def test_smart_packaging_caps_cached_sound_to_highlight_duration(monkeypatch, tmp_path):
    cached_audio = tmp_path / "magic.mp3"
    cached_audio.write_bytes(b"fake mp3")
    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: {"Magic reveal": str(cached_audio)})
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 3_210_000)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 8_000_000}],
        sound_effects={
            "enabled": True,
            "count": 1,
            "duration": 360_000,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["Magic reveal"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [{"start": 1_000_000, "end": 1_800_000, "text": "橘黄色"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert audio_infos[0]["start"] == 1_000_000
    assert audio_infos[0]["end"] == 1_800_000
    assert audio_infos[0]["duration"] == 800_000


def test_smart_packaging_sound_effects_exposes_preview_urls(monkeypatch, tmp_path):
    cached_audio = tmp_path / "magic.mp3"
    cached_audio.write_bytes(b"fake mp3")
    preview_audio = tmp_path / "preview.mp3"
    preview_audio.write_bytes(b"fake mp3")
    empty_preview_dir = tmp_path / "empty_previews"
    empty_preview_dir.mkdir()
    monkeypatch.setattr(smart_packaging_module, "SOUND_EFFECT_PREVIEW_DIR", str(empty_preview_dir))

    monkeypatch.setattr(
        smart_packaging_module,
        "_load_jianying_sound_entries",
        lambda sound_draft_dir=None: [{"name": "Magic reveal", "material_id": "7179145118102916355"}],
    )
    monkeypatch.setattr(
        smart_packaging_module,
        "_build_jianying_sound_path_map",
        lambda req: {"Magic reveal": str(cached_audio)},
    )
    monkeypatch.setattr(
        smart_packaging_module,
        "_preview_audio_path",
        lambda material_id, audio_path: str(preview_audio),
    )
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 2_000_000)

    result = smart_packaging_module.get_smart_packaging_sound_effects(
        SmartPackagingSoundEffectsRequest(),
        "http://localhost:30000",
    )

    assert len(result.sound_effects) == 1
    assert result.sound_effects[0].name == "Magic reveal"
    assert result.sound_effects[0].preview_url == "http://localhost:30000/output/sound_effect_previews/preview.mp3"
    assert result.sound_effects[0].duration == 2_000_000


def test_smart_packaging_sound_effects_use_preview_file_names(monkeypatch, tmp_path):
    preview_dir = tmp_path / "previews"
    preview_dir.mkdir()
    first_audio = preview_dir / "咻.mp3"
    second_audio = preview_dir / "爆炸声.mp3"
    first_audio.write_bytes(b"fake first mp3")
    second_audio.write_bytes(b"fake second mp3")

    monkeypatch.setattr(smart_packaging_module, "SOUND_EFFECT_PREVIEW_DIR", str(preview_dir))
    monkeypatch.setattr(smart_packaging_module, "_audio_duration_or_default", lambda path, default_duration: 1_000_000)

    result = smart_packaging_module.get_smart_packaging_sound_effects(
        SmartPackagingSoundEffectsRequest(),
        "http://localhost:30000",
    )

    assert [item.name for item in result.sound_effects] == ["咻", "爆炸声"]
    assert result.sound_effects[0].preview_url == "http://localhost:30000/output/sound_effect_previews/咻.mp3"

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}]
    )
    sound_path_map = smart_packaging_module._build_jianying_sound_path_map(req)

    assert sound_path_map["咻"] == str(first_audio)
    assert sound_path_map["爆炸声"] == str(second_audio)


def test_smart_packaging_maps_jianying_sound_by_material_id_hash(monkeypatch, tmp_path):
    cache_dir = tmp_path / "music"
    cache_dir.mkdir()
    correct_audio = cache_dir / "correct.mp3"
    wrong_audio = cache_dir / "wrong.mp3"
    correct_audio.write_bytes(b"correct mp3")
    wrong_audio.write_bytes(b"wrong mp3")
    material_id = "6896679333541285133"
    (cache_dir / "downLoadcfg").write_text(
        json.dumps(
            {
                "list": [
                    {"date": "1", "hex": "not-this-material", "path": wrong_audio.name},
                    {
                        "date": "2",
                        "hex": hashlib.md5(material_id.encode("utf-8")).hexdigest(),
                        "path": correct_audio.name,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    empty_preview_dir = tmp_path / "empty_previews"
    empty_preview_dir.mkdir()
    monkeypatch.setattr(smart_packaging_module, "SOUND_EFFECT_PREVIEW_DIR", str(empty_preview_dir))
    monkeypatch.setattr(
        smart_packaging_module,
        "_load_jianying_sound_entries",
        lambda sound_draft_dir=None: [{"name": "滴，提示音", "material_id": material_id}],
    )

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "jianying_sound_draft_dir": "/tmp/sound-draft",
            "jianying_cache_dir": str(cache_dir),
        },
    )

    sound_path_map = smart_packaging_module._build_jianying_sound_path_map(req)

    assert sound_path_map["滴，提示音"] == str(correct_audio)


def test_smart_packaging_does_not_use_unmatched_cached_sound(monkeypatch, tmp_path):
    cached_audio = tmp_path / "ding.mp3"
    cached_audio.write_bytes(b"fake mp3")
    fallback_tones = []

    monkeypatch.setattr(smart_packaging_module, "_build_jianying_sound_path_map", lambda req: {"Ding，可爱提示音": str(cached_audio)})
    monkeypatch.setattr(
        smart_packaging_module,
        "_write_tone_wav",
        lambda path, tone, duration_seconds=0.34, sample_rate=44100: fallback_tones.append(tone),
    )

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/product.mp4", "duration": 3_000_000}],
        sound_effects={
            "enabled": True,
            "count": 1,
            "auto_for_highlights": True,
            "highlight_sound_effects": ["不存在的剪映音效"],
            "use_jianying_cache": True,
        },
    )

    audio_infos = smart_packaging_module._build_highlight_audio_infos(
        [{"start": 0, "end": 800_000, "text": "格兰芬多"}],
        req,
        smart_packaging_module.random.Random(1),
    )

    assert audio_infos[0]["local_audio_path"] != str(cached_audio)
    assert fallback_tones == ["pop"]


def test_smart_packaging_detects_full_video_duration_when_missing(monkeypatch):
    video_calls = []
    cleaned = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000005",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        video_calls.append(json.loads(video_infos))
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    monkeypatch.setattr(smart_packaging_module, "download", lambda url, save_dir: "/tmp/full-video.mp4")
    monkeypatch.setattr(smart_packaging_module, "get_media_duration", lambda path: 12_345_000)
    monkeypatch.setattr(smart_packaging_module, "cleanup_temp_file", lambda path: cleaned.append(path))
    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)

    req = SmartPackagingRequest(
        videos=[{"video_url": "https://assets.example.com/full.mp4"}],
        caption={"enabled": False},
        effects={"enabled": False},
        filters={"enabled": False},
    )

    result = asyncio.run(smart_packaging_func(req))

    video_info = video_calls[0][0]
    assert video_info["start"] == 0
    assert video_info["end"] == 12_345_000
    assert video_info["duration"] == 12_345_000
    assert video_info["local_video_path"] == "/tmp/full-video.mp4"
    assert result.drafts[0].duration == 12_345_000
    assert cleaned == ["/tmp/full-video.mp4"]


def test_smart_packaging_uses_local_video_path(monkeypatch):
    video_calls = []
    asr_calls = []
    cleaned = []

    monkeypatch.setattr(
        smart_packaging_module,
        "create_draft",
        lambda width, height: "https://example.com/get_draft?draft_id=2026010100000000000006",
    )

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        video_calls.append(json.loads(video_infos))
        return draft_url, "track-video", ["video-id"], ["video-segment"], []

    async def fake_add_captions_async(draft_url, captions, **kwargs):
        return draft_url, "track-caption", ["text-id"], ["caption-segment"], []

    async def fake_save_draft_async(draft_url, **kwargs):
        return draft_url

    def fake_transcribe_video_to_captions(video_url, asr, local_video_path=None):
        asr_calls.append((video_url, local_video_path))
        return [{"start": 0, "end": 1_000_000, "text": "本地视频字幕"}]

    def fail_download(url, save_dir):
        raise AssertionError("local video should not be downloaded")

    monkeypatch.setattr(smart_packaging_module.os.path, "isfile", lambda path: path == "/tmp/local-video.mp4")
    monkeypatch.setattr(smart_packaging_module, "download", fail_download)
    monkeypatch.setattr(smart_packaging_module, "get_media_duration", lambda path: 9_000_000)
    monkeypatch.setattr(smart_packaging_module, "cleanup_temp_file", lambda path: cleaned.append(path))
    monkeypatch.setattr(smart_packaging_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(smart_packaging_module, "add_captions_async", fake_add_captions_async)
    monkeypatch.setattr(smart_packaging_module, "save_draft_async", fake_save_draft_async)
    monkeypatch.setattr(smart_packaging_module, "transcribe_video_to_captions", fake_transcribe_video_to_captions)

    req = SmartPackagingRequest(
        videos=[{"local_video_path": "/tmp/local-video.mp4"}],
        caption={"enabled": True, "source": "asr", "highlight_enabled": False},
        asr={"enabled": True, "endpoint": "https://example.com/asr"},
        effects={"enabled": False},
        filters={"enabled": False},
    )

    result = asyncio.run(smart_packaging_func(req))

    video_info = video_calls[0][0]
    assert video_info["video_url"] == "/tmp/local-video.mp4"
    assert video_info["local_video_path"] == "/tmp/local-video.mp4"
    assert video_info["end"] == 9_000_000
    assert asr_calls == [("/tmp/local-video.mp4", "/tmp/local-video.mp4")]
    assert result.drafts[0].source_video_url == "/tmp/local-video.mp4"
    assert result.drafts[0].duration == 9_000_000
    assert cleaned == []


def test_split_long_text_keeps_semantic_phrase():
    pieces = smart_packaging_module._split_long_text("下方有到一把象征着勇气的格兰芬多宝剑", 10)
    assert pieces == ["下方有到", "一把象征着勇气的", "格兰芬多宝剑"]


def test_split_long_text_keeps_product_sales_phrases():
    pieces = smart_packaging_module._split_long_text("如果你们要是有喜欢这一款包包的", 10)
    assert pieces == ["如果你们要是有", "喜欢这一款包包的"]


def test_split_long_text_keeps_livestream_phrase():
    pieces = smart_packaging_module._split_long_text("今天我们可以来直播间看一看", 10)
    assert pieces == ["今天我们可以", "来直播间看一看"]


def test_split_long_text_keeps_spell_phrase():
    pieces = smart_packaging_module._split_long_text("而且它是对应到一个咒语", 10)
    assert pieces == ["而且它是", "对应到一个咒语"]


def test_smart_packaging_default_sticker_count_and_sound_pool():
    req = SmartPackagingRequest(videos=[{"video_url": "https://assets.example.com/video.mp4"}])
    assert req.caption.font_size == 12
    assert req.caption.highlight_font_size == 28
    assert req.stickers.count == 0
    assert smart_packaging_module.DEFAULT_HIGHLIGHT_SOUND_EFFECTS == (
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
