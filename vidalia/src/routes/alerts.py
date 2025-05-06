"""Alert routes for the Vidalia application"""
from flask import Blueprint, current_app, render_template, jsonify, send_file, request, make_response
from io import BytesIO
from datetime import datetime, timedelta
import json
import traceback
import requests

bp = Blueprint('alerts', __name__)

@bp.app_template_filter('from_json')
def from_json(value):
    """Template filter to parse JSON string"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}

def _parse_alert_message(message: str) -> None:
    """Parse and log alert message content"""
    if not message:
        return
        
    try:
        parsed_message = json.loads(message)
        current_app.logger.debug(f"Parsed Message: {json.dumps(parsed_message, indent=2)}")
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Failed to parse message: {e}")

@bp.route('/alerts')
def list_alerts():
    """Display list of alerts with PCAP download options"""
    try:
        current_app.logger.debug("Attempting to fetch alerts from Security Onion API...")
        current_app.logger.debug(f"Using API URL: {current_app.config['SO_API_URL']}")
        current_app.logger.debug(f"Using client ID: {current_app.config['SO_CLIENT_ID']}")
        raw_alerts = current_app.so_api.get_alerts()
        current_app.logger.debug(f"Successfully fetched alerts: {json.dumps(raw_alerts, indent=2)}")
        current_app.logger.debug(f"Raw API Response: {json.dumps(raw_alerts, indent=2)}")
        
        # Check if JSON is requested
        if request.headers.get('Accept') == 'application/json':
            response = jsonify(raw_alerts)
        else:
            # Pass raw alerts directly to template
            response = make_response(render_template('alerts/list.html', alerts=raw_alerts))
            
        # Disable caching to ensure fresh data
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        current_app.logger.error(f"Error fetching alerts: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('errors/500.html'), 500

def _create_job_data(alert: dict) -> dict:
    """Create PCAP job data from alert"""
    # Get timestamp from alert
    timestamp_str = alert.get('timestamp', '')
    if not timestamp_str:
        raise ValueError("Alert missing required timestamp")
        
    # Handle different timestamp formats
    try:
        if 'Z' in timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        current_app.logger.error(f"Failed to parse timestamp: {timestamp_str}")
        raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e
    
    start_time = timestamp - timedelta(minutes=5)
    end_time = timestamp + timedelta(minutes=5)
    
    # Get network info from payload
    payload = alert.get('payload', {})
    
    # Try to get info from message JSON first, then fall back to direct payload fields
    try:
        message = json.loads(payload.get('message', '{}'))
        source_info = {
            "ip": message.get('src_ip', payload.get('source.ip', '')),
            "port": message.get('src_port', payload.get('source.port', ''))
        }
        destination_info = {
            "ip": message.get('dest_ip', payload.get('destination.ip', '')),
            "port": message.get('dest_port', payload.get('destination.port', ''))
        }
        network_info = {
            "transport": message.get('proto', payload.get('network.transport', '')),
            "packet_source": message.get('pkt_src', payload.get('network.packet_source', ''))
        }
    except (json.JSONDecodeError, TypeError):
        current_app.logger.error("Failed to parse message JSON, using direct payload fields")
        source_info = {
            "ip": payload.get('source.ip', ''),
            "port": payload.get('source.port', '')
        }
        destination_info = {
            "ip": payload.get('destination.ip', ''),
            "port": payload.get('destination.port', '')
        }
        network_info = {
            "transport": payload.get('network.transport', ''),
            "packet_source": payload.get('network.packet_source', '')
        }
    
    current_app.logger.debug(f"Source info: {json.dumps(source_info, indent=2)}")
    current_app.logger.debug(f"Destination info: {json.dumps(destination_info, indent=2)}")
    current_app.logger.debug(f"Network info: {json.dumps(network_info, indent=2)}")
    
    # Get sensor information - try both nested and direct fields
    sensor_name = payload.get('observer.name', '')
        
    if not sensor_name:
        current_app.logger.error("Failed to find sensor information")
        current_app.logger.error("Alert data structure:")
        current_app.logger.error(json.dumps(alert, indent=2))
        current_app.logger.error("Payload data:")
        current_app.logger.error(json.dumps(payload, indent=2))
        raise ValueError("Alert missing required sensor information (observer.name). Check logs for alert structure.")
        
    current_app.logger.debug(f"Using sensor: {sensor_name}")
        
    return {
        "type": "pcap",  # Specify job type
        "nodeId": sensor_name,  # Use sensor name as nodeId
        "sensorId": sensor_name,  # Use sensor name as sensorId
        "filter": {
            "importId": "",  # Required by API
            "beginTime": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),  # Format time as ISO8601
            "endTime": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "srcIp": source_info["ip"],
            "dstIp": destination_info["ip"],
            "srcPort": int(source_info["port"]) if source_info["port"] else None,  # Convert port to integer
            "dstPort": int(destination_info["port"]) if destination_info["port"] else None,  # Convert port to integer
            "protocol": network_info["transport"].lower() if network_info["transport"] else None,  # Use transport field
            "parameters": {}  # Required by API
        }
    }

@bp.route('/alerts/<alert_id>/pcap/job', methods=['POST'])
def create_pcap_job(alert_id):
    """Create and download PCAP for a specific alert"""
    try:
        # Get raw alert details
        raw_alerts = current_app.so_api.get_alerts()
        
        # Log all alerts for debugging
        current_app.logger.debug("All alerts:")
        for idx, a in enumerate(raw_alerts):
            current_app.logger.debug(f"Alert {idx}:")
            current_app.logger.debug(json.dumps(a, indent=2))
            if "_source" in a:
                current_app.logger.debug(f"Alert {idx} _source:")
                current_app.logger.debug(json.dumps(a["_source"], indent=2))
        
        # Find alert by _id or id
        alert = next((a for a in raw_alerts if str(a.get('_id', a.get('id', ''))) == alert_id), None)
        
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
            
        # Log specific alert data
        current_app.logger.debug("Selected alert data structure:")
        current_app.logger.debug(json.dumps(alert, indent=2))
        if "_source" in alert:
            current_app.logger.debug("Alert _source:")
            current_app.logger.debug(json.dumps(alert["_source"], indent=2))
        
        # Create job data from alert
        job_data = _create_job_data(alert)
        current_app.logger.debug(f"Creating PCAP job with data: {json.dumps(job_data, indent=2)}")
        
        # Create PCAP job
        job_id = current_app.so_api.create_pcap_job(job_data)
        current_app.logger.debug(f"Created PCAP job with ID: {job_id}")
    
        # Return job ID for status polling
        return jsonify({
            "status": "pending",
            "message": "PCAP job created",
            "job_id": job_id
        }), 202
    except Exception as e:
        current_app.logger.error(f"Error in PCAP job creation: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            response = e.response
            current_app.logger.error(f"HTTP Error Status: {response.status_code}")
            current_app.logger.error(f"Response Headers: {dict(response.headers)}")
            current_app.logger.error(f"Response Content: {response.text}")
        return jsonify({"error": str(e)}), 500

@bp.route('/alerts/<alert_id>/pcap/status/<int:job_id>')
def check_pcap_status(alert_id, job_id):
    """Check status of a PCAP job"""
    try:
        job = current_app.so_api.get_job_status(job_id)
        current_app.logger.debug(f"Job status: {json.dumps(job, indent=2)}")
        
        if job['status'] == 0:  # Pending
            return jsonify({
                "status": "pending",
                "message": "PCAP job in progress",
                "job_id": job_id,
                "job_status": job
            }), 202
        elif job['status'] == 1:  # Complete
            return jsonify({
                "status": "complete",
                "message": "PCAP job complete",
                "job_id": job_id
            }), 200
        else:  # Failed
            error_msg = f"PCAP job failed with status: {job['status']}"
            if 'error' in job:
                error_msg += f" - {job['error']}"
            return jsonify({
                "status": "failed",
                "message": error_msg,
                "job_id": job_id,
                "job_status": job
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error checking PCAP job status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/alerts/<alert_id>/pcap/download/<int:job_id>')
def download_pcap(alert_id, job_id):
    """Download PCAP data for a completed job (legacy method)"""
    try:
        # Verify job is complete
        job = current_app.so_api.get_job_status(job_id)
        if job['status'] != 1:
            return jsonify({
                "status": "failed",
                "message": "PCAP job not complete",
                "job_id": job_id,
                "job_status": job
            }), 400
            
        # Download PCAP data
        current_app.logger.debug(f"Downloading PCAP for job {job_id}")
        pcap_data = current_app.so_api.download_pcap(job_id)
        
        # Send file to user
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y%m%d-%H%M%S')
        filename = f"alert_{alert_id}_{timestamp_str}.pcap"
        current_app.logger.debug(f"Sending PCAP file: {filename}")
        
        return send_file(
            BytesIO(pcap_data),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
            
    except Exception as e:
        current_app.logger.error(f"Error downloading PCAP: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
@bp.route('/alerts/<alert_id>/pcap/direct')
def direct_pcap_download(alert_id):
    """
    Download PCAP directly using the joblookup endpoint.
    This simplified method requires only one API call instead of three.
    """
    try:
        # Get raw alert details
        raw_alerts = current_app.so_api.get_alerts()
        
        # Find alert by _id or id
        alert = next((a for a in raw_alerts if str(a.get('_id', a.get('id', ''))) == alert_id), None)
        
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
            
        # Log selected alert data
        current_app.logger.debug("Selected alert data structure:")
        current_app.logger.debug(json.dumps(alert, indent=2))
        
        # Extract required parameters
        timestamp_str = alert.get('timestamp', '')
        if not timestamp_str:
            return jsonify({"error": "Alert missing timestamp"}), 400
            
        # Handle different timestamp formats
        try:
            if 'Z' in timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.fromisoformat(timestamp_str)
            # Format time for the API
            time_param = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError as e:
            current_app.logger.error(f"Failed to parse timestamp: {timestamp_str}")
            return jsonify({"error": f"Invalid timestamp format: {timestamp_str}"}), 400
        
        # Try to get Elasticsearch ID or Community ID
        payload = alert.get('payload', {})
        
        # Extract Elasticsearch document ID
        esid = alert.get('_id', alert.get('id', None))
        
        # Try to get network community ID from payload
        ncid = None
        if 'network' in payload and 'community_id' in payload['network']:
            ncid = payload['network']['community_id']
        
        # Alternatively try message field or direct field
        if not ncid and 'message' in payload:
            try:
                message = json.loads(payload['message'])
                if 'network' in message and 'community_id' in message['network']:
                    ncid = message['network']['community_id']
            except (json.JSONDecodeError, TypeError):
                pass
                
        # Direct field access (flattened format)
        if not ncid and 'network.community_id' in payload:
            ncid = payload['network.community_id']
            
        if not esid and not ncid:
            return jsonify({"error": "Alert missing required identifiers (esid or community_id)"}), 400
            
        current_app.logger.debug(f"Using direct PCAP lookup with time={time_param}, esid={esid}, ncid={ncid}")
            
        # Download PCAP directly
        pcap_data = current_app.so_api.lookup_pcap_by_event(
            time=time_param,
            esid=esid,
            ncid=ncid
        )
        
        # Send file to user
        timestamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"alert_{alert_id}_{timestamp_str}.pcap"
        current_app.logger.debug(f"Sending PCAP file: {filename}")
        
        return send_file(
            BytesIO(pcap_data),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
            
    except Exception as e:
        current_app.logger.error(f"Error in direct PCAP download: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        if isinstance(e, requests.exceptions.HTTPError):
            response = e.response
            current_app.logger.error(f"HTTP Error Status: {response.status_code}")
            current_app.logger.error(f"Response Headers: {dict(response.headers)}")
            current_app.logger.error(f"Response Content: {response.text}")
        return jsonify({"error": str(e)}), 500
