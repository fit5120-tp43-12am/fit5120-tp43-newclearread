# This file contains a simple test endpoint used to check that the API is running.

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/test")
def test():
    """
    GET /api/test

    Returns a short message to confirm the API server is up and reachable.

    Returns:
        dict: a fixed JSON message
    """
    return {"message": "Hello from API router!"}
