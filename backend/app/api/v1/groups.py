from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/groups", tags=["groups (sprint 5)"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="not implemented yet (sprint 5): secret santa & group rooms",
)


@router.post("", status_code=501)
async def create_group():
    raise _NOT_IMPLEMENTED


@router.get("/{group_id}", status_code=501)
async def get_group(group_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{group_id}/invite", status_code=501)
async def invite_to_group(group_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{group_id}/join", status_code=501)
async def join_group(group_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{group_id}/santa/draw", status_code=501)
async def santa_draw(group_id: str):
    raise _NOT_IMPLEMENTED


@router.get("/{group_id}/santa/my-receiver", status_code=501)
async def santa_my_receiver(group_id: str):
    raise _NOT_IMPLEMENTED