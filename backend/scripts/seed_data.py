"""Popula o banco com dados iniciais: admin, produtos e operadores de exemplo."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.operator import Operator
from app.models.product import Product
from app.models.user import WebUser
from app.services.auth_service import hash_password

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

PRODUCTS = [
    ("SORV-MOR-1L", "Sorvete Morango 1L", "L"),
    ("SORV-CHOC-1L", "Sorvete Chocolate 1L", "L"),
    ("ACAI-500ML", "Açaí 500ml", "L"),
    ("ACAI-1L", "Açaí 1L", "L"),
    ("PICOLE-LIM", "Picolé Limão", "un"),
]

OPERATORS = [
    ("João Silva", "1001"),
    ("Maria Santos", "1002"),
]


async def seed():
    async with SessionLocal() as db:
        # Admin
        exists = await db.execute(select(WebUser).where(WebUser.username == "admin"))
        if not exists.scalar_one_or_none():
            db.add(WebUser(
                username="admin",
                full_name="Administrador",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role="admin",
            ))
            print(f"✓ Usuário admin criado (senha: {ADMIN_PASSWORD})")
        else:
            print("  Admin já existe, pulando...")

        # Produtos
        for sku, name, unit in PRODUCTS:
            ex = await db.execute(select(Product).where(Product.sku == sku))
            if not ex.scalar_one_or_none():
                db.add(Product(sku=sku, name=name, unit=unit))
                print(f"✓ Produto: {name}")

        # Operadores
        for name, badge in OPERATORS:
            ex = await db.execute(select(Operator).where(Operator.badge_code == badge))
            if not ex.scalar_one_or_none():
                db.add(Operator(name=name, badge_code=badge))
                print(f"✓ Operador: {name} ({badge})")

        await db.commit()
    print("\nDados iniciais inseridos com sucesso.")
    print("IMPORTANTE: Altere a senha do admin no primeiro acesso!")


if __name__ == "__main__":
    asyncio.run(seed())
