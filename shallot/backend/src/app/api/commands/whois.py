# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import whois
import ipaddress
from typing import Optional, Union
from ...database import AsyncSessionLocal
from ...services.chat_users import get_chat_user_by_platform_id
from ...models.chat_users import ChatService
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from .validation import command_validator

def is_valid_ip(ip: str) -> bool:
    """Validate IPv4 or IPv6 address format."""
    try:
        # This will validate both IPv4 and IPv6 addresses
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def get_ip_version(ip: str) -> Optional[int]:
    """Get IP version (4 or 6) for a valid IP address."""
    try:
        return ipaddress.ip_address(ip).version
    except ValueError:
        return None

def format_whois_info(w) -> str:
    """Format WHOIS information into a readable string."""
    if not w:
        return "No WHOIS information found"
    
    # Priority fields to always include if available
    priority_fields = [
        'domain_name', 'registrar', 'org', 'name', 'country',
        'creation_date', 'expiration_date', 'name_servers'
    ]
    
    info = []
    
    # First add priority fields
    for field in priority_fields:
        if hasattr(w, field) and getattr(w, field):
            value = getattr(w, field)
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            info.append(f"{field}: {value}")
    
    # Then add any remaining fields that have values
    for attr in dir(w):
        if (attr not in priority_fields and 
            not attr.startswith('_') and 
            not callable(getattr(w, attr)) and
            attr != 'text'):
            value = getattr(w, attr)
            if value:
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value)
                info.append(f"{attr}: {value}")
    
    # Get the formatted output
    output = '\n'.join(info)
    
    # If we still have room, add some of the raw text
    if hasattr(w, 'text') and w.text:
        remaining_length = 1900 - len(output)  # Leave some buffer
        if remaining_length > 100:  # Only add if we have reasonable space
            # Filter out commented lines and empty lines from raw text
            raw_lines = w.text.split('\n')
            filtered_lines = [line for line in raw_lines 
                            if line.strip() and  # Skip empty lines
                            not line.strip().startswith('#') and  # Skip comments
                            not line.strip().startswith('%') and  # Skip % comments
                            not line.strip().startswith(';')]  # Skip ; comments
            raw_excerpt = '\n'.join(filtered_lines)[:remaining_length]
            output += f"\n\nRaw WHOIS Data (truncated):\n{raw_excerpt}"
    
    # Final safety check - truncate if still too long
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    
    # Format output based on platform
    if not output:
        return "No WHOIS information found"
    
    formatted_output = f"```\n{output}\n```"
    return formatted_output

@requires_permission()  # Whois command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=1, optional_args=0)  # Requires exactly one argument: IP address
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the whois command."""
    print(f"[DEBUG] Processing whois command for platform: {platform}, user_id: {user_id}")
    print(f"[DEBUG] Full command text: '{command}'")
    
    try:
        # Extract IP address from command
        ip_address = command.split()[1]  # Safe to access since validator ensures argument exists
        if not is_valid_ip(ip_address):
            return "Error: Invalid IP address format. Please provide a valid IPv4 or IPv6 address."
        
        try:
            # Perform WHOIS lookup
            w = whois.whois(ip_address)
            return format_whois_info(w)
        except Exception as e:
            print(f"[DEBUG] WHOIS lookup failed: {str(e)}")
            return f"Error performing WHOIS lookup: {str(e)}"
            
    except Exception as e:
        print(f"[DEBUG] Error processing whois command: {str(e)}")
        raise
