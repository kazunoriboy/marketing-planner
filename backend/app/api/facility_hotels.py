"""施設管理API（施設管理者用）"""
import os
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlmodel import Session, select
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel

from app.core.database import get_session
from app.core.llm import get_llm_client
from app.core.image_utils import save_facility_image, delete_facility_image_file
from app.models import FacilityAdmin, FacilityAdminHotel, Hotel, FacilityAdminHotelRole, AnalysisSession
from app.auth.dependencies import get_current_facility_admin
from app.services.hotel_scrape_service import HotelScrapeService
from sqlmodel import select

router = APIRouter(prefix="/facility/hotels", tags=["Facility Hotels"])

# 施設画像の種別（API・DB で共通）
FACILITY_IMAGE_TYPES = [
    "exterior", "interior", "room", "bath", "cuisine", "lobby",
    "restaurant", "sightseeing", "staff", "other",
]
FACILITY_IMAGE_MAX_COUNT = 10
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class HotelCreateRequest(BaseModel):
    """施設作成リクエスト"""
    name: str
    address: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    features: dict = {}
    strengths: dict = {}
    cv_url: Optional[str] = None


class HotelUpdateRequest(BaseModel):
    """施設更新リクエスト"""
    name: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    features: Optional[dict] = None
    strengths: Optional[dict] = None
    cv_url: Optional[str] = None


class FacilityImageItemResponse(BaseModel):
    """施設画像1件のレスポンス"""
    key: str
    url: str
    description: str
    type: str
    order: int


class FacilityImageUpdateRequest(BaseModel):
    """施設画像メタデータ更新リクエスト"""
    type: Optional[str] = None
    description: Optional[str] = None


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
    cv_url: Optional[str]
    hotel_assets: dict = {}  # 施設の資産情報
    facility_images: list = []  # 施設画像（最大10件）
    role: str  # 施設管理者の権限
    
    class Config:
        from_attributes = True


class HotelDetailResponse(HotelResponse):
    """施設詳細レスポンス"""
    created_at: datetime
    updated_at: datetime


class HotelAssetsUpdateRequest(BaseModel):
    """施設の資産更新リクエスト"""
    # カテゴリごとの資産リスト
    room_amenities: Optional[List[str]] = None  # 部屋の設備・備品
    shared_facilities: Optional[List[str]] = None  # 共有施設
    dining: Optional[List[str]] = None  # 料理・食事
    services: Optional[List[str]] = None  # サービス
    experiences: Optional[List[str]] = None  # 体験・アクティビティ


@router.get("", response_model=List[HotelResponse])
async def list_my_hotels(
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    自分の施設一覧を取得
    
    - 直接紐付けられている施設
    - 同じ企業グループの他の管理者が作成した施設（自動的に紐付けを作成）
    """
    # 直接紐付けられている施設を取得
    permissions = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id
        )
    ).all()
    
    # 既に紐付けられている施設IDのセット
    linked_hotel_ids = {perm.hotel_id for perm in permissions}
    
    hotels = []
    hotel_permissions_map = {}
    
    # 直接紐付けられている施設を追加
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
                cv_url=hotel.cv_url,
                hotel_assets=hotel.hotel_assets or {},
                facility_images=hotel.facility_images if hotel.facility_images else [],
                role=perm.role,
            ))
            hotel_permissions_map[hotel.id] = perm.role
    
    # 同じ企業グループの他の管理者が作成した施設を取得
    if facility_admin.company_id is not None:
        # 同じ企業グループの全管理者を取得
        same_company_admins = session.exec(
            select(FacilityAdmin).where(
                FacilityAdmin.company_id == facility_admin.company_id
            )
        ).all()
        
        same_company_admin_ids = {admin.id for admin in same_company_admins}
        
        # 同じ企業グループの管理者が作成した施設を取得
        # （他の管理者に紐付けられている施設 = そのグループの施設）
        other_permissions = session.exec(
            select(FacilityAdminHotel).where(
                FacilityAdminHotel.facility_admin_id.in_(same_company_admin_ids)
            )
        ).all()
        
        # ユニークな施設IDのセットを作成（重複を避けるため）
        unique_hotel_ids = set()
        for perm in other_permissions:
            if perm.hotel_id not in linked_hotel_ids:
                unique_hotel_ids.add(perm.hotel_id)
        
        # まだ紐付けられていない施設を追加
        for hotel_id in unique_hotel_ids:
            hotel = session.exec(
                select(Hotel).where(Hotel.id == hotel_id)
            ).first()
            if hotel:
                # 自動的に紐付けを作成（owner権限）
                new_permission = FacilityAdminHotel(
                    facility_admin_id=facility_admin.id,
                    hotel_id=hotel.id,
                    role=FacilityAdminHotelRole.owner,
                )
                session.add(new_permission)
                linked_hotel_ids.add(hotel.id)
                
                hotels.append(HotelResponse(
                    id=hotel.id,
                    name=hotel.name,
                    address=hotel.address,
                    postal_code=hotel.postal_code,
                    phone=hotel.phone,
                    website=hotel.website,
                    features=hotel.features,
                    strengths=hotel.strengths,
                    cv_url=hotel.cv_url,
                    hotel_assets=hotel.hotel_assets or {},
                    facility_images=hotel.facility_images if hotel.facility_images else [],
                    role=FacilityAdminHotelRole.owner,
                ))
        
        session.commit()
    
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
        cv_url=request.cv_url,
    )
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    # 作成者にオーナー権限を付与
    permission = FacilityAdminHotel(
        facility_admin_id=facility_admin.id,
        hotel_id=hotel.id,
        role=FacilityAdminHotelRole.owner,
    )
    
    session.add(permission)
    
    # 同じ企業グループの全管理者に自動的に紐付け（全員owner権限）
    if facility_admin.company_id is not None:
        # 同じcompany_idを持つ全管理者を取得
        same_company_admins = session.exec(
            select(FacilityAdmin).where(
                FacilityAdmin.company_id == facility_admin.company_id,
                FacilityAdmin.id != facility_admin.id  # 作成者を除く
            )
        ).all()
        
        # 各管理者に施設を紐付け
        for admin in same_company_admins:
            # 既に紐付けられているかチェック
            existing = session.exec(
                select(FacilityAdminHotel).where(
                    FacilityAdminHotel.facility_admin_id == admin.id,
                    FacilityAdminHotel.hotel_id == hotel.id
                )
            ).first()
            
            if not existing:
                admin_permission = FacilityAdminHotel(
                    facility_admin_id=admin.id,
                    hotel_id=hotel.id,
                    role=FacilityAdminHotelRole.owner,
                )
                session.add(admin_permission)
    
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
        cv_url=hotel.cv_url,
        hotel_assets=hotel.hotel_assets or {},
        facility_images=hotel.facility_images if hotel.facility_images else [],
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
        cv_url=hotel.cv_url,
        hotel_assets=hotel.hotel_assets or {},
        facility_images=hotel.facility_images if hotel.facility_images else [],
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
    if request.cv_url is not None:
        hotel.cv_url = request.cv_url
    
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
        cv_url=hotel.cv_url,
        hotel_assets=hotel.hotel_assets or {},
        facility_images=hotel.facility_images if hotel.facility_images else [],
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


# ============================================
# 施設画像 API
# ============================================

@router.post("/{hotel_id}/images", response_model=FacilityImageItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_facility_image(
    hotel_id: int,
    file: UploadFile = File(...),
    type: str = Form(...),
    description: str = Form(""),
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session),
):
    """
    施設画像を1枚アップロードする。
    1MB 超過時はサーバ側で圧縮して保存する。1施設あたり最大10枚まで。
    """
    # 権限確認（owner または editor）
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id,
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

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    images = list(hotel.facility_images or [])
    if len(images) >= FACILITY_IMAGE_MAX_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"施設画像は最大{FACILITY_IMAGE_MAX_COUNT}枚までです",
        )

    if type not in FACILITY_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効な種別です。有効な値: {', '.join(FACILITY_IMAGE_TYPES)}",
        )

    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効なファイル形式です。有効な形式: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    content = await file.read()
    try:
        key, url = save_facility_image(hotel_id, content, file_ext)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ストレージ接続に失敗しました",
        )

    order = max((item.get("order", 0) for item in images), default=-1) + 1
    new_item = {
        "key": key,
        "url": url,
        "description": description or "",
        "type": type,
        "order": order,
    }
    images.append(new_item)
    hotel.facility_images = images
    hotel.updated_at = datetime.utcnow()
    flag_modified(hotel, "facility_images")
    session.add(hotel)
    session.commit()
    session.refresh(hotel)

    return FacilityImageItemResponse(
        key=new_item["key"],
        url=new_item["url"],
        description=new_item["description"],
        type=new_item["type"],
        order=new_item["order"],
    )


@router.delete("/{hotel_id}/images/{image_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_facility_image(
    hotel_id: int,
    image_key: str,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session),
):
    """指定 key の施設画像を削除する（DB と実ファイルの両方）。"""
    # 権限確認（owner または editor）
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id,
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

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    images = hotel.facility_images if hotel.facility_images else []
    new_images = [item for item in images if item.get("key") != image_key]
    if len(new_images) == len(images):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された画像が見つかりません",
        )

    # 削除対象の url を取得してから S3 上のオブジェクトを削除
    removed = next((item for item in images if item.get("key") == image_key), None)
    if removed:
        try:
            delete_facility_image_file(hotel_id, image_key, removed.get("url", ""))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ストレージ接続に失敗しました",
            )

    hotel.facility_images = new_images
    hotel.updated_at = datetime.utcnow()
    flag_modified(hotel, "facility_images")
    session.add(hotel)
    session.commit()


@router.put("/{hotel_id}/images/{image_key}", response_model=FacilityImageItemResponse)
async def update_facility_image(
    hotel_id: int,
    image_key: str,
    request: FacilityImageUpdateRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session),
):
    """指定 key の施設画像の種別・説明を更新する（実ファイルは変更しない）。"""
    # 権限確認（owner または editor）
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id,
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

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    images = list(hotel.facility_images or [])
    target_index = next((i for i, item in enumerate(images) if item.get("key") == image_key), None)
    if target_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定された画像が見つかりません",
        )

    item = dict(images[target_index])
    if request.type is not None:
        if request.type not in FACILITY_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無効な種別です。有効な値: {', '.join(FACILITY_IMAGE_TYPES)}",
            )
        item["type"] = request.type
    if request.description is not None:
        item["description"] = request.description

    images[target_index] = item
    hotel.facility_images = images
    hotel.updated_at = datetime.utcnow()
    flag_modified(hotel, "facility_images")
    session.add(hotel)
    session.commit()
    session.refresh(hotel)

    return FacilityImageItemResponse(
        key=item["key"],
        url=item["url"],
        description=item.get("description", ""),
        type=item["type"],
        order=item.get("order", 0),
    )


# ============================================
# 施設の資産管理 API
# ============================================

@router.get("/{hotel_id}/assets", response_model=dict)
async def get_hotel_assets(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設の資産情報を取得
    
    カテゴリ:
    - room_amenities: 部屋の設備・備品（露天風呂、マッサージチェア等）
    - shared_facilities: 共有施設（大浴場、サウナ、エステ等）
    - dining: 料理・食事（会席料理、朝食バイキング等）
    - services: サービス（送迎、ルームサービス等）
    - experiences: 体験・アクティビティ（陶芸体験、釣り等）
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
    
    # デフォルトのカテゴリ構造を返す
    default_assets = {
        "room_amenities": [],
        "shared_facilities": [],
        "dining": [],
        "services": [],
        "experiences": [],
    }
    
    return {**default_assets, **(hotel.hotel_assets or {})}


@router.put("/{hotel_id}/assets", response_model=dict)
async def update_hotel_assets(
    hotel_id: int,
    request: HotelAssetsUpdateRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    施設の資産情報を更新
    
    - 指定したカテゴリのみ更新される
    - nullのカテゴリは更新されない
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
    
    # 既存の資産情報を取得（なければ空）
    current_assets = hotel.hotel_assets or {}
    
    # 指定されたカテゴリのみ更新
    if request.room_amenities is not None:
        current_assets["room_amenities"] = request.room_amenities
    if request.shared_facilities is not None:
        current_assets["shared_facilities"] = request.shared_facilities
    if request.dining is not None:
        current_assets["dining"] = request.dining
    if request.services is not None:
        current_assets["services"] = request.services
    if request.experiences is not None:
        current_assets["experiences"] = request.experiences
    
    hotel.hotel_assets = current_assets
    hotel.updated_at = datetime.utcnow()
    
    session.add(hotel)
    session.commit()
    session.refresh(hotel)
    
    return hotel.hotel_assets


# ============================================
# 宿・周辺情報 API
# ============================================

class HotelDetailAttractionItem(BaseModel):
    """周辺観光スポット1件"""
    name: str
    distance: str


class HotelDetailSurrounding(BaseModel):
    """周辺情報"""
    description: str = ""
    attractions: List[HotelDetailAttractionItem] = []


class HotelStoryDetailResponse(BaseModel):
    """宿・周辺情報レスポンス"""
    story: str = ""
    highlights: List[str] = []
    surrounding: HotelDetailSurrounding = HotelDetailSurrounding()
    access: str = ""


class HotelDetailUpdateRequest(BaseModel):
    """宿・周辺情報更新リクエスト"""
    story: Optional[str] = None
    highlights: Optional[List[str]] = None
    surrounding: Optional[HotelDetailSurrounding] = None
    access: Optional[str] = None


@router.get("/{hotel_id}/detail", response_model=HotelStoryDetailResponse)
async def get_hotel_detail(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """宿のストーリー・周辺情報を取得"""
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

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    detail = hotel.hotel_detail or {}
    surrounding_data = detail.get("surrounding", {})
    return HotelStoryDetailResponse(
        story=detail.get("story", ""),
        highlights=detail.get("highlights", []),
        surrounding=HotelDetailSurrounding(
            description=surrounding_data.get("description", ""),
            attractions=[
                HotelDetailAttractionItem(
                    name=a.get("name", ""),
                    distance=a.get("distance", ""),
                )
                for a in surrounding_data.get("attractions", [])
            ],
        ),
        access=detail.get("access", ""),
    )


@router.put("/{hotel_id}/detail", response_model=HotelStoryDetailResponse)
async def update_hotel_detail(
    hotel_id: int,
    request: HotelDetailUpdateRequest,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """宿のストーリー・周辺情報を更新"""
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

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    current = dict(hotel.hotel_detail or {})
    if request.story is not None:
        current["story"] = request.story
    if request.highlights is not None:
        current["highlights"] = request.highlights
    if request.surrounding is not None:
        current["surrounding"] = {
            "description": request.surrounding.description,
            "attractions": [
                {"name": a.name, "distance": a.distance}
                for a in request.surrounding.attractions
            ],
        }
    if request.access is not None:
        current["access"] = request.access

    hotel.hotel_detail = current
    hotel.updated_at = datetime.utcnow()
    flag_modified(hotel, "hotel_detail")
    session.add(hotel)
    session.commit()
    session.refresh(hotel)

    detail = hotel.hotel_detail or {}
    surrounding_data = detail.get("surrounding", {})
    return HotelStoryDetailResponse(
        story=detail.get("story", ""),
        highlights=detail.get("highlights", []),
        surrounding=HotelDetailSurrounding(
            description=surrounding_data.get("description", ""),
            attractions=[
                HotelDetailAttractionItem(
                    name=a.get("name", ""),
                    distance=a.get("distance", ""),
                )
                for a in surrounding_data.get("attractions", [])
            ],
        ),
        access=detail.get("access", ""),
    )


class HotelAutoFillResponse(BaseModel):
    """公式サイト自動入力レスポンス"""
    highlights: List[str] = []
    surrounding: HotelDetailSurrounding = HotelDetailSurrounding()
    access: str = ""


@router.post("/{hotel_id}/detail/auto-fill", response_model=HotelAutoFillResponse)
async def auto_fill_hotel_detail(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session),
):
    """公式サイトURLからハイライト・周辺情報・アクセスを自動取得"""
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id,
        )
    ).first()

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この施設へのアクセス権限がありません",
        )

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    if not hotel.website:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公式サイトのURLが設定されていません",
        )

    result = await HotelScrapeService.scrape_hotel_info(hotel.website, hotel.name)

    surrounding_raw = result.get("surrounding", {})
    attractions = [
        HotelDetailAttractionItem(
            name=a.get("name", ""),
            distance=a.get("distance", ""),
        )
        for a in surrounding_raw.get("attractions", [])
    ]

    return HotelAutoFillResponse(
        highlights=result.get("highlights", []),
        surrounding=HotelDetailSurrounding(
            description=surrounding_raw.get("description", ""),
            attractions=attractions,
        ),
        access=result.get("access", ""),
    )


class SurroundingFromMarketResponse(BaseModel):
    """市場データから生成した周辺情報"""
    surrounding: HotelDetailSurrounding = HotelDetailSurrounding()


@router.post("/{hotel_id}/detail/fill-surrounding-from-market", response_model=SurroundingFromMarketResponse)
async def fill_surrounding_from_market(
    hotel_id: int,
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session),
):
    """市場分析データ（地域トレンド）から周辺観光情報を生成"""
    permission = session.exec(
        select(FacilityAdminHotel).where(
            FacilityAdminHotel.facility_admin_id == facility_admin.id,
            FacilityAdminHotel.hotel_id == hotel_id,
        )
    ).first()

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この施設へのアクセス権限がありません",
        )

    hotel = session.exec(select(Hotel).where(Hotel.id == hotel_id)).first()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="施設が見つかりません",
        )

    analysis = session.exec(
        select(AnalysisSession).where(AnalysisSession.hotel_id == hotel_id)
    ).first()

    if analysis is None or not analysis.regional_trends:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="市場分析データがありません。先にマーケティングAIの「市場を知る」で分析を実行してください。",
        )

    import json, re

    system_prompt = (
        "あなたは宿泊施設のマーケティング専門家です。"
        "地域トレンドの分析文から、宿泊施設の公式ウェブサイトで使えるような"
        "周辺エリアの説明文と観光スポット情報を抽出・整形してください。"
    )

    user_prompt = f"""以下は「{hotel.name}」が立地するエリアの地域トレンド分析です。

---
{analysis.regional_trends}
---

この分析文から、宿泊施設ウェブサイト向けに以下のJSON形式で周辺情報を整形してください：

{{
  "surrounding": {{
    "description": "周辺エリアを宿泊客に伝える説明文（150〜300文字程度）",
    "attractions": [
      {{"name": "観光スポット名", "distance": "目安の距離・時間（例：車で20分）"}}
    ]
  }}
}}

ルール:
- description は旅行者向けの魅力的な文章にする
- attractions は分析文中で言及されている具体的なスポット名のみ抽出（最大8件）
- 距離情報がない場合は空文字""にする
- 純粋なJSONのみを返す（コードブロック不要）"""

    try:
        llm = get_llm_client(model_name="gemini-3.1-flash-lite")
        raw = await llm.generate_structured_output(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2048,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI生成エラーが発生しました",
        )

    try:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        result = json.loads(cleaned)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI応答のパースに失敗しました",
        )

    surrounding_raw = result.get("surrounding", {})
    if not isinstance(surrounding_raw, dict):
        surrounding_raw = {}

    attractions_raw = surrounding_raw.get("attractions", [])
    if not isinstance(attractions_raw, list):
        attractions_raw = []

    attractions = [
        HotelDetailAttractionItem(
            name=str(a.get("name", "")),
            distance=str(a.get("distance", "")),
        )
        for a in attractions_raw
        if isinstance(a, dict)
    ]

    return SurroundingFromMarketResponse(
        surrounding=HotelDetailSurrounding(
            description=str(surrounding_raw.get("description", "")),
            attractions=attractions,
        )
    )


@router.post("/{hotel_id}/assets/extract-from-image", response_model=dict)
async def extract_assets_from_image(
    hotel_id: int,
    file: UploadFile = File(...),
    facility_admin: FacilityAdmin = Depends(get_current_facility_admin),
    session: Session = Depends(get_session)
):
    """
    画像から施設の資産を自動抽出
    
    - 画像（スクリーンショットなど）をアップロード
    - OCRでテキストを読み取り
    - AIが資産をカテゴリ別に分類して返却
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
    
    # ファイル形式チェック
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="画像ファイルをアップロードしてください",
        )
    
    try:
        # 画像データを読み込み
        image_data = await file.read()
        
        # LLMで画像を分析して資産を抽出
        llm_client = get_llm_client(model_name="gemini-3.1-flash-lite")
        
        system_prompt = """あなたは宿泊施設の資産を分析するエキスパートです。
画像から読み取れるテキストを元に、施設の資産をカテゴリ別に抽出してください。

【カテゴリ定義】
- room_amenities: 部屋の設備・備品（露天風呂、マッサージチェア、加湿器、コーヒーメーカー、ミニバー等）
- shared_facilities: 共有施設（大浴場、貸切風呂、サウナ、エステ、庭園、足湯、ラウンジ、プール等）
- dining: 料理・食事（会席料理、和朝食、洋朝食、バイキング、鉄板焼き、部屋食、アラカルト等）
- services: サービス（送迎、荷物預かり、ルームサービス、マッサージ、コンシェルジュ、ベビーシッター等）
- experiences: 体験・アクティビティ（陶芸体験、そば打ち体験、農業体験、釣り、クルージング、サイクリング等）

【出力ルール】
- 純粋なJSONのみを返してください（マークダウンのコードブロックは使わない）
- 各カテゴリは文字列の配列
- 画像から読み取れた内容のみを抽出（推測しない）
- 重複を除外"""

        prompt = """この画像から、宿泊施設の資産・設備・サービス情報を読み取ってください。

以下のJSON形式で出力してください：
{
    "room_amenities": ["部屋の設備1", "部屋の設備2"],
    "shared_facilities": ["共有施設1", "共有施設2"],
    "dining": ["料理1", "料理2"],
    "services": ["サービス1", "サービス2"],
    "experiences": ["体験1", "体験2"]
}

画像内に該当する情報がないカテゴリは空配列[]としてください。"""

        response = await llm_client.analyze_image(
            image_data=image_data,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=4096
        )
        
        # JSONをパース
        import json
        import re
        
        # コードブロックを除去
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()
        
        try:
            extracted_assets = json.loads(cleaned)
        except json.JSONDecodeError:
            # JSONパースに失敗した場合は空を返す
            extracted_assets = {
                "room_amenities": [],
                "shared_facilities": [],
                "dining": [],
                "services": [],
                "experiences": [],
            }
        
        # 必要なキーが存在することを保証
        default_structure = {
            "room_amenities": [],
            "shared_facilities": [],
            "dining": [],
            "services": [],
            "experiences": [],
        }
        
        for key in default_structure:
            if key not in extracted_assets or not isinstance(extracted_assets[key], list):
                extracted_assets[key] = []
        
        return extracted_assets
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"画像分析エラー: {str(e)}",
        )

