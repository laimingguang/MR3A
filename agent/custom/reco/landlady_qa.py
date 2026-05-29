# -*- coding: utf-8 -*-
"""老板娘问答：搜库答题（CustomRecognition）及学题共用 OCR / 单轮状态。"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
from maa.define import (
    AndRecognitionResult,
    OCRResult,
    OrRecognitionResult,
    RecognitionDetail,
    RectType,
)

from custom.pipeline_params import parse_pipeline_json_param
from utils.logger import logger
from utils.text_match import (
    extract_question_body,
    find_best_answer_box,
    find_best_question,
    is_active_question_round,
    join_ocr_lines,
    load_qa_db,
)

DEFAULT_DB = "resource/data/老板娘问答.json"
NODE_QUESTION = "问答_题目OCR"
NODE_OPTIONS = "问答_选项OCR"
LEARN_OFFSET = [95, -17, 374, 36]
QUESTION_ROI = [400, 80, 840, 220]

_pending: Optional["PendingRound"] = None


@dataclass
class PendingRound:
    body: str
    raw: str


def set_pending_round(body: str, raw: str) -> None:
    global _pending
    _pending = PendingRound(body=body, raw=raw)


def pop_pending_round() -> Optional[PendingRound]:
    global _pending
    pending, _pending = _pending, None
    return pending


def iter_ocr_boxes(detail: Optional[RecognitionDetail]) -> List[Tuple[str, Any]]:
    if detail is None or not detail.hit:
        return []
    out: List[Tuple[str, Any]] = []

    def walk(results: Any) -> None:
        if not results:
            return
        for item in results:
            if isinstance(item, OCRResult) and item.text and item.box is not None:
                out.append((item.text.strip(), item.box))
            elif isinstance(item, (AndRecognitionResult, OrRecognitionResult)):
                for sub in item.sub_results or []:
                    if isinstance(sub, RecognitionDetail):
                        out.extend(iter_ocr_boxes(sub))
            elif isinstance(item, RecognitionDetail):
                out.extend(iter_ocr_boxes(item))

    walk(detail.filtered_results or detail.all_results)
    return out


def box_xywh(box: Any) -> Tuple[int, int, int, int]:
    if hasattr(box, "x"):
        return int(box.x), int(box.y), int(box.w), int(box.h)
    if isinstance(box, dict):
        return int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    return int(box[0]), int(box[1]), int(box[2]), int(box[3])


def apply_offset(box: Any, offset: Sequence[int]) -> List[int]:
    x, y, w, h = box_xywh(box)
    dx, dy, dw, dh = (int(offset[i]) for i in range(4))
    nw, nh = w + dw, h + dh
    if nw <= 0 or nh <= 0:
        raise ValueError(f"无效 ROI offset: {offset}")
    return [x + dx, y + dy, nw, nh]


def match_box(rd: RecognitionDetail) -> Any:
    br = rd.best_result
    if br is not None and getattr(br, "box", None) is not None:
        return br.box
    return rd.box


def ocr_roi(
    context: Context,
    image: np.ndarray,
    roi: List[int],
    node: str = NODE_OPTIONS,
) -> str:
    """在指定 ROI 上复用流水线 OCR 节点（仅覆盖 roi，走默认 det+rec）。"""
    detail = context.run_recognition(
        node,
        image,
        {node: {"recognition": {"param": {"roi": roi}}}},
    )
    items = iter_ocr_boxes(detail)
    if items:
        return join_ocr_lines(items)
    if detail and detail.hit and isinstance(detail.best_result, OCRResult):
        return (detail.best_result.text or "").strip()
    return ""


def ocr_answer_from_icon(
    rd: RecognitionDetail,
    context: Context,
    image: np.ndarray,
    offset: Sequence[int],
) -> str:
    try:
        return ocr_roi(context, image, apply_offset(match_box(rd), offset)).strip()
    except ValueError as e:
        logger.warning(f"LandladyQa learn: icon+offset 无效 ({e})")
        return ""


@AgentServer.custom_recognition("LandladyQaAnswer")
class LandladyQaAnswer(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> Union[CustomRecognition.AnalyzeResult, Optional[RectType]]:
        param = parse_pipeline_json_param(argv.custom_recognition_param)
        db_path = str(param.get("db_path", DEFAULT_DB)).strip() or DEFAULT_DB
        min_q = float(param.get("min_question_ratio", 0.85))
        min_a = float(param.get("min_answer_ratio", 0.78))
        fallback = param.get("fallback_random", True) is not False

        try:
            db = load_qa_db(db_path)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"LandladyQa: 题库加载失败 {e}")
            return None
        logger.debug(f"LandladyQa: 题库 {db_path} 共 {len(db)} 条")

        image = argv.image
        if image is None:
            logger.debug("LandladyQa: 无截图，跳过")
            return None

        q_node = str(param.get("question_recognition", NODE_QUESTION))
        o_node = str(param.get("options_recognition", NODE_OPTIONS))

        raw = join_ocr_lines(iter_ocr_boxes(context.run_recognition(q_node, image)))
        if not is_active_question_round(raw):
            logger.debug(f"LandladyQa: 非答题轮次 raw={raw!r}")
            return None

        body = extract_question_body(raw)
        q_match = find_best_question(body, db, min_ratio=min_q) if body else None
        logger.debug(
            f"LandladyQa: 题干 body={body!r} "
            f"匹配={'无' if not q_match else f'{q_match.score:.2f} {q_match.entry.answer!r}'}"
        )
        o_items = iter_ocr_boxes(context.run_recognition(o_node, image))
        if not o_items:
            logger.debug("LandladyQa: 选项 OCR 为空")
            return None

        answer_match = None
        target: Optional[str] = None

        if q_match:
            target = q_match.entry.answer
            answer_match = find_best_answer_box(o_items, target, min_ratio=min_a)

        if answer_match:
            box, text = answer_match.box, answer_match.text
            logger.debug(
                f"LandladyQa: 选项匹配 {answer_match.score:.2f} -> {text!r}"
            )
        elif fallback:
            text, box = random.choice(o_items)
            logger.debug(f"LandladyQa: 随机选项 {text!r} (target={target!r})")
        else:
            logger.debug("LandladyQa: 无匹配且未启用随机")
            return None

        set_pending_round(body=body, raw=raw)
        logger.debug(f"LandladyQa: 点击 {text!r} box={box_xywh(box)}")
        return CustomRecognition.AnalyzeResult(box=box, detail={"option": text})
