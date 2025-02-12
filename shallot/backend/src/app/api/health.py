# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

"""Health check endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_db
from ..core.securityonion import client as so_client
from ..core.discord import client as discord_client
from ..core.slack import client as slack_client
from ..core.matrix import client as matrix_client

router = APIRouter()

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check endpoint."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Get Security Onion status
    so_status = so_client.get_status()

    return {
        "status": "ok",
        "version": "0.1.0",
        "database": db_status,
        "security_onion": so_status,
        "DISCORD": discord_client.get_status(),
        "SLACK": slack_client.get_status(),
        "MATRIX": matrix_client.get_status(),
    }
