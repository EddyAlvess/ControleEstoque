import csv
import io
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement import InventoryMovement
from app.models.operator import Operator
from app.models.product import Product
from app.schemas.movement import ReportSummaryItem


async def get_movements_query(
    db: AsyncSession,
    movement_type: str | None = None,
    operator_id: int | None = None,
    product_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shift: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            InventoryMovement,
            Operator.name.label("operator_name"),
            Product.name.label("product_name"),
            Product.unit.label("product_unit"),
        )
        .join(Operator, InventoryMovement.operator_id == Operator.id)
        .join(Product, InventoryMovement.product_id == Product.id)
    )

    if movement_type:
        stmt = stmt.where(InventoryMovement.movement_type == movement_type)
    if operator_id:
        stmt = stmt.where(InventoryMovement.operator_id == operator_id)
    if product_id:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if date_from:
        stmt = stmt.where(InventoryMovement.recorded_at >= date_from)
    if date_to:
        stmt = stmt.where(InventoryMovement.recorded_at <= date_to)
    if shift:
        stmt = stmt.where(InventoryMovement.shift == shift)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(InventoryMovement.recorded_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(stmt)).all()
    results = []
    for row in rows:
        mv = row[0]
        results.append({
            "id": mv.id,
            "movement_type": mv.movement_type,
            "operator_id": mv.operator_id,
            "operator_name": row.operator_name,
            "product_id": mv.product_id,
            "product_name": row.product_name,
            "product_unit": row.product_unit,
            "quantity": float(mv.quantity),
            "shift": mv.shift,
            "device_id": mv.device_id,
            "notes": mv.notes,
            "recorded_at": mv.recorded_at,
            "created_at": mv.created_at,
        })
    return results, total


async def get_summary(
    db: AsyncSession,
    movement_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shift: str | None = None,
) -> list[ReportSummaryItem]:
    stmt = (
        select(
            InventoryMovement.product_id,
            Product.name.label("product_name"),
            Product.unit.label("product_unit"),
            InventoryMovement.movement_type,
            func.sum(InventoryMovement.quantity).label("total_quantity"),
            func.count(InventoryMovement.id).label("count"),
        )
        .join(Product, InventoryMovement.product_id == Product.id)
        .group_by(
            InventoryMovement.product_id,
            Product.name,
            Product.unit,
            InventoryMovement.movement_type,
        )
    )

    if movement_type:
        stmt = stmt.where(InventoryMovement.movement_type == movement_type)
    if date_from:
        stmt = stmt.where(InventoryMovement.recorded_at >= date_from)
    if date_to:
        stmt = stmt.where(InventoryMovement.recorded_at <= date_to)
    if shift:
        stmt = stmt.where(InventoryMovement.shift == shift)

    rows = (await db.execute(stmt)).all()
    return [
        ReportSummaryItem(
            product_id=r.product_id,
            product_name=r.product_name,
            product_unit=r.product_unit,
            movement_type=r.movement_type,
            total_quantity=float(r.total_quantity),
            count=r.count,
        )
        for r in rows
    ]


async def export_csv(
    db: AsyncSession,
    movement_type: str | None = None,
    operator_id: int | None = None,
    product_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shift: str | None = None,
) -> str:
    rows, _ = await get_movements_query(
        db, movement_type, operator_id, product_id, date_from, date_to, shift,
        page=1, page_size=100000,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Tipo", "Operador", "Produto", "Unidade",
        "Quantidade", "Turno", "Terminal", "Observações", "Data/Hora Registro",
    ])
    for r in rows:
        tipo = "Entrada" if r["movement_type"] == "ENTRY" else "Saída"
        shift_map = {"MORNING": "Manhã", "AFTERNOON": "Tarde", "NIGHT": "Noite"}
        writer.writerow([
            r["id"],
            tipo,
            r["operator_name"],
            r["product_name"],
            r["product_unit"],
            r["quantity"],
            shift_map.get(r["shift"] or "", r["shift"] or ""),
            r["device_id"] or "",
            r["notes"] or "",
            r["recorded_at"].strftime("%d/%m/%Y %H:%M:%S") if r["recorded_at"] else "",
        ])
    return output.getvalue()
