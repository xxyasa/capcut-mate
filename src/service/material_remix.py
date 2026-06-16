import json
import os
import random
import shutil
import time
import uuid
from pathlib import Path
from typing import Iterable, List, Optional

import config
from exceptions import CustomError, CustomException
from src.schemas.material_remix import (
    MaterialInput,
    MaterialRemixDraft,
    MaterialRemixRequest,
    MaterialRemixResponse,
)
from src.service.add_audios import add_audios_async
from src.service.add_captions import add_captions_async
from src.service.add_videos import add_videos_async
from src.service.create_draft import create_draft
from src.service.save_draft import save_draft_async
from src.utils.logger import logger


DEFAULT_BGM_URLS: List[str] = []

TRANSITIONS_BY_STYLE = {
    "smooth": ["叠化", "模糊", "泛光"],
    "fast": ["白光快闪", "推近", "右移", "左移", "抖动"],
    "auto": ["叠化", "模糊", "泛光", "白光快闪", "推近", "拉远", "右移", "左移", "滑动"],
}

TRANSITION_DURATION_BY_STYLE = {
    "smooth": (500_000, 900_000),
    "fast": (250_000, 500_000),
    "auto": (350_000, 700_000),
}


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _copy_local_material_to_output(local_path: str, task_id: str, category: str) -> str:
    source = Path(local_path).expanduser()
    if not source.is_file():
        raise CustomException(
            CustomError.RESOURCE_NOT_FOUND,
            f"local material not found: {local_path}",
        )

    material_dir = Path(config.PROJECT_ROOT) / "output" / "materials" / task_id / category
    material_dir.mkdir(parents=True, exist_ok=True)

    safe_name = source.name.replace("/", "_").replace("\\", "_")
    target = material_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    shutil.copy2(source, target)

    relative_path = os.path.relpath(str(target), config.PROJECT_ROOT).replace(os.sep, "/")
    base_url = config.DOWNLOAD_URL.rstrip("/")
    return f"{base_url}/{relative_path}"


def _normalize_material_inputs(
    materials: Iterable[MaterialInput],
    urls: Iterable[object],
    task_id: str,
    category: str,
) -> List[str]:
    normalized = [str(url) for url in urls]

    for material in materials:
        if material.type == "url":
            url = str(material.url) if material.url else ""
            if not _is_http_url(url):
                raise CustomException(CustomError.PARAM_VALIDATION_FAILED, f"invalid material url: {url}")
            normalized.append(url)
            continue

        if material.type == "local":
            normalized.append(_copy_local_material_to_output(material.path or "", task_id, category))
            continue

        raise CustomException(CustomError.PARAM_VALIDATION_FAILED, f"unsupported material type: {material.type}")

    return normalized


def _build_video_plan(
    video_urls: List[str],
    req: MaterialRemixRequest,
    randomizer: random.Random,
) -> tuple[List[dict], int]:
    shuffled = list(video_urls)
    randomizer.shuffle(shuffled)

    video_infos: List[dict] = []
    timeline_start = 0
    cursor = 0

    while timeline_start < req.target_duration:
        if cursor >= len(shuffled):
            randomizer.shuffle(shuffled)
            cursor = 0

        video_url = shuffled[cursor]
        cursor += 1

        remaining = req.target_duration - timeline_start
        clip_duration = randomizer.randint(req.clip_min_duration, req.clip_max_duration)
        clip_duration = min(clip_duration, remaining)
        if clip_duration <= 0:
            break

        transition_name = None
        transition_duration = 0
        if video_infos:
            transition_name = randomizer.choice(TRANSITIONS_BY_STYLE[req.style])
            min_duration, max_duration = TRANSITION_DURATION_BY_STYLE[req.style]
            transition_duration = randomizer.randint(min_duration, max_duration)
            transition_duration = min(transition_duration, max(100_000, clip_duration // 4))

        video_infos.append(
            {
                "video_url": video_url,
                "start": timeline_start,
                "end": timeline_start + clip_duration,
                "duration": clip_duration,
                "transition": transition_name,
                "transition_duration": transition_duration,
                "volume": 0.0 if req.mute_original else 1.0,
            }
        )
        timeline_start += clip_duration

    return video_infos, timeline_start


def _select_bgm(bgm_urls: List[str], req: MaterialRemixRequest, randomizer: random.Random) -> str:
    candidates = bgm_urls or DEFAULT_BGM_URLS
    if not candidates:
        return ""
    return randomizer.choice(candidates)


async def material_remix(req: MaterialRemixRequest) -> MaterialRemixResponse:
    task_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    video_urls = _normalize_material_inputs(req.videos, req.video_urls, task_id, "videos")
    bgm_urls = _normalize_material_inputs(req.bgms, req.bgm_urls, task_id, "bgm")
    if not video_urls:
        raise CustomException(CustomError.INVALID_VIDEO_INFO, "no video materials")

    base_seed = req.seed if req.seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
    drafts: List[MaterialRemixDraft] = []

    for index in range(req.output_count):
        draft_seed = base_seed + index
        randomizer = random.Random(draft_seed)
        draft_url = create_draft(width=req.width, height=req.height)

        try:
            video_infos, duration = _build_video_plan(video_urls, req, randomizer)
            _, _, _, segment_ids, _ = await add_videos_async(
                draft_url=draft_url,
                video_infos=json.dumps(video_infos, ensure_ascii=False),
            )

            bgm_url = _select_bgm(bgm_urls, req, randomizer)
            if bgm_url:
                await add_audios_async(
                    draft_url=draft_url,
                    audio_infos=json.dumps(
                        [
                            {
                                "audio_url": bgm_url,
                                "start": 0,
                                "end": duration,
                                "duration": duration,
                                "volume": 0.45 if not req.voiceover.enabled else 0.2,
                            }
                        ],
                        ensure_ascii=False,
                    ),
                )

            if req.voiceover.enabled and req.voiceover.audio_url:
                await add_audios_async(
                    draft_url=draft_url,
                    audio_infos=json.dumps(
                        [
                            {
                                "audio_url": str(req.voiceover.audio_url),
                                "start": 0,
                                "end": duration,
                                "duration": duration,
                                "volume": 1.0,
                            }
                        ],
                        ensure_ascii=False,
                    ),
                )

            if req.caption.enabled and req.caption.items:
                await add_captions_async(
                    draft_url=draft_url,
                    captions=json.dumps(req.caption.items, ensure_ascii=False),
                )

            await save_draft_async(draft_url=draft_url)
            drafts.append(
                MaterialRemixDraft(
                    draft_url=draft_url,
                    duration=duration,
                    seed=draft_seed,
                    selected_videos=[item["video_url"] for item in video_infos],
                    bgm_url=bgm_url,
                    segment_ids=segment_ids,
                )
            )
        except Exception:
            logger.exception(f"material_remix failed, draft_url={draft_url}, seed={draft_seed}")
            raise

    return MaterialRemixResponse(drafts=drafts)
