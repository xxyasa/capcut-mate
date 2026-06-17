import subprocess
import os
import shutil
from typing import Optional
from src.utils.logger import logger


def _get_duration_with_ffprobe(file_path: str) -> Optional[int]:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        logger.info("ffprobe not found, fallback to pymediainfo")
        return None

    cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        logger.error(f"ffprobe 执行失败: {result.stderr}")
        return None

    duration_str = result.stdout.strip()
    if not duration_str:
        logger.warning(f"ffprobe 未能获取到文件时长: {file_path}")
        return None

    return int(float(duration_str) * 1_000_000)


def _get_duration_with_pymediainfo(file_path: str) -> Optional[int]:
    try:
        from pymediainfo import MediaInfo
    except Exception as exc:
        logger.error(f"pymediainfo 不可用: {exc}")
        return None

    try:
        media_info = MediaInfo.parse(file_path)
    except Exception as exc:
        logger.error(f"pymediainfo 解析失败: {exc}")
        return None

    for track_type in ("Video", "Audio", "General"):
        for track in media_info.tracks:
            if track.track_type != track_type:
                continue
            duration_ms = getattr(track, "duration", None)
            if duration_ms:
                return int(float(duration_ms) * 1000)
    return None


def get_media_duration(file_path: str) -> Optional[int]:
    """
    获取音视频文件的时长，返回微秒数
    
    Args:
        file_path (str): 音视频文件的路径
        
    Returns:
        Optional[int]: 文件时长（微秒），如果获取失败则返回 None
        
    Example:
        duration_us = get_media_duration("test.mp3")
        if duration_us:
            print(f"文件时长: {duration_us} 微秒")
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None

        duration_microseconds = _get_duration_with_ffprobe(file_path)
        if duration_microseconds is None:
            duration_microseconds = _get_duration_with_pymediainfo(file_path)
        if duration_microseconds is None:
            logger.warning(f"未能获取到文件时长: {file_path}")
            return None
        
        logger.info(f"文件 {file_path} 的时长: {duration_microseconds} 微秒")
        return duration_microseconds
        
    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe 执行超时: {file_path}")
        return None
    except ValueError as e:
        logger.error(f"解析时长失败: {e}, 输出内容: {result.stdout if 'result' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"获取媒体文件时长时发生未知错误: {e}")
        return None


def get_media_duration_formatted(file_path: str) -> Optional[str]:
    """
    获取音视频文件的时长，返回格式化的字符串 (HH:MM:SS.mmm)
    
    Args:
        file_path (str): 音视频文件的路径
        
    Returns:
        Optional[str]: 格式化的时长字符串，如果获取失败则返回 None
    """
    duration_us = get_media_duration(file_path)
    if duration_us is None:
        return None
        
    # 转换为秒和毫秒
    total_seconds = duration_us / 1_000_000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
