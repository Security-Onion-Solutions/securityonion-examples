"""Grid management routes for the Vidalia application"""
import requests
from flask import Blueprint, render_template, jsonify, request, flash, current_app
from src.config import get_api_client
import json
import logging
import traceback

logger = logging.getLogger(__name__)

bp = Blueprint('grid', __name__, url_prefix='/grid')

@bp.route('/')
def grid_view():
    """Display grid management interface with node statuses"""
    try:
        logger.debug("Fetching grid node statuses...")
        # Get grid nodes from Security Onion API
        api_client = get_api_client()
        nodes_response = api_client.get_grid_nodes()
        logger.debug(f"Grid nodes response: {json.dumps(nodes_response, indent=2)}")
        
        # Transform API response into template-friendly format
        nodes = []
        for node in nodes_response:
            # Map API status to UI status (healthy, warning, error)
            raw_status = node.get("status", "unknown").lower()
            needs_reboot = node.get("osNeedsRestart", 0) == 1
            
            # If node needs reboot, mark as warning regardless of status
            if needs_reboot:
                status = "warning"
            # Otherwise map based on raw status
            elif raw_status == "ok":
                status = "healthy"
            elif raw_status in ["degraded", "warning"]:
                status = "warning"
            elif raw_status in ["error", "failed", "critical"]:
                status = "error"
            else:
                status = "error"  # Default to error for unknown states
                
            # Convert uptime seconds to readable format
            uptime_seconds = node.get("osUptimeSeconds", 0)
            days = uptime_seconds // (24 * 3600)
            remaining = uptime_seconds % (24 * 3600)
            hours = remaining // 3600
            uptime = f"{days}d {hours}h"
            
            # Log raw node data for debugging
            logger.debug(f"Processing node: {json.dumps(node, indent=2)}")
            
            node_data = {
                "name": node.get("id", "unknown"),
                "status": status,
                "last_check": node.get("updateTime"),
                "uptime": uptime,
                "needs_reboot": node.get("osNeedsRestart", 0) == 1,
                "cpu_used": f"{node.get('cpuUsedPct', 0):.1f}%",
                "memory_used": f"{node.get('memoryUsedPct', 0):.1f}%",
                "disk_used": f"{node.get('diskUsedRootPct', 0):.1f}%"
            }
            logger.debug(f"Transformed node data: {json.dumps(node_data, indent=2)}")
            nodes.append(node_data)
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'nodes': nodes})
            
        return render_template('grid/view.html', nodes=nodes)
    except Exception as e:
        error_msg = 'Error retrieving grid status'
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 405:
                error_msg = 'Grid management is not configured on the server'
            elif e.response.status_code == 401:
                error_msg = 'Authentication failed'
            elif e.response.status_code == 403:
                error_msg = 'Insufficient permissions'
            elif e.response.status_code == 500:
                error_msg = 'Error retrieving grid status from server'
            else:
                error_msg = f'Error retrieving grid status: {str(e)}'
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(error_msg, 'danger')  # Use Bootstrap danger class for errors
        return render_template('grid/view.html', nodes=[])

@bp.route('/<node_name>/reboot', methods=['POST'])
def reboot_node(node_name):
    """Trigger reboot for a specific grid node"""
    logger.debug(f"Reboot request received for node: {node_name}")
    api_client = get_api_client()
    
    try:
        # Call Security Onion API to restart node
        logger.debug(f"Initiating restart for node: {node_name}")
        api_client.restart_node(node_name)
        
        return jsonify({
            "status": "success",
            "message": f"Reboot initiated for node {node_name}"
        })
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Error rebooting node: {str(e)}"
        if e.response.status_code == 405:
            error_msg = "Grid management is not configured on the server"
        elif e.response.status_code == 401:
            error_msg = "Authentication failed"
        elif e.response.status_code == 403:
            error_msg = "Insufficient permissions"
        elif e.response.status_code == 404:
            error_msg = f"Node '{node_name}' not found"
        elif e.response.status_code == 500:
            error_msg = "Server error while rebooting node"
        
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
        return jsonify({
            "status": "error",
            "message": error_msg
        }), e.response.status_code
        
    except Exception as e:
        error_msg = f"Error rebooting node: {str(e)}"
        logger.error(f"{error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 500
