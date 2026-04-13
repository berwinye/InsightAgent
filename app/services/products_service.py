from sqlalchemy.orm import Session
from app.models.products import Product
from app.core.exceptions import NotFoundError


def list_products(db: Session, skip: int = 0, limit: int = 100) -> dict:
    total = db.query(Product).count()
    items = db.query(Product).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def get_product(db: Session, product_code: str) -> Product:
    product = db.query(Product).filter(Product.productCode == product_code).first()
    if not product:
        raise NotFoundError("Product", product_code)
    return product
