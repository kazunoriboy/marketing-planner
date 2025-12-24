"""施設管理API（施設管理者用）"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.database import get_session
from app.models import FacilityAdmin, FacilityAdminHotel, Hotel, FacilityAdminHotelRole
from app.auth.dependencies import get_current_facility_admin

router = APIRouter(prefix="/facility/hotels", tags=["Facility Hotels"])


class HotelCreateRequest(BaseModel):
    """施設作成リクエスト"""
    name: str
    address: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    features: dict = {}
    strengths: dict = {}


class HotelUpdateRequest(BaseModel):
    """施設更新リクエスト"""
    name: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    features: Optional[dict] = None
    strengths: Optional[dict] = None


class HotelResponse(BaseModel):
    """施設レスポンス"""
    id: int
    name: str
    address: str
    postal_code: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    features: dict
    strengths: dict
    role: str  # 施設管理者の権限
    
    class Config:
        from_attributes = True


class HotelDetailResponse(HotelResponse):
    """施設詳細レスポンス"""
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[HotelResponse])
async def list_my_hotels(
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    自分の施設一覧を取得
    
    - 紐付けられている施設のみ返す
    """
    permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id
        )
    ).all()
    
    hotels = []
    for perm in permissions:
        hotel = session.exec(
            select(Hotel).where(Hotel.id == perm.hotel_id)
        ).first()
        if hotel:
            hotels.append(HotelResponse(
                id=hotel.id,
                name=hotel.name,
                address=hotel.address,
                postal_code=hotel.postal_code,
                phone=hotel.phone,
                website=hotel.website,
                features=hotel.features,
                strengths=hotel.strengths,
                role=perm.role,
            ))
    
    return hotels


@router.post("", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
async def create_hotel(
    request: HotelCreateRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設を新規登録
    
    - 作成した施設にはオーナー権限が自動付与される
    """
    # 施設作成
    hotel = Hotel(
        name=request.name,
        address=request.address,
        postal_code=request.postal_code,
        phone=request.phone,
        website=request.website,
        features=request.features,
        strengths=request.strengths,
    )
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    # オーナー権限を付与
    permission = FacilityAdminHotel(
        facility_admin_id=facility_admin.id,
        hotel_id=hotel.id,
        role=FacilityAdminHotelRole.owner,
    )
    
    session.add(permission)
    session.commit()
    
    return HotelResponse(
        id=hotel.id,
        name=hotel.name,
        address=hotel.address,
        postal_code=hotel.postal_code,
        phone=hotel.phone,
        website=hotel.website,
        features=hotel.features,
        strengths=hotel.strengths,
        role=FacilityAdminHotelRole.owner,
    )


@router.get("/{hotel_id}", response_model=HotelDetailResponse)
async def get_hotel(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設詳細を取得
    
    - 自分に紐付けられている施設のみ取得可能
    """
    # 権限確認
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この施設へのアクセス権限がありません",
        )
    
    hotel = session.exec(
        select(Hotel).where(Hotel.id == hotel_id)
    ).first()
    
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )
    
    return HotelDetailResponse(
        id=hotel.id,
        name=hotel.name,
        address=hotel.address,
        postal_code=hotel.postal_code,
        phone=hotel.phone,
        website=hotel.website,
        features=hotel.features,
        strengths=hotel.strengths,
        role=permission.role,
        created_at=hotel.created_at,
        updated_at=hotel.updated_at,
    )


@router.put("/{hotel_id}", response_model=HotelDetailResponse)
async def update_hotel(
    hotel_id: int,
    request: HotelUpdateRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設を更新
    
    - オーナーまたはエディター権限が必要
    """
    # 権限確認
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この施設へのアクセス権限がありません",
        )
    
    if permission.role not in [FacilityAdminHotelRole.owner, FacilityAdminHotelRole.editor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="編集権限がありません",
        )
    
    hotel = session.exec(
        select(Hotel).where(Hotel.id == hotel_id)
    ).first()
    
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )
    
    # 更新
    if request.name is not None:
        hotel.name = request.name
    if request.address is not None:
        hotel.address = request.address
    if request.postal_code is not None:
        hotel.postal_code = request.postal_code
    if request.phone is not None:
        hotel.phone = request.phone
    if request.website is not None:
        hotel.website = request.website
    if request.features is not None:
        hotel.features = request.features
    if request.strengths is not None:
        hotel.strengths = request.strengths
    
    hotel.updated_at = datetime.utcnow()
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    return HotelDetailResponse(
        id=hotel.id,
        name=hotel.name,
        address=hotel.address,
        postal_code=hotel.postal_code,
        phone=hotel.phone,
        website=hotel.website,
        features=hotel.features,
        strengths=hotel.strengths,
        role=permission.role,
        created_at=hotel.created_at,
        updated_at=hotel.updated_at,
    )


@router.delete("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hotel(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設を削除
    
    - オーナー権限が必要
    """
    # 権限確認
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この施設へのアクセス権限がありません",
        )
    
    if permission.role != FacilityAdminHotelRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="オーナー権限が必要です",
        )
    
    hotel = session.exec(
        select(Hotel).where(Hotel.id == hotel_id)
    ).first()
    
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )
    
    # すべての紐付けを削除
    all_permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).all()
    
    for perm in all_permissions:
        session.delete(perm)
    
    # 施設を削除
    session.delete(hotel)
    session.commit()

