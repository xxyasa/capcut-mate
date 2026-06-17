#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def copytree(src: Path, dst: Path):
    if not src.exists():
        raise FileNotFoundError(f"Missing source directory: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True)


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
    for item in text_templates:
        material_id = item["material_id"]
        src = artist_effect_dir / material_id
        if src.is_dir():
            copytree(src, output_dir / "artistEffect" / material_id)
        else:
            missing_artist_effects.append(material_id)

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
        "missing_audio_files": missing_audio_files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"smart-assets: {output_dir.resolve()}")
    print(f"text templates: {len(text_templates)}, missing artistEffect: {len(missing_artist_effects)}")
    print(f"sound effects: {len(sound_effects)}, missing audio: {len(missing_audio_files)}")


if __name__ == "__main__":
    main()
