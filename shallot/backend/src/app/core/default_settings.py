"""Default application settings."""
import json
from ..schemas.settings import SettingCreate

DEFAULT_SETTINGS = [
    SettingCreate(
        key="system",
        value=json.dumps({
            "debugLogging": False
        }),
        description="System-wide settings"
    ),
    SettingCreate(
        key="SECURITY_ONION",
        value=json.dumps({
            "apiUrl": "",
            "clientId": "",
            "clientSecret": "",
            "pollInterval": 60,
            "verifySSL": True
        }),
        description="Security Onion integration settings"
    ),
    SettingCreate(
        key="SLACK",
        value=json.dumps({
            "enabled": False,
            "botToken": "",
            "signingSecret": "",
            "commandPrefix": "!",
            "requireApproval": True,
            "alertNotifications": False,
            "alertChannel": ""
        }),
        description="Slack integration settings"
    ),
    SettingCreate(
        key="DISCORD",
        value=json.dumps({
            "enabled": False,
            "botToken": "",
            "commandPrefix": "!",
            "requireApproval": True,
            "alertNotifications": False,
            "alertChannel": ""
        }),
        description="Discord integration settings"
    ),
    SettingCreate(
        key="MATRIX",
        value=json.dumps({
            "enabled": False,
            "homeserverUrl": "",
            "userId": "",
            "accessToken": "",
            "deviceId": "",
            "commandPrefix": "!",
            "requireApproval": True,
            "alertNotifications": False,
            "alertRoom": ""
        }),
        description="Matrix integration settings"
    )
]
