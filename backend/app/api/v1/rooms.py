from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/rooms", tags=["rooms (sprint 5)"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="not implemented yet (sprint 5): group gift selection room",
)


@router.post("", status_code=501)
async def create_room():
    raise _NOT_IMPLEMENTED


@router.get("/{room_id}", status_code=501)
async def get_room(room_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{room_id}/candidates", status_code=501)
async def add_candidate(room_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{room_id}/vote", status_code=501)
async def vote(room_id: str):
    raise _NOT_IMPLEMENTED


@router.post("/{room_id}/close", status_code=501)
async def close_room(room_id: str):
    raise _NOT_IMPLEMENTED