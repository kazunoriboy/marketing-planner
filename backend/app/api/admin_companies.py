"""企業グループ管理API（システムアドミン用）"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.database import get_session
from app.models import SystemAdmin, Company, FacilityAdmin
from app.auth.dependencies import get_current_system_admin

router = APIRouter(prefix="/admin/companies", tags=["Admin Company Management"])


class CompanyCreateRequest(BaseModel):
    """企業グループ作成リクエスト"""
    name: str


class CompanyUpdateRequest(BaseModel):
    """企業グループ更新リクエスト"""
    name: str


class CompanyResponse(BaseModel):
    """企業グループレスポンス"""
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanyDetailResponse(CompanyResponse):
    """企業グループ詳細レスポンス（管理者情報含む）"""
    admin_count: int = 0
    admins: List[dict] = []


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    企業グループ一覧を取得
    
    - ページネーション対応
    """
    query = select(Company).offset(skip).limit(limit)
    companies = session.exec(query).all()
    
    return [CompanyResponse(
        id=c.id,
        name=c.name,
        created_at=c.created_at,
        updated_at=c.updated_at,
    ) for c in companies]


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    request: CompanyCreateRequest,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    企業グループを作成
    """
    # 企業グループ作成
    company = Company(
        name=request.name,
    )
    
    session.add(company)
    session.commit()
    session.refresh(company)
    
    return CompanyResponse(
        id=company.id,
        name=company.name,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: int,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    企業グループ詳細を取得
    
    - 紐付けられた管理者情報も含む
    """
    company = session.exec(
        select(Company).where(Company.id == company_id)
    ).first()
    
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="企業グループが見つかりません",
        )
    
    # 紐付けられた管理者を取得
    admins = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.company_id == company_id)
    ).all()
    
    admin_list = []
    for admin in admins:
        admin_list.append({
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "is_active": admin.is_active,
        })
    
    return CompanyDetailResponse(
        id=company.id,
        name=company.name,
        created_at=company.created_at,
        updated_at=company.updated_at,
        admin_count=len(admin_list),
        admins=admin_list,
    )


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    request: CompanyUpdateRequest,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    企業グループを更新
    """
    company = session.exec(
        select(Company).where(Company.id == company_id)
    ).first()
    
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="企業グループが見つかりません",
        )
    
    # 更新
    company.name = request.name
    company.updated_at = datetime.utcnow()
    
    session.add(company)
    session.commit()
    session.refresh(company)
    
    return CompanyResponse(
        id=company.id,
        name=company.name,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    _admin: SystemAdmin = Depends(get_current_system_admin)
):
    """
    企業グループを削除
    
    - 紐付けられた管理者のcompany_idはNULLになる
    """
    company = session.exec(
        select(Company).where(Company.id == company_id)
    ).first()
    
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="企業グループが見つかりません",
        )
    
    # 紐付けられた管理者のcompany_idをNULLに設定
    admins = session.exec(
        select(FacilityAdmin).where(FacilityAdmin.company_id == company_id)
    ).all()
    
    for admin in admins:
        admin.company_id = None
        admin.updated_at = datetime.utcnow()
        session.add(admin)
    
    # 企業グループを削除
    session.delete(company)
    session.commit()
