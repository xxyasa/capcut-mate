import os
import pathlib
import shutil
from typing import Iterable

from src.utils.logger import logger


_CACHE_ASSETS_INSTALLED = False


def default_jianying_cache_dir() -> pathlib.Path:
    explicit = os.getenv("JIANYING_TARGET_CACHE_DIR") or os.getenv("JIANYING_CACHE_DIR")
    if explicit:
        return pathlib.Path(explicit).expanduser()
    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return pathlib.Path(local_app_data) / "JianyingPro" / "User Data" / "Cache"
        return pathlib.Path.home() / "AppData" / "Local" / "JianyingPro" / "User Data" / "Cache"
    return pathlib.Path.home() / "Movies" / "JianyingPro" / "User Data" / "Cache"


def _smart_assets_dir() -> pathlib.Path | None:
    explicit = os.getenv("SMART_PACKAGING_ASSETS_DIR")
    if explicit:
        return pathlib.Path(explicit).expanduser()
    candidate = pathlib.Path.cwd() / "smart-assets"
    return candidate if candidate.exists() else None


def _dedupe_paths(paths: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    seen: set[str] = set()
    result: list[pathlib.Path] = []
    for path in paths:
        value = str(path.expanduser())
        if value in seen:
            continue
        seen.add(value)
        result.append(path.expanduser())
    return result


def install_smart_packaging_cache_assets() -> None:
    """Install packaged smart-assets into Jianying's cache so draft animations resolve locally."""
    global _CACHE_ASSETS_INSTALLED
    if _CACHE_ASSETS_INSTALLED:
        return
    if os.getenv("SMART_PACKAGING_INSTALL_JIANYING_CACHE", "1").strip().lower() in {"0", "false", "no"}:
        _CACHE_ASSETS_INSTALLED = True
        return

    assets_dir = _smart_assets_dir()
    if not assets_dir or not assets_dir.exists():
        _CACHE_ASSETS_INSTALLED = True
        return

    target_cache_dir = default_jianying_cache_dir()
    copied = 0
    for bucket in ("effect", "artistEffect"):
        source_bucket = assets_dir / bucket
        if not source_bucket.is_dir():
            continue
        target_bucket = target_cache_dir / bucket
        target_bucket.mkdir(parents=True, exist_ok=True)
        for item in source_bucket.iterdir():
            target = target_bucket / item.name
            try:
                if target.exists():
                    continue
                if item.is_dir():
                    shutil.copytree(item, target)
                    copied += 1
                elif item.is_file():
                    shutil.copy2(item, target)
            except Exception as exc:
                logger.warning(f"Failed to install Jianying cache asset: {item} -> {target}, error={exc}")

    if copied:
        logger.info(f"Installed {copied} smart asset cache folders into {target_cache_dir}")
    _CACHE_ASSETS_INSTALLED = True


def _candidate_bucket_dirs(bucket: str) -> list[pathlib.Path]:
    env_name = "JIANYING_ARTIST_EFFECT_CACHE_DIR" if bucket == "artistEffect" else "JIANYING_EFFECT_CACHE_DIR"
    paths = [default_jianying_cache_dir() / bucket]
    if os.getenv(env_name):
        paths.append(pathlib.Path(os.getenv(env_name, "")).expanduser())
    assets_dir = _smart_assets_dir()
    if assets_dir:
        paths.append(assets_dir / bucket)
    return _dedupe_paths(paths)


def _first_resource_payload(resource_dir: pathlib.Path) -> pathlib.Path | None:
    if not resource_dir.exists():
        return None
    if resource_dir.is_file():
        return resource_dir
    children = sorted(
        (
            child for child in resource_dir.iterdir()
            if child.name != ".DS_Store" and not child.name.endswith("_modity_time.txt")
        ),
        key=lambda child: (not child.is_dir(), child.name),
    )
    return children[0] if children else resource_dir


def resolve_jianying_cache_resource_path(
    bucket: str,
    resource_id: str,
    effect_id: str = "",
    md5: str = "",
) -> str:
    install_smart_packaging_cache_assets()
    keys = [value for value in (effect_id, resource_id) if value]
    for base_dir in _candidate_bucket_dirs(bucket):
        for key in keys:
            if md5:
                exact = base_dir / key / md5
                if exact.exists():
                    return str(exact)
            payload = _first_resource_payload(base_dir / key)
            if payload:
                return str(payload)
        if md5 and base_dir.exists():
            for exact in base_dir.glob(f"*/{md5}"):
                if exact.exists():
                    return str(exact)
    return ""


def localize_jianying_cache_path(path_value: str) -> str:
    if not path_value:
        return ""
    parts = pathlib.Path(path_value).expanduser().parts
    for index, part in enumerate(parts):
        if part not in {"effect", "artistEffect"} or index + 1 >= len(parts):
            continue
        install_smart_packaging_cache_assets()
        candidate = default_jianying_cache_dir() / part / pathlib.Path(*parts[index + 1:])
        if candidate.exists():
            return str(candidate)
        break
    expanded = pathlib.Path(path_value).expanduser()
    return str(expanded) if expanded.exists() else ""
