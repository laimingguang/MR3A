"""Pipeline Custom 参数解析：兼容 JSON 字符串或已反序列化的 dict，以及整型时长多种写法。"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

JsonParam = Union[str, Dict[str, Any], None]


def parse_pipeline_json_param(raw: JsonParam) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        return json.loads(s)
    raise TypeError(
        f"custom_*_param 应为 JSON 字符串或 dict，实际为 {type(raw).__name__}"
    )


def normalize_duration_ms(value: Any) -> Optional[int]:
    """将 duration 规范为非负 int；非法则返回 None。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value < 0 or not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            v = int(s)
        except ValueError:
            return None
        return v if v >= 0 else None
    return None
