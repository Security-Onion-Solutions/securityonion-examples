"""Grid management routes for the Vidalia application"""
from flask import Blueprint, current_app, render_template, jsonify, request, flash
import json
import traceback

bp = Blueprint('grid', __name__)

@bp.route('/grid')
def grid_view():
    """Display grid management interface with node statuses"""
    try:
        current_app.logger.debug("Fetching grid node statuses...")
        # Get grid nodes from Security Onion API
        nodes_response = current_app.so_api.get_grid_nodes()
        current_app.logger.debug(f"Grid nodes response: {json.dumps(nodes_response, indent=2)}")
        
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
            current_app.logger.debug(f"Processing node: {json.dumps(node, indent=2)}")
            
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
            current_app.logger.debug(f"Transformed node data: {json.dumps(node_data, indent=2)}")
            nodes.append(node_data)
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'nodes': nodes})
            
        return render_template('grid/view.html', nodes=nodes)
    except Exception as e:
        current_app.logger.error(f"Error fetching grid status: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Error retrieving grid status', 'error')
        return render_template('grid/view.html', nodes=[])

@bp.route('/grid/<node_name>/reboot', methods=['POST'])
def reboot_node(node_name):
    """Trigger reboot for a specific grid node"""
    try:
        current_app.logger.debug(f"Reboot request received for node: {node_name}")
        # Get node info from grid nodes to verify ID
        nodes_response = current_app.so_api.get_grid_nodes()
        node = next((n for n in nodes_response if n.get("id") == node_name), None)
        
        if not node:
            error_msg = f"Node '{node_name}' not found in grid nodes"
            current_app.logger.error(error_msg)
            return jsonify({
                "status": "error",
                "message": error_msg
            }), 404
            
        current_app.logger.debug(f"Found matching node: {json.dumps(node, indent=2)}")
        
        # Call Security Onion API to restart node
        current_app.logger.debug(f"Initiating restart for node: {node_name}")
        current_app.so_api.restart_node(node_name)
        return jsonify({
            "status": "success",
            "message": f"Reboot initiated for node {node_name}"
        })
    except Exception as e:
        current_app.logger.error(f"Error rebooting node {node_name}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error rebooting node: {str(e)}"
        }), 500
