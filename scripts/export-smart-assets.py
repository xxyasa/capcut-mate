#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac"}
CACHE_BUCKETS = {"artistEffect", "effect"}
ARTIST_EFFECT_PANELS = {"default", "flower"}
IGNORE_PATTERNS = (".DS_Store", ".backup", "*.bak", "*.tmp")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def copytree(src: Path, dst: Path):
    if not src.exists():
        raise FileNotFoundError(f"Missing source directory: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


def parse_depends(depends_path: Path):
    if not depends_path.is_file():
        return []

    records = {}
    for raw_line in depends_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or line.startswith("size="):
            continue
        if "\\" not in line or "=" not in line:
            continue
        index, rest = line.split("\\", 1)
        key, value = rest.split("=", 1)
        record = records.setdefault(index, {})
        record[key.strip()] = value.strip()

    return [records[key] for key in sorted(records, key=lambda item: int(item) if item.isdigit() else item)]


def cache_path_info(path: Path):
    parts = path.parts
    for index, part in enumerate(parts):
        if part in CACHE_BUCKETS and index + 1 < len(parts):
            return part, parts[index + 1], parts[index + 2:]
    return None


def top_cache_dir_from_path(path: Path):
    info = cache_path_info(path)
    if not info:
        return None
    bucket, key, _ = info
    parts = path.parts
    for index, part in enumerate(parts):
        if part == bucket and index + 1 < len(parts) and parts[index + 1] == key:
            return Path(*parts[: index + 2])
    return None


def guess_dependency_bucket(record: dict):
    raw_path = str(record.get("path") or "").strip()
    if raw_path:
        info = cache_path_info(Path(raw_path).expanduser())
        if info:
            return info[0]
    panel = str(record.get("panel") or "").strip()
    return "artistEffect" if panel in ARTIST_EFFECT_PANELS else "effect"


def dependency_cache_key(record: dict):
    raw_path = str(record.get("path") or "").strip()
    if raw_path:
        info = cache_path_info(Path(raw_path).expanduser())
        if info:
            return info[1]
    return str(record.get("id") or "").strip()


def enqueue_artist_effect_depends(output_dir: Path, material_id: str, queue: list[Path]):
    material_dir = output_dir / "artistEffect" / material_id
    if not material_dir.is_dir():
        return
    queue.extend(sorted(material_dir.glob("*/depends")))


def copy_dependency_asset(record: dict, cache_dir: Path, output_dir: Path):
    bucket = guess_dependency_bucket(record)
    cache_key = dependency_cache_key(record)
    material_id = str(record.get("id") or "").strip()
    raw_path = Path(str(record.get("path") or "")).expanduser() if record.get("path") else None

    candidate_dirs = []
    if raw_path:
        raw_top_dir = top_cache_dir_from_path(raw_path)
        if raw_top_dir:
            candidate_dirs.append(raw_top_dir)
        info = cache_path_info(raw_path)
        if info:
            _, path_key, _ = info
            candidate_dirs.append(cache_dir / bucket / path_key)
    if cache_key:
        candidate_dirs.append(cache_dir / bucket / cache_key)
    if material_id and material_id != cache_key:
        candidate_dirs.append(cache_dir / bucket / material_id)

    seen = set()
    for candidate in candidate_dirs:
        candidate = candidate.expanduser()
        candidate_key = str(candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        if not candidate.is_dir():
            continue
        info = cache_path_info(candidate)
        dst_key = info[1] if info else candidate.name
        copytree(candidate, output_dir / bucket / dst_key)
        return {"bucket": bucket, "key": dst_key, "id": material_id, "source": str(candidate)}

    return None


def iter_material_values(key_value_path: Path):
    data = load_json(key_value_path)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                yield key, value


def extract_text_templates(draft_dir: Path):
    items = []
    for key, value in iter_material_values(draft_dir / "key_value.json"):
        material_id = str(value.get("materialId") or key or "").strip()
        name = str(value.get("materialName") or value.get("name") or "").strip()
        if not material_id:
            continue
        if value.get("materialType") == "text_template" or value.get("materialCategory") in {"text", "text_template"}:
            items.append({"name": name or material_id, "material_id": material_id})
        elif value.get("effectId") or value.get("effect_id"):
            items.append({"name": name or material_id, "material_id": material_id})
    return dedupe_items(items)


def extract_sound_effects(draft_dir: Path):
    items = []
    for key, value in iter_material_values(draft_dir / "key_value.json"):
        if value.get("materialCategory") != "audio" or value.get("materialSubcategory") != "sound_effect":
            continue
        material_id = str(value.get("materialId") or key or "").strip()
        name = str(value.get("materialName") or value.get("name") or "").strip()
        if material_id:
            items.append({"name": name or material_id, "material_id": material_id})
    return dedupe_items(items)


def dedupe_items(items):
    result = []
    seen = set()
    for item in items:
        material_id = item["material_id"]
        if material_id in seen:
            continue
        seen.add(material_id)
        result.append(item)
    return result


def load_music_mapping(music_dir: Path):
    cfg_path = music_dir / "downLoadcfg"
    if not cfg_path.is_file():
        return {}
    data = load_json(cfg_path)
    mapping = {}
    for item in data.get("list", []):
        if not isinstance(item, dict):
            continue
        hex_key = str(item.get("hex") or "").strip().lower()
        raw_path = item.get("path")
        if not hex_key or not raw_path:
            continue
        audio_path = Path(str(raw_path))
        if not audio_path.is_absolute():
            audio_path = music_dir / audio_path
        if audio_path.suffix.lower() in AUDIO_SUFFIXES and audio_path.is_file():
            mapping[hex_key] = audio_path
    return mapping


def material_hex(material_id: str):
    return hashlib.md5(str(material_id).encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Export smart packaging assets for Windows desktop package.")
    parser.add_argument("--projects-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--text-template-draft", default="文字模板2")
    parser.add_argument("--sound-draft", default="音效库2")
    parser.add_argument("--output", default="smart-assets")
    parser.add_argument("--version", default=datetime.now().strftime("%Y.%m.%d"))
    args = parser.parse_args()

    projects_dir = Path(args.projects_dir).expanduser()
    cache_dir = Path(args.cache_dir).expanduser()
    output_dir = Path(args.output).expanduser()
    text_draft_dir = projects_dir / args.text_template_draft
    sound_draft_dir = projects_dir / args.sound_draft
    artist_effect_dir = cache_dir / "artistEffect"
    music_dir = cache_dir / "music"

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    copytree(text_draft_dir, output_dir / "text_templates" / args.text_template_draft)
    copytree(sound_draft_dir, output_dir / "sound_effects" / args.sound_draft)

    text_templates = extract_text_templates(text_draft_dir)
    sound_effects = extract_sound_effects(sound_draft_dir)

    missing_artist_effects = []
    copied_artist_effects = set()
    copied_effects = set()
    depends_queue = []
    for item in text_templates:
        material_id = item["material_id"]
        src = artist_effect_dir / material_id
        if src.is_dir():
            copytree(src, output_dir / "artistEffect" / material_id)
            copied_artist_effects.add(material_id)
            enqueue_artist_effect_depends(output_dir, material_id, depends_queue)
        else:
            missing_artist_effects.append(material_id)

    missing_asset_dependencies = []
    processed_depends = set()
    while depends_queue:
        depends_path = depends_queue.pop(0)
        depends_key = str(depends_path)
        if depends_key in processed_depends:
            continue
        processed_depends.add(depends_key)
        for record in parse_depends(depends_path):
            copied = copy_dependency_asset(record, cache_dir, output_dir)
            if not copied:
                missing_asset_dependencies.append(
                    {
                        "id": str(record.get("id") or ""),
                        "panel": str(record.get("panel") or ""),
                        "path": str(record.get("path") or ""),
                        "depends": str(depends_path),
                    }
                )
                continue
            if copied["bucket"] == "artistEffect":
                if copied["key"] not in copied_artist_effects:
                    copied_artist_effects.add(copied["key"])
                    enqueue_artist_effect_depends(output_dir, copied["key"], depends_queue)
            elif copied["bucket"] == "effect":
                copied_effects.add(copied["key"])

    (output_dir / "music").mkdir(parents=True, exist_ok=True)
    if (music_dir / "downLoadcfg").is_file():
        shutil.copy2(music_dir / "downLoadcfg", output_dir / "music" / "downLoadcfg")

    music_mapping = load_music_mapping(music_dir)
    missing_audio_files = []
    copied_audio = set()
    for item in sound_effects:
        material_id = item["material_id"]
        src = music_mapping.get(material_hex(material_id))
        if not src:
            missing_audio_files.append(material_id)
            continue
        dst = output_dir / "music" / src.name
        if src not in copied_audio:
            shutil.copy2(src, dst)
            copied_audio.add(src)

    manifest = {
        "version": args.version,
        "text_template_draft": args.text_template_draft,
        "sound_draft": args.sound_draft,
        "text_templates": text_templates,
        "sound_effects": sound_effects,
        "missing_artist_effects": missing_artist_effects,
        "copied_artist_effects": sorted(copied_artist_effects),
        "copied_effects": sorted(copied_effects),
        "missing_asset_dependencies": missing_asset_dependencies,
        "missing_audio_files": missing_audio_files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"smart-assets: {output_dir.resolve()}")
    print(f"text templates: {len(text_templates)}, missing artistEffect: {len(missing_artist_effects)}")
    print(f"asset dependencies: artistEffect={len(copied_artist_effects)}, effect={len(copied_effects)}, missing={len(missing_asset_dependencies)}")
    print(f"sound effects: {len(sound_effects)}, missing audio: {len(missing_audio_files)}")


if __name__ == "__main__":
    main()
