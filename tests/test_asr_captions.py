import importlib
from unittest.mock import Mock

from src.schemas.smart_packaging import SmartPackagingAsrConfig


asr_module = importlib.import_module("src.service.asr_captions")


def test_openai_compatible_asr_upload_uses_ascii_filename(monkeypatch, tmp_path):
    audio_path = tmp_path / "中文音频文件.mp3"
    audio_path.write_bytes(b"fake audio")
    captured = {}
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"segments": []}
    response.text = ""

    def fake_post(url, headers, files, data, timeout):
        captured["filename"] = files["file"][0]
        captured["data"] = data
        return response

    monkeypatch.setattr(asr_module.requests, "post", fake_post)

    payload = asr_module._request_openai_compatible(
        str(audio_path),
        SmartPackagingAsrConfig(
            enabled=True,
            provider="openai_compatible",
            endpoint="https://example.com/audio/transcriptions",
            api_key="sk-test",
            model="whisper-large-v3",
            timestamp_granularities=["word", "segment"],
        ),
    )

    assert payload == {"segments": []}
    assert captured["filename"] == "audio.mp3"
    assert captured["filename"].isascii()
    assert captured["data"]["model"] == "whisper-large-v3"


def test_custom_json_asr_upload_uses_ascii_filename(monkeypatch, tmp_path):
    audio_path = tmp_path / "曾仕强讲座.mp3"
    audio_path.write_bytes(b"fake audio")
    captured = {}
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"segments": []}
    response.text = ""

    def fake_post(url, headers, files, data, timeout):
        captured["filename"] = files["file"][0]
        captured["video_url"] = data["video_url"]
        return response

    monkeypatch.setattr(asr_module.requests, "post", fake_post)

    payload = asr_module._request_custom_json(
        str(audio_path),
        "https://assets.example.com/video.mp4",
        SmartPackagingAsrConfig(
            enabled=True,
            provider="custom_json",
            endpoint="https://example.com/asr",
            api_key="sk-test",
            model="whisper-large-v3",
        ),
    )

    assert payload == {"segments": []}
    assert captured["filename"] == "audio.mp3"
    assert captured["filename"].isascii()
    assert captured["video_url"] == "https://assets.example.com/video.mp4"


def test_asr_auth_header_cleans_copied_bearer_prefix():
    asr = SmartPackagingAsrConfig(
        enabled=True,
        endpoint="https://example.com/asr",
        api_key="Authorization: Bearer sk-test-key\n",
    )

    assert asr_module._auth_headers(asr) == {"Authorization": "Bearer sk-test-key"}


def test_asr_auth_header_rejects_non_ascii_key():
    asr = SmartPackagingAsrConfig(
        enabled=True,
        endpoint="https://example.com/asr",
        api_key="sk-测试",
    )

    try:
        asr_module._auth_headers(asr)
    except ValueError as exc:
        assert "API Key" in str(exc)
        assert "中文" in str(exc)
    else:
        raise AssertionError("expected invalid non-ascii API key to fail")
