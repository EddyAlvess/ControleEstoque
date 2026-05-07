from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user_or_esp32
from app.models.category import Category
from app.models.product import Product
from app.models.user import WebUser
from app.schemas.product import ProductCreate, ProductRead, ProductReadFull, ProductUpdate

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=list[ProductReadFull])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    rows = (await db.execute(
        select(Product, Category.name.label("category_name"))
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Product.is_active == True)
        .order_by(Product.name)
    )).all()
    return [
        ProductReadFull(
            id=r[0].id,
            sku=r[0].sku,
            name=r[0].name,
            unit=r[0].unit,
            category_id=r[0].category_id,
            is_active=r[0].is_active,
            created_at=r[0].created_at,
            category_name=r[1],
        )
        for r in rows
    ]


@router.get("/by-sku/{sku}", response_model=ProductReadFull)
async def get_product_by_sku(
    sku: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    """Busca um produto pelo SKU — usado pelo terminal ESP32 para lookup por código."""
    row = (await db.execute(
        select(Product, Category.name.label("category_name"))
        .outerjoin(Category, Product.category_id == Category.id)
        .where(Product.sku == sku, Product.is_active == True)
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return ProductReadFull(
        id=row[0].id, sku=row[0].sku, name=row[0].name, unit=row[0].unit,
        category_id=row[0].category_id, is_active=row[0].is_active,
        created_at=row[0].created_at, category_name=row[1],
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    exists = await db.execute(select(Product).where(Product.sku == data.sku))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="SKU já cadastrado")
    prod = Product(sku=data.sku, name=data.name, unit=data.unit, category_id=data.category_id)
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod


@router.put("/{prod_id}", response_model=ProductRead)
async def update_product(
    prod_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(Product).where(Product.id == prod_id))
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if data.sku is not None:
        prod.sku = data.sku
    if data.name is not None:
        prod.name = data.name
    if data.unit is not None:
        prod.unit = data.unit
    if "category_id" in data.model_fields_set:
        prod.category_id = data.category_id
    if data.is_active is not None:
        prod.is_active = data.is_active
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod


@router.delete("/{prod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    prod_id: int,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(Product).where(Product.id == prod_id))
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    prod.is_active = False
    db.add(prod)
    await db.commit()
