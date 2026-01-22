"""ユーザー管理API（システムアドミン用）"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import SystemAdmin, FacilityAdmin, FacilityAdminHotel, Hotel, Company
from app.auth.password import hash_password
from app.auth.schemas import (
    FacilityAdminResponse,
    FacilityAdminCreateRequest,
    FacilityAdminUpdateRequest,
    FacilityAdminHotelRole,
)
from app.auth.dependencies import get_current_system_admin

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


class FacilityAdminDetailResponse(FacilityAdminResponse):
    """施設管理者詳細レスポンス（施設情報含む）"""
    hotels: List[dict] = []
    company_id: Optional[int] = None


class FacilityAdminListResponse(FacilityAdminResponse):
    """施設管理者リストレスポンス"""
    hotel_count: int = 0
    company_id: Optional[int] = None
    company_name: Optional[str] = None


@router.get("", response_model=List[FacilityAdminListResponse])
async def list_facility_admins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者一覧を取得
    
    - ページネーション対応
    - アクティブ状態でフィルタリング可能
    """
    query = select(FacilityAdmin)
    
    if is_active is not None:
        query = query.where(FacilityAdmin.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    facility_admins = session.exec(query).all()
    
    # 施設数と企業グループ情報を取得
    result = []
    for fa in facility_admins:
        hotel_count = session.exec(
            select(FacilityAdminHotel).where(
                FacilityAdminHotel.facility_admin_id == fa.id
            )
        ).all()
        
        # 企業グループ情報を取得
        company_name = None
        if fa.company_id:
            company = session.exec(
                select(Company).where(Company.id == fa.company_id)
            ).first()
            if company:
                company_name = company.name
        
        result.append(FacilityAdminListResponse(
            id=fa.id,
            email=fa.email,
            name=fa.name,
            is_active=fa.is_active,
            hotel_count=len(hotel_count),
            company_id=fa.company_id,
            company_name=company_name,
        ))
    
    return result


@router.post("", response_model=FacilityAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_facility_admin(
    request: FacilityAdminCreateRequest,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者を作成
    
    - メールアドレスは一意である必要がある
    - パスワードは強度ポリシーに従う必要がある
    """
    # メールアドレス重複チェック
    existing = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.email == request.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に使用されています",
        )
    
    # 企業グループ存在確認（company_idが指定されている場合）
    if request.company_id is not None:
        company = session.exec(
            select(Company).where(Company.id == request.company_id)
        ).first()
        
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定された企業グループが見つかりません",
            )
    
    # 施設管理者作成
    facility_admin = FacilityAdmin(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        is_active=True,
        company_id=request.company_id,
    )
    
    session.add(facility_admin)
    session.commit()
    session.refresh(facility_admin)
    
    # 企業グループが指定されている場合、そのグループの既存施設を自動的に紐付け
    if facility_admin.company_id is not None:
        # 同じ企業グループの他の管理者を取得
        same_company_admins = session.exec(
            select(FacilityAdmin).where(
                FacilityAdmin.company_id == facility_admin.company_id,
                FacilityAdmin.id != facility_admin.id  # 自分を除く
            )
        ).all()
        
        # 同じ企業グループの管理者が作成した施設を取得
        same_company_admin_ids = {admin.id for admin in same_company_admins}
        
        if same_company_admin_ids:
            # 他の管理者に紐付けられている施設を取得
            other_permissions = session.exec(
                select(FacilityAdminHotel).where(
                    FacilityAdminHotel.facility_admin_id.in_(same_company_admin_ids)
                )
            ).all()
            
            # 既に紐付けられている施設IDを取得（新規作成なので空のはずだが念のため）
            existing_permissions = session.exec(
                select(FacilityAdminHotel).where(
                    FacilityAdminHotel.facility_admin_id == facility_admin.id
                )
            ).all()
            existing_hotel_ids = {perm.hotel_id for perm in existing_permissions}
            
            # まだ紐付けられていない施設を自動的に紐付け
            for perm in other_permissions:
                if perm.hotel_id not in existing_hotel_ids:
                    new_permission = FacilityAdminHotel(
                        facility_admin_id=facility_admin.id,
                        hotel_id=perm.hotel_id,
                        role=FacilityAdminHotelRole.owner,
                    )
                    session.add(new_permission)
            
            session.commit()
    
    return FacilityAdminResponse(
        id=facility_admin.id,
        email=facility_admin.email,
        name=facility_admin.name,
        is_active=facility_admin.is_active,
    )


@router.get("/{user_id}", response_model=FacilityAdminDetailResponse)
async def get_facility_admin(
    user_id: int,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者詳細を取得
    
    - 紐付けられた施設情報も含む
    """
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == user_id)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設管理者が見つかりません",
        )
    
    # 紐付けられた施設を取得
    permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == user_id
        )
    ).all()
    
    hotels = []
    for perm in permissions:
        hotel = session.exec(
            select(Hotel).where(Hotel.id == perm.hotel_id)
        ).first()
        if hotel:
            hotels.append({
                "id": hotel.id,
                "name": hotel.name,
                "role": perm.role,
            })
    
    return FacilityAdminDetailResponse(
        id=facility_admin.id,
        email=facility_admin.email,
        name=facility_admin.name,
        is_active=facility_admin.is_active,
        hotels=hotels,
        company_id=facility_admin.company_id,
    )


@router.put("/{user_id}", response_model=FacilityAdminResponse)
async def update_facility_admin(
    user_id: int,
    request: FacilityAdminUpdateRequest,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者を更新
    """
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == user_id)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設管理者が見つかりません",
        )
    
    # 更新
    if request.name is not None:
        facility_admin.name = request.name
    if request.is_active is not None:
        facility_admin.is_active = request.is_active
    old_company_id = facility_admin.company_id
    
    if request.company_id is not None:
        # 企業グループ存在確認
        # Noneまたは0の場合はNULLに設定（企業グループから外す）
        if request.company_id == 0 or request.company_id is None:
            facility_admin.company_id = None
        else:
            company = session.exec(
                select(Company).where(Company.id == request.company_id)
            ).first()
            
            if company is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定された企業グループが見つかりません",
                )
            facility_admin.company_id = request.company_id
    
    facility_admin.updated_at = datetime.utcnow()
    session.add(facility_admin)
    session.commit()
    session.refresh(facility_admin)
    
    # 企業グループに追加された場合、そのグループの既存施設を自動的に紐付け
    if request.company_id is not None and request.company_id != 0 and old_company_id != facility_admin.company_id:
        # 同じ企業グループの他の管理者を取得
        same_company_admins = session.exec(
            select(FacilityAdmin).where(
                FacilityAdmin.company_id == facility_admin.company_id,
                FacilityAdmin.id != facility_admin.id  # 自分を除く
            )
        ).all()
        
        # 同じ企業グループの管理者が作成した施設を取得
        same_company_admin_ids = {admin.id for admin in same_company_admins}
        
        if same_company_admin_ids:
            # 他の管理者に紐付けられている施設を取得
            other_permissions = session.exec(
                select(FacilityAdminHotel).where(
                    FacilityAdminHotel.facility_admin_id.in_(same_company_admin_ids)
                )
            ).all()
            
            # 既に紐付けられている施設IDを取得
            existing_permissions = session.exec(
                select(FacilityAdminHotel).where(
                    FacilityAdminHotel.facility_admin_id == facility_admin.id
                )
            ).all()
            existing_hotel_ids = {perm.hotel_id for perm in existing_permissions}
            
            # まだ紐付けられていない施設を自動的に紐付け
            for perm in other_permissions:
                if perm.hotel_id not in existing_hotel_ids:
                    new_permission = FacilityAdminHotel(
                        facility_admin_id=facility_admin.id,
                        hotel_id=perm.hotel_id,
                        role=FacilityAdminHotelRole.owner,
                    )
                    session.add(new_permission)
            
            session.commit()
    
    session.add(facility_admin)
    session.commit()
    session.refresh(facility_admin)
    
    return FacilityAdminResponse(
        id=facility_admin.id,
        email=facility_admin.email,
        name=facility_admin.name,
        is_active=facility_admin.is_active,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_facility_admin(
    user_id: int,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者を削除
    
    - 紐付けられた施設との関連も削除される
    """
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == user_id)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設管理者が見つかりません",
        )
    
    # 紐付けを削除
    permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == user_id
        )
    ).all()
    
    for perm in permissions:
        session.delete(perm)
    
    # 施設管理者を削除
    session.delete(facility_admin)
    session.commit()


@router.post("/{user_id}/hotels/{hotel_id}", status_code=status.HTTP_201_CREATED)
async def assign_hotel_to_admin(
    user_id: int,
    hotel_id: int,
    role: FacilityAdminHotelRole = FacilityAdminHotelRole.viewer,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者に施設を紐付け
    """
    # 施設管理者存在確認
    facility_admin = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.id == user_id)
    ).first()
    
    if facility_admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設管理者が見つかりません",
        )
    
    # 施設存在確認
    hotel = session.exec(
        select(Hotel).where(Hotel.id == hotel_id)
    ).first()
    
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )
    
    # 重複チェック
    existing = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == user_id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if existing:
        # 既存の権限を更新
        existing.role = role
        session.add(existing)
        session.commit()
        return {"message": "権限を更新しました", "role": role}
    
    # 新規紐付け作成
    permission = FacilityAdminHotel(
        facility_admin_id=user_id,
        hotel_id=hotel_id,
        role=role,
    )
    
    session.add(permission)
    session.commit()
    
    return {"message": "施設を紐付けました", "role": role}


@router.delete("/{user_id}/hotels/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_hotel_from_admin(
    user_id: int,
    hotel_id: int,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    施設管理者から施設の紐付けを解除
    """
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == user_id,
            FacilityAdminHotel.hotel_id == hotel_id
        )
    ).first()
    
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="紐付けが見つかりません",
        )
    
    session.delete(permission)
    session.commit()


