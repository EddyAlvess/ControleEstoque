from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

_SP = ZoneInfo("America/Sao_Paulo")

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user
from app.services.auth_service import decode_access_token
from app.models.category import Category
from app.models.movement import InventoryMovement
from app.models.operator import Operator
from app.models.product import Product
from app.models.shift import Shift
from app.models.user import WebUser
from app.services import report_service
from app.services.settings_service import settings_cache

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def _ctx(request: Request, user: WebUser, **kwargs) -> dict:
    return {"request": request, "current_user": user, "cs": settings_cache.get(), **kwargs}


@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = Query(None)):
    token = request.cookies.get("access_token")
    if token and decode_access_token(token):
        return RedirectResponse(url="/dashboard")
    ctx = {"request": request}
    if error:
        ctx["error"] = "Usuário ou senha incorretos. Tente novamente."
    resp = templates.TemplateResponse("login.html", ctx)
    resp.delete_cookie("access_token")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_user),
):
    now_sp = datetime.now(_SP)
    today_start = now_sp.replace(hour=0, minute=0, second=0, microsecond=0)

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
    stock_by_category = await report_service.get_stock_by_category(db)

    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request, user,
            total_entry=float(total_entry),
            total_exit=float(total_exit),
            recent=recent_rows,
            summary=[s.model_dump() for s in summary],
            stock_by_category=stock_by_category,
            now=now_sp.strftime("%d/%m/%Y"),
        ),
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    movement_type: str | None = Query(None),
    operator_id: int | None = Query(None),
    category_id: int | None = Query(None),
    product_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    shift: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_user),
):
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None

    rows, total = await report_service.get_movements_query(
        db, movement_type, operator_id, product_id, df, dt, shift, page, page_size, category_id
    )
    summary = await report_service.get_summary(
        db, movement_type, df, dt, shift, category_id, product_id
    )

    operators = (await db.execute(
        select(Operator).where(Operator.is_active == True).order_by(Operator.name)
    )).scalars().all()
    categories = (await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.name)
    )).scalars().all()
    products = (await db.execute(
        select(Product).where(Product.is_active == True).order_by(Product.name)
    )).scalars().all()
    shifts = (await db.execute(
        select(Shift).where(Shift.is_active == True).order_by(Shift.start_hour)
    )).scalars().all()

    pages = max(1, (total + page_size - 1) // page_size)

    filter_params = urlencode({k: v for k, v in {
        "movement_type": movement_type,
        "operator_id": operator_id,
        "category_id": category_id,
        "product_id": product_id,
        "date_from": date_from,
        "date_to": date_to,
        "shift": shift,
        "page_size": page_size,
    }.items() if v is not None})

    return templates.TemplateResponse(
        "reports.html",
        _ctx(
            request, user,
            summary=summary,
            rows=rows,
            total=total,
            operators=operators,
            categories=categories,
            products=products,
            shifts=shifts,
            page=page,
            page_size=page_size,
            pages=pages,
            filter_params=filter_params,
            filters={
                "movement_type": movement_type,
                "operator_id": operator_id,
                "category_id": category_id,
                "product_id": product_id,
                "date_from": date_from,
                "date_to": date_to,
                "shift": shift,
            },
        ),
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
    ops_list = [
        {
            "id": op.id, "name": op.name, "badge_code": op.badge_code,
            "is_active": op.is_active, "has_pin": bool(op.pin_hash),
        }
        for op in operators
    ]
    return templates.TemplateResponse("admin/operators.html", _ctx(request, user, operators=ops_list))


@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    rows = (await db.execute(
        select(Product, Category.name.label("category_name"))
        .outerjoin(Category, Product.category_id == Category.id)
        .order_by(Product.name)
    )).all()
    prods_list = [
        {
            "id": r[0].id, "sku": r[0].sku, "name": r[0].name,
            "unit": r[0].unit, "category_id": r[0].category_id,
            "category_name": r[1], "is_active": r[0].is_active,
        }
        for r in rows
    ]
    categories = (await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.name)
    )).scalars().all()
    return templates.TemplateResponse(
        "admin/products.html",
        _ctx(request, user, products=prods_list, categories=categories),
    )


@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    cats = (await db.execute(select(Category).order_by(Category.name))).scalars().all()
    cats_list = [{"id": c.id, "name": c.name, "is_active": c.is_active} for c in cats]
    return templates.TemplateResponse("admin/categories.html", _ctx(request, user, categories=cats_list))


@router.get("/admin/shifts", response_class=HTMLResponse)
async def admin_shifts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: WebUser = Depends(require_admin),
):
    shifts = (await db.execute(select(Shift).order_by(Shift.start_hour))).scalars().all()
    shifts_list = [
        {"id": s.id, "name": s.name, "label": s.label,
         "start_hour": s.start_hour, "end_hour": s.end_hour, "is_active": s.is_active}
        for s in shifts
    ]
    return templates.TemplateResponse("admin/shifts.html", _ctx(request, user, shifts=shifts_list))


@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    user: WebUser = Depends(require_admin),
):
    return templates.TemplateResponse("admin/settings.html", _ctx(request, user))
