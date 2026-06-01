import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    CaseMaterial,
    CaseMaterialCreate,
    CaseMaterialPublic,
    CaseMaterialsPublic,
    CaseMaterialUpdate,
    Message,
    Movement,
    MovementCreate,
    MovementPublic,
    MovementsPublic,
    MovementUpdate,
    TargetGender,
    TargetGenderCreate,
    TargetGenderPublic,
    TargetGendersPublic,
    TargetGenderUpdate,
    WatchStyle,
    WatchStyleCreate,
    WatchStylePublic,
    WatchStylesPublic,
    WatchStyleUpdate,
)

AdminDep = Depends(get_current_active_superuser)

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

_movements = APIRouter(prefix="/movements", dependencies=[AdminDep])


@_movements.post("/", response_model=MovementPublic)
def create_movement(*, session: SessionDep, item_in: MovementCreate) -> Any:
    item = Movement.model_validate(item_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_movements.get("/", response_model=MovementsPublic)
def read_movements(session: SessionDep) -> Any:
    count = session.exec(select(func.count()).select_from(Movement)).one()
    items = session.exec(select(Movement)).all()
    return MovementsPublic(data=list(items), count=count)


@_movements.get("/{id}", response_model=MovementPublic)
def read_movement(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(Movement, id)
    if not item:
        raise HTTPException(status_code=404, detail="Movement not found")
    return item


@_movements.put("/{id}", response_model=MovementPublic)
def update_movement(*, session: SessionDep, id: uuid.UUID, item_in: MovementUpdate) -> Any:
    item = session.get(Movement, id)
    if not item:
        raise HTTPException(status_code=404, detail="Movement not found")
    item.sqlmodel_update(item_in.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_movements.delete("/{id}", response_model=Message)
def delete_movement(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(Movement, id)
    if not item:
        raise HTTPException(status_code=404, detail="Movement not found")
    try:
        session.delete(item)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Movement is referenced by other records")
    return Message(message="Movement deleted successfully")


# ---------------------------------------------------------------------------
# CaseMaterial
# ---------------------------------------------------------------------------

_case_materials = APIRouter(prefix="/case-materials", dependencies=[AdminDep])


@_case_materials.post("/", response_model=CaseMaterialPublic)
def create_case_material(*, session: SessionDep, item_in: CaseMaterialCreate) -> Any:
    item = CaseMaterial.model_validate(item_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_case_materials.get("/", response_model=CaseMaterialsPublic)
def read_case_materials(session: SessionDep) -> Any:
    count = session.exec(select(func.count()).select_from(CaseMaterial)).one()
    items = session.exec(select(CaseMaterial)).all()
    return CaseMaterialsPublic(data=list(items), count=count)


@_case_materials.get("/{id}", response_model=CaseMaterialPublic)
def read_case_material(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(CaseMaterial, id)
    if not item:
        raise HTTPException(status_code=404, detail="CaseMaterial not found")
    return item


@_case_materials.put("/{id}", response_model=CaseMaterialPublic)
def update_case_material(*, session: SessionDep, id: uuid.UUID, item_in: CaseMaterialUpdate) -> Any:
    item = session.get(CaseMaterial, id)
    if not item:
        raise HTTPException(status_code=404, detail="CaseMaterial not found")
    item.sqlmodel_update(item_in.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_case_materials.delete("/{id}", response_model=Message)
def delete_case_material(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(CaseMaterial, id)
    if not item:
        raise HTTPException(status_code=404, detail="CaseMaterial not found")
    try:
        session.delete(item)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="CaseMaterial is referenced by other records")
    return Message(message="CaseMaterial deleted successfully")


# ---------------------------------------------------------------------------
# TargetGender
# ---------------------------------------------------------------------------

_target_genders = APIRouter(prefix="/target-genders", dependencies=[AdminDep])


@_target_genders.post("/", response_model=TargetGenderPublic)
def create_target_gender(*, session: SessionDep, item_in: TargetGenderCreate) -> Any:
    item = TargetGender.model_validate(item_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_target_genders.get("/", response_model=TargetGendersPublic)
def read_target_genders(session: SessionDep) -> Any:
    count = session.exec(select(func.count()).select_from(TargetGender)).one()
    items = session.exec(select(TargetGender)).all()
    return TargetGendersPublic(data=list(items), count=count)


@_target_genders.get("/{id}", response_model=TargetGenderPublic)
def read_target_gender(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(TargetGender, id)
    if not item:
        raise HTTPException(status_code=404, detail="TargetGender not found")
    return item


@_target_genders.put("/{id}", response_model=TargetGenderPublic)
def update_target_gender(*, session: SessionDep, id: uuid.UUID, item_in: TargetGenderUpdate) -> Any:
    item = session.get(TargetGender, id)
    if not item:
        raise HTTPException(status_code=404, detail="TargetGender not found")
    item.sqlmodel_update(item_in.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_target_genders.delete("/{id}", response_model=Message)
def delete_target_gender(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(TargetGender, id)
    if not item:
        raise HTTPException(status_code=404, detail="TargetGender not found")
    try:
        session.delete(item)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="TargetGender is referenced by other records")
    return Message(message="TargetGender deleted successfully")


# ---------------------------------------------------------------------------
# WatchStyle
# ---------------------------------------------------------------------------

_watch_styles = APIRouter(prefix="/watch-styles", dependencies=[AdminDep])


@_watch_styles.post("/", response_model=WatchStylePublic)
def create_watch_style(*, session: SessionDep, item_in: WatchStyleCreate) -> Any:
    item = WatchStyle.model_validate(item_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_watch_styles.get("/", response_model=WatchStylesPublic)
def read_watch_styles(session: SessionDep) -> Any:
    count = session.exec(select(func.count()).select_from(WatchStyle)).one()
    items = session.exec(select(WatchStyle)).all()
    return WatchStylesPublic(data=list(items), count=count)


@_watch_styles.get("/{id}", response_model=WatchStylePublic)
def read_watch_style(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(WatchStyle, id)
    if not item:
        raise HTTPException(status_code=404, detail="WatchStyle not found")
    return item


@_watch_styles.put("/{id}", response_model=WatchStylePublic)
def update_watch_style(*, session: SessionDep, id: uuid.UUID, item_in: WatchStyleUpdate) -> Any:
    item = session.get(WatchStyle, id)
    if not item:
        raise HTTPException(status_code=404, detail="WatchStyle not found")
    item.sqlmodel_update(item_in.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@_watch_styles.delete("/{id}", response_model=Message)
def delete_watch_style(session: SessionDep, id: uuid.UUID) -> Any:
    item = session.get(WatchStyle, id)
    if not item:
        raise HTTPException(status_code=404, detail="WatchStyle not found")
    try:
        session.delete(item)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="WatchStyle is referenced by other records")
    return Message(message="WatchStyle deleted successfully")


# Register all sub-routers
router.include_router(_movements)
router.include_router(_case_materials)
router.include_router(_target_genders)
router.include_router(_watch_styles)
