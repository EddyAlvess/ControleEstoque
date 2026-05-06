from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user
from app.services.auth_service import decode_access_token
from app.models.movement import InventoryMovement
from app.models.operator import Operator
from app.models.product import Product
from app.models.user import WebUser
from app.services import report_service

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def _ctx(request: Request, user: WebUser, **kwargs) -> dict:
    return {"request": request, "current_user": user, **kwargs}


@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    if token and decode_access_token(token):
        return RedirectResponse(url="/dashboard")
    resp = templates.TemplateResponse("login.html", {"request": request})
    resp.delete_cookie("access_token")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_user),
):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    total_entry = (await db.execute(
        select(func.coalesce(func.sum(InventoryMovement.quantity), 0))
        .where(InventoryMovement.movement_type == "ENTRY")
        .where(InventoryMovement.recorded_at >= today_start)
    )).scalar()

    total_exit = (await db.execute(
        select(func.coalesce(func.sum(InventoryMovement.quantity), 0))
        .where(InventoryMovement.movement_type == "EXIT")
        .where(InventoryMovement.recorded_at >= today_start)
    )).scalar()

    recent_rows, _ = await report_service.get_movements_query(db, page=1, page_size=10)

    summary = await report_service.get_summary(db, date_from=today_start)

    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request, user,
            total_entry=float(total_entry),
            total_exit=float(total_exit),
            recent=recent_rows,
            summary=[s.model_dump() for s in summary],
            now=datetime.now().strftime("%d/%m/%Y"),
        ),
    )


@router.get("/movements", response_class=HTMLResponse)
async def movements_page(
    request: Request,
    movement_type: str | None = Query(None),
    operator_id: int | None = Query(None),
    product_id: int | None = Query(None),
    shift: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_user),
):
    rows, total = await report_service.get_movements_query(
        db, movement_type, operator_id, product_id, None, None, shift, page, 50
    )
    operators = (await db.execute(select(Operator).where(Operator.is_active == True).order_by(Operator.name))).scalars().all()
    products = (await db.execute(select(Product).where(Product.is_active == True).order_by(Product.name))).scalars().all()
    pages = (total + 49) // 50
    return templates.TemplateResponse(
        "movements.html",
        _ctx(request, user, rows=rows, total=total, page=page, pages=pages,
             operators=operators, products=products,
             filters={"movement_type": movement_type, "operator_id": operator_id,
                      "product_id": product_id, "shift": shift}),
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    movement_type: str | None = Query(None),
    operator_id: int | None = Query(None),
    product_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    shift: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_user),
):
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    summary = await report_service.get_summary(db, movement_type, df, dt, shift)
    rows, total = await report_service.get_movements_query(
        db, movement_type, operator_id, product_id, df, dt, shift, page=1, page_size=200
    )
    operators = (await db.execute(select(Operator).where(Operator.is_active == True).order_by(Operator.name))).scalars().all()
    products = (await db.execute(select(Product).where(Product.is_active == True).order_by(Product.name))).scalars().all()
    return templates.TemplateResponse(
        "reports.html",
        _ctx(request, user, summary=summary, rows=rows, total=total,
             operators=operators, products=products,
             filters={"movement_type": movement_type, "operator_id": operator_id,
                      "product_id": product_id, "date_from": date_from,
                      "date_to": date_to, "shift": shift}),
    )


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    users = (await db.execute(select(WebUser).order_by(WebUser.username))).scalars().all()
    return templates.TemplateResponse("admin/users.html", _ctx(request, user, users=users))


@router.get("/admin/operators", response_class=HTMLResponse)
async def admin_operators(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    operators = (await db.execute(select(Operator).order_by(Operator.name))).scalars().all()
    return templates.TemplateResponse("admin/operators.html", _ctx(request, user, operators=operators))


@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    products = (await db.execute(select(Product).order_by(Product.name))).scalars().all()
    return templates.TemplateResponse("admin/products.html", _ctx(request, user, products=products))
