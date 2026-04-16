from collections.abc import Iterable


def validate_reviewer_avoidance(
    project_leader_id: int,
    business_user_id: int,
    first_reviewer_id: int | None,
    second_reviewer_id: int | None,
    third_reviewer_id: int | None,
) -> tuple[bool, str]:
    """Validate reviewer avoidance rules in a project."""
    reviewer_ids = [rid for rid in [first_reviewer_id, second_reviewer_id, third_reviewer_id] if rid is not None]

    restricted_ids = {project_leader_id, business_user_id}
    if any(rid in restricted_ids for rid in reviewer_ids):
        return False, "项目负责人/业务负责人不得担任任一审核老师"

    if len(reviewer_ids) != len(set(reviewer_ids)):
        return False, "一审、二审、三审人员必须互斥"

    return True, "ok"


def filter_candidates(raw_user_ids: Iterable[int], excluded_user_ids: set[int]) -> list[int]:
    """Filter invalid candidate user ids for next assignee picker."""
    return [uid for uid in raw_user_ids if uid not in excluded_user_ids]
