from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.work_order import WorkOrder


def get_project_party_user_ids(
    db: Session,
    project_id: int,
    work_order: WorkOrder | None = None,
    project: Project | None = None,
) -> set[int]:
    project_row = project or db.query(Project).filter(Project.id == project_id).first()
    if not project_row:
        return set()

    project_member_ids = {
        user_id for (user_id,) in db.query(ProjectMember.user_id).filter(ProjectMember.project_id == project_id).all()
    }
    project_party_ids = set(project_member_ids)
    if project_row.project_leader_id:
        project_party_ids.add(project_row.project_leader_id)
    if work_order and work_order.project_leader_id:
        project_party_ids.add(work_order.project_leader_id)
    if project_row.business_user_id in project_member_ids or project_row.business_user_id == project_row.project_leader_id:
        project_party_ids.add(project_row.business_user_id)
    return {user_id for user_id in project_party_ids if user_id}


def validate_not_project_party(target_user_id: int | None, project_party_ids: set[int], role_label: str) -> None:
    if target_user_id and target_user_id in project_party_ids:
        raise HTTPException(status_code=400, detail=f"该账号已是本项目项目方成员，不能担任{role_label}")


def validate_support_role_not_project_party(target_user_id: int | None, project_party_ids: set[int], role_label: str) -> None:
    validate_not_project_party(target_user_id, project_party_ids, role_label)


def validate_reviewer_round_conflict(target_user_id: int | None, work_order: WorkOrder, review_round: str) -> None:
    if not target_user_id:
        return
    conflict_targets = {
        "FIRST": {work_order.second_reviewer_id, work_order.third_reviewer_id},
        "SECOND": {work_order.first_reviewer_id, work_order.third_reviewer_id},
        "THIRD": {work_order.first_reviewer_id, work_order.second_reviewer_id},
    }
    if target_user_id in {item for item in conflict_targets.get(review_round, set()) if item}:
        raise HTTPException(status_code=400, detail="同一账号不能兼任一审、二审、三审老师")


def validate_signers_not_reviewers(reviewer_names: set[str], signer_one: str | None, signer_two: str | None) -> None:
    signers = {item.strip() for item in [signer_one or "", signer_two or ""] if item and item.strip()}
    if reviewer_names.intersection(signers):
        raise HTTPException(status_code=400, detail="一/二/三审老师不能作为本人参与审核项目的签字评估师")


def validate_member_not_conflicting_with_assigned_roles(target_user_id: int, work_order: WorkOrder | None) -> None:
    if not work_order:
        return
    assigned_role_user_ids = {
        work_order.contract_reviewer_id,
        work_order.first_reviewer_id,
        work_order.second_reviewer_id,
        work_order.third_reviewer_id,
        work_order.print_room_handler_id,
        work_order.archive_reviewer_id,
    }
    if target_user_id in {item for item in assigned_role_user_ids if item}:
        raise HTTPException(status_code=400, detail="???????????????????????????")
