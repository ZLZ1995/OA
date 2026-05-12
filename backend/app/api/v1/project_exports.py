from datetime import date, datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.archive import Archive
from app.models.invoice import Invoice
from app.models.print_room_record import PrintRoomRecord
from app.models.project import Project
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.project_flow import get_project_leader_display_name, get_project_source_display

router = APIRouter(prefix="/project-exports", tags=["项目清单导出"])


def _contains(value: str | None, keyword: str | None) -> bool:
    return not keyword or keyword.lower() in (value or "").lower()


def _format_date(value: datetime | date | None) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value[:10]
    return value.strftime("%Y-%m-%d")


def _project_progress(project: Project, work_order: WorkOrder | None) -> str:
    if project.termination_status == "APPROVED":
        return "已作废"
    if project.archived_at is not None or (work_order and work_order.current_status == "ARCHIVED"):
        return "已归档"
    return "进行中"


def _user_name(db: Session, user_id: int | None) -> str:
    if not user_id:
        return ""
    return db.query(User.real_name).filter(User.id == user_id).scalar() or ""


def _project_created_date(project: Project) -> date:
    value = project.start_date or project.created_at
    if isinstance(value, datetime):
        return value.date()
    return value


def _col_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xlsx(rows: list[list[object]]) -> bytes:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            ref = f"{_col_name(col_index)}{row_index}"
            text = escape("" if value is None else str(value))
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        f'{"".join(sheet_rows)}'
        "</sheetData>"
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="项目清单" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def _collect_rows(
    db: Session,
    project_no: str | None,
    project_name: str | None,
    report_no: str | None,
    project_leader_name: str | None,
    undertaking_unit: str | None,
    signer_name: str | None,
    amount_min: float | None,
    amount_max: float | None,
    project_date_from: date | None,
    project_date_to: date | None,
    report_type: str | None = None,
    valuation_base_date_from: date | None = None,
    valuation_base_date_to: date | None = None,
    business_salesman: str | None = None,
    project_source: str | None = None,
    external_project_leader_name: str | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    projects = db.query(Project).filter(Project.deleted_at.is_(None)).order_by(Project.id.desc()).all()
    for project in projects:
        work_order = db.query(WorkOrder).filter(WorkOrder.project_id == project.id).order_by(WorkOrder.id.desc()).first()
        leader = db.query(User).filter(User.id == project.project_leader_id).first()
        record = db.query(PrintRoomRecord).filter(PrintRoomRecord.work_order_id == work_order.id).first() if work_order else None
        invoice = db.query(Invoice).filter(Invoice.work_order_id == work_order.id).order_by(Invoice.id.desc()).first() if work_order else None
        archive = db.query(Archive).filter(Archive.work_order_id == work_order.id).first() if work_order else None
        archived_at = project.archived_at or (archive.archive_at if archive else None)
        amount = float(invoice.amount) if invoice else None
        signers = "、".join(item for item in [work_order.signer_one if work_order else None, work_order.signer_two if work_order else None] if item)
        first_reviewer_name = _user_name(db, work_order.first_reviewer_id) if work_order else ""
        second_reviewer_name = _user_name(db, work_order.second_reviewer_id) if work_order else ""
        third_reviewer_name = _user_name(db, work_order.third_reviewer_id) if work_order else ""
        project_created_date = _project_created_date(project)
        leader_display_name = get_project_leader_display_name(project, leader.real_name if leader else None) or ""

        if not _contains(project.project_code, project_no):
            continue
        if not _contains(project.project_name, project_name):
            continue
        if not _contains(record.paper_report_no if record else None, report_no):
            continue
        if not _contains(leader_display_name, project_leader_name):
            continue
        if undertaking_unit and project.undertaking_unit != undertaking_unit:
            continue
        if signer_name and signer_name.lower() not in signers.lower():
            continue
        if amount_min is not None and (amount is None or amount < amount_min):
            continue
        if amount_max is not None and (amount is None or amount > amount_max):
            continue
        if project_date_from and project_created_date < project_date_from:
            continue
        if project_date_to and project_created_date > project_date_to:
            continue
        if report_type and project.report_type != report_type:
            continue
        if valuation_base_date_from and (project.valuation_base_date is None or project.valuation_base_date < valuation_base_date_from):
            continue
        if valuation_base_date_to and (project.valuation_base_date is None or project.valuation_base_date > valuation_base_date_to):
            continue
        if not _contains(project.business_salesman, business_salesman):
            continue
        if project_source and project.project_source != project_source:
            continue
        if not _contains(project.external_project_leader_name, external_project_leader_name):
            continue

        rows.append(
            {
                "project_no": project.project_code,
                "project_name": project.project_name,
                "project_created_date": _format_date(project_created_date),
                "project_progress": _project_progress(project, work_order),
                "report_no": record.paper_report_no if record else "",
                "project_leader_name": leader_display_name,
                "undertaking_unit": project.undertaking_unit,
                "report_type": project.report_type or "",
                "valuation_base_date": _format_date(project.valuation_base_date),
                "business_salesman": project.business_salesman or "",
                "project_source": project.project_source,
                "project_source_display": get_project_source_display(project.project_source),
                "external_project_leader_name": project.external_project_leader_name or "",
                "amount": amount if amount is not None else "",
                "signer_names": signers,
                "first_reviewer_name": first_reviewer_name,
                "second_reviewer_name": second_reviewer_name,
                "third_reviewer_name": third_reviewer_name,
                "archive_date": _format_date(archived_at),
            }
        )
    return rows


@router.get("")
def list_project_export_rows(
    project_no: str | None = None,
    project_name: str | None = None,
    report_no: str | None = None,
    project_leader_name: str | None = None,
    undertaking_unit: str | None = None,
    signer_name: str | None = None,
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    project_date_from: date | None = None,
    project_date_to: date | None = None,
    report_type: str | None = None,
    valuation_base_date_from: date | None = None,
    valuation_base_date_to: date | None = None,
    business_salesman: str | None = None,
    project_source: str | None = None,
    external_project_leader_name: str | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict[str, list[dict[str, object]]]:
    return {
        "items": _collect_rows(
            db,
            project_no,
            project_name,
            report_no,
            project_leader_name,
            undertaking_unit,
            signer_name,
            amount_min,
            amount_max,
            project_date_from,
            project_date_to,
            report_type,
            valuation_base_date_from,
            valuation_base_date_to,
            business_salesman,
            project_source,
            external_project_leader_name,
        )
    }


@router.get("/excel")
def export_project_rows_excel(
    project_no: str | None = None,
    project_name: str | None = None,
    report_no: str | None = None,
    project_leader_name: str | None = None,
    undertaking_unit: str | None = None,
    signer_name: str | None = None,
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    project_date_from: date | None = None,
    project_date_to: date | None = None,
    report_type: str | None = None,
    valuation_base_date_from: date | None = None,
    valuation_base_date_to: date | None = None,
    business_salesman: str | None = None,
    project_source: str | None = None,
    external_project_leader_name: str | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> Response:
    rows = _collect_rows(
        db,
        project_no,
        project_name,
        report_no,
        project_leader_name,
        undertaking_unit,
        signer_name,
        amount_min,
        amount_max,
        project_date_from,
        project_date_to,
        report_type,
        valuation_base_date_from,
        valuation_base_date_to,
        business_salesman,
        project_source,
        external_project_leader_name,
    )
    data = [[
        "项目编号",
        "项目名称",
        "项目立项日期",
        "项目进度",
        "报告编号",
        "项目负责人姓名",
        "承接单位",
        "报告类型",
        "评估基准日",
        "项目承接业务员",
        "项目来源",
        "外部项目负责人姓名",
        "收费金额",
        "签字评估师姓名",
        "一审人员姓名",
        "二审人员姓名",
        "三审人员姓名",
        "归档日期",
    ]]
    data.extend(
        [
            [
                row["project_no"],
                row["project_name"],
                row["project_created_date"],
                row["project_progress"],
                row["report_no"],
                row["project_leader_name"],
                row["undertaking_unit"],
                row["report_type"],
                row["valuation_base_date"],
                row["business_salesman"],
                row["project_source_display"],
                row["external_project_leader_name"],
                row["amount"],
                row["signer_names"],
                row["first_reviewer_name"],
                row["second_reviewer_name"],
                row["third_reviewer_name"],
                row["archive_date"],
            ]
            for row in rows
        ]
    )
    content = _xlsx(data)
    filename = f"project-list-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
