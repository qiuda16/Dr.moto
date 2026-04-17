import base64
import io
import logging
import os
import re
import json
from html import unescape
from typing import Any

import requests
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger("ai.ocr")

OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr_vl:8080").rstrip("/")
OCR_SERVICE_TIMEOUT_SECONDS = int(os.getenv("OCR_SERVICE_TIMEOUT_SECONDS", "1800"))
OCR_PDF_BATCH_PAGES = max(1, int(os.getenv("OCR_PDF_BATCH_PAGES", "4")))
BFF_URL = os.getenv("BFF_URL", "").rstrip("/")
LLM_CLASSIFIER_ENABLED = os.getenv("OCR_LLM_CLASSIFIER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
LLM_PROVIDER = os.getenv("OCR_LLM_PROVIDER", "openai").strip().lower()
LLM_API_URL = os.getenv("OCR_LLM_API_URL", "").rstrip("/")
LLM_MODEL = os.getenv("OCR_LLM_MODEL", "")
LLM_API_KEY = os.getenv("OCR_LLM_API_KEY", "")
LLM_TIMEOUT_SECONDS = int(os.getenv("OCR_LLM_TIMEOUT_SECONDS", "120"))

PARSER_VERSION = "paddleocr-vl-technician-v2"

SECTION_LABELS = {"doc_title", "paragraph_title", "section_title", "title"}
OPERATION_KEYWORDS = (
    "拆",
    "装",
    "更换",
    "检查",
    "清洁",
    "紧固",
    "拧紧",
    "松开",
    "连接",
    "断开",
    "测量",
    "调整",
    "加注",
    "排放",
    "安装",
    "拆卸",
)

SPEC_PATTERNS = [
    ("torque", "扭矩", re.compile(r"(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>N[·\s-]?m|Nm|N-m|kgf[·\s-]?m)", re.I)),
    ("pressure", "胎压", re.compile(r"(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>psi|kpa|bar)", re.I)),
    ("voltage", "电压", re.compile(r"(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>v|volt)", re.I)),
    ("capacity", "容量", re.compile(r"(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>l|L|ml|mL|cc)", re.I)),
    ("clearance", "间隙", re.compile(r"(?P<value>\d+(?:\.\d+)?)\s?(?P<unit>mm)", re.I)),
]

NON_PROCEDURE_PAGE_TYPES = {"cover", "preface", "index", "legend", "reference"}
NON_SPEC_PAGE_TYPES = {"cover", "preface", "index", "legend"}
PAGE_TYPE_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("cover", ("维修手册", "service manual", "owner manual", "suzuki", "honda", "yamaha", "ducati", "bmw")),
    ("preface", ("前言", "preface", "编者的话", "说明", "本手册是")),
    ("index", ("索引", "目录", "contents", "基本信息 1", "点检保养", "发动机 3")),
    ("legend", ("专用符号", "符号 涵义", "special symbols", "注：", "符号说明")),
    ("spec_table", ("扭矩", "nm", "psi", "kpa", "volt", "容量", "mm")),
    ("procedure", ("拆卸", "安装", "更换", "检查", "调整", "步骤", "作业")),
]

SPEC_TYPE_ALIASES = {
    "torque": "torque",
    "pressure": "pressure",
    "voltage": "voltage",
    "capacity": "capacity",
    "fluid": "capacity",
    "clearance": "clearance",
    "electrical": "voltage",
}

SPEC_TYPE_LABELS = {
    "torque": "扭矩",
    "pressure": "胎压/压力",
    "voltage": "电气",
    "capacity": "油液/容量",
    "clearance": "间隙",
}

SPEC_RANGE_PATTERN = r"\d+(?:\.\d+)?(?:\s*[-~～]\s*\d+(?:\.\d+)?)?"
STEP_PREFIX_PATTERN = re.compile(
    r"^(?:[#•·\-\s]+|(?:step|item)\s*\d+\s*[:.\-]|\d+\s*[.)、:：-]|[A-Za-z]\s*[.)、:：-]|[IVXivx]+\s*[.)、:：-]|[一二三四五六七八九十]+\s*[、.])\s*",
    re.I,
)
STEP_START_PATTERN = re.compile(
    r"^(?:(?:step|item)\s*\d+\s*[:.\-]|\d+\s*[.)、:：-]|[A-Za-z]\s*[.)、:：-]|[IVXivx]+\s*[.)、:：-]|[一二三四五六七八九十]+\s*[、.])\s*",
    re.I,
)
STEP_DETAIL_HINTS = ("扭矩", "N·m", "Nm", "注意", "警告", "使用", "安装", "拆下", "更换", "加注", "涂抹", "清洁", "确认", "检查")
TABLE_VALUE_SPLIT_PATTERN = re.compile(r"\s*(?:[:：]\s*|\|\s*|/+\s*|\t+|\s{2,})")
ENGLISH_OBJECT_PATTERN = re.compile(
    r"\b(?:bolt|nut|screw|washer|plug|filter|oil|coolant|brake|fork|chain|sprocket|wheel|tire|caliper|disc|cover|seal|bearing|spark\s+plug|drain\s+bolt|engine\s+oil)\b",
    re.I,
)
TOOL_CODE_PATTERN = re.compile(r"\b[A-Z]{2,}-\d{3,}\b")
FASTENER_SIZE_PATTERN = re.compile(r"\bM\d+(?:\s*[xX×]\s*\d+(?:\.\d+)?)?(?:\s*[-~～]\s*\d+(?:\.\d+)?)?\b", re.I)
SCREWDRIVER_SIZE_PATTERN = re.compile(r"(?<![A-Z])(?:PH|SL|T)\s?\d{1,2}\b", re.I)
SOCKET_PATTERN = re.compile(r"\b\d{1,2}(?:\.\d+)?\s?(?:mm|MM)\s*(?:套筒|扳手|梅花扳手|开口扳手)\b")
ALLEN_PATTERN = re.compile(r"\b\d{1,2}(?:\.\d+)?\s?(?:mm|MM)\s*(?:内六角|六角扳手)\b")

TOOL_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("扭力扳手", "扭力扳手"),
    ("力矩扳手", "扭力扳手"),
    ("套筒", "套筒"),
    ("开口扳手", "开口扳手"),
    ("梅花扳手", "梅花扳手"),
    ("内六角扳手", "内六角扳手"),
    ("六角扳手", "六角扳手"),
    ("十字螺丝刀", "十字螺丝刀"),
    ("一字螺丝刀", "一字螺丝刀"),
    ("卡簧钳", "卡簧钳"),
    ("拉马", "拉马"),
    ("塞尺", "塞尺"),
    ("游标卡尺", "游标卡尺"),
    ("千分尺", "千分尺"),
    ("torque wrench", "扭力扳手"),
    ("allen wrench", "内六角扳手"),
    ("allen key", "内六角扳手"),
    ("socket wrench", "套筒"),
    ("feeler gauge", "塞尺"),
    ("screwdriver", "螺丝刀"),
    ("トルクレンチ", "扭力扳手"),
    ("六角レンチ", "内六角扳手"),
    ("ソケットレンチ", "套筒"),
    ("シックネスゲージ", "塞尺"),
)

FASTENER_DRIVE_HINTS: tuple[tuple[str, str], ...] = (
    ("内六角", "内六角"),
    ("六角", "六角"),
    ("十字", "十字"),
    ("一字", "一字"),
    ("梅花", "梅花"),
    ("torx", "梅花"),
    ("phillips", "十字"),
    ("allen", "内六角"),
)

MATERIAL_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("机油滤清器", "机油滤清器"),
    ("机滤", "机油滤清器"),
    ("机油", "机油"),
    ("空气滤清器", "空气滤清器"),
    ("空滤", "空气滤清器"),
    ("空气滤芯", "空气滤芯"),
    ("滤芯", "滤芯"),
    ("火花塞", "火花塞"),
    ("冷却液", "冷却液"),
    ("防冻液", "冷却液"),
    ("制动液", "制动液"),
    ("刹车油", "制动液"),
    ("前叉油", "前叉油"),
    ("齿轮油", "齿轮油"),
    ("润滑脂", "润滑脂"),
    ("黄油", "润滑脂"),
    ("螺纹锁固剂", "螺纹锁固剂"),
    ("螺纹胶", "螺纹锁固剂"),
    ("密封胶", "密封胶"),
    ("垫片", "垫片"),
    ("油封", "油封"),
    ("o型圈", "O型圈"),
    ("engine oil", "机油"),
    ("oil filter", "机油滤清器"),
    ("air filter", "空气滤清器"),
    ("coolant", "冷却液"),
    ("brake fluid", "制动液"),
    ("fork oil", "前叉油"),
    ("gear oil", "齿轮油"),
    ("sealant", "密封胶"),
    ("thread locking agent", "螺纹锁固剂"),
    ("エンジンオイル", "机油"),
    ("オイルフィルタ", "机油滤清器"),
    ("エアフィルタ", "空气滤清器"),
    ("クーラント", "冷却液"),
    ("ブレーキフルード", "制动液"),
    ("フォークオイル", "前叉油"),
)

GENERIC_STEP_PHRASES = {
    "拆卸",
    "安装",
    "检查",
    "调整",
    "清洁",
    "测量",
    "更换",
    "作业",
    "步骤",
    "注意事项",
    "维修信息",
    "基本信息",
    "目录",
}

ACTION_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("removal", ("拆下", "拆卸", "卸下", "取下", "拔下", "松开", "放出", "排出")),
    ("installation", ("安装", "装回", "装入", "回装", "复位", "装配")),
    ("tightening", ("紧固", "拧紧", "按扭矩", "按规定扭矩", "锁紧")),
    ("inspection", ("检查", "确认", "观察", "测量", "检测")),
    ("adjustment", ("调整", "校准", "对正", "张紧", "设定")),
    ("filling", ("加注", "注入", "加入", "补充")),
    ("cleaning", ("清洁", "清洗", "擦净")),
)

CAUTION_HINTS = ("注意", "警告", "危险", "小心", "防止", "避免", "不得", "严禁")
VERIFICATION_HINTS = ("确认", "检查", "无渗漏", "无卡滞", "转动顺畅", "达到规定", "到位", "对正", "自由间隙")


FLUID_MATERIAL_NAMES = {"机油", "冷却液", "制动液", "前叉油", "齿轮油"}
FILTER_MATERIAL_HINTS = ("滤", "滤芯", "滤清器")


def _join_text_parts(parts: list[str]) -> str | None:
    items = [item.strip() for item in parts if str(item or "").strip()]
    return "、".join(dict.fromkeys(items)) or None


REPAIR_TRANSLATION_PHRASES_EN: tuple[tuple[str, str], ...] = (
    ("thread locking agent", "螺纹锁固剂"),
    ("engine oil capacity", "机油容量"),
    ("drain bolt torque", "放油螺栓扭矩"),
    ("oil filter", "机油滤清器"),
    ("engine oil", "机油"),
    ("drain bolt", "放油螺栓"),
    ("service limit", "使用限度"),
    ("standard value", "标准值"),
    ("limit value", "极限值"),
    ("applicable model", "适用车型"),
    ("special tool", "专用工具"),
    ("service tool", "专用工具"),
    ("cold engine", "冷机"),
    ("valve clearance", "气门间隙"),
    ("chain slack", "链条松弛量"),
    ("brake fluid", "制动液"),
    ("fork oil", "前叉油"),
    ("coolant", "冷却液"),
    ("spark plug", "火花塞"),
    ("feeler gauge", "塞尺"),
    ("allen wrench", "内六角扳手"),
    ("allen key", "内六角扳手"),
    ("torque wrench", "扭力扳手"),
    ("torque", "扭矩"),
    ("remove", "拆下"),
    ("install", "安装"),
    ("replace", "更换"),
    ("inspect", "检查"),
    ("check", "检查"),
    ("adjust", "调整"),
    ("tighten", "紧固"),
    ("loosen", "松开"),
    ("apply", "涂覆"),
    ("fill", "加注"),
    ("drain", "排放"),
    ("clean", "清洁"),
    ("bolt", "螺栓"),
    ("nut", "螺母"),
    ("screw", "螺钉"),
    ("washer", "垫片"),
    ("plug", "塞"),
    ("filter", "滤清器"),
    ("tool", "工具"),
    ("note", "备注"),
    ("model", "车型"),
)

REPAIR_TRANSLATION_PHRASES_JA: tuple[tuple[str, str], ...] = (
    ("エンジンオイル容量", "机油容量"),
    ("ドレンボルト締付トルク", "放油螺栓扭矩"),
    ("サービスリミット", "使用限度"),
    ("基準値", "标准值"),
    ("専用工具", "专用工具"),
    ("適用車種", "适用车型"),
    ("備考", "备注"),
    ("項目", "项目"),
    ("エンジンオイル", "机油"),
    ("オイルフィルタ", "机油滤清器"),
    ("ドレンボルト", "放油螺栓"),
    ("ブレーキフルード", "制动液"),
    ("クーラント", "冷却液"),
    ("フォークオイル", "前叉油"),
    ("バルブクリアランス", "气门间隙"),
    ("チェーンたるみ", "链条松弛量"),
    ("締付トルク", "扭矩"),
    ("取外し", "拆下"),
    ("取り外し", "拆下"),
    ("取付け", "安装"),
    ("取り付け", "安装"),
    ("交換", "更换"),
    ("点検", "检查"),
    ("調整", "调整"),
    ("清掃", "清洁"),
    ("締め付け", "紧固"),
    ("給油", "加注"),
    ("排出", "排放"),
    ("冷機", "冷机"),
)


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff]", str(text or "")))


def _translate_repair_text(text: str | None) -> str:
    source = _clean_text(text)
    if not source:
        return source
    if _contains_chinese(source) and not _contains_japanese(source) and not re.search(r"[A-Za-z]", source):
        return source
    translated = source
    for raw, zh in sorted(REPAIR_TRANSLATION_PHRASES_JA, key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(raw, zh)
    for raw, zh in sorted(REPAIR_TRANSLATION_PHRASES_EN, key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(raw)}\b", zh, translated, flags=re.I)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated if translated.lower() != source.lower() else source


def _build_bilingual_text(text: str | None) -> dict[str, str | None]:
    original = _clean_text(text)
    zh = _translate_repair_text(original)
    return {
        "original": original or None,
        "zh": zh if zh and zh != original else None,
    }


def _augment_named_row_bilingual(item: dict[str, Any], name_key: str = "name") -> dict[str, Any]:
    row = dict(item or {})
    bilingual = _build_bilingual_text(row.get(name_key))
    if bilingual["zh"]:
        row[f"{name_key}_zh"] = bilingual["zh"]
    if bilingual["original"]:
        row[f"{name_key}_original"] = bilingual["original"]
    return row


def _is_table_like_line(line: str) -> bool:
    normalized = _clean_step_text(line)
    if not normalized:
        return False
    if STEP_START_PATTERN.match(normalized) or re.match(r"^[•·\-]\s*", normalized):
        return False
    return len([part for part in TABLE_VALUE_SPLIT_PATTERN.split(normalized) if part.strip()]) >= 2


def _classify_line_role(line: str) -> str:
    normalized = _clean_step_text(line)
    stripped = _strip_step_prefix(normalized)
    if not normalized:
        return "empty"
    if normalized.startswith("#"):
        return "title"
    if STEP_START_PATTERN.match(normalized) or re.match(r"^[•·\-]\s*", normalized):
        return "procedure"
    if _is_table_like_line(normalized) and _looks_like_spec_content(normalized):
        return "spec"
    if _is_specific_step_line(normalized):
        return "procedure"
    if _looks_like_spec_content(stripped):
        return "spec"
    if len(normalized) <= 28 and not re.search(r"[。；;]", normalized):
        return "title"
    return "note"


def _segment_page_content(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current_role = ""
    current_lines: list[str] = []
    for raw_line in _split_clean_lines(text):
        role = _classify_line_role(raw_line)
        if role == "empty":
            continue
        if current_role and role != current_role:
            segments.append(
                {
                    "role": current_role,
                    "text": "\n".join(current_lines).strip(),
                    "line_count": len(current_lines),
                }
            )
            current_lines = []
        current_role = role
        current_lines.append(raw_line)
    if current_role and current_lines:
        segments.append(
            {
                "role": current_role,
                "text": "\n".join(current_lines).strip(),
                "line_count": len(current_lines),
            }
        )
    return segments


def _normalize_spec_table_column(value: str) -> str:
    normalized = _clean_step_text(value).lower()
    compact = re.sub(r"[\s_.-]+", "", normalized)
    if any(token in normalized for token in ("\u9879\u76ee", "item", "name", "\u90e8\u4f4d", "\u68c0\u67e5\u9879\u76ee", "\u96f6\u4ef6\u540d\u79f0", "part", "\u9805\u76ee", "\u90e8\u54c1\u540d")) or compact in {"item", "part", "name"}:
        return "item"
    if any(token in normalized for token in ("\u6807\u51c6", "spec", "\u6807\u51c6\u503c", "value", "\u6807\u51c6\u8303\u56f4", "\u89c4\u5b9a\u503c", "set value", "reference", "\u57fa\u6e96\u5024", "\u6a19\u6e96\u503c", "\u898f\u5b9a\u5024")) or compact in {"std", "spec", "standard", "setvalue", "reference"}:
        return "standard_value"
    if any(token in normalized for token in ("\u6781\u9650", "limit", "service limit", "\u4f7f\u7528\u9650\u5ea6", "\u78e8\u8017\u9650\u5ea6", "\u5141\u8bb8\u6781\u9650", "\u4f7f\u7528\u9650\u5ea6", "\u9650\u5ea6", "\u30b5\u30fc\u30d3\u30b9\u30ea\u30df\u30c3\u30c8")) or compact in {"limit", "max", "minmax", "servicelimit"}:
        return "limit_value"
    if any(token in normalized for token in ("\u5de5\u5177", "tool", "\u4e13\u7528\u5de5\u5177", "service tool", "sst", "\u5c02\u7528\u5de5\u5177", "\u5de5\u5177\u540d")) or compact in {"tool", "tools", "servicetool", "sst"}:
        return "tool"
    if any(token in normalized for token in ("\u5907\u6ce8", "note", "\u8bf4\u660e", "comment", "\u6ce8\u610f", "\u5099\u8003", "\u6ce8\u610f\u4e8b\u9805")) or compact in {"note", "notes", "remark", "remarks", "comment"}:
        return "note"
    if any(token in normalized for token in ("\u9002\u7528\u8f66\u578b", "applicable model", "model", "vehicle", "\u9069\u7528\u8eca\u7a2e", "\u9069\u7528\u8eca\u578b")) or compact in {"model", "models", "vehicle", "applicablemodel"}:
        return "model"
    return normalized or "column"


def _extract_spec_table_rows(text: str) -> list[dict[str, Any]]:
    lines = _split_clean_lines(text)
    split_rows: list[list[str]] = []
    for line in lines:
        normalized_line = _clean_step_text(line)
        looks_tabular = _is_table_like_line(normalized_line) or "|" in normalized_line or "：" in line or ":" in line
        if not looks_tabular:
            continue
        parts = [part.strip() for part in TABLE_VALUE_SPLIT_PATTERN.split(normalized_line) if part.strip()]
        if len(parts) >= 2:
            split_rows.append(parts[:6])
    if len(split_rows) < 2:
        return []
    header = split_rows[0]
    header_keys = [_normalize_spec_table_column(part) for part in header]
    if len(set(header_keys)) == 1 and header_keys[0] == "column":
        header_keys = ["item", "standard_value", "limit_value", "tool", "note", "model"][: len(header)]
        data_rows = split_rows
    else:
        data_rows = split_rows[1:]
    rows: list[dict[str, Any]] = []
    for row in data_rows[:80]:
        mapped: dict[str, Any] = {"source_text": " | ".join(row)}
        for index, cell in enumerate(row):
            key = header_keys[index] if index < len(header_keys) else f"column_{index + 1}"
            mapped[key] = cell
        if mapped.get("item") or mapped.get("standard_value"):
            rows.append(mapped)
    return rows


def _augment_spec_table_rows_bilingual(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    augmented: list[dict[str, Any]] = []
    for row in rows or []:
        item = dict(row or {})
        for key in ("item", "tool", "note", "model"):
            bilingual = _build_bilingual_text(item.get(key))
            if bilingual["zh"]:
                item[f"{key}_zh"] = bilingual["zh"]
            if bilingual["original"]:
                item[f"{key}_original"] = bilingual["original"]
        augmented.append(item)
    return augmented


def _augment_specs_bilingual(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    augmented: list[dict[str, Any]] = []
    for row in rows or []:
        item = dict(row or {})
        bilingual = _build_bilingual_text(item.get("label"))
        if bilingual["zh"]:
            item["label_zh"] = bilingual["zh"]
        if bilingual["original"]:
            item["label_original"] = bilingual["original"]
        augmented.append(item)
    return augmented


def _detect_document_language(text: str) -> str:
    source = _clean_text(text)
    if not source:
        return "zh-CN"
    if _contains_chinese(source):
        return "zh-CN"
    if re.search(r"[\u3040-\u30ff]", source):
        return "ja-JP"
    if re.search(r"[A-Za-z]", source):
        return "en"
    return "unknown"


def _post_progress(
    job_id: int | None,
    status: str,
    progress_percent: int,
    message: str,
    processed_batches: int | None = None,
    total_batches: int | None = None,
):
    if not job_id or not BFF_URL:
        return
    try:
        payload: dict[str, Any] = {
            "status": status,
            "progress_percent": progress_percent,
            "progress_message": message,
        }
        if processed_batches is not None:
            payload["processed_batches"] = processed_batches
        if total_batches is not None:
            payload["total_batches"] = total_batches
        requests.post(
            f"{BFF_URL}/mp/knowledge/internal/parse-jobs/{job_id}/progress",
            json=payload,
            timeout=15,
        ).raise_for_status()
    except Exception as exc:
        logger.warning("Failed to report OCR progress for job %s: %s", job_id, exc)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _summarize_text(text: str) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:220]


def _split_clean_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line and line.strip()]


def _normalize_label_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip("：:;；，,.- ")


def _clean_step_text(value: str) -> str:
    text = _clean_text(value)
    text = text.replace("：", ":").replace("（", "(").replace("）", ")")
    text = re.sub(r"[│｜¦]", "|", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([；;，,。])\s*", r"\1", text)
    return text.strip()


def _dedupe_dict_items(items: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for item in items:
        key = tuple(str(item.get(field) or "").strip().lower() for field in key_fields)
        if not any(key):
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _infer_subject_label(line: str, base_label: str, match_start: int) -> str:
    prefix = _normalize_label_text((line or "")[:match_start])
    if not prefix:
        return base_label
    candidates = [segment for segment in re.split(r"[：:\-;；，,]\s*", prefix) if segment.strip()]
    subject = _normalize_label_text(candidates[-1] if candidates else prefix)
    if not subject:
        return base_label
    if base_label in subject:
        return subject
    if len(subject) > 24:
        subject = subject[-24:]
    return f"{subject}{base_label}"


def _extract_tools_from_line(line: str) -> list[str]:
    tools: list[str] = []
    normalized_line = str(line or "")
    lowered = normalized_line.lower()
    for pattern in (TOOL_CODE_PATTERN, SCREWDRIVER_SIZE_PATTERN, SOCKET_PATTERN, ALLEN_PATTERN):
        for match in pattern.finditer(normalized_line):
            tools.append(_normalize_label_text(match.group(0)))
    allen_size_match = re.search(r"\bM\d+\b", normalized_line, re.I)
    if allen_size_match and ("内六角扳手" in normalized_line or "六角扳手" in normalized_line):
        suffix = "内六角扳手" if "内六角扳手" in normalized_line else "六角扳手"
        tools.append(f"{allen_size_match.group(0).upper()} {suffix}")
    for raw_keyword, normalized_keyword in TOOL_KEYWORDS:
        if raw_keyword in normalized_line or raw_keyword in lowered:
            tools.append(normalized_keyword)
    result: list[str] = []
    seen: set[str] = set()
    for tool_name in tools:
        name = _normalize_label_text(tool_name)
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        result.append(name)
    prioritized = sorted(result, key=len, reverse=True)
    filtered: list[str] = []
    for item in prioritized:
        compact = item.replace(" ", "")
        if any(compact != existing.replace(" ", "") and compact in existing.replace(" ", "") for existing in filtered):
            continue
        filtered.append(item)
    return filtered


def _extract_materials_from_line(line: str) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []
    normalized_line = str(line or "")
    for raw_keyword, normalized_keyword in MATERIAL_KEYWORDS:
        lowered = normalized_line.lower()
        if raw_keyword in normalized_line or raw_keyword in lowered:
            quantity_match = re.search(
                rf"{re.escape(raw_keyword)}[^0-9]{{0,6}}(?P<value>{SPEC_RANGE_PATTERN})\s?(?P<unit>L|l|ml|mL|cc|g|kg|瓶|支|个|只)",
                normalized_line,
                re.I,
            )
            materials.append(
                {
                    "name": normalized_keyword,
                    "value": quantity_match.group("value").replace(" ", "") if quantity_match else "",
                    "unit": quantity_match.group("unit") if quantity_match else "",
                    "source_text": normalized_line[:220],
                }
            )
    return _dedupe_dict_items(materials, ("name", "value", "unit"))


def _extract_fasteners_from_line(line: str) -> list[dict[str, Any]]:
    fasteners: list[dict[str, Any]] = []
    normalized_line = str(line or "")
    if "螺" not in normalized_line and "bolt" not in normalized_line.lower() and "screw" not in normalized_line.lower():
        return []
    sizes = [match.group(0).replace(" ", "") for match in FASTENER_SIZE_PATTERN.finditer(normalized_line)]
    drive_type = ""
    lowered = normalized_line.lower()
    for hint, normalized in FASTENER_DRIVE_HINTS:
        if hint in normalized_line or hint in lowered:
            drive_type = normalized
            break
    name_candidates = re.findall(r"([\u4e00-\u9fffA-Za-z0-9（）()\-]{2,24}螺(?:栓|钉|丝|母))", normalized_line)
    fastener_name = _normalize_label_text(name_candidates[-1]) if name_candidates else ""
    if "扳手" in fastener_name and "螺" in fastener_name:
        trailing = fastener_name[fastener_name.rfind("扳手") + 2 :]
        trailing = trailing.lstrip("拆下安装更换固定使用")
        if "螺" in trailing:
            fastener_name = trailing
    fastener_name = re.sub(r"^(拆下|装回|安装|更换|拆卸|回装|紧固|松开|取下|卸下)", "", fastener_name)
    fastener_name = _normalize_label_text(fastener_name)
    for size in sizes or [""]:
        fasteners.append(
            {
                "name": fastener_name or _infer_subject_label(normalized_line, "螺栓", normalized_line.find(size) if size else len(normalized_line)),
                "size": size,
                "drive_type": drive_type,
                "source_text": normalized_line[:220],
            }
        )
    return _dedupe_dict_items(fasteners, ("name", "size", "drive_type"))


def _strip_step_prefix(line: str) -> str:
    cleaned = _clean_step_text(line)
    cleaned = STEP_PREFIX_PATTERN.sub("", cleaned, count=1)
    return cleaned.strip()


def _looks_like_generic_step(line: str) -> bool:
    normalized = _normalize_label_text(_strip_step_prefix(line))
    if not normalized:
        return True
    if normalized in GENERIC_STEP_PHRASES:
        return True
    if len(normalized) <= 6 and any(keyword == normalized for keyword in OPERATION_KEYWORDS):
        return True
    if re.fullmatch(r"[A-Za-z0-9\s\-_/]+", normalized) and len(normalized.split()) <= 2:
        return True
    return False


def _has_specific_object(line: str) -> bool:
    normalized = _normalize_label_text(_strip_step_prefix(line))
    if not normalized:
        return False
    object_tokens = (
        "螺栓", "螺母", "螺钉", "机油", "机油滤清器", "机滤", "空气滤清器", "空滤", "滤芯",
        "制动盘", "制动钳", "卡钳", "链条", "链轮", "火花塞", "前叉", "减震器", "车轮",
        "后轮", "前轮", "轮胎", "放油螺栓", "排油螺栓", "机盖", "离合器", "气门", "垫片",
        "油封", "O型圈", "冷却液", "制动液", "前叉油", "端盖", "壳体", "轴承", "销", "套筒",
    )
    if any(token in normalized for token in object_tokens):
        return True
    if ENGLISH_OBJECT_PATTERN.search(normalized):
        return True
    if bool(re.search(r"M\d+|[0-9]+(?:\.[0-9]+)?(?:N·m|Nm|mm|L|ml|cc)", normalized, re.I)):
        return True
    if len(TABLE_VALUE_SPLIT_PATTERN.split(normalized)) >= 2 and _extract_tools_from_line(normalized):
        return True
    return False


def _is_specific_step_line(line: str) -> bool:
    normalized = _normalize_label_text(_strip_step_prefix(line))
    if not normalized or _looks_like_generic_step(normalized):
        return False
    has_operation = any(keyword in normalized for keyword in OPERATION_KEYWORDS)
    if not has_operation:
        has_operation = bool(_extract_tools_from_line(normalized)) and bool(re.search(r"\d", normalized))
    if not has_operation and re.search(r"\b(?:remove|install|replace|inspect|check|adjust|tighten|clean|apply|fill|drain)\b", normalized, re.I):
        has_operation = True
    if not has_operation:
        return False
    return _has_specific_object(normalized) or len(normalized) >= 10


def _merge_step_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    current = ""
    for raw_line in lines:
        if str(raw_line or "").lstrip().startswith("#"):
            if current and _is_specific_step_line(current):
                merged.append(current)
            current = ""
            continue
        line = _clean_step_text(raw_line)
        if not line:
            continue
        bullet_started = bool(re.match(r"^[•·\-]\s*", raw_line.strip()))
        new_step = bool(STEP_START_PATTERN.match(raw_line.strip())) or (
            bullet_started and _is_specific_step_line(line)
        ) or (
            _is_specific_step_line(line) and not current
        )
        if new_step:
            if current and _is_specific_step_line(current):
                merged.append(current)
            current = line
            continue
        is_detail_line = len(line) <= 60 or any(token in line for token in STEP_DETAIL_HINTS)
        if not is_detail_line and TABLE_VALUE_SPLIT_PATTERN.search(line):
            left_side = TABLE_VALUE_SPLIT_PATTERN.split(line, maxsplit=1)[0]
            is_detail_line = bool(left_side) and len(left_side) <= 24
        if current and is_detail_line:
            current = _clean_step_text(f"{current}；{_strip_step_prefix(line)}")
            continue
        if _is_specific_step_line(line):
            if current and _is_specific_step_line(current):
                merged.append(current)
            current = line
    if current and _is_specific_step_line(current):
        merged.append(current)
    return merged


def _infer_action_type(text: str) -> str:
    normalized = _clean_step_text(text)
    for action_type, hints in ACTION_TYPE_HINTS:
        if any(hint in normalized for hint in hints):
            return action_type
    return "operation"


def _infer_target_component(text: str, fasteners: list[dict[str, Any]] | None = None, materials: list[dict[str, Any]] | None = None) -> str | None:
    normalized = _strip_step_prefix(text)
    if fasteners:
        candidate = _clean_text((fasteners[0] or {}).get("name"))
        if candidate:
            return candidate
    if materials:
        candidate = _clean_text((materials[0] or {}).get("name"))
        if candidate:
            return candidate
    match = re.search(
        r"([\u4e00-\u9fffA-Za-z0-9（）()\-]{2,24}(?:螺栓|螺母|螺钉|机油滤清器|机油|空气滤清器|滤芯|火花塞|前叉|减震器|制动盘|制动钳|卡钳|链条|链轮|车轮|轮胎|放油螺栓|排油螺栓|端盖|壳体|气门|轴承|油封|O型圈))",
        normalized,
    )
    if match:
        return _normalize_label_text(match.group(1))
    return None


def _extract_caution_notes(text: str) -> list[str]:
    normalized = _clean_step_text(text)
    notes = []
    for hint in CAUTION_HINTS:
        if hint in normalized:
            notes.append(normalized)
            break
    return notes


def _extract_verification_points(
    text: str,
    torque_specs: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> list[str]:
    normalized = _clean_step_text(text)
    checks: list[str] = []
    if torque_specs:
        checks.extend(
            [f"按规定扭矩紧固 {item.get('label') or '紧固件'}：{item.get('value')}{item.get('unit')}" for item in torque_specs]
        )
    if materials:
        for item in materials:
            if item.get("value") and item.get("unit"):
                checks.append(f"确认 {item.get('name')} 加注量为 {item.get('value')}{item.get('unit')}")
    if fasteners:
        for item in fasteners:
            checks.append(
                "确认 "
                + " / ".join(part for part in [item.get("name"), item.get("size"), item.get("drive_type")] if part)
                + " 已正确装配"
            )
    for hint in VERIFICATION_HINTS:
        if hint in normalized:
            checks.append(normalized)
            break
    return _dedupe_dict_items([{"text": item} for item in checks], ("text",))


def _component_context(
    instruction: str,
    fasteners: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
) -> tuple[str | None, str | None]:
    target_component = _infer_target_component(instruction, fasteners, materials)
    fastener_name = _clean_text((fasteners or [{}])[0].get("name")) if fasteners else ""
    material_name = _clean_text((materials or [{}])[0].get("name")) if materials else ""
    primary = target_component or fastener_name or material_name or None
    combined = _join_text_parts([target_component or "", fastener_name, material_name])
    return primary, combined


def _infer_preconditions(
    instruction: str,
    action_type: str,
    tools: list[str] | None = None,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> list[str]:
    primary, context = _component_context(instruction, fasteners, materials)
    rows: list[str] = []
    if tools:
        tool_summary = _join_text_parts(list(tools)[:3])
        if tool_summary:
            rows.append(f"开工前备齐 {tool_summary}")
    if action_type == "removal" and primary:
        rows.append(f"确认 {primary} 周边已清洁，便于拆卸后检查密封面和螺纹")
    if action_type == "filling":
        fluid = _clean_text((materials or [{}])[0].get("name")) if materials else ""
        if fluid:
            rows.append(f"加注前确认 {fluid} 规格和容器清洁，避免混油或污染")
    if context and any(name in context for name in FLUID_MATERIAL_NAMES):
        rows.append(f"在 {context} 作业位置下方准备接液容器和擦拭材料")
    if context and any(hint in context for hint in FILTER_MATERIAL_HINTS):
        rows.append(f"拆装 {context} 前先确认新件、密封件或滤芯型号已备妥")
    return list(dict.fromkeys(rows))[:3]


def _infer_setup_conditions(
    instruction: str,
    action_type: str,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> list[str]:
    primary, context = _component_context(instruction, fasteners, materials)
    rows: list[str] = []
    if primary:
        rows.append(f"保持 {primary} 可视、可触达，避免被外壳或附件遮挡")
    if action_type in {"removal", "installation", "tightening"} and fasteners:
        rows.append("按原装顺序放置拆下的紧固件，防止混位或长度装错")
    if context and any(name in context for name in ("机油", "冷却液", "前叉油", "制动液")):
        rows.append("液体相关作业时保持车身稳定，必要时使车辆处于水平姿态")
    return list(dict.fromkeys(rows))[:3]


def _infer_reassembly_requirements(
    instruction: str,
    torque_specs: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> list[str]:
    primary, context = _component_context(instruction, fasteners, materials)
    rows: list[str] = []
    for item in torque_specs or []:
        label = item.get("label") or (primary or "紧固件")
        value = item.get("value")
        unit = item.get("unit")
        if value and unit:
            rows.append(f"复装 {label} 时按 {value}{unit} 扭矩锁紧")
    for item in fasteners or []:
        detail = _join_text_parts([item.get("name") or "", item.get("size") or "", item.get("drive_type") or ""])
        if detail:
            rows.append(f"回装时核对 {detail} 与拆下件一致")
    for item in materials or []:
        name = _clean_text(item.get("name"))
        value = item.get("value")
        unit = item.get("unit")
        if name and value and unit:
            rows.append(f"复装后补充 {name} 至 {value}{unit}")
    if context and any(hint in context for hint in FILTER_MATERIAL_HINTS):
        rows.append(f"复装 {context} 前检查密封圈、垫片或滤芯接触面是否完好")
    return list(dict.fromkeys(rows))[:4]


def _infer_common_failure_modes(
    instruction: str,
    action_type: str,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> list[str]:
    primary, context = _component_context(instruction, fasteners, materials)
    rows: list[str] = []
    if fasteners:
        rows.append(f"{primary or '该部位'} 螺纹滑牙或螺栓规格装错")
    if context and any(hint in context for hint in FILTER_MATERIAL_HINTS):
        rows.append(f"{context} 密封圈漏装、旧密封件未更换或接触面未清洁")
    if context and any(name in context for name in FLUID_MATERIAL_NAMES):
        rows.append(f"{context} 加注量错误、液体混用或作业后渗漏")
    if action_type == "tightening" and primary:
        rows.append(f"{primary} 扭矩不足导致松动，或过扭导致变形")
    return list(dict.fromkeys(rows))[:3]


def _infer_step_criticality(
    instruction: str,
    action_type: str,
    torque_specs: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
) -> str:
    normalized = _clean_step_text(instruction)
    material_names = " ".join(_clean_text(item.get("name")) for item in (materials or []))
    if torque_specs or any(token in normalized for token in CAUTION_HINTS):
        return "critical"
    if any(name in material_names for name in ("制动液", "冷却液", "机油")):
        return "critical"
    if action_type in {"tightening", "adjustment", "filling"}:
        return "major"
    return "normal"


def _infer_executor_role(action_type: str, criticality: str) -> str:
    if criticality == "critical":
        return "主修技师"
    if action_type in {"inspection", "adjustment", "tightening"}:
        return "维修技师"
    return "技师/学徒按标准作业"


def _infer_support_role(
    action_type: str,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> str | None:
    names = " ".join(_clean_text(item.get("name")) for item in (materials or []))
    if any(name in names for name in ("机油", "冷却液", "制动液", "前叉油")):
        return "物料员备液或备件"
    if fasteners and action_type in {"removal", "installation", "tightening"}:
        return "工位助手整理拆下件与新紧固件"
    return None


def _infer_verification_role(action_type: str, criticality: str) -> str:
    if criticality == "critical":
        return "班组长/质检复核"
    if action_type in {"inspection", "adjustment", "tightening"}:
        return "主修技师自检"
    return "岗位自检"


def _infer_record_requirements(
    action_type: str,
    torque_specs: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
    acceptance_checks: list[str] | None = None,
) -> list[str]:
    rows: list[str] = []
    for item in torque_specs or []:
        if item.get("value") and item.get("unit"):
            rows.append(f"记录 {item.get('label') or '扭矩'} = {item.get('value')}{item.get('unit')}")
    for item in materials or []:
        if item.get("value") and item.get("unit"):
            rows.append(f"记录 {item.get('name') or '耗材'} 用量 = {item.get('value')}{item.get('unit')}")
    if action_type in {"inspection", "adjustment"} and acceptance_checks:
        rows.append("记录检查结果与是否达标")
    return list(dict.fromkeys(rows))[:4]


def _infer_step_purpose(
    action_type: str,
    target_component: str | None = None,
    materials: list[dict[str, Any]] | None = None,
) -> str | None:
    material_name = _clean_text((materials or [{}])[0].get("name")) if materials else ""
    if action_type == "removal" and target_component:
        return f"为后续检查、清洁或更换 {target_component} 创造作业条件"
    if action_type == "installation" and target_component:
        return f"将 {target_component} 按标准状态复装到位"
    if action_type == "tightening" and target_component:
        return f"确保 {target_component} 达到规定锁紧状态"
    if action_type == "filling" and material_name:
        return f"将 {material_name} 补充到规定容量或液位"
    if action_type == "inspection" and target_component:
        return f"确认 {target_component} 状态满足继续装配或交车要求"
    if target_component:
        return f"完成 {target_component} 当前工序要求"
    return None


def _infer_completion_definition(
    target_component: str | None = None,
    acceptance_checks: list[str] | None = None,
    reassembly_requirements: list[str] | None = None,
) -> list[str]:
    rows: list[str] = []
    if target_component:
        rows.append(f"{target_component} 已按标准完成本工序且可进入下一步")
    rows.extend(reassembly_requirements or [])
    rows.extend(acceptance_checks or [])
    return list(dict.fromkeys(rows))[:4]


def _infer_input_requirements(
    tools: list[str] | None = None,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
    preconditions: list[str] | None = None,
) -> list[str]:
    rows: list[str] = []
    if tools:
        rows.append(f"工具已备齐：{_join_text_parts(list(tools)[:3])}")
    if materials:
        names = _join_text_parts([_clean_text(item.get("name")) for item in materials[:3]])
        if names:
            rows.append(f"物料已备齐：{names}")
    if fasteners:
        names = _join_text_parts([_clean_text(item.get('name')) for item in fasteners[:3]])
        if names:
            rows.append(f"紧固件已确认：{names}")
    rows.extend(preconditions or [])
    return list(dict.fromkeys(rows))[:4]


def _infer_output_results(
    target_component: str | None = None,
    completion_definition: list[str] | None = None,
    action_type: str = "operation",
) -> list[str]:
    rows: list[str] = []
    if action_type == "removal" and target_component:
        rows.append(f"{target_component} 已拆下并可进入后续检查/更换")
    elif action_type == "installation" and target_component:
        rows.append(f"{target_component} 已复装到位")
    elif action_type == "filling" and target_component:
        rows.append(f"{target_component} 已补充至规定状态")
    rows.extend(completion_definition or [])
    return list(dict.fromkeys(rows))[:4]


def _build_step_semantics(
    instruction: str,
    tools: list[str] | None = None,
    torque_specs: list[dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
    fasteners: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    action_type = _infer_action_type(instruction)
    verification_points = [item["text"] for item in _extract_verification_points(instruction, torque_specs, materials, fasteners)]
    caution_notes = [item for item in _extract_caution_notes(instruction) if item]
    preconditions = _infer_preconditions(instruction, action_type, tools, materials, fasteners)
    setup_conditions = _infer_setup_conditions(instruction, action_type, materials, fasteners)
    reassembly_requirements = _infer_reassembly_requirements(instruction, torque_specs, materials, fasteners)
    failure_modes = _infer_common_failure_modes(instruction, action_type, materials, fasteners)
    criticality = _infer_step_criticality(instruction, action_type, torque_specs, materials)
    record_requirements = _infer_record_requirements(action_type, torque_specs, materials, verification_points)
    target_component = _infer_target_component(instruction, fasteners, materials)
    completion_definition = _infer_completion_definition(target_component, verification_points, reassembly_requirements)
    input_requirements = _infer_input_requirements(tools, materials, fasteners, preconditions)
    output_results = _infer_output_results(target_component, completion_definition, action_type)
    return {
        "action_type": action_type,
        "target_component": target_component,
        "tooling_summary": "、".join(tools or []) or None,
        "step_purpose": _infer_step_purpose(action_type, target_component, materials),
        "input_requirements": input_requirements,
        "preconditions": preconditions[:4],
        "setup_conditions": setup_conditions[:4],
        "control_points": verification_points[:4],
        "acceptance_checks": verification_points[:4],
        "completion_definition": completion_definition,
        "output_results": output_results,
        "reassembly_requirements": reassembly_requirements[:4],
        "caution_notes": caution_notes[:3],
        "common_failure_modes": failure_modes[:3],
        "criticality": criticality,
        "executor_role": _infer_executor_role(action_type, criticality),
        "support_role": _infer_support_role(action_type, materials, fasteners),
        "verification_role": _infer_verification_role(action_type, criticality),
        "record_requirements": record_requirements,
    }


def _find_matching_specs_for_line(line: str, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_line = _normalize_label_text(line)
    matches = []
    for item in specs or []:
        source_text = _normalize_label_text(item.get("source_text"))
        label = _normalize_label_text(item.get("label"))
        if source_text and source_text in normalized_line:
            matches.append(item)
            continue
        if label and label.replace("扭矩", "") and label.replace("扭矩", "") in normalized_line:
            matches.append(item)
    return _dedupe_dict_items(matches, ("type", "label", "value", "unit"))


def _build_step_cards(pages: list[dict[str, Any]], specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    section_title = ""
    for page in pages:
        page_number = page.get("page_number")
        lines = _split_clean_lines(page.get("text") or "")
        merged_lines = _merge_step_lines(lines)
        for raw_line in merged_lines:
            line = raw_line.strip("•·- ")
            if not line:
                continue
            if line.startswith("#"):
                section_title = _normalize_label_text(line.lstrip("#"))
                continue
            if not _is_specific_step_line(line):
                continue
            line_specs = _find_matching_specs_for_line(line, specs)
            line_tools = _extract_tools_from_line(line)
            line_materials = _extract_materials_from_line(line)
            line_fasteners = _extract_fasteners_from_line(line)
            torque_specs = [item for item in line_specs if item.get("type") == "torque"]
            related_specs = [item for item in line_specs if item.get("type") != "torque"]
            semantics = _build_step_semantics(
                _strip_step_prefix(line),
                line_tools,
                torque_specs,
                line_materials,
                line_fasteners,
            )
            cards.append(
                {
                    "step_order": len(cards) + 1,
                    "section_title": section_title or None,
                    "instruction": _strip_step_prefix(line)[:400],
                    "instruction_original": _clean_step_text(raw_line if raw_line else line)[:400],
                    "instruction_zh": _build_bilingual_text(_clean_step_text(raw_line if raw_line else line)[:400]).get("zh"),
                    "required_tools": [_augment_named_row_bilingual({"name": item}) for item in line_tools],
                    "torque_specs": torque_specs,
                    "related_specs": related_specs,
                    "materials": [_augment_named_row_bilingual(item) for item in line_materials],
                    "fasteners": [_augment_named_row_bilingual(item) for item in line_fasteners],
                    **semantics,
                    "source_page": page_number,
                }
            )
    return cards


def _collect_reference_items(pages: list[dict[str, Any]]) -> dict[str, Any]:
    tools: list[str] = []
    materials: list[dict[str, Any]] = []
    fasteners: list[dict[str, Any]] = []
    for page in pages:
        for line in _split_clean_lines(page.get("text") or ""):
            tools.extend(_extract_tools_from_line(line))
            materials.extend(_extract_materials_from_line(line))
            fasteners.extend(_extract_fasteners_from_line(line))
    return {
        "tools": [_augment_named_row_bilingual({"name": name}) for name in dict.fromkeys(tools)],
        "materials": [_augment_named_row_bilingual(item) for item in _dedupe_dict_items(materials, ("name", "value", "unit"))],
        "fasteners": [_augment_named_row_bilingual(item) for item in _dedupe_dict_items(fasteners, ("name", "size", "drive_type"))],
    }


def _extract_specs(text: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    lines = _split_clean_lines(text) or [text or ""]
    range_patterns = [
        (
            spec_type,
            label,
            re.compile(pattern.pattern.replace(r"\d+(?:\.\d+)?", SPEC_RANGE_PATTERN, 1), pattern.flags),
        )
        for spec_type, label, pattern in SPEC_PATTERNS
    ]
    for line in lines:
        for spec_type, label, pattern in range_patterns:
            for match in pattern.finditer(line):
                value = match.group("value").replace(" ", "")
                unit = match.group("unit")
                derived_label = _infer_subject_label(line, label, match.start())
                key = (spec_type, value, unit.lower())
                if key in seen:
                    continue
                seen.add(key)
                specs.append(
                    {
                        "type": spec_type,
                        "label": derived_label,
                        "value": value,
                        "unit": unit,
                        "source_text": _normalize_label_text(line[:220]),
                    }
                )
        parts = [part.strip() for part in TABLE_VALUE_SPLIT_PATTERN.split(_clean_step_text(line)) if part.strip()]
        if len(parts) >= 2:
            joined = " ".join(parts[:3])
            for spec_type, label, pattern in range_patterns:
                for match in pattern.finditer(joined):
                    value = match.group("value").replace(" ", "")
                    unit = match.group("unit")
                    source_seed = parts[0] if parts else joined
                    derived_label = _infer_subject_label(f"{source_seed} {joined}", label, len(source_seed) + 1)
                    key = (spec_type, value, unit.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    specs.append(
                        {
                            "type": spec_type,
                            "label": derived_label,
                            "value": value,
                            "unit": unit,
                            "source_text": _normalize_label_text(line[:220]),
                        }
                    )
    return specs


def _normalize_numeric_text(value: str) -> str:
    return (
        str(value or "")
        .replace("～", "~")
        .replace("—", "-")
        .replace("–", "-")
        .replace("·", "·")
        .strip()
    )


def _score_spec_item(item: dict[str, Any]) -> tuple[int, int, int]:
    label = str(item.get("label") or "")
    source_text = str(item.get("source_text") or "")
    value = str(item.get("value") or "")
    return (
        1 if any(token in label for token in ("螺栓", "螺母", "油压", "机油", "游隙", "气门")) else 0,
        len(source_text),
        len(value),
    )


def _is_heading_like_instruction(text: str) -> bool:
    normalized = re.sub(r"^[#•·\-\s]+", "", str(text or "")).strip()
    if not normalized:
        return True
    if normalized.endswith(("调整", "检查", "测量", "拆卸", "安装")) and len(normalized) <= 16:
        return True
    if normalized.startswith(("前照灯", "油压", "气门间隙", "空气滤清器")) and len(normalized) <= 20:
        return True
    return False


def _extract_sections_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in blocks:
        label = str(block.get("label") or "").lower()
        content = _clean_text(block.get("content"))
        if not content:
            continue
        if label in SECTION_LABELS or content.startswith("#"):
            title = content.lstrip("#").strip()
            if title and title not in seen:
                seen.add(title)
                sections.append({"title": title, "label": label or "heading"})
    return sections


def _looks_like_spec_content(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        token in lowered
        for token in ("扭矩", "nm", "n·m", "psi", "kpa", "volt", "电压", "容量", "机油", "油压", "间隙", "mm")
    )


def _guess_page_type(text: str, sections: list[dict[str, Any]] | None = None) -> str:
    content = f"{' '.join((item.get('title') or '') for item in (sections or []))}\n{text or ''}".lower()
    for page_type, hints in PAGE_TYPE_HINTS:
        if any(hint.lower() in content for hint in hints):
            return page_type
    return "general"


def _call_llm_json(system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
    if not (LLM_CLASSIFIER_ENABLED and LLM_API_URL and LLM_MODEL):
        return None
    try:
        if LLM_PROVIDER == "ollama":
            response = requests.post(
                f"{LLM_API_URL}/api/chat",
                json={
                    "model": LLM_MODEL,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "options": {"temperature": 0},
                },
                timeout=LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            content = ((data.get("message") or {}).get("content") or "").strip()
        else:
            headers = {"Content-Type": "application/json"}
            if LLM_API_KEY:
                headers["Authorization"] = f"Bearer {LLM_API_KEY}"
            response = requests.post(
                f"{LLM_API_URL}/chat/completions",
                headers=headers,
                json={
                    "model": LLM_MODEL,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        logger.warning("LLM JSON call failed: %s", exc)
        return None


def _classify_page_with_llm(text: str, sections: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    snippet = (text or "").strip()
    if len(snippet) > 2400:
        snippet = snippet[:2400]
    title_hint = " / ".join(item.get("title") or "" for item in (sections or [])[:8] if item.get("title"))
    return _call_llm_json(
        "Return only JSON. Classify a motorcycle service-manual page.",
        (
            "Return a JSON object with keys: page_type, is_procedure_page, is_spec_page, reason. "
            "page_type must be one of cover/preface/index/legend/spec_table/procedure/general. "
            "reason must be a short Chinese sentence.\n"
            f"Title hints: {title_hint or '-'}\n"
            f"Page text:\n{snippet}"
        ),
    )


def _detect_layout_profile(text: str) -> dict[str, Any]:
    lines = _split_clean_lines(text)
    numbered_steps = sum(1 for line in lines if STEP_START_PATTERN.match(line.strip()))
    bullet_steps = sum(1 for line in lines if re.match(r"^[•·\-]\s*", line.strip()))
    table_like = sum(1 for line in lines if _is_table_like_line(line))
    long_lines = sum(1 for line in lines if len(_clean_step_text(line)) >= 48)
    short_lines = sum(1 for line in lines if len(_clean_step_text(line)) <= 24)
    if numbered_steps >= 2 and numbered_steps >= bullet_steps:
        layout_mode = "numbered_steps"
    elif table_like >= max(2, len(lines) // 2):
        layout_mode = "table_dense"
    elif bullet_steps >= 2:
        layout_mode = "bullet_steps"
    elif (numbered_steps + bullet_steps) >= 2 and table_like >= 1:
        layout_mode = "mixed_layout"
    elif lines and long_lines >= max(2, len(lines) // 2):
        layout_mode = "prose_heavy"
    else:
        layout_mode = "mixed_layout" if lines else "sparse"
    return {
        "layout_mode": layout_mode,
        "line_count": len(lines),
        "numbered_steps": numbered_steps,
        "bullet_steps": bullet_steps,
        "table_like_lines": table_like,
        "long_lines": long_lines,
        "short_lines": short_lines,
    }


def _choose_extraction_strategy(
    page_type: str,
    layout_profile: dict[str, Any],
    is_procedure_page: bool,
    is_spec_page: bool,
) -> str:
    layout_mode = str(layout_profile.get("layout_mode") or "")
    if page_type == "procedure" or layout_mode in {"numbered_steps", "bullet_steps"}:
        return "procedure_first"
    if page_type == "spec_table" or layout_mode == "table_dense":
        return "spec_table_first"
    if is_procedure_page and is_spec_page and layout_mode == "mixed_layout":
        return "mixed_layout"
    if is_procedure_page:
        return "procedure_first"
    if is_spec_page:
        return "spec_table_first"
    return "conservative"


def _build_page_semantics(text: str, sections: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    guessed = _guess_page_type(text, sections)
    layout_profile = _detect_layout_profile(text)
    semantics = {
        "page_type": guessed,
        "reason": "heuristic",
        "source": "heuristic",
        "is_procedure_page": guessed not in NON_PROCEDURE_PAGE_TYPES,
        "is_spec_page": guessed not in NON_SPEC_PAGE_TYPES,
        "layout_profile": layout_profile,
    }
    llm_result = _classify_page_with_llm(text, sections)
    if llm_result:
        page_type = str(llm_result.get("page_type") or guessed).strip().lower()
        semantics = {
            "page_type": page_type or guessed,
            "reason": llm_result.get("reason") or "llm",
            "source": "llm",
            "is_procedure_page": bool(llm_result.get("is_procedure_page")),
            "is_spec_page": bool(llm_result.get("is_spec_page")),
            "layout_profile": layout_profile,
        }
    semantics["extraction_strategy"] = _choose_extraction_strategy(
        str(semantics.get("page_type") or guessed),
        layout_profile,
        bool(semantics.get("is_procedure_page")),
        bool(semantics.get("is_spec_page")),
    )
    return semantics


def _extract_procedures(text: str) -> list[dict[str, Any]]:
    procedures: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = [line.strip(" -\t") for line in (text or "").splitlines()]
    for line in _merge_step_lines(lines):
        if len(line) < 4:
            continue
        if line.startswith("#"):
            continue
        if not _is_specific_step_line(line):
            continue
        normalized = re.sub(r"\s+", " ", _strip_step_prefix(line))
        if normalized in seen:
            continue
        seen.add(normalized)
        tools = _extract_tools_from_line(normalized)
        materials = _extract_materials_from_line(normalized)
        fasteners = _extract_fasteners_from_line(normalized)
        torque_specs = [item for item in _extract_specs(normalized) if item.get("type") == "torque"]
        semantics = _build_step_semantics(normalized, tools, torque_specs, materials, fasteners)
        procedures.append(
            {
                "step_order": len(procedures) + 1,
                "instruction": normalized[:400],
                "instruction_original": _clean_step_text(line)[:400],
                "instruction_zh": _build_bilingual_text(_clean_step_text(line)[:400]).get("zh"),
                "required_tools": ", ".join(tools) if tools else None,
                "required_tools_bilingual": [_augment_named_row_bilingual({"name": item}) for item in tools],
                "torque_spec": "；".join(
                    f"{item.get('label')}: {item.get('value')}{item.get('unit')}" for item in torque_specs
                )
                if torque_specs
                else None,
                "hazards": None,
                "materials": [_augment_named_row_bilingual(item) for item in materials] or None,
                "fasteners": [_augment_named_row_bilingual(item) for item in fasteners] or None,
                **semantics,
            }
        )
    return procedures


def _normalize_llm_spec_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    raw_type = str(item.get("type") or item.get("spec_type") or "").strip().lower()
    spec_type = SPEC_TYPE_ALIASES.get(raw_type, raw_type or "other")
    value = str(item.get("value") or "").strip()
    unit = str(item.get("unit") or "").strip()
    source_text = _clean_text(item.get("source_text") or item.get("evidence") or item.get("context") or "")
    if not value and not source_text:
        return None
    return {
        "type": spec_type,
        "label": str(item.get("label") or SPEC_TYPE_LABELS.get(spec_type) or "参数").strip(),
        "value": value or source_text[:80],
        "unit": unit,
        "source_text": source_text or value,
    }


def _extract_specs_with_llm(text: str, sections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    snippet = (text or "").strip()
    if len(snippet) > 3200:
        snippet = snippet[:3200]
    title_hint = " / ".join(item.get("title") or "" for item in (sections or [])[:8] if item.get("title"))
    parsed = _call_llm_json(
        "Return only JSON. You extract explicit technical specifications from motorcycle service manuals.",
        (
            "Return a JSON object with key specs. specs must be an array. "
            "Each item must use fields: type, label, value, unit, source_text. "
            "type should be torque/pressure/voltage/capacity/clearance. "
            "Only keep explicit technical values supported by the page text. "
            "Do not translate. Keep original Chinese wording when possible. "
            "Do not infer missing values, units, labels, or tools. "
            "If nothing reliable exists, return {\"specs\":[]}.\n"
            f"Title hints: {title_hint or '-'}\n"
            f"Page text:\n{snippet}"
        ),
    )
    specs = []
    for item in (parsed or {}).get("specs") or []:
        normalized = _normalize_llm_spec_item(item)
        if normalized:
            specs.append(normalized)
    return specs


def _normalize_llm_procedure_item(item: Any, index: int, page_text: str = "") -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    instruction = _strip_step_prefix(_clean_text(item.get("instruction") or item.get("step") or ""))
    if not instruction or not _is_specific_step_line(instruction):
        return None
    required_tools = _clean_text(item.get("required_tools") or item.get("tools") or "")
    torque_spec = _clean_text(item.get("torque_spec") or item.get("spec") or "")
    hazards = _clean_text(item.get("hazards") or item.get("caution") or "")
    if required_tools.lower() in {"n/a", "none", "null", "-"}:
        required_tools = ""
    if torque_spec.lower() in {"n/a", "none", "null", "-"}:
        torque_spec = ""
    if hazards.lower() in {"n/a", "none", "null", "-"}:
        hazards = ""
    lowered_text = (page_text or "").lower()
    if required_tools and required_tools.lower() not in lowered_text and not re.search(r"[A-Z]{2,}-\d{3,}", required_tools):
        required_tools = ""
    if hazards and hazards.lower() not in lowered_text and not any(token in hazards for token in ("警告", "注意", "危险", "小心")):
        hazards = ""
    materials = _extract_materials_from_line(instruction) or None
    fasteners = _extract_fasteners_from_line(instruction) or None
    semantics = _build_step_semantics(
        instruction,
        _extract_tools_from_line(instruction),
        [item for item in _extract_specs(instruction) if item.get("type") == "torque"],
        materials or [],
        fasteners or [],
    )
    return {
        "step_order": int(item.get("step_order") or index),
        "instruction": instruction[:400],
        "instruction_original": instruction[:400],
        "required_tools": required_tools or ", ".join(_extract_tools_from_line(instruction)) or None,
        "torque_spec": torque_spec or None,
        "hazards": hazards or None,
        "materials": materials,
        "fasteners": fasteners,
        **semantics,
    }


def _extract_procedures_with_llm(text: str, sections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    snippet = (text or "").strip()
    if len(snippet) > 3200:
        snippet = snippet[:3200]
    title_hint = " / ".join(item.get("title") or "" for item in (sections or [])[:8] if item.get("title"))
    parsed = _call_llm_json(
        "Return only JSON. You extract explicit maintenance procedures from motorcycle service manuals.",
        (
            "Return a JSON object with key procedures. procedures must be an array. "
            "Each item should use fields: step_order, instruction, required_tools, torque_spec, hazards. "
            "Only keep actual maintenance operations. Do not include cover text, preface, index, symbol legend or general explanations. "
            "Keep the instruction in the original page language. Do not translate Chinese to English. "
            "Do not invent required_tools, torque_spec, or hazards. If the page does not explicitly say them, use null or empty string. "
            "If nothing reliable exists, return {\"procedures\":[]}.\n"
            f"Title hints: {title_hint or '-'}\n"
            f"Page text:\n{snippet}"
        ),
    )
    procedures = []
    for index, item in enumerate((parsed or {}).get("procedures") or [], start=1):
        normalized = _normalize_llm_procedure_item(item, index, snippet)
        if normalized:
            procedures.append(normalized)
    return procedures


def _merge_specs(regex_specs: list[dict[str, Any]], llm_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in [*(regex_specs or []), *(llm_specs or [])]:
        item = dict(item)
        item["value"] = _normalize_numeric_text(item.get("value"))
        item["unit"] = _normalize_numeric_text(item.get("unit"))
        key = (
            str(item.get("type") or ""),
            str(item.get("label") or ""),
            str(item.get("value") or ""),
            str(item.get("unit") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    preferred: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in merged:
        dedupe_key = (
            str(item.get("type") or ""),
            str(item.get("value") or ""),
            str(item.get("unit") or ""),
        )
        current = preferred.get(dedupe_key)
        if current is None or _score_spec_item(item) > _score_spec_item(current):
            preferred[dedupe_key] = item
    return list(preferred.values())


def _merge_procedures(regex_procedures: list[dict[str, Any]], llm_procedures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*(llm_procedures or []), *(regex_procedures or [])]:
        instruction = re.sub(r"\s+", " ", str(item.get("instruction") or "")).strip()
        normalized_key = re.sub(r"^[#•·\-\s]+", "", instruction).strip("。.;；")
        if not instruction or normalized_key in seen or _is_heading_like_instruction(normalized_key):
            continue
        seen.add(normalized_key)
        cleaned = dict(item)
        cleaned["instruction"] = instruction
        merged.append(cleaned)
    for index, item in enumerate(merged, start=1):
        item["step_order"] = index
    return merged


def _extract_specs_from_segments(
    text: str,
    sections: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    preferred_segments = [item["text"] for item in segments if item.get("role") in {"spec", "title"} and item.get("text")]
    source_text = "\n".join(preferred_segments) if preferred_segments else text
    regex_specs = _extract_specs(source_text)
    llm_specs = _extract_specs_with_llm(source_text, sections)
    return _merge_specs(regex_specs, llm_specs), ("llm+regex" if llm_specs else "regex")


def _extract_procedures_from_segments(
    text: str,
    sections: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    preferred_segments = [item["text"] for item in segments if item.get("role") in {"procedure", "title"} and item.get("text")]
    source_text = "\n".join(preferred_segments) if preferred_segments else text
    regex_procedures = _extract_procedures(source_text)
    llm_procedures = _extract_procedures_with_llm(source_text, sections)
    return _merge_procedures(regex_procedures, llm_procedures), ("llm+regex" if llm_procedures else "regex")


def _build_page_from_layout_result(item: dict[str, Any], page_number: int) -> dict[str, Any]:
    pruned = (item.get("prunedResult") or {}) if isinstance(item, dict) else {}
    parsing_res_list = pruned.get("parsing_res_list") or []
    markdown_text = ((item.get("markdown") or {}).get("text") or "") if isinstance(item, dict) else ""

    blocks = []
    for block_index, block in enumerate(parsing_res_list, start=1):
        content = _clean_text(block.get("block_content"))
        if not content:
            continue
        blocks.append(
            {
                "id": block.get("block_id") or block_index,
                "label": block.get("block_label") or "text",
                "content": content,
                "order": block.get("block_order"),
                "bbox": block.get("block_bbox"),
                "group_id": block.get("group_id"),
            }
        )

    text_parts = [block["content"] for block in blocks]
    markdown_clean = _clean_text(markdown_text)
    if markdown_clean:
        text_parts.append(markdown_clean)
    text = "\n".join(part for part in text_parts if part).strip()
    sections = _extract_sections_from_blocks(blocks)
    semantics = _build_page_semantics(text, sections)
    segments = _segment_page_content(text)
    spec_table_rows = _augment_spec_table_rows_bilingual(_extract_spec_table_rows(text))
    specs = []
    procedures = []
    spec_source = "disabled"
    procedure_source = "disabled"
    should_extract_specs = bool(semantics.get("is_spec_page")) or _looks_like_spec_content(text)
    if should_extract_specs:
        specs, spec_source = _extract_specs_from_segments(text, sections, segments)
    if semantics.get("is_procedure_page"):
        procedures, procedure_source = _extract_procedures_from_segments(text, sections, segments)

    for item in specs:
        item.setdefault("page_number", page_number)
        item.setdefault("page_label", f"第 {page_number} 页")
    for item in procedures:
        item.setdefault("page_number", page_number)
        item.setdefault("page_label", f"第 {page_number} 页")

    return {
        "page_number": page_number,
        "page_label": f"第 {page_number} 页",
        "text": text,
        "summary": _summarize_text(text),
        "blocks": blocks,
        "sections": sections,
        "content_segments": segments,
        "spec_table_rows": spec_table_rows,
        "specs": specs,
        "procedures": procedures,
        "page_type": semantics.get("page_type"),
        "page_type_reason": semantics.get("reason"),
        "page_type_source": semantics.get("source"),
        "layout_profile": semantics.get("layout_profile"),
        "extraction_strategy": semantics.get("extraction_strategy"),
        "spec_extraction_source": spec_source,
        "procedure_extraction_source": procedure_source,
        "confidence": 1.0,
    }


def _normalize_paddle_service_result(payload: dict[str, Any], page_offset: int = 0) -> dict[str, Any]:
    raw_results = ((((payload or {}).get("result") or {}).get("layoutParsingResults")) or [])
    pages = [
        _build_page_from_layout_result(item, page_offset + index)
        for index, item in enumerate(raw_results, start=1)
    ]

    sections: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    procedures: list[dict[str, Any]] = []
    for page in pages:
        sections.extend(page.get("sections") or [])
        specs.extend(page.get("specs") or [])
        procedures.extend(page.get("procedures") or [])

    seen_sections: set[str] = set()
    unique_sections = []
    for item in sections:
        title = item.get("title") or ""
        if title in seen_sections:
            continue
        seen_sections.add(title)
        unique_sections.append(item)

    seen_specs: set[tuple[str, str, str]] = set()
    unique_specs = []
    for item in specs:
        key = (str(item.get("type") or ""), str(item.get("value") or ""), str(item.get("unit") or ""))
        if key in seen_specs:
            continue
        seen_specs.add(key)
        unique_specs.append(item)

    summary = ""
    for page in pages:
        if page.get("summary"):
            summary = page["summary"]
            break

    return {
        "status": "completed",
        "provider": "paddleocr-vl-service",
        "parser_version": PARSER_VERSION,
        "page_count": len(pages),
        "summary": summary,
        "sections": unique_sections,
        "specs": unique_specs,
        "procedures": procedures[:120],
        "pages": pages,
        "processed_batches": 1,
        "total_batches": 1,
    }


def _merge_parse_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    merged_pages: list[dict[str, Any]] = []
    merged_sections: list[dict[str, Any]] = []
    merged_specs: list[dict[str, Any]] = []
    merged_procedures: list[dict[str, Any]] = []

    for result in results:
        merged_pages.extend(result.get("pages") or [])
        merged_sections.extend(result.get("sections") or [])
        merged_specs.extend(result.get("specs") or [])
        merged_procedures.extend(result.get("procedures") or [])

    summary = ""
    for result in results:
        if result.get("summary"):
            summary = result["summary"]
            break

    unique_sections = []
    seen_sections: set[str] = set()
    for item in merged_sections:
        title = item.get("title") or ""
        if not title or title in seen_sections:
            continue
        seen_sections.add(title)
        unique_sections.append(item)

    unique_specs = []
    seen_specs: set[tuple[str, str, str]] = set()
    for item in merged_specs:
        key = (str(item.get("type") or ""), str(item.get("value") or ""), str(item.get("unit") or ""))
        if key in seen_specs:
            continue
        seen_specs.add(key)
        unique_specs.append(item)

    for index, procedure in enumerate(merged_procedures, start=1):
        procedure["step_order"] = index

    return {
        "status": "completed",
        "provider": "paddleocr-vl-service",
        "parser_version": PARSER_VERSION,
        "page_count": len(merged_pages),
        "summary": summary,
        "sections": unique_sections,
        "specs": unique_specs,
        "procedures": merged_procedures[:300],
        "pages": merged_pages,
        "processed_batches": len(results),
        "total_batches": len(results),
    }


def _collect_applicability(sections: list[dict[str, Any]], text: str) -> dict[str, Any]:
    joined_titles = " ".join(item.get("title") or "" for item in sections)
    combined = f"{joined_titles}\n{text}"
    brand = None
    model = None
    brand_match = re.search(r"\b(SUZUKI|HONDA|YAMAHA|KAWASAKI|BMW|DUCATI|KTM|APRILIA|TRIUMPH)\b", combined, re.I)
    if brand_match:
        brand = brand_match.group(1).upper()
    model_match = re.search(r"\b([A-Z]{2,}\d{2,}[A-Z0-9-]*)\b", combined)
    if model_match:
        model = model_match.group(1)
    return {
        "brand": brand,
        "model_name": model,
        "year_range": None,
        "engine_code": None,
    }


def _normalize_heading_key(value: str | None) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip().lower()
    return text


def _extract_toc_entries(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    toc_entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    pattern = re.compile(r"([A-Za-z0-9\u4e00-\u9fff\s]{2,24}?)\s+(\d{1,2})(?=\s+[A-Za-z0-9\u4e00-\u9fff].{0,20}?\s+\d|$)")
    for page in pages:
        if str(page.get("page_type") or "") != "index":
            continue
        text = str(page.get("text") or "")
        for raw_title, chapter in pattern.findall(text):
            title = re.sub(r"\s+", " ", raw_title).strip(" .:-")
            if not title or len(title) < 2:
                continue
            key = _normalize_heading_key(title)
            if key in seen:
                continue
            seen.add(key)
            toc_entries.append(
                {
                    "title": title,
                    "chapter_no": chapter,
                    "toc_page_number": page.get("page_number"),
                }
            )
    return toc_entries


def _locate_toc_segments(pages: list[dict[str, Any]], toc_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not toc_entries:
        return []
    searchable_pages = []
    for page in pages:
        searchable_pages.append(
            {
                "page_number": page.get("page_number"),
                "sections": [_normalize_heading_key(item.get("title")) for item in (page.get("sections") or []) if isinstance(item, dict)],
                "text": _normalize_heading_key(page.get("text")),
            }
        )
    located = []
    last_start = 0
    for entry in toc_entries:
        title_key = _normalize_heading_key(entry.get("title"))
        matched_page = None
        for page in searchable_pages:
            page_no = int(page.get("page_number") or 0)
            if page_no and page_no < last_start:
                continue
            if title_key in page["sections"] or title_key in page["text"]:
                matched_page = page_no
                break
        located.append(
            {
                **entry,
                "start_page": matched_page,
            }
        )
        if matched_page:
            last_start = matched_page
    segments = []
    for index, entry in enumerate(located):
        start_page = entry.get("start_page")
        next_start = None
        for later in located[index + 1:]:
            if later.get("start_page"):
                next_start = later.get("start_page")
                break
        end_page = (next_start - 1) if (start_page and next_start and next_start > start_page) else None
        segments.append(
            {
                "title": entry.get("title"),
                "chapter_no": entry.get("chapter_no"),
                "toc_page_number": entry.get("toc_page_number"),
                "start_page": start_page,
                "end_page": end_page,
                "resolved": bool(start_page),
            }
        )
    return segments


def _build_manual_template_bundle(result: dict[str, Any]) -> dict[str, Any]:
    pages = result.get("pages") or []
    all_text = "\n".join(page.get("text") or "" for page in pages)
    sections = result.get("sections") or []
    specs = result.get("specs") or []
    procedures = result.get("procedures") or []
    toc_entries = _extract_toc_entries(pages)
    toc_segments = _locate_toc_segments(pages, toc_entries)
    step_cards = _build_step_cards(pages, specs)
    reference_items = _collect_reference_items(pages)
    specs = _augment_specs_bilingual(specs)
    procedures = [
        dict(
            item,
            instruction_zh=item.get("instruction_zh")
            or _build_bilingual_text(item.get("instruction_original") or item.get("instruction")).get("zh"),
        )
        for item in procedures
    ]

    document_profile = {
        "document_title": next((item.get("title") for item in sections if item.get("title")), None),
        "document_type": "维修手册",
        "language": _detect_document_language(all_text),
        "page_count": result.get("page_count") or len(pages),
    }
    applicability = _collect_applicability(sections, all_text)
    operation_names = [item.get("instruction") for item in procedures[:30] if item.get("instruction")]
    operation_index = {
        "operation_names": operation_names,
        "sections": [item.get("title") for item in sections if item.get("title")][:30],
    }

    torque_specs = [item for item in specs if item.get("type") == "torque"]
    fluid_specs = [item for item in specs if item.get("type") == "capacity"]
    pressure_specs = [item for item in specs if item.get("type") == "pressure"]
    voltage_specs = [item for item in specs if item.get("type") == "voltage"]
    clearance_specs = [item for item in specs if item.get("type") == "clearance"]
    fastener_specs = reference_items["fasteners"]
    materials = reference_items["materials"]
    tool_refs = reference_items["tools"]
    critical_steps = [item for item in step_cards if item.get("criticality") == "critical"][:40]
    spec_table_rows = [
        row
        for page in pages
        for row in (page.get("spec_table_rows") or [])
        if isinstance(row, dict)
    ][:120]
    spec_table_rows = _augment_spec_table_rows_bilingual(spec_table_rows)
    top_torque_specs = sorted(
        torque_specs,
        key=lambda item: (
            1 if "螺栓" in str(item.get("label") or "") else 0,
            len(str(item.get("label") or "")),
            len(str(item.get("source_text") or "")),
        ),
        reverse=True,
    )[:40]

    normalized_manual = {
        "document_profile": document_profile,
        "applicability": applicability,
        "operation_index": operation_index,
        "toc_segments": toc_segments,
        "procedures": {
            "steps": procedures,
            "step_cards": step_cards[:200],
            "required_tools": tool_refs,
            "safety_cautions": [],
            "quality_checks": critical_steps,
            "critical_steps": critical_steps,
        },
        "specifications": {
            "torque_specs": torque_specs,
            "top_torque_specs": top_torque_specs,
            "fluid_specs": fluid_specs,
            "pressure_specs": pressure_specs,
            "voltage_specs": voltage_specs,
            "clearance_specs": clearance_specs,
            "fastener_specs": fastener_specs,
            "spec_table_rows": spec_table_rows,
        },
        "parts_and_materials": {
            "parts": [],
            "consumables": [item for item in materials if item.get("name") not in {"机油", "冷却液", "制动液", "前叉油", "齿轮油"}],
            "fluids": [item for item in materials if item.get("name") in {"机油", "冷却液", "制动液", "前叉油", "齿轮油"}],
            "filters": [item for item in materials if "滤" in str(item.get("name") or "")],
        },
        "technician_view": {
            "quick_reference": {
                "torque": top_torque_specs,
                "fluids": fluid_specs,
                "filters": [item for item in materials if "滤" in str(item.get("name") or "")],
                "fasteners": fastener_specs,
                "tools": tool_refs,
                "critical_steps": critical_steps,
            },
            "step_cards": step_cards[:200],
        },
        "traceability": {
            "page_summaries": [
                {
                    "page_number": page.get("page_number"),
                    "summary": page.get("summary"),
                    "page_type": page.get("page_type"),
                    "page_type_reason": page.get("page_type_reason"),
                    "layout_profile": page.get("layout_profile"),
                    "extraction_strategy": page.get("extraction_strategy"),
                    "content_segments": page.get("content_segments"),
                    "spec_table_rows": page.get("spec_table_rows"),
                }
                for page in pages[:50]
            ],
            "source_pages": [page.get("page_number") for page in pages],
            "toc_segments": toc_segments,
        },
    }

    completion = [
        {
            "key": "document_profile",
            "label": "资料基本信息",
            "is_complete": bool(document_profile["document_title"] and document_profile["page_count"]),
            "present_children": [key for key, value in document_profile.items() if value],
            "missing_children": [key for key, value in document_profile.items() if not value],
        },
        {
            "key": "applicability",
            "label": "适用车型范围",
            "is_complete": bool(applicability["brand"] or applicability["model_name"]),
            "present_children": [key for key, value in applicability.items() if value],
            "missing_children": [key for key, value in applicability.items() if not value],
        },
        {
            "key": "operation_index",
            "label": "维修/保养项目索引",
            "is_complete": bool(operation_index["operation_names"] or toc_segments),
            "present_children": [
                "operation_names" if operation_index["operation_names"] else "",
                "sections" if operation_index["sections"] else "",
                "toc_segments" if toc_segments else "",
            ],
            "missing_children": [
                "operation_names" if not operation_index["operation_names"] else "",
                "toc_segments" if not toc_segments else "",
            ],
        },
        {
            "key": "procedures",
            "label": "标准施工步骤",
            "is_complete": bool(procedures or step_cards),
            "present_children": [
                "steps" if procedures else "",
                "step_cards" if step_cards else "",
            ],
            "missing_children": ["steps"] if not procedures else [],
        },
        {
            "key": "specifications",
            "label": "关键技术参数",
            "is_complete": bool(specs),
            "present_children": [
                name
                for name, value in normalized_manual["specifications"].items()
                if value
            ],
            "missing_children": [
                name
                for name, value in normalized_manual["specifications"].items()
                if not value
            ],
        },
        {
            "key": "parts_and_materials",
            "label": "配件与耗材",
            "is_complete": bool(materials),
            "present_children": [
                "consumables" if normalized_manual["parts_and_materials"]["consumables"] else "",
                "fluids" if normalized_manual["parts_and_materials"]["fluids"] else "",
                "filters" if normalized_manual["parts_and_materials"]["filters"] else "",
            ],
            "missing_children": [
                "consumables" if not normalized_manual["parts_and_materials"]["consumables"] else "",
                "fluids" if not normalized_manual["parts_and_materials"]["fluids"] else "",
                "filters" if not normalized_manual["parts_and_materials"]["filters"] else "",
            ],
        },
        {
            "key": "technician_view",
            "label": "维修工快查视图",
            "is_complete": bool(step_cards or top_torque_specs or fastener_specs),
            "present_children": [
                "step_cards" if step_cards else "",
                "torque" if top_torque_specs else "",
                "fasteners" if fastener_specs else "",
                "tools" if tool_refs else "",
            ],
            "missing_children": [
                "step_cards" if not step_cards else "",
                "torque" if not top_torque_specs else "",
                "fasteners" if not fastener_specs else "",
            ],
        },
        {
            "key": "traceability",
            "label": "可追溯信息",
            "is_complete": bool(pages),
            "present_children": ["source_pages" if pages else "", "page_summaries" if pages else ""],
            "missing_children": [] if pages else ["source_pages", "page_summaries"],
        },
    ]

    for item in completion:
        item["present_children"] = [child for child in item["present_children"] if child]

    completed_count = sum(1 for item in completion if item["is_complete"])
    completion_ratio = completed_count / len(completion) if completion else 0
    manual_template = {
        "version": "manual-template-v1",
        "completion_ratio": completion_ratio,
        "completion": completion,
    }
    return {
        "manual_template": manual_template,
        "normalized_manual": normalized_manual,
    }


def _call_paddle_service(
    file_bytes: bytes,
    filename: str,
    content_type: str | None = None,
    job_id: int | None = None,
) -> dict[str, Any]:
    is_pdf = filename.lower().endswith(".pdf") or (content_type or "").lower() == "application/pdf"
    if is_pdf:
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        if total_pages > OCR_PDF_BATCH_PAGES:
            logger.info("Parsing PDF in batches: total_pages=%s batch_pages=%s", total_pages, OCR_PDF_BATCH_PAGES)
            batch_results = []
            total_batches = (total_pages + OCR_PDF_BATCH_PAGES - 1) // OCR_PDF_BATCH_PAGES
            _post_progress(job_id, "processing", 1, f"\u51c6\u5907\u5206\u6279\u89e3\u6790\uff0c\u5171 {total_batches} \u6279", 0, total_batches)
            for batch_index, start in enumerate(range(0, total_pages, OCR_PDF_BATCH_PAGES), start=1):
                writer = PdfWriter()
                for page_index in range(start, min(start + OCR_PDF_BATCH_PAGES, total_pages)):
                    writer.add_page(reader.pages[page_index])
                buffer = io.BytesIO()
                writer.write(buffer)
                batch_bytes = buffer.getvalue()

                _post_progress(
                    job_id,
                    "processing",
                    min(99, max(1, int(((batch_index - 1) / total_batches) * 100))),
                    f"\u6b63\u5728\u89e3\u6790\u7b2c {batch_index}/{total_batches} \u6279",
                    batch_index - 1,
                    total_batches,
                )
                batch_result = _call_paddle_service(
                    batch_bytes,
                    f"{os.path.splitext(filename)[0]}_part_{start + 1}.pdf",
                    "application/pdf",
                    None,
                )

                page_offset = start
                for page in batch_result.get("pages") or []:
                    page["page_number"] = page_offset + int(page.get("page_number") or 0)
                    page["page_label"] = f"第 {page['page_number']} 页"
                batch_results.append(batch_result)

                _post_progress(
                    job_id,
                    "processing",
                    min(99, max(1, int((batch_index / total_batches) * 100))),
                    f"\u5df2\u5b8c\u6210\u7b2c {batch_index}/{total_batches} \u6279",
                    batch_index,
                    total_batches,
                )
            merged = _merge_parse_results(batch_results)
            merged["processed_batches"] = len(batch_results)
            merged["total_batches"] = total_batches
            return merged

    payload = {
        "file": base64.b64encode(file_bytes).decode("ascii"),
        "fileType": 0 if is_pdf else 1,
        "useLayoutDetection": True,
        "prettifyMarkdown": True,
        "restructurePages": False,
        "formatBlockContent": True,
    }
    response = requests.post(
        f"{OCR_SERVICE_URL}/layout-parsing",
        json=payload,
        timeout=OCR_SERVICE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _normalize_paddle_service_result(response.json())


def parse_document(
    file_bytes: bytes,
    filename: str,
    content_type: str | None = None,
    job_id: int | None = None,
) -> dict[str, Any]:
    logger.info("Trying PaddleOCR-VL service at %s", OCR_SERVICE_URL)
    result = _call_paddle_service(file_bytes, filename, content_type, job_id)
    template_bundle = _build_manual_template_bundle(result)
    result.update(
        {
            "manual_template": template_bundle["manual_template"],
            "normalized_manual": template_bundle["normalized_manual"],
        }
    )
    return result
