import json
import importlib

add_videos_module = importlib.import_module("src.service.add_videos")


def test_prepare_videos_copies_local_file_into_draft_assets(monkeypatch):
    copied = []

    monkeypatch.setattr(add_videos_module.helper, "get_url_param", lambda url, key: "draft-local")
    monkeypatch.setattr(add_videos_module, "DRAFT_CACHE", {"draft-local": object()})
    monkeypatch.setattr(add_videos_module.os, "makedirs", lambda name, exist_ok=True: None)
    monkeypatch.setattr(add_videos_module.os.path, "isfile", lambda path: path == "/tmp/source.mov")
    monkeypatch.setattr(add_videos_module.helper, "gen_unique_id", lambda: "copied-video")
    monkeypatch.setattr(add_videos_module.shutil, "copy2", lambda source, target: copied.append((source, target)))

    video_infos = json.dumps(
        [
            {
                "video_url": "/tmp/source.mov",
                "local_video_path": "/tmp/source.mov",
                "start": 0,
                "end": 1_000_000,
            }
        ],
        ensure_ascii=False,
    )

    prepared = add_videos_module._prepare_videos_local_files(
        "http://localhost/get_draft?draft_id=draft-local",
        video_infos,
    )

    assert copied == [
        (
            "/tmp/source.mov",
            add_videos_module.os.path.join(
                add_videos_module.config.DRAFT_DIR,
                "draft-local",
                "assets",
                "videos",
                "copied-video.mov",
            ),
        )
    ]
    assert prepared[0]["local_video_path"].endswith("assets/videos/copied-video.mov")
