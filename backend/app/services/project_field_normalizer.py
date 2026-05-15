EVALUATION_BUSINESS_NATURES = (
    "\u56fd\u6709\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1",
    "\u5883\u5916\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1",
    "\u8bc1\u5238\u671f\u8d27\u8bc4\u4f30\u4e1a\u52a1",
    "\u53f8\u6cd5\u8bc4\u4f30\u4e1a\u52a1",
    "\u91d1\u878d\u8d44\u4ea7\u8bc4\u4f30\u4e1a\u52a1",
    "\u73e0\u5b9d\u9996\u9970\u8bc4\u4f30\u4e1a\u52a1",
    "\u5176\u4ed6",
)

REPORT_TYPES = (
    "\u8bc4\u4f30\u62a5\u544a",
    "\u4f30\u503c\u62a5\u544a",
    "\u54a8\u8be2\u62a5\u544a",
    "\u590d\u6838\u62a5\u544a",
    "\u8ffd\u6eaf\u6027\u62a5\u544a",
)

PROJECT_SOURCES = ("INTERNAL", "EXTERNAL")
UNDERTAKING_UNITS = ("\u4e2d\u52e4", "\u4e2d\u7acb\u56fd\u9645", "\u4e2d\u4f17", "\u5176\u4ed6")

DEFAULT_EVALUATION_BUSINESS_NATURE = EVALUATION_BUSINESS_NATURES[0]
DEFAULT_REPORT_TYPE = REPORT_TYPES[0]
DEFAULT_PROJECT_SOURCE = "INTERNAL"
DEFAULT_UNDERTAKING_UNIT = UNDERTAKING_UNITS[0]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_dirty_placeholder(value: str | None) -> bool:
    text = _clean(value)
    if not text:
        return False
    return set(text) <= {"?", "\ufffd"}


def normalize_evaluation_business_nature(value: str | None, *, allow_none: bool = False) -> str | None:
    text = _clean(value)
    if text in EVALUATION_BUSINESS_NATURES:
        return text
    if not text and allow_none:
        return None
    if not text or _is_dirty_placeholder(text):
        return None if allow_none else DEFAULT_EVALUATION_BUSINESS_NATURE
    return text


def normalize_report_type(value: str | None) -> str:
    text = _clean(value)
    if text in REPORT_TYPES:
        return text
    if not text or _is_dirty_placeholder(text):
        return DEFAULT_REPORT_TYPE
    return text


def normalize_project_source(value: str | None) -> str:
    text = _clean(value)
    if text in PROJECT_SOURCES:
        return text
    if text in {"\u8bc4\u4f30\u4e00\u90e8", "\u5185\u90e8"}:
        return "INTERNAL"
    if text in {"\u8bc4\u4f30\u4e8c\u90e8", "\u5916\u90e8"}:
        return "EXTERNAL"
    return DEFAULT_PROJECT_SOURCE


def normalize_undertaking_unit(value: str | None) -> str:
    text = _clean(value)
    if text in UNDERTAKING_UNITS:
        return text
    if not text or _is_dirty_placeholder(text):
        return DEFAULT_UNDERTAKING_UNIT
    return text


def normalize_external_project_leader_name(value: str | None) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if _is_dirty_placeholder(text):
        return "\u9879\u76ee\u8d1f\u8d23\u4ebaA"
    return text
