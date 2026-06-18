import os
import json
import pathlib
import shutil
import subprocess
import sys
import uuid

try:
    import pymediainfo
except Exception:
    pymediainfo = None

from typing import Optional, Literal
from typing import Dict, Any


def _find_ffprobe() -> str | None:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return ffprobe_path

    app_root = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parents[2]))
    for candidate in (
        app_root / "tools" / "ffprobe.exe",
        app_root / "tools" / "ffprobe",
        pathlib.Path(__file__).resolve().parents[2] / "tools" / "ffprobe.exe",
        pathlib.Path(__file__).resolve().parents[2] / "tools" / "ffprobe",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _run_ffprobe(path: str) -> dict | None:
    ffprobe_path = _find_ffprobe()
    if not ffprobe_path:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height,duration:format=duration",
                "-of",
                "json",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _duration_to_microseconds(value: object) -> int | None:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if duration <= 0:
        return None
    return int(duration * 1_000_000)


def _probe_duration(data: dict, stream: dict | None = None) -> int | None:
    if stream:
        duration = _duration_to_microseconds(stream.get("duration"))
        if duration:
            return duration
    return _duration_to_microseconds((data.get("format") or {}).get("duration"))


def _run_imageio_ffmpeg(path: str) -> dict | None:
    try:
        import imageio_ffmpeg
    except Exception:
        return None
    try:
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-i", path, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except Exception:
        return None

    output = f"{result.stdout}\n{result.stderr}"
    duration_match = __import__("re").search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    duration = None
    if duration_match:
        hours = int(duration_match.group(1))
        minutes = int(duration_match.group(2))
        seconds = float(duration_match.group(3))
        duration = int((hours * 3600 + minutes * 60 + seconds) * 1_000_000)

    video_match = __import__("re").search(r"Video:.*?(\d{2,5})x(\d{2,5})", output)
    return {
        "duration": duration,
        "has_audio": "Audio:" in output,
        "has_video": "Video:" in output,
        "width": int(video_match.group(1)) if video_match else 0,
        "height": int(video_match.group(2)) if video_match else 0,
    }


def _parse_with_pymediainfo(path: str):
    if pymediainfo is None:
        return None
    media_info = getattr(pymediainfo, "MediaInfo", pymediainfo)
    try:
        if hasattr(media_info, "can_parse") and not media_info.can_parse():
            return None
        return media_info.parse(path, mediainfo_options={"File_TestContinuousFileNames": "0"})
    except TypeError:
        return media_info.parse(path)
    except Exception:
        return None

class CropSettings:
    """素材的裁剪设置, 各属性均在0-1之间, 注意素材的坐标原点在左上角"""

    upper_left_x: float
    upper_left_y: float
    upper_right_x: float
    upper_right_y: float
    lower_left_x: float
    lower_left_y: float
    lower_right_x: float
    lower_right_y: float

    def __init__(self, *, upper_left_x: float = 0.0, upper_left_y: float = 0.0,
                 upper_right_x: float = 1.0, upper_right_y: float = 0.0,
                 lower_left_x: float = 0.0, lower_left_y: float = 1.0,
                 lower_right_x: float = 1.0, lower_right_y: float = 1.0):
        """初始化裁剪设置, 默认参数表示不裁剪"""
        self.upper_left_x = upper_left_x
        self.upper_left_y = upper_left_y
        self.upper_right_x = upper_right_x
        self.upper_right_y = upper_right_y
        self.lower_left_x = lower_left_x
        self.lower_left_y = lower_left_y
        self.lower_right_x = lower_right_x
        self.lower_right_y = lower_right_y

    def export_json(self) -> Dict[str, Any]:
        return {
            "upper_left_x": self.upper_left_x,
            "upper_left_y": self.upper_left_y,
            "upper_right_x": self.upper_right_x,
            "upper_right_y": self.upper_right_y,
            "lower_left_x": self.lower_left_x,
            "lower_left_y": self.lower_left_y,
            "lower_right_x": self.lower_right_x,
            "lower_right_y": self.lower_right_y
        }

class VideoMaterial:
    """本地视频素材（视频或图片）, 一份素材可以在多个片段中使用"""

    material_id: str
    """素材全局id, 自动生成"""
    local_material_id: str
    """素材本地id, 意义暂不明确"""
    material_name: str
    """素材名称"""
    path: str
    """素材文件路径"""
    duration: int
    """素材时长, 单位为微秒"""
    height: int
    """素材高度"""
    width: int
    """素材宽度"""
    crop_settings: CropSettings
    """素材裁剪设置"""
    material_type: Literal["video", "photo"]
    """素材类型: 视频或图片"""

    def __init__(self, path: str, material_name: Optional[str] = None, crop_settings: CropSettings = CropSettings()):
        """从指定位置加载视频（或图片）素材

        Args:
            path (`str`): 素材文件路径, 支持mp4, mov, avi等常见视频文件及jpg, jpeg, png等图片文件.
            material_name (`str`, optional): 素材名称, 如果不指定, 默认使用文件名作为素材名称.
            crop_settings (`CropSettings`, optional): 素材裁剪设置, 默认不裁剪.

        Raises:
            `FileNotFoundError`: 素材文件不存在.
            `ValueError`: 不支持的素材文件类型.
        """
        path = os.path.abspath(path)
        postfix = os.path.splitext(path)[1]
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到 {path}")

        self.material_name = material_name if material_name else os.path.basename(path)
        self.material_id = uuid.uuid4().hex
        self.path = path
        self.crop_settings = crop_settings
        self.local_material_id = ""

        info = _parse_with_pymediainfo(path)
        if info:
            # 有视频轨道的视为视频素材
            if len(info.video_tracks):
                self.material_type = "video"
                self.duration = int(info.video_tracks[0].duration * 1e3)  # type: ignore
                self.width, self.height = info.video_tracks[0].width, info.video_tracks[0].height  # type: ignore
                return
            elif len(getattr(info, "image_tracks", [])):
                self.material_type = "photo"
                self.duration = 10800000000  # 相当于3h
                self.width, self.height = info.image_tracks[0].width, info.image_tracks[0].height  # type: ignore
                return

        probe_data = _run_ffprobe(path)
        streams = probe_data.get("streams", []) if probe_data else []
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        if video_stream:
            self.width = int(video_stream.get("width") or 0)
            self.height = int(video_stream.get("height") or 0)
            if postfix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                self.material_type = "photo"
                self.duration = 10800000000
                return
            duration = _probe_duration(probe_data or {}, video_stream)
            if duration:
                self.material_type = "video"
                self.duration = duration
                return

        ffmpeg_data = _run_imageio_ffmpeg(path)
        if ffmpeg_data and ffmpeg_data.get("has_video"):
            self.width = int(ffmpeg_data.get("width") or 0)
            self.height = int(ffmpeg_data.get("height") or 0)
            if postfix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                self.material_type = "photo"
                self.duration = 10800000000
                return
            duration = ffmpeg_data.get("duration")
            if duration:
                self.material_type = "video"
                self.duration = int(duration)
                return

        raise ValueError(f"输入的素材文件 {path} 没有视频轨道或图片轨道")

    def export_json(self) -> Dict[str, Any]:
        video_material_json = {
            "audio_fade": None,
            "category_id": "",
            "category_name": "local",
            "check_flag": 63487,
            "crop": self.crop_settings.export_json(),
            "crop_ratio": "free",
            "crop_scale": 1.0,
            "duration": self.duration,
            "height": self.height,
            "id": self.material_id,
            "local_material_id": self.local_material_id,
            "material_id": self.material_id,
            "material_name": self.material_name,
            "media_path": "",
            "path": self.path,
            "type": self.material_type,
            "width": self.width
        }
        return video_material_json

class AudioMaterial:
    """本地音频素材"""

    material_id: str
    """素材全局id, 自动生成"""
    material_name: str
    """素材名称"""
    path: str
    """素材文件路径"""

    duration: int
    """素材时长, 单位为微秒"""

    _AUDIO_POSTFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}

    def __init__(self, path: str, material_name: Optional[str] = None):
        """从指定位置加载音频素材, 注意视频文件不应该作为音频素材使用

        Args:
            path (`str`): 素材文件路径, 支持mp3, wav等常见音频文件.
            material_name (`str`, optional): 素材名称, 如果不指定, 默认使用文件名作为素材名称.

        Raises:
            `FileNotFoundError`: 素材文件不存在.
            `ValueError`: 不支持的素材文件类型.
        """
        path = os.path.abspath(path)
        postfix = os.path.splitext(path)[1].lower()
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到 {path}")

        self.material_name = material_name if material_name else os.path.basename(path)
        self.material_id = uuid.uuid4().hex
        self.path = path

        info = _parse_with_pymediainfo(path)
        if info:
            if not len(info.audio_tracks):
                raise ValueError(f"给定的素材文件 {path} 没有音频轨道")
            if len(info.video_tracks) and postfix not in self._AUDIO_POSTFIXES:
                raise ValueError("音频素材不应包含视频轨道")
            self.duration = int(info.audio_tracks[0].duration * 1e3)  # type: ignore
            return

        probe_data = _run_ffprobe(path)
        streams = probe_data.get("streams", []) if probe_data else []
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        has_video_stream = any(stream.get("codec_type") == "video" for stream in streams)
        if has_video_stream and postfix not in self._AUDIO_POSTFIXES:
            raise ValueError("音频素材不应包含视频轨道")
        duration = _probe_duration(probe_data or {}, audio_stream) if audio_stream else None
        if not audio_stream or not duration:
            ffmpeg_data = _run_imageio_ffmpeg(path)
            if ffmpeg_data and ffmpeg_data.get("has_video") and postfix not in self._AUDIO_POSTFIXES:
                raise ValueError("音频素材不应包含视频轨道")
            if ffmpeg_data and ffmpeg_data.get("has_audio"):
                duration = ffmpeg_data.get("duration")
        if not duration:
            raise ValueError(f"给定的素材文件 {path} 没有音频轨道")
        self.duration = int(duration)

    def export_json(self) -> Dict[str, Any]:
        return {
            "app_id": 0,
            "category_id": "",
            "category_name": "local",
            "check_flag": 3,
            "copyright_limit_type": "none",
            "duration": self.duration,
            "effect_id": "",
            "formula_id": "",
            "id": self.material_id,
            "local_material_id": self.material_id,
            "music_id": self.material_id,
            "name": self.material_name,
            "path": self.path,
            "source_platform": 0,
            "type": "extract_music",
            "wave_points": []
        }
