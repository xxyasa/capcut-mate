import asyncio
import importlib
import json

from src.schemas.material_remix import MaterialInput, MaterialRemixRequest
from src.service import material_remix as material_remix_func

material_remix_module = importlib.import_module("src.service.material_remix")


def test_material_remix_builds_multiple_drafts(monkeypatch):
    created = []
    video_calls = []
    audio_calls = []
    saved = []

    def fake_create_draft(width, height):
        draft_url = f"https://example.com/get_draft?draft_id=20260101000000{len(created):08d}"
        created.append((width, height, draft_url))
        return draft_url

    async def fake_add_videos_async(draft_url, video_infos, **kwargs):
        video_calls.append((draft_url, json.loads(video_infos)))
        return draft_url, "track-video", ["video-id"], ["segment-id"], []

    async def fake_add_audios_async(draft_url, audio_infos, **kwargs):
        audio_calls.append((draft_url, json.loads(audio_infos)))
        return draft_url, "track-audio", ["audio-id"]

    async def fake_save_draft_async(draft_url, **kwargs):
        saved.append(draft_url)
        return draft_url

    monkeypatch.setattr(material_remix_module, "create_draft", fake_create_draft)
    monkeypatch.setattr(material_remix_module, "add_videos_async", fake_add_videos_async)
    monkeypatch.setattr(material_remix_module, "add_audios_async", fake_add_audios_async)
    monkeypatch.setattr(material_remix_module, "save_draft_async", fake_save_draft_async)

    req = MaterialRemixRequest(
        video_urls=[
            "https://assets.example.com/a.mp4",
            "https://assets.example.com/b.mp4",
        ],
        bgm_urls=["https://assets.example.com/bgm.mp3"],
        output_count=2,
        width=1080,
        height=1920,
        target_duration=5_000_000,
        clip_min_duration=2_000_000,
        clip_max_duration=2_000_000,
        seed=7,
    )

    result = asyncio.run(material_remix_func(req))

    assert len(result.drafts) == 2
    assert len(created) == 2
    assert len(video_calls) == 2
    assert len(audio_calls) == 2
    assert saved == [draft.draft_url for draft in result.drafts]

    first_video_infos = video_calls[0][1]
    assert sum(item["end"] - item["start"] for item in first_video_infos) == 5_000_000
    assert first_video_infos[0]["transition"] is None
    assert all(item["transition"] for item in first_video_infos[1:])
    assert all(item["transition_duration"] > 0 for item in first_video_infos[1:])
    assert all(item["volume"] == 0.0 for item in first_video_infos)
    assert audio_calls[0][1][0]["audio_url"] == "https://assets.example.com/bgm.mp3"
    assert audio_calls[0][1][0]["end"] == 5_000_000


def test_local_material_is_copied_and_url_normalized(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video")

    project_root = tmp_path / "project"
    project_root.mkdir()

    monkeypatch.setattr(material_remix_module.config, "PROJECT_ROOT", str(project_root))
    monkeypatch.setattr(material_remix_module.config, "DOWNLOAD_URL", "http://127.0.0.1/")

    urls = material_remix_module._normalize_material_inputs(
        materials=[MaterialInput(type="local", path=str(source))],
        urls=[],
        task_id="task001",
        category="videos",
    )

    assert len(urls) == 1
    assert urls[0].startswith("http://127.0.0.1/output/materials/task001/videos/")
    copied = list((project_root / "output" / "materials" / "task001" / "videos").iterdir())
    assert len(copied) == 1
    assert copied[0].read_bytes() == b"fake-video"
