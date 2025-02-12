from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum
from ..models.chat_users import ChatUserRole
from ..core.permissions import CommandPermission, COMMAND_PERMISSIONS

PlatformType = Literal["DISCORD", "SLACK", "MATRIX", "TEAMS"]  # Must match ChatService enum values

class CommandType(str, Enum):
    ALERTS = "alerts"
    HELP = "help"
    STATUS = "status"
    REGISTER = "register"
    ACK = "ack"
    DETECTIONS = "detections"
    HUNT = "hunt"
    ESCALATE = "escalate"
    WHOIS = "whois"
    DIG = "dig"

class Command(BaseModel):
    name: str = Field(..., description="The name of the command (e.g. alerts)")
    description: str = Field(..., description="Description of what the command does")
    permission: CommandPermission = Field(default=CommandPermission.ADMIN, description="Permission level required to execute this command")
    example: str = Field(..., description="Example usage of the command")
    platforms: Optional[List[PlatformType]] = Field(None, description="List of platforms this command is available on. If None, available on all platforms.")

    class Config:
        validate_assignment = True
        
    def __init__(self, **data):
        if 'permission' not in data:
            # Get permission from COMMAND_PERMISSIONS
            data['permission'] = COMMAND_PERMISSIONS.get(
                data.get('name', ''), 
                CommandPermission.ADMIN
            )
        super().__init__(**data)

class CommandTestRequest(BaseModel):
    command: str = Field(..., description="The command to test (e.g. !alerts)")
    platform: PlatformType = Field("DISCORD", description="The platform to test the command for")

class CommandTestResponse(BaseModel):
    command: str = Field(..., description="The command that was tested")
    response: str = Field(..., description="The simulated response from the bot")
    success: bool = Field(..., description="Whether the command was processed successfully")

class CommandListResponse(BaseModel):
    commands: List[Command] = Field(..., description="List of available commands")

def create_command(name: str, description: str, example: str) -> Command:
    """Helper function to create Command objects with proper permission handling"""
    return Command(
        name=name,
        description=description,
        permission=COMMAND_PERMISSIONS.get(name, CommandPermission.ADMIN),
        example=example
    )

AVAILABLE_COMMANDS = [
    create_command(
        name="escalate",
        description="Create a case from an event and include related events from the last 24 hours (max 100 events)",
        example="!escalate <eventid> [case title]"
    ),
    create_command(
        name="hunt",
        description="Search for related events using network community ID",
        example="!hunt <eventid>"
    ),
    create_command(
        name="detections",
        description="Manage detection rules: enable/disable rules, view summaries, or add suppressions by IP/CIDR for source/destination traffic",
        example="!detections <enable|disable|summary|suppress> <publicid> [by_src|by_dst|by_either] [ip|cidr]"
    ),
    create_command(
        name="ack",
        description="Acknowledge an alert by event ID",
        example="!ack <eventid>"
    ),
    create_command(
        name="alerts",
        description="Get recent security alerts from Security Onion",
        example="!alerts"
    ),
    create_command(
        name="help",
        description="Show available commands based on user role",
        example="!help"
    ),
    create_command(
        name="status",
        description="Check system operational status",
        example="!status"
    ),
    create_command(
        name="register",
        description="Register as a new user",
        example="!register"
    ),
    create_command(
        name="whois",
        description="Look up detailed information about an IP address",
        example="!whois 8.8.8.8"
    ),
    create_command(
        name="dig",
        description="Perform DNS lookups for an IP address to find associated hostnames",
        example="!dig 8.8.8.8"
    )
]
