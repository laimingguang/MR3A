# -*- coding: utf-8 -*-
"""老板娘问答：答错学题入库（CustomAction）。"""

from __future__ import annotations

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from custom.pipeline_params import parse_pipeline_json_param
from custom.reco.landlady_qa import (
    DEFAULT_DB,
    LEARN_OFFSET,
    NODE_QUESTION,
    QUESTION_ROI,
    match_box,
    ocr_answer_from_icon,
    ocr_roi,
    pop_pending_round,
)
from utils.logger import logger
from utils.text_match import append_qa_entry, extract_question_body, strip_option_prefix


@AgentServer.custom_action("LandladyQaLearnAnswer")
class LandladyQaLearnAnswer(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        param = parse_pipeline_json_param(argv.custom_action_param)
        db_path = str(param.get("db_path", DEFAULT_DB)).strip() or DEFAULT_DB
        offset = param.get("target_offset", LEARN_OFFSET)
        if not isinstance(offset, list) or len(offset) != 4:
            return CustomAction.RunResult(success=False)

        rd = argv.reco_detail
        image = context.tasker.controller.cached_image
        if not rd or not rd.hit or rd.box is None or image is None:
            logger.error("LandladyQa learn: 未匹配到选项区「回答正确」图标")
            return CustomAction.RunResult(success=False)

        answer = strip_option_prefix(ocr_answer_from_icon(rd, context, image, offset))
        logger.debug(f"LandladyQa learn: OCR 答案={answer!r} offset={offset}")
        if not answer:
            logger.error(
                f"LandladyQa learn: OCR 答案为空 (icon={match_box(rd)} offset={offset})"
            )
            return CustomAction.RunResult(success=False)

        pending = pop_pending_round()
        if pending and (pending.body or pending.raw):
            question = pending.body or extract_question_body(pending.raw)
            logger.debug(f"LandladyQa learn: 题干来自缓存 {question!r}")
        else:
            question = extract_question_body(
                ocr_roi(context, image, QUESTION_ROI, NODE_QUESTION)
            )
            logger.debug(f"LandladyQa learn: 题干重新 OCR {question!r}")
        if not question:
            logger.error("LandladyQa learn: 无法取得题干")
            return CustomAction.RunResult(success=False)

        on_dup = str(param.get("on_duplicate", "update"))
        try:
            append_qa_entry(db_path, question, answer, on_duplicate=on_dup)
        except (OSError, ValueError) as e:
            logger.error(f"LandladyQa learn: 写入失败 {e}")
            return CustomAction.RunResult(success=False)

        logger.debug(
            f"LandladyQa learn: 已写入 {db_path} Q={question!r} A={answer!r} dup={on_dup}"
        )
        return CustomAction.RunResult(success=True)
