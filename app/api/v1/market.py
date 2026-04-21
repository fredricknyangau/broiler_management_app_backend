from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (  # Auth optional for reading market prices? enforcing for now, set_tenant_context
    get_current_non_viewer, get_current_user, get_db)
from app.db.models.market import MarketPrice
from app.schemas.market import MarketPriceCreate, MarketPriceResponse

router = APIRouter()


@router.post(
    "/prices", response_model=MarketPriceResponse, status_code=status.HTTP_201_CREATED
)
async def create_market_price(
    item_in: MarketPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_non_viewer),  # Only auth users can add prices
):
    """
    Record a new market price.
    """
    item = MarketPrice(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/prices", response_model=List[MarketPriceResponse])
async def read_market_prices(
    county: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    # Open endpoint? Or auth? Let's keep it open or auth.
    # Use auth for consistency based on other endpoints.
):
    """
    List market prices.
    """
    stmt = select(MarketPrice)
    if county:
        stmt = stmt.filter(MarketPrice.county == county)
    result = await db.execute(
        stmt.order_by(MarketPrice.price_date.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.put("/prices/{price_id}", response_model=MarketPriceResponse)
async def update_market_price(
    price_id: UUID,
    item_in: MarketPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_non_viewer),
):
    """
    Update a market price.
    """
    result = await db.execute(select(MarketPrice).filter(MarketPrice.id == price_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Market price not found")

    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    # db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/prices/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_price(
    price_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a market price entry.
    """
    result = await db.execute(select(MarketPrice).filter(MarketPrice.id == price_id))
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=404, detail="Market price not found")

    await db.delete(item)
    await db.commit()
    return None
