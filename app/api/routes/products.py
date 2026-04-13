from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.ro_session import get_ro_db
from app.schemas.products import ProductBase, ProductList
from app.services.products_service import get_product, list_products

router = APIRouter(prefix="/products", tags=["Products"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=ProductList, summary="List all products")
def list_products_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_ro_db),
):
    return list_products(db, skip=skip, limit=limit)


@router.get("/{product_code}", response_model=ProductBase, summary="Get product by code")
def get_product_endpoint(product_code: str, db: Session = Depends(get_ro_db)):
    return get_product(db, product_code)
