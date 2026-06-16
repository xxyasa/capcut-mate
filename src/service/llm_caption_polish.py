import json
import re
from typing import Any, Dict, List, Optional

import requests

from exceptions import CustomError, CustomException
from src.schemas.smart_packaging import SmartPackagingLlmCaptionConfig
from src.utils.logger import logger


def _auth_headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _build_prompt(captions: List[dict]) -> str:
    compact = [
        {
            "index": index,
            "start": caption["start"],
            "end": caption["end"],
            "text": caption["text"],
        }
        for index, caption in enumerate(captions)
    ]
    return (
        "你是中文短视频字幕校对助手。请在不改变字幕段数、不改变每段时间轴、"
        "不合并、不拆分、不增删信息的前提下，修正 ASR 字幕里的错别字、同音误识别、"
        "明显标点和专有名词错误。每段字幕长度应尽量接近原文，避免扩写。"
        "同时，请为每段字幕提炼适合做短视频花字强调的重点词列表 highlights，"
        "优先选择产品描述、颜色、材质、结构、卖点、情绪价值、金句里的核心词。"
        "每个重点词控制在 2 到 5 个中文字符，单段最多 3 个；一般只选择形容词、名词、品牌名、IP 名、"
        "产品相关词、颜色词、材质词、结构词、功能词或情绪/卖点核心词。"
        "不要选择泛指词、数量词、代词、助词结构、普通口水词、动宾半截短语或 ASR 粘连出来的不自然片段；"
        "禁止返回“xx的xx的”“xx的一个”“一个xx”“这一款”“这个/那个/我们/你们”等结构，"
        "也禁止返回包含“到这一款/喜欢到/那里是可以/前方这边/前方还做了/欢这一款”等口语壳的词。"
        "如果候选词里同时出现泛化片段和核心商品词，只保留核心商品词，例如："
        "“喜欢到这一款包包的”只能返回“包包”，不能返回“到这一款包”；"
        "“铁锈红的一个包身”返回“铁锈红”“包身”，不能返回“一个包”；"
        "“前方还做了压纹设计”返回“压纹”或“设计”，不能返回“前方还做了”。"
        "同一段内 highlights 必须去重；互相包含或语义重复的词只保留更自然、更具体的那个。"
        "在输出前自检 highlights：每个词单独读出来必须像一个自然中文词语或商品属性词，不能像截断的句子。"
        "只提取原字幕中出现或校正后文本中自然出现的词，不要改写成原文没有的营销词。"
        "只返回 JSON 数组，数组长度必须与输入一致；每项格式为 "
        '{"index": 0, "text": "修正后的字幕", "highlights": ["重点词1", "重点词2"]}。不要返回 markdown。'
        f"\n输入字幕：{json.dumps(compact, ensure_ascii=False)}"
    )


def _is_valid_highlight_term(text: str) -> bool:
    if not 2 <= len(text) <= 5:
        return False
    weak_words = {
        "一个", "一种", "一款", "这款", "这一款", "这个", "那个", "我们", "你们", "他们", "大家",
        "今天", "然后", "可以", "继续", "来看", "那里", "这里", "这边", "那边", "前方", "后方",
        "还做了", "做了", "是可以",
    }
    if text in weak_words:
        return False
    if text.startswith((
        "一个", "一种", "一款", "这个", "那个", "这一个", "这一款", "然后", "可以", "继续", "来看",
        "那里", "这里", "这边", "那边", "前方", "后方", "欢这一款", "喜欢到", "到这一款", "到这款",
    )):
        return False
    if any(word in text for word in (
        "我们", "你们", "他们", "大家", "这边", "那边", "可以", "做了", "还是", "还做",
        "这一款", "这一个", "这款", "一款", "这个", "那个", "喜欢到",
    )):
        return False
    if text.endswith(("的一个", "的一款", "的这个", "的那个")):
        return False
    if re.search(r"的.{1,3}的", text):
        return False
    if "的" in text:
        return False
    if text.count("的") >= 2:
        return False
    return True


def _highlight_core_term(text: str) -> str:
    product_terms = (
        "格兰芬多", "斯莱特林", "赫奇帕奇", "拉文克劳", "橘黄色", "橙黄色", "铁锈红", "铁锈",
        "红色", "黄色", "蓝色", "白色", "黑色", "金色", "银色", "棕色", "包身", "包包",
        "小隔层", "隔层", "拉链", "宝剑", "勇气", "压纹", "学院", "赠送", "魔杖", "设计",
    )
    for term in sorted(product_terms, key=len, reverse=True):
        if term in text:
            return term
    suffix_pattern = r"[\u4e00-\u9fff]{1,4}(?:色|红|黄|蓝|白|黑|金|银|棕|包|剑|纹|层|链)"
    matches = [match.group(0) for match in re.finditer(suffix_pattern, text)]
    if matches:
        return sorted(matches, key=len, reverse=True)[0]
    return text


def _clean_highlight_term(text: str) -> str:
    cleaned = re.sub(r"\s+", "", str(text or ""))
    cleaned = re.sub(r"[，,。！？!?；;：:“”\"'、（）()\[\]【】《》<>]", "", cleaned)
    cleaned = re.sub(r"的+$", "", cleaned)
    return cleaned


def _normalize_highlight_term(text: str) -> str:
    cleaned = _clean_highlight_term(text)
    if _is_valid_highlight_term(cleaned):
        return cleaned
    core = _highlight_core_term(cleaned)
    if core != cleaned and _is_valid_highlight_term(core):
        return core
    return ""


def _extract_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    return str(content)


def _parse_json_array(text: str) -> List[dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", cleaned)
        if not match:
            raise
        data = json.loads(match.group(0))

    if not isinstance(data, list):
        raise ValueError("LLM response is not a JSON array")
    return data


def _normalize_llm_highlights(item: dict) -> List[str]:
    raw_highlights = item.get("highlights")
    if raw_highlights is None:
        raw_highlights = item.get("highlight_terms")
    if raw_highlights is None:
        raw_highlights = item.get("highlight")

    if isinstance(raw_highlights, str):
        candidates = re.split(r"[|,，、\n]+", raw_highlights)
    elif isinstance(raw_highlights, list):
        candidates = [str(value) for value in raw_highlights]
    else:
        candidates = []

    normalized = []
    seen = set()
    for candidate in candidates:
        cleaned = _normalize_highlight_term(candidate)
        if not cleaned or cleaned in seen:
            continue
        if not _is_valid_highlight_term(cleaned):
            continue
        if any(cleaned != kept and (cleaned in kept or kept in cleaned) for kept in normalized):
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
        if len(normalized) >= 3:
            break
    return normalized


def polish_captions_with_llm(
    captions: List[dict],
    llm: SmartPackagingLlmCaptionConfig,
    fallback_api_key: Optional[str] = None,
) -> List[dict]:
    """用 LLM 校对字幕文本，但强制保留原字幕段数与时间轴。"""

    if not llm.enabled or not llm.endpoint or not captions:
        return captions

    payload = {
        "model": llm.model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": _build_prompt(captions)}],
            }
        ],
        "stream": False,
    }

    try:
        response = requests.post(
            llm.endpoint,
            headers=_auth_headers(llm.api_key or fallback_api_key),
            json=payload,
            timeout=llm.timeout,
        )
        response.raise_for_status()
        items = _parse_json_array(_extract_content(response.json()))
    except Exception as exc:
        logger.error(f"LLM caption polish failed: {exc}")
        raise CustomException(CustomError.MATERIAL_CREATE_FAILED, f"LLM caption polish failed: {exc}") from exc

    by_index = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "")).strip()
        if text:
            by_index[index] = {"text": text, "highlights": _normalize_llm_highlights(item)}

    polished = [dict(caption) for caption in captions]
    if len(by_index) != len(captions):
        logger.warning("LLM response count mismatch, keep original captions")
        return captions

    for index, caption in enumerate(polished):
        caption["text"] = by_index[index]["text"]
        if by_index[index]["highlights"]:
            caption["highlights"] = by_index[index]["highlights"]
            caption["highlight"] = "|".join(by_index[index]["highlights"])
    return polished
