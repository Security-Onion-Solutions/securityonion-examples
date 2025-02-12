import dns.resolver
import ipaddress
from typing import Optional
from ...database import AsyncSessionLocal
from ...services.chat_users import get_chat_user_by_platform_id
from ...models.chat_users import ChatService
from ...core.permissions import CommandPermission
from ...core.decorators import requires_permission
from .validation import command_validator

def is_valid_ip(ip: str) -> bool:
    """Validate IPv4 or IPv6 address format."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def format_dns_records(records: list) -> str:
    """Format DNS records into a readable string."""
    if not records:
        return "No DNS records found"
    
    formatted = []
    for record in records:
        formatted.append(str(record))
    
    output = '\n'.join(formatted)
    
    # Format output for chat display
    if not output:
        return "No DNS records found"
    
    # Final safety check - truncate if too long
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    
    formatted_output = f"```\n{output}\n```"
    return formatted_output

@requires_permission()  # Dig command permission is already defined in COMMAND_PERMISSIONS
@command_validator(required_args=1, optional_args=0)  # Requires exactly one argument: IP address
async def process(command: str, user_id: str = None, platform: ChatService = None, username: str = None, channel_id: str = None) -> str:
    """Process the dig command."""
    print(f"[DEBUG] Processing dig command for platform: {platform}, user_id: {user_id}")
    print(f"[DEBUG] Full command text: '{command}'")
    
    try:
        # Extract IP address from command
        ip_address = command.split()[1]  # Safe to access since validator ensures argument exists
        if not is_valid_ip(ip_address):
            return "Error: Invalid IP address format. Please provide a valid IPv4 or IPv6 address."
        
        try:
            # Perform reverse DNS lookup
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '8.8.4.4']  # Use Google DNS servers
            
            print(f"[DEBUG] Using nameservers: {resolver.nameservers}")
            
            # Convert IP to reverse lookup format
            reverse_ip = dns.reversename.from_address(ip_address)
            print(f"[DEBUG] Reverse IP format: {reverse_ip}")
            
            results = []
            results.append(f"; <<>> DiG 9.18 <<>> {ip_address}")
            results.append(";; global options: +cmd")
            
            # Get current time
            from datetime import datetime
            current_time = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            
            try:
                print(f"[DEBUG] Attempting lookup for {ip_address}")
                
                # First try A record
                try:
                    a_answer = resolver.resolve(ip_address, 'A')
                    
                    results.append(";; Got answer:")
                    results.append(f";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: {a_answer.response.id}")
                    results.append(f";; flags: qr rd ra; QUERY: 1, ANSWER: {len(a_answer)}, AUTHORITY: 0, ADDITIONAL: 1")
                    results.append("")
                    results.append(";; QUESTION SECTION:")
                    results.append(f";{ip_address}.                       IN      A")
                    results.append("")
                    results.append(";; ANSWER SECTION:")
                    for rdata in a_answer:
                        results.append(f"{ip_address}.                600     IN      A       {rdata}")
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    results.append(";; Got answer:")
                    results.append(";; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN, id: 0")
                    results.append(";; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 0")
                
                # Then try PTR record
                try:
                    ptr_answer = resolver.resolve(reverse_ip, 'PTR')
                    results.append("")
                    results.append(";; PTR RECORDS:")
                    for rdata in ptr_answer:
                        results.append(f"{reverse_ip}  600     IN      PTR     {rdata}")
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    results.append("")
                    results.append(";; No PTR records found")
                
                results.append("")
                results.append(f";; Query time: 0 msec")
                results.append(f";; SERVER: {resolver.nameservers[0]}#{resolver.port}({resolver.nameservers[0]}) (UDP)")
                results.append(f";; WHEN: {current_time}")
                
            except Exception as e:
                print(f"[DEBUG] Error in DNS lookup: {str(e)}")
                results.append(f";; Error: {str(e)}")
            
            output = '\n'.join(results)
            
            # Final safety check - truncate if too long
            if len(output) > 1900:
                output = output[:1900] + "\n... (truncated)"
                
            return f"```\n{output}\n```"
            
        except Exception as e:
            print(f"[DEBUG] DNS lookup failed: {str(e)}")
            return f"Error performing DNS lookup: {str(e)}"
            
    except Exception as e:
        print(f"[DEBUG] Error processing dig command: {str(e)}")
        raise
