# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from contextlib import asynccontextmanager
from typing import Dict, Any, AsyncGenerator
import asyncio
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all permission check details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to DEBUG level
logging.getLogger('app.core.decorators').setLevel(logging.DEBUG)
logging.getLogger('app.services.chat_users').setLevel(logging.DEBUG)

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .api import api_router
from .database import (
    get_db,
    init_db,
    close_db,
    AsyncSessionLocal,
)
from . import models  # Import all models to register with SQLAlchemy
from .models.settings import Settings  # Import Settings model explicitly
from .schemas.settings import SettingCreate
from .services.settings import ensure_required_settings
from .api.settings import init_default_settings
from .services.users import get_user_count
from .core.securityonion import client as so_client
from .core.discord import client as discord_client
from .core.slack import client as slack_client
from .core.matrix import client as matrix_client
from .core.logging import debug_log

from .core.default_settings import DEFAULT_SETTINGS


async def refresh_so_token():
    """Background task to refresh Security Onion API token before expiration."""
    while True:
        try:
            # Only attempt refresh if we have a token and expiration time
            if so_client._access_token and so_client._token_expires:
                # Calculate time until expiration
                time_until_expiry = so_client._token_expires - datetime.utcnow()
                
                # If token expires in less than 10 minutes, refresh it
                if time_until_expiry < timedelta(minutes=10):
                    await debug_log("Token expiring soon, refreshing...")
                    await so_client._ensure_token()
                else:
                    # Sleep until 10 minutes before expiration
                    sleep_time = (time_until_expiry - timedelta(minutes=10)).total_seconds()
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                        continue
            
            # If no token or invalid expiration, check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"[ERROR] Token refresh failed: {str(e)}")  # Keep errors as regular prints
            await asyncio.sleep(60)  # Wait a minute before retrying


async def check_new_alerts():
    """Background task to check for new alerts."""
    while True:
        try:
            await debug_log("Checking for new alerts...")
            # Get current time for date range in UTC
            now = datetime.utcnow()
            time_60s_ago = now - timedelta(seconds=60)
            
            # Format parameters for Security Onion API
            query_params = {
                "query": "tags:alert AND NOT event.acknowledged:true",  # Only unacknowledged alerts
                "range": f"{time_60s_ago.strftime('%Y/%m/%d %I:%M:%S %p')} - {now.strftime('%Y/%m/%d %I:%M:%S %p')}",
                "zone": "UTC",  # Timezone for the range
                "format": "2006/01/02 3:04:05 PM",  # Time format specification
                "fields": "*",  # Request all fields to ensure we get everything we need
                "metricLimit": 10000,  # Number as int, not string
                "eventLimit": 10000,  # Number as int, not string
                "sort": "@timestamp:desc"  # Newest first
            }
            
            # Query alerts from Security Onion
            base_url = so_client._base_url.rstrip('/') + '/'
            await debug_log(f"Making request to: {base_url}connect/events")
            await debug_log(f"With headers: {so_client._get_headers()}")
            await debug_log(f"With params: {query_params}")
            
            try:
                response = await so_client._client.get(
                    f"{base_url}connect/events",
                    headers=so_client._get_headers(),
                    params=query_params
                )
                await debug_log(f"Got response with status: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] Failed to make request: {str(e)}")
                
            if response.status_code == 200:
                try:
                    data = response.json()
                    await debug_log(f"Security Onion API response data: {json.dumps(data, indent=2)}")
                    events = data.get('events', [])
                    await debug_log(f"Found {len(events)} events")
                    
                    alerts = []
                    if not events:
                        await debug_log("No new alerts found")
                    else:
                        for event in events:
                            payload = event.get('payload', {})
                            await debug_log(f"Processing event payload: {json.dumps(payload, indent=2)}")
                            message_str = payload.get('message', '{}')
                            try:
                                message = json.loads(message_str)
                                await debug_log(f"Parsed message: {json.dumps(message, indent=2)}")
                                alert_data = message.get('alert', {})
                                if alert_data:
                                    await debug_log("Found alert data in message")
                                    severity_label = payload.get('event.severity_label', 'UNKNOWN')
                                    alerts.append({
                                        'name': alert_data.get('signature', 'Untitled Alert'),
                                        'severity_label': severity_label,
                                        'ruleid': alert_data.get('signature_id', 'Unknown'),
                                        'eventid': payload.get('log.id.uid', 'Unknown'),
                                        'source_ip': message.get('src_ip', 'Unknown'),
                                        'source_port': str(message.get('src_port', 'Unknown')),
                                        'destination_ip': message.get('dest_ip', 'Unknown'),
                                        'destination_port': str(message.get('dest_port', 'Unknown')),
                                        'observer_name': payload['observer.name'] if 'observer.name' in payload else 'Unknown',
                                        'timestamp': event.get('@timestamp') or
                                                   event.get('timestamp') or
                                                   payload.get('@timestamp') or
                                                   payload.get('timestamp') or
                                                   'Unknown'
                                    })
                            except json.JSONDecodeError:
                                await debug_log("Failed to parse message JSON")
                                continue
                    
                    if alerts:
                        # Format alerts for notification
                        await debug_log(f"Found {len(alerts)} new alert(s), preparing to send notifications...")
                        
                        # Split alerts into chunks of 10 to avoid message length limits
                        chunk_size = 10
                        for i in range(0, len(alerts), chunk_size):
                            chunk = alerts[i:i + chunk_size]
                            alert_lines = [f"🚨 Alerts {i+1}-{i+len(chunk)} of {len(alerts)} from the last 60 seconds:"]
                            
                            for alert in chunk:
                                alert_lines.extend([
                                    "",  # Blank line between alerts
                                    f"[{alert['severity_label']}] - {alert['name']}",
                                    f"  ruleid: {alert['ruleid']}",
                                    f"  eventid: {alert['eventid']}",
                                    f"  source: {alert['source_ip']}:{alert['source_port']}",
                                    f"  destination: {alert['destination_ip']}:{alert['destination_port']}",
                                    f"  observer.name: {alert['observer_name']}",
                                    f"  timestamp: {alert['timestamp']}"
                                ])
                            
                            alert_text = "\n".join(alert_lines)
                            
                            # Send to Discord if enabled
                            if discord_client._enabled:
                                await debug_log(f"Sending chunk {i//chunk_size + 1} to Discord...")
                                if await discord_client.send_alert(alert_text):
                                    await debug_log(f"Successfully sent chunk {i//chunk_size + 1} to Discord")
                                else:
                                    await debug_log(f"Failed to send chunk {i//chunk_size + 1} to Discord")
                            
                            # Send to Slack if enabled
                            if slack_client._enabled:
                                await debug_log(f"Sending chunk {i//chunk_size + 1} to Slack...")
                                if await slack_client.send_alert(alert_text):
                                    await debug_log(f"Successfully sent chunk {i//chunk_size + 1} to Slack")
                                else:
                                    await debug_log(f"Failed to send chunk {i//chunk_size + 1} to Slack")
                                    
                            # Send to Matrix if enabled
                            if matrix_client._enabled:
                                await debug_log(f"Sending chunk {i//chunk_size + 1} to Matrix...")
                                if await matrix_client.send_alert(alert_text):
                                    await debug_log(f"Successfully sent chunk {i//chunk_size + 1} to Matrix")
                                else:
                                    await debug_log(f"Failed to send chunk {i//chunk_size + 1} to Matrix")
                                    
                except Exception as e:
                    print(f"[ERROR] Failed to process response: {str(e)}")
            else:
                print(f"[ERROR] Bad response status: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Alert check failed: {str(e)}")
        
        await asyncio.sleep(60)  # Wait 60 seconds before next check


async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    # Startup
    await init_db()
    
    # Initialize Security Onion client first
    try:
        print("Initializing Security Onion client...")
        await so_client.initialize()
        print("Security Onion client initialized successfully")
        
        # Only start background tasks if Security Onion is properly connected
        if so_client._connected:
            print("Security Onion connected, starting background tasks...")
            alert_task = asyncio.create_task(check_new_alerts())
            token_refresh_task = asyncio.create_task(refresh_so_token())
        else:
            print("Security Onion not configured/connected, skipping background tasks")
            alert_task = None
            token_refresh_task = None
    except Exception as e:
        print(f"Error initializing Security Onion client: {str(e)}")
        alert_task = None
        token_refresh_task = None
        
    # Initialize Discord client
    try:
        print("Initializing Discord client...")
        await discord_client.initialize()
        print("Discord client initialized successfully")
    except Exception as e:
        print(f"Error initializing Discord client: {str(e)}")
        
    # Initialize Slack client
    try:
        print("Initializing Slack client...")
        await slack_client.initialize()
        print("Slack client initialized successfully")
    except Exception as e:
        print(f"Error initializing Slack client: {str(e)}")
        
    # Initialize Matrix client
    try:
        print("Initializing Matrix client...")
        await matrix_client.initialize()
        print("Matrix client initialized successfully")
    except Exception as e:
        print(f"Error initializing Matrix client: {str(e)}")
    
    # Initialize settings using a new session
    async with AsyncSessionLocal() as db:
        try:
            print("Initializing default settings...")
            try:
                print("\nInitializing default settings...")
                # Initialize all settings from default_settings.py
                await init_default_settings(db)
                print("Default settings initialized successfully")
                
                # Verify settings were created
                result = await db.execute(text("SELECT key FROM settings"))
                settings = result.fetchall()
                print(f"Current settings in database: {[s[0] for s in settings]}")
                
                # Verify each required setting exists
                from .core.default_settings import DEFAULT_SETTINGS
                required_keys = {s.key for s in DEFAULT_SETTINGS}
                existing_keys = {s[0] for s in settings}
                missing_keys = required_keys - existing_keys
                if missing_keys:
                    print(f"Warning: Missing settings: {missing_keys}")
                    # Try to create missing settings
                    for setting in DEFAULT_SETTINGS:
                        if setting.key in missing_keys:
                            print(f"Creating missing setting: {setting.key}")
                            await init_default_settings(db)
                else:
                    print("All required settings exist")
            except Exception as e:
                print(f"Error during settings initialization: {str(e)}")
                raise
            
            # Check if any users exist
            user_count = await get_user_count(db)
            if user_count == 0:
                print("\n" + "="*80)
                print("No users exist in the database.")
                print("Create the first superuser by making a POST request to /auth/first-user")
                print("Example:")
                print('  curl -X POST http://localhost:8000/auth/first-user \\')
                print('    -H "Content-Type: application/json" \\')
                print('    -d \'{"username": "admin", "password": "password123"}\'')
                print("="*80 + "\n")
            
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    
    yield
    
    # Shutdown
    if alert_task and token_refresh_task:
        alert_task.cancel()  # Cancel the alert checking task
        token_refresh_task.cancel()  # Cancel the token refresh task
        try:
            await alert_task
            await token_refresh_task
        except asyncio.CancelledError:
            pass
    
    await close_db()
    await so_client.close()
    await discord_client.close()
    await slack_client.close()
    await matrix_client.close()


app = FastAPI(
    title="Security Onion Chat Bot",
    description="A chat bot interface for Security Onion",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://localhost:3000"],  # Frontend development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"status": "ok", "message": "Security Onion Chat Bot API"}
