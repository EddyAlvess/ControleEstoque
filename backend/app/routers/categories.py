from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user_or_esp32
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.name)
    )
    return result.scalars().all()


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    exists = await db.execute(select(Category).where(Category.name == data.name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Categoria já existe")
    cat = Category(name=data.name)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/{cat_id}", response_model=CategoryRead)
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    if data.name is not None:
        cat.name = data.name
    if data.is_active is not None:
        cat.is_active = data.is_active
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    await db.execute(update(Product).where(Product.category_id == cat_id).values(category_id=None))
    await db.delete(cat)
    await db.commit()
