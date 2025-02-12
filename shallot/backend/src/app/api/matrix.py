"""Matrix integration endpoints."""
from typing import Dict, Any, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
import nio

from ..models.settings import Settings
from ..core.matrix import MatrixClient
from ..services.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Store the Matrix client instance
matrix_client: MatrixClient = None
# Store processed transaction IDs to prevent duplicate processing
processed_txns: set[str] = set()


async def get_matrix_client() -> MatrixClient:
    """Get or create Matrix client instance.
    
    Returns:
        MatrixClient: The Matrix client instance
    """
    global matrix_client
    if matrix_client is None:
        settings = await get_settings()
        matrix_client = MatrixClient(settings)
        await matrix_client.connect()
    return matrix_client


@router.put("/api/matrix/transactions/{txn_id}")
async def transactions(
    txn_id: str,
    request: Request,
    client: MatrixClient = Depends(get_matrix_client)
) -> Dict[str, Any]:
    """Handle incoming Matrix events.
    
    This endpoint receives events from the Matrix homeserver.
    Events are sent with transaction IDs to ensure exactly-once delivery.
    
    Args:
        txn_id: Unique transaction ID
        request: The incoming request containing Matrix events
        client: The Matrix client instance
        
    Returns:
        Dict containing status of event processing
        
    Raises:
        HTTPException: If event processing fails
    """
    if not client.connected:
        raise HTTPException(
            status_code=503,
            detail="Matrix client not connected"
        )

    # Check if we've already processed this transaction
    if txn_id in processed_txns:
        return {"status": "success"}  # Idempotent response

    try:
        # Get the request body
        body = await request.json()
        
        # Process each event in the transaction
        for event in body.get("events", []):
            if event.get("type") == "m.room.message":
                # Extract room ID and create RoomMessageText event
                room_id = event.get("room_id")
                if not room_id:
                    logger.warning(f"No room_id in event: {event}")
                    continue
                    
                content = event.get("content", {})
                if content.get("msgtype") != "m.text":
                    continue
                    
                # Create Matrix event object
                matrix_event = nio.RoomMessageText(
                    source=event,
                    sender=event.get("sender"),
                    room_id=room_id,
                    content=content,
                    event_id=event.get("event_id")
                )
                
                # Process the message
                await client.process_message(room_id, matrix_event)
        
        # Mark transaction as processed
        processed_txns.add(txn_id)
        # Limit size of processed transactions set
        if len(processed_txns) > 1000:
            processed_txns.clear()  # Simple cleanup strategy
            
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing Matrix transaction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Matrix transaction: {str(e)}"
        )


@router.post("/api/matrix/rooms/{room_id}/join")
async def join_room(
    room_id: str,
    client: MatrixClient = Depends(get_matrix_client)
) -> Dict[str, Any]:
    """Join a Matrix room.
    
    This endpoint allows the bot to join a room it's been invited to.
    
    Args:
        room_id: ID of the room to join
        client: The Matrix client instance
        
    Returns:
        Dict containing status of room join
        
    Raises:
        HTTPException: If joining fails
    """
    if not client.connected:
        raise HTTPException(
            status_code=503,
            detail="Matrix client not connected"
        )

    try:
        # TODO: Implement room joining in MatrixClient
        # await client.join_room(room_id)
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error joining Matrix room: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to join Matrix room: {str(e)}"
        )


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup Matrix client on shutdown."""
    global matrix_client
    if matrix_client:
        await matrix_client.disconnect()
        matrix_client = None
