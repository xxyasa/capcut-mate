import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List

import requests

from exceptions import CustomError, CustomException
from src.schemas.smart_packaging import SmartPackagingAsrConfig
from src.utils.download import download
from src.utils.logger import logger


ASR_UPLOAD_FILENAME = "audio.mp3"


def _normalize_api_key(api_key: str | None) -> str:
    if not api_key:
        return ""
    cleaned = str(api_key).strip().replace("\u3000", " ")
    if cleaned.lower().startswith("authorization:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    cleaned = re.sub(r"\s+", "", cleaned)
    try:
        cleaned.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("ASR API Key 只能包含英文/数字/符号，请检查是否粘入了中文、全角空格或说明文字") from exc
    return cleaned


def _raise_for_status_with_body(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:500] if response.text else ""
        raise requests.HTTPError(f"{exc}; response body: {body}", response=response) from exc


def _auth_headers(asr: SmartPackagingAsrConfig) -> Dict[str, str]:
    api_key = _normalize_api_key(asr.api_key)
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _time_to_microseconds(value: Any) -> int:
    if value is None:
        return 0

    number = float(value)
    if number > 100_000:
        return int(number)
    if number > 1000:
        return int(number * 1000)
    return int(number * 1_000_000)


def _extract_segments(payload: Dict[str, Any]) -> List[dict]:
    segments = payload.get("segments")
    if segments is None and isinstance(payload.get("data"), dict):
        segments = payload["data"].get("segments")
    if segments is None and isinstance(payload.get("result"), dict):
        segments = payload["result"].get("segments")
    if segments is None:
        return []

    captions: List[dict] = []
    for item in segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("sentence") or item.get("content") or "").strip()
        if not text:
            continue

        start = _time_to_microseconds(item.get("start", item.get("start_time")))
        end = _time_to_microseconds(item.get("end", item.get("end_time")))
        if end <= start:
            continue

        captions.append({"start": start, "end": end, "text": text})

    return captions


def _request_custom_json(local_audio_path: str, video_url: str, asr: SmartPackagingAsrConfig) -> Dict[str, Any]:
    with open(local_audio_path, "rb") as audio_file:
        files = {"file": (ASR_UPLOAD_FILENAME, audio_file, "audio/mpeg")}
        data = {
            "video_url": video_url,
            "audio_url": video_url,
        }
        if asr.model:
            data["model"] = asr.model
        if asr.language:
            data["language"] = asr.language

        response = requests.post(
            asr.endpoint,
            headers=_auth_headers(asr),
            files=files,
            data=data,
            timeout=asr.timeout,
        )
    _raise_for_status_with_body(response)
    return response.json()


def _request_openai_compatible(local_audio_path: str, asr: SmartPackagingAsrConfig) -> Dict[str, Any]:
    with open(local_audio_path, "rb") as audio_file:
        files = {"file": (ASR_UPLOAD_FILENAME, audio_file, "audio/mpeg")}
        data = {
            "model": asr.model or "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities": json.dumps(asr.timestamp_granularities),
        }
        if asr.language:
            data["language"] = asr.language

        response = requests.post(
            asr.endpoint,
            headers=_auth_headers(asr),
            files=files,
            data=data,
            timeout=asr.timeout,
        )
    _raise_for_status_with_body(response)
    return response.json()


def _extract_audio_for_asr(local_video_path: str, temp_dir: str) -> str:
    local_audio_path = os.path.join(temp_dir, "asr_audio.mp3")
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        try:
            import imageio_ffmpeg

            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = "ffmpeg"
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        local_video_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        local_audio_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
    if result.returncode != 0 or not os.path.exists(local_audio_path):
        raise CustomException(
            CustomError.MATERIAL_CREATE_FAILED,
            f"ASR audio extract failed: {result.stderr[-500:]}",
        )
    return local_audio_path


def transcribe_video_to_captions(
    video_url: str,
    asr: SmartPackagingAsrConfig,
    local_video_path: str | None = None,
) -> List[dict]:
    """调用 ASR 服务，将视频识别为带时间轴的字幕列表。"""

    if not asr.enabled:
        return []
    if not asr.endpoint:
        logger.info("ASR endpoint is empty, skip transcription")
        return []

    with tempfile.TemporaryDirectory(prefix="capcut_asr_") as temp_dir:
        video_path_for_asr = local_video_path or download(video_url, temp_dir)
        local_audio_path = _extract_audio_for_asr(video_path_for_asr, temp_dir)
        try:
            if asr.provider == "openai_compatible":
                payload = _request_openai_compatible(local_audio_path, asr)
            else:
                payload = _request_custom_json(local_audio_path, video_url, asr)
        except Exception as exc:
            logger.error(f"ASR request failed: {exc}")
            raise CustomException(CustomError.MATERIAL_CREATE_FAILED, f"ASR request failed: {exc}") from exc

    captions = _extract_segments(payload)
    logger.info(f"ASR parsed {len(captions)} captions, video_url: {video_url}")
    return captions
