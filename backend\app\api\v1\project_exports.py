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

router = APIRouter(prefix="/project-exports", tags=["项目清单导出"])


def _contains(value: str | None, keyword: str | None) -> bool:
    return not keyword or keyword.lower() in (value or "").lower()


def _format_date(value: datetime | date | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")


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
        '</sheetData>'
        '</worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="项目清单" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
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
    archive_date_from: date | None,
    archive_date_to: date | None,
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

        if not _contains(project.project_code, project_no):
            continue
        if not _contains(project.project_name, project_name):
            continue
        if not _contains(record.paper_report_no if record else None, report_no):
            continue
        if not _contains(leader.real_name if leader else None, project_leader_name):
            continue
        if undertaking_unit and project.undertaking_unit != undertaking_unit:
            continue
        if signer_name and signer_name.lower() not in signers.lower():
            continue
        if amount_min is not None and (amount is None or amount < amount_min):
            continue
        if amount_max is not None and (amount is None or amount > amount_max):
            continue
        if archive_date_from and (not archived_at or archived_at.date() < archive_date_from):
            continue
        if archive_date_to and (not archived_at or archived_at.date() > archive_date_to):
            continue

        rows.append({
            "project_no": project.project_code,
            "project_name": project.project_name,
            "report_no": record.paper_report_no if record else "",
            "project_leader_name": leader.real_name if leader else "",
            "undertaking_unit": project.undertaking_unit,
            "amount": amount if amount is not None else "",
            "signer_names": signers,
            "archive_date": _format_date(archived_at),
        })
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
    archive_date_from: date | None = None,
    archive_date_to: date | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> dict[str, list[dict[str, object]]]:
    return {"items": _collect_rows(db, project_no, project_name, report_no, project_leader_name, undertaking_unit, signer_name, amount_min, amount_max, archive_date_from, archive_date_to)}


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
    archive_date_from: date | None = None,
    archive_date_to: date | None = None,
    db: Session = Depends(get_db),
    _: set[str] = Depends(require_roles("ADMIN")),
) -> Response:
    rows = _collect_rows(db, project_no, project_name, report_no, project_leader_name, undertaking_unit, signer_name, amount_min, amount_max, archive_date_from, archive_date_to)
    data = [["项目编号", "项目名称", "报告编号", "项目负责人姓名", "承接单位", "收费金额", "签字评估师姓名", "归档日期"]]
    data.extend([
        [row["project_no"], row["project_name"], row["report_no"], row["project_leader_name"], row["undertaking_unit"], row["amount"], row["signer_names"], row["archive_date"]]
        for row in rows
    ])
    content = _xlsx(data)
    filename = f"project-list-{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
