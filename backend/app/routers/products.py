from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user, require_user_or_esp32
from app.models.product import Product
from app.models.user import WebUser
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    result = await db.execute(
        select(Product).where(Product.is_active == True).order_by(Product.name)
    )
    return result.scalars().all()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    exists = await db.execute(select(Product).where(Product.sku == data.sku))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="SKU já cadastrado")
    prod = Product(sku=data.sku, name=data.name, unit=data.unit)
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
    if data.name is not None:
        prod.name = data.name
    if data.unit is not None:
        prod.unit = data.unit
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
