import httpx

from app.core.config import settings
from app.services.oa_agent_context import build_deterministic_project_answer


SYSTEM_PROMPT = """你是 OA 系统客服 Agent，只能基于后端提供的已授权数据回答。
要求：
1. 使用简洁流程型中文回答。
2. 优先说明当前状态、当前节点、当前处理人、下一步操作和页面入口。
3. 不要编造项目状态、审批意见或附件内容。
4. 不读取、不总结任何附件正文；附件只能说明元信息。
5. 不代用户提交、审批、修改、上传或删除，只给操作建议。
6. 如果信息不足，直接说明需要用户补充项目名称、项目编号或客户名称。
7. 回答“操作入口”时必须优先使用上下文里的 operation_entry、operation_url 和 operation_hint，不要只笼统回答“项目详情页 > 项目流程”。
8. 如果当前账号不是本节点处理人，必须明确说明“当前有权限处理流程的账号：xxx”，不要只说当前账号无权限或暂无待办。
"""


def build_project_prompt(user_message: str, context: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "用户问题：\n"
                f"{user_message}\n\n"
                "已授权项目上下文：\n"
                f"{context}\n\n"
                "请输出简洁流程型回答。"
            ),
        },
    ]


def generate_agent_answer(user_message: str, context: dict) -> str:
    if not settings.deepseek_api_key:
        return build_deterministic_project_answer(context)

    payload = {
        "model": settings.deepseek_model,
        "messages": build_project_prompt(user_message, context),
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.deepseek_timeout_seconds) as client:
            response = client.post(
                f"{settings.deepseek_api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return ensure_operation_guide(content.strip(), context)
    except Exception:
        return build_deterministic_project_answer(context)
    return build_deterministic_project_answer(context)


def ensure_operation_guide(answer: str, context: dict) -> str:
    flow = context.get("flow") if isinstance(context, dict) else None
    if not isinstance(flow, dict):
        return answer

    entry = str(flow.get("operation_entry") or "").strip()
    url = str(flow.get("operation_url") or "").strip()
    hint = str(flow.get("operation_hint") or "").strip()
    if not entry:
        return answer

    answer = ensure_handler_guidance(answer, flow)
    entry_prefix = "操作入口："
    hint_prefix = "操作提示："
    url_prefix = "直达链接："
    lines: list[str] = []

    for line in answer.strip().splitlines():
        stripped = line.strip()
        normalized = stripped.lstrip("-* ").replace("**", "").replace("`", "")
        if _is_operation_guide_line(normalized):
            continue
        if stripped.startswith("[点击进入]") or stripped.startswith("点击进入"):
            continue
        if url and url in stripped:
            if any(keyword in normalized for keyword in ("操作入口", "操作链接", "入口链接", "直达链接")):
                continue
            continue
        lines.append(line.rstrip())

    lines.append(f"{entry_prefix}{entry}。")
    if hint:
        lines.append(f"{hint_prefix}{hint}")
    if url:
        lines.append(f"{url_prefix}{url}")
    return "\n".join(lines)


def ensure_handler_guidance(answer: str, flow: dict) -> str:
    action = str(flow.get("available_action") or "")
    handler_name = str(flow.get("current_handler_name") or "").strip()
    if not handler_name or "当前有权限处理流程的账号" not in action:
        return answer
    if "当前有权限处理流程的账号" in answer:
        return answer

    lines: list[str] = []
    inserted = False
    for line in answer.strip().splitlines():
        lines.append(line)
        if not inserted and line.strip().startswith("当前处理人"):
            lines.append(f"当前有权限处理流程的账号：{handler_name}")
            inserted = True
    if not inserted:
        lines.append(f"当前有权限处理流程的账号：{handler_name}")
    return "\n".join(lines)


def _is_operation_guide_line(normalized_line: str) -> bool:
    return normalized_line.startswith(
        (
            "操作入口：",
            "操作入口:",
            "操作链接：",
            "操作链接:",
            "入口链接：",
            "入口链接:",
            "直达链接：",
            "直达链接:",
            "操作提示：",
            "操作提示:",
            "提示：",
            "提示:",
        )
    )
