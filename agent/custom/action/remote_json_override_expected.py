# -*- coding: utf-8 -*-
"""从远端 JSON 拉取键值，经 override_pipeline 合并到流水线节点（OCR expected、InputText 等）。"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union, cast

import requests
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from custom.pipeline_params import parse_pipeline_json_param
from utils.logger import logger

# 内置镜像：依次尝试，任一成功即采用响应体（HTTP 2xx + 可解析 JSON）
_MirrorBuilder = Callable[[str, str, str, str], str]


def _mirror_jsdelivr_cdn(owner: str, repo: str, ref: str, path: str) -> str:
    return f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{ref}/{path}"


def _mirror_jsdelivr_fastly(owner: str, repo: str, ref: str, path: str) -> str:
    return f"https://fastly.jsdelivr.net/gh/{owner}/{repo}@{ref}/{path}"


def _mirror_raw_githubusercontent(owner: str, repo: str, ref: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"


DEFAULT_MIRROR_BUILDERS: Tuple[_MirrorBuilder, ...] = (
    _mirror_jsdelivr_cdn,
    _mirror_jsdelivr_fastly,
    _mirror_raw_githubusercontent,
)

# 省略 github_repo / repo 时使用（Fork 其它仓库时请显式传 repo）
DEFAULT_GITHUB_REPO = "originalsage/MR3A"
# 仅传 overrides、不写 path 时使用的相对路径
DEFAULT_REMOTE_META_PATH = "assets/remote/game-meta.json"


def _effective_github_repo(param: Mapping[str, Any]) -> str:
    for key in ("github_repo", "repo"):
        v = param.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    logger.debug(
        "RemoteJsonOverrideExpected: 未指定 github_repo/repo，使用默认 "
        f"{DEFAULT_GITHUB_REPO}"
    )
    return DEFAULT_GITHUB_REPO


def _parse_github_repo(repo_spec: str) -> Tuple[str, str]:
    s = repo_spec.strip().strip("/")
    if "/" not in s:
        raise ValueError("github_repo 须为 owner/repo 形式")
    owner, repo = s.split("/", 1)
    owner, repo = owner.strip(), repo.strip().strip("/")
    if not owner or not repo or "/" in repo:
        raise ValueError("github_repo 须为 owner/repo 形式")
    return owner, repo


def _normalize_resource_path(p: str) -> str:
    return p.strip().lstrip("/")


def _collect_try_urls(param: Dict[str, Any]) -> List[str]:
    """
    解析待尝试的 URL 列表（顺序即尝试顺序）。

    优先级：urls > url（绝对）> path / 无前缀 url > 仅 overrides（默认 path+默认 repo）。
    """
    raw_urls = param.get("urls")
    if isinstance(raw_urls, list) and raw_urls:
        out: List[str] = []
        for i, u in enumerate(raw_urls):
            if not isinstance(u, str) or not u.strip():
                raise ValueError(f"urls[{i}] 须为非空字符串")
            out.append(u.strip())
        return out

    single = param.get("url")
    if isinstance(single, str) and single.strip():
        s = single.strip()
        if "://" in s:
            return [s]
        # 无协议：视为仓库内相对 path，github_repo/repo 可省略（默认本仓库）
        gh = _effective_github_repo(param)
        return _expand_github_mirrors(gh, param)

    path_only = param.get("path")
    if isinstance(path_only, str) and path_only.strip():
        gh = _effective_github_repo(param)
        return _expand_github_mirrors(gh, param)

    # 最简：只写 overrides，使用默认 upstream 与默认 meta 路径
    if param.get("overrides") is not None:
        gh = _effective_github_repo(param)
        merged = dict(param)
        merged.setdefault("path", DEFAULT_REMOTE_META_PATH)
        return _expand_github_mirrors(gh, merged)

    raise ValueError(
        "缺少 url、urls、path，或未写 path 时的 overrides（可用默认 meta 路径）"
    )


def _expand_github_mirrors(github_repo: str, param: Dict[str, Any]) -> List[str]:
    owner, repo = _parse_github_repo(github_repo)
    ref_raw = param.get("ref", "main")
    if not isinstance(ref_raw, str) or not ref_raw.strip():
        raise ValueError("ref 须为非空字符串")
    ref = ref_raw.strip()

    rel = param.get("path")
    if not isinstance(rel, str) or not rel.strip():
        rel = param.get("url")
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError("简写模式下须设置 path（或无前缀的 url）")
    path = _normalize_resource_path(rel)

    custom = param.get("mirror_builders")
    builders: Sequence[_MirrorBuilder]
    if custom is not None:
        if not isinstance(custom, list) or not custom:
            raise ValueError("mirror_builders 须为非空字符串数组")
        # 字符串关键字 -> 内置名
        name_map: Dict[str, _MirrorBuilder] = {
            "jsdelivr": _mirror_jsdelivr_cdn,
            "jsdelivr_cdn": _mirror_jsdelivr_cdn,
            "fastly": _mirror_jsdelivr_fastly,
            "jsdelivr_fastly": _mirror_jsdelivr_fastly,
            "raw": _mirror_raw_githubusercontent,
            "raw_github": _mirror_raw_githubusercontent,
        }
        tmp: List[_MirrorBuilder] = []
        for i, item in enumerate(custom):
            if isinstance(item, str) and item in name_map:
                tmp.append(name_map[item])
            else:
                raise ValueError(
                    f"mirror_builders[{i}] 未知项 {item!r}，"
                    f"可选: jsdelivr, fastly, raw"
                )
        builders = tmp
    else:
        builders = DEFAULT_MIRROR_BUILDERS

    return [b(owner, repo, ref, path) for b in builders]


def _get_by_dotted_path(root: Any, path: str) -> Any:
    if not path or not path.strip():
        return root
    cur: Any = root
    for part in path.strip().split("."):
        if not isinstance(cur, MutableMapping) or part not in cur:
            raise KeyError(part)
        cur = cur[part]
    return cur


def _default_expected_set_path(merge_path: str) -> str:
    return "expected" if merge_path == "v1" else "recognition.param.expected"


def _parse_set_path(raw: Any, *, default_set: str) -> str:
    if raw is None:
        return default_set
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("set / target 须为非空字符串")
    return raw.strip()


def _normalize_overrides(
    raw: Any, *, default_set: str
) -> List[Dict[str, Any]]:
    """
    每项: node, json_key, set（写入节点下的点号路径，默认 OCR expected）,
    expected_as_list 可选（仅对 expected 字段生效，缺省用全局参数）。
    """
    if isinstance(raw, list):
        out: List[Dict[str, Any]] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise TypeError(f"overrides[{i}] 须为对象")
            node = item.get("node")
            jk = item.get("json_key")
            if not isinstance(node, str) or not node.strip():
                raise ValueError(f"overrides[{i}].node 须为非空字符串")
            if not isinstance(jk, str) or not jk.strip():
                raise ValueError(f"overrides[{i}].json_key 须为非空字符串")
            st = _parse_set_path(
                item.get("set", item.get("target")), default_set=default_set
            )
            entry: Dict[str, Any] = {
                "node": node.strip(),
                "json_key": jk.strip(),
                "set": st,
            }
            if "expected_as_list" in item:
                eal = item["expected_as_list"]
                if not isinstance(eal, bool):
                    raise TypeError(f"overrides[{i}].expected_as_list 须为 bool")
                entry["expected_as_list"] = eal
            out.append(entry)
        if not out:
            raise ValueError("overrides 数组不能为空")
        return out
    if isinstance(raw, dict):
        out = []
        for node, spec in raw.items():
            if not isinstance(node, str) or not node.strip():
                raise ValueError("overrides 对象键须为非空节点名")
            if isinstance(spec, str) and spec.strip():
                out.append(
                    {
                        "node": node.strip(),
                        "json_key": spec.strip(),
                        "set": default_set,
                    }
                )
            elif isinstance(spec, dict):
                jk = spec.get("json_key")
                if not isinstance(jk, str) or not jk.strip():
                    raise ValueError(
                        f"节点 {node!r} 的对象值须含非空 json_key 字符串"
                    )
                st = _parse_set_path(
                    spec.get("set", spec.get("target")),
                    default_set=default_set,
                )
                entry = {"node": node.strip(), "json_key": jk.strip(), "set": st}
                if "expected_as_list" in spec:
                    eal = spec["expected_as_list"]
                    if not isinstance(eal, bool):
                        raise TypeError(
                            f"节点 {node!r} 的 expected_as_list 须为 bool"
                        )
                    entry["expected_as_list"] = eal
                out.append(entry)
            else:
                raise TypeError(
                    f"节点 {node!r} 的值须为字符串（远端键名）或对象 "
                    f"{{ \"json_key\", \"set\"? }}"
                )
        if not out:
            raise ValueError("overrides 对象不能为空")
        return out
    raise TypeError("overrides 须为数组或对象")


def _value_to_remote_text(val: Any) -> str:
    if val is None:
        raise ValueError("值为 null")
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool)):
        return str(val)
    raise TypeError(f"不支持的 JSON 值类型: {type(val).__name__}")


def _build_expected_field(
    text: str, *, as_list: bool
) -> Union[str, List[str]]:
    if as_list:
        return [text]
    return text


def _subtree_from_dotted_path(dotted: str, leaf: Any) -> Dict[str, Any]:
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        raise ValueError("set 路径不能为空")
    cur: Any = leaf
    for p in reversed(parts):
        cur = {p: cur}
    return cast(Dict[str, Any], cur)


def _deep_merge_dict(dst: MutableMapping[str, Any], src: Mapping[str, Any]) -> None:
    for k, v in src.items():
        if (
            k in dst
            and isinstance(dst[k], MutableMapping)
            and isinstance(v, Mapping)
        ):
            _deep_merge_dict(cast(MutableMapping[str, Any], dst[k]), v)
        else:
            dst[k] = v


def _is_recognition_expected_path(set_path: str, merge_path: str) -> bool:
    if merge_path == "v1":
        return set_path == "expected"
    return set_path == "recognition.param.expected"


def _leaf_value_for_override(
    raw_remote: Any,
    *,
    set_path: str,
    merge_path: str,
    item: Mapping[str, Any],
    global_expected_as_list: bool,
) -> Any:
    """按 set 路径决定写入流水线的叶子值类型。"""
    if _is_recognition_expected_path(set_path, merge_path):
        eal = item.get("expected_as_list")
        use_list = eal if isinstance(eal, bool) else global_expected_as_list
        text = _value_to_remote_text(raw_remote)
        return _build_expected_field(text, as_list=use_list)

    # 其它路径（如 action.param.input_text）：标量转字符串
    return _value_to_remote_text(raw_remote)


def _single_url_fetch_to_text(
    u: str,
    *,
    method: str,
    headers: Optional[Dict[str, Any]],
    req_params: Optional[Dict[str, Any]],
    json_body: Any,
    data_body: Any,
    timeout: Any,
    verify: bool,
    body_json_regex: Optional[str],
    log_failures: bool,
) -> Optional[str]:
    """请求单 URL；成功返回响应体中用于 json.loads 的字符串，失败返回 None。"""
    logf = logger.warning if log_failures else logger.debug
    try:
        resp = requests.request(
            method,
            u,
            headers=headers,
            params=req_params,
            json=json_body if json_body is not None else None,
            data=data_body,
            timeout=timeout,
            verify=verify,
        )
    except requests.RequestException as e:
        logf(f"RemoteJsonOverrideExpected: {u} 请求异常: {e}")
        return None

    if not resp.ok:
        logf(f"RemoteJsonOverrideExpected: {u} HTTP {resp.status_code}")
        return None

    text = resp.text
    if body_json_regex:
        m = re.search(body_json_regex, text, re.DOTALL)
        if not m or not m.groups():
            logf(f"RemoteJsonOverrideExpected: {u} body_json_regex 未匹配")
            return None
        text = m.group(1)

    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        logf(f"RemoteJsonOverrideExpected: {u} JSON 无效: {e}")
        return None

    return text


def _fetch_first_ok_json_text(
    urls: List[str],
    *,
    method: str,
    headers: Optional[Dict[str, Any]],
    req_params: Optional[Dict[str, Any]],
    json_body: Any,
    data_body: Any,
    timeout: Any,
    verify: bool,
    body_json_regex: Optional[str],
    parallel_mirrors: bool,
) -> str:
    if parallel_mirrors and len(urls) > 1:

        def _work(u: str) -> Tuple[str, Optional[str]]:
            return u, _single_url_fetch_to_text(
                u,
                method=method,
                headers=headers,
                req_params=req_params,
                json_body=json_body,
                data_body=data_body,
                timeout=timeout,
                verify=verify,
                body_json_regex=body_json_regex,
                log_failures=False,
            )

        pool = ThreadPoolExecutor(max_workers=len(urls))
        try:
            futures = [pool.submit(_work, u) for u in urls]
            for fut in as_completed(futures):
                u, text = fut.result()
                if text is not None:
                    logger.debug(f"RemoteJsonOverrideExpected: 并行竞速成功 {u}")
                    return text
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        raise RuntimeError("所有镜像 URL 均失败（并行）")

    last_log: Optional[str] = None
    for u in urls:
        text = _single_url_fetch_to_text(
            u,
            method=method,
            headers=headers,
            req_params=req_params,
            json_body=json_body,
            data_body=data_body,
            timeout=timeout,
            verify=verify,
            body_json_regex=body_json_regex,
            log_failures=True,
        )
        if text is not None:
            logger.debug(f"RemoteJsonOverrideExpected: 顺序拉取成功 {u}")
            return text
        last_log = f"{u} 失败"

    raise RuntimeError(last_log or "所有镜像 URL 均失败")


@AgentServer.custom_action("RemoteJsonOverrideExpected")
class RemoteJsonOverrideExpected(CustomAction):
    """
    GET/POST 远端 JSON，将键值经 override_pipeline **深度合并**到目标节点字段。

    地址：urls / 绝对 url / path / 仅 overrides（默认 game-meta 路径）——同前。

    overrides（每项写入节点名 node 下的一条点号路径 set）：
    - 数组: [{ "node", "json_key", "set"?, "expected_as_list"? }, ...]；set / target 缺省为 OCR expected
      （v2: recognition.param.expected；v1: expected，由 expected_merge_path 决定）。
    - 对象简写:
      - 值 **字符串**：远端键名 = 该字符串，set 为默认 OCR expected（仅适合改 OCR）。
      - 值 **对象**：须含 json_key；可选 set / target、expected_as_list（仅 expected 字段）。

    非 OCR 的 ``set``（如 ``action.param.input_text``）仅支持字符串/数字/布尔等标量（数字会转成字符串）。

    **parallel_mirrors**（可选，默认 ``true``）：存在多个镜像 URL 时默认**并发**请求各镜像，
    取**最先**返回且 JSON 合法的一条（更快，但同一时刻出站请求更多）；设为 ``false`` 则改为顺序尝试；仅单 URL 时始终顺序。
    拉取成功不写入 **info**（命中镜像见 **debug**：``顺序拉取成功`` / ``并行竞速成功``）；并行时单条失败亦用 **debug**。

    InputText 示例::

        {
            "path": "assets/remote/game-meta.json",
            "overrides": {
                "兑换兑换码": {
                    "json_key": "兑换码",
                    "set": "action.param.input_text"
                }
            }
        }
        
        {
            "path": "assets/remote/game-meta.json",
            "overrides": {
                "检查版本": "版本名称"
            }
        }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        try:
            param = parse_pipeline_json_param(argv.custom_action_param)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"RemoteJsonOverrideExpected: 参数解析失败: {e}")
            return CustomAction.RunResult(success=False)

        try:
            try_urls = _collect_try_urls(param)
        except ValueError as e:
            logger.error(f"RemoteJsonOverrideExpected: {e}")
            return CustomAction.RunResult(success=False)

        merge_path = str(param.get("expected_merge_path", "v2")).lower()
        if merge_path not in ("v1", "v2"):
            logger.error("RemoteJsonOverrideExpected: expected_merge_path 仅支持 v1 / v2")
            return CustomAction.RunResult(success=False)

        default_set = _default_expected_set_path(merge_path)

        try:
            overrides = _normalize_overrides(
                param.get("overrides"), default_set=default_set
            )
        except (TypeError, ValueError) as e:
            logger.error(f"RemoteJsonOverrideExpected: overrides 无效: {e}")
            return CustomAction.RunResult(success=False)

        method = str(param.get("method", "GET")).upper()
        headers = param.get("headers")
        if headers is not None and not isinstance(headers, dict):
            logger.error("RemoteJsonOverrideExpected: headers 须为对象")
            return CustomAction.RunResult(success=False)

        req_params = param.get("params")
        if req_params is not None and not isinstance(req_params, dict):
            logger.error("RemoteJsonOverrideExpected: params 须为对象")
            return CustomAction.RunResult(success=False)

        timeout_raw = param.get("timeout", 10)
        if isinstance(timeout_raw, (list, tuple)) and len(timeout_raw) >= 2:
            timeout: Any = (float(timeout_raw[0]), float(timeout_raw[1]))
        else:
            try:
                timeout = float(timeout_raw)
            except (TypeError, ValueError):
                logger.error(f"RemoteJsonOverrideExpected: 无效 timeout: {timeout_raw!r}")
                return CustomAction.RunResult(success=False)

        verify = param.get("verify", True)
        if not isinstance(verify, bool):
            verify = True

        body_json_regex = param.get("body_json_regex")
        if body_json_regex is not None and not isinstance(body_json_regex, str):
            logger.error("RemoteJsonOverrideExpected: body_json_regex 须为字符串")
            return CustomAction.RunResult(success=False)

        root_json_path = param.get("root_json_path")
        if root_json_path is not None and not isinstance(root_json_path, str):
            logger.error("RemoteJsonOverrideExpected: root_json_path 须为字符串")
            return CustomAction.RunResult(success=False)

        expected_as_list = param.get("expected_as_list", True)
        if not isinstance(expected_as_list, bool):
            expected_as_list = True

        json_body = param.get("json")
        data_body = param.get("data")

        parallel_mirrors = param.get("parallel_mirrors", True)
        if not isinstance(parallel_mirrors, bool):
            parallel_mirrors = True

        try:
            text = _fetch_first_ok_json_text(
                try_urls,
                method=method,
                headers=headers,
                req_params=req_params,
                json_body=json_body,
                data_body=data_body,
                timeout=timeout,
                verify=verify,
                body_json_regex=body_json_regex,
                parallel_mirrors=parallel_mirrors,
            )
        except RuntimeError as e:
            logger.error(f"RemoteJsonOverrideExpected: {e}")
            return CustomAction.RunResult(success=False)

        try:
            root_data: Any = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"RemoteJsonOverrideExpected: JSON 解析失败: {e}")
            return CustomAction.RunResult(success=False)

        try:
            data = _get_by_dotted_path(
                root_data, root_json_path if isinstance(root_json_path, str) else ""
            )
        except KeyError as e:
            logger.error(f"RemoteJsonOverrideExpected: root_json_path 缺少键: {e}")
            return CustomAction.RunResult(success=False)

        if not isinstance(data, MutableMapping):
            logger.error(
                "RemoteJsonOverrideExpected: 用于取键的根对象须为 JSON 对象（dict）"
            )
            return CustomAction.RunResult(success=False)

        patch: Dict[str, Any] = {}

        for item in overrides:
            node = item["node"]
            jk = item["json_key"]
            set_path = item["set"]
            try:
                remote_raw = data[jk]
            except KeyError:
                logger.error(
                    f"RemoteJsonOverrideExpected: 远端 JSON 缺少键 {jk!r}（节点 {node!r}）"
                )
                return CustomAction.RunResult(success=False)

            try:
                leaf = _leaf_value_for_override(
                    remote_raw,
                    set_path=set_path,
                    merge_path=merge_path,
                    item=item,
                    global_expected_as_list=expected_as_list,
                )
            except (TypeError, ValueError) as e:
                logger.error(
                    f"RemoteJsonOverrideExpected: 键 {jk!r} 取值无效（节点 {node!r}）: {e}"
                )
                return CustomAction.RunResult(success=False)

            try:
                subtree = _subtree_from_dotted_path(set_path, leaf)
            except ValueError as e:
                logger.error(
                    f"RemoteJsonOverrideExpected: 节点 {node!r} set 无效: {e}"
                )
                return CustomAction.RunResult(success=False)

            if node not in patch:
                patch[node] = {}
            if not isinstance(patch[node], dict):
                logger.error(
                    f"RemoteJsonOverrideExpected: 节点 {node!r} 合并冲突（非对象）"
                )
                return CustomAction.RunResult(success=False)
            _deep_merge_dict(cast(MutableMapping[str, Any], patch[node]), subtree)

        if not context.override_pipeline(patch):
            logger.error("RemoteJsonOverrideExpected: override_pipeline 失败")
            return CustomAction.RunResult(success=False)

        logger.debug(
            f"RemoteJsonOverrideExpected: 已合并 {len(overrides)} 条远端字段到流水线"
        )
        return CustomAction.RunResult(success=True)
