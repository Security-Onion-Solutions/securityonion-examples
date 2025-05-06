import pytest
from flask import url_for
from urllib.parse import parse_qs, urlparse
import json

def test_alerts_list_alternate_format(app, client, mock_responses, api_client):
    """Test the alerts list handles alternate alert data format."""
    # Mock OAuth token endpoint
    mock_responses.post(
        "https://mock-so-api/oauth2/token",
        json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        status=200
    )

    # Mock the API response with the alternate format (without alert in message)
    mock_responses.get(
        "https://mock-so-api/connect/events/",
        json={
            "events": [{
                "source": "soagsa:.ds-logs-suricata.alerts-so-2025.05.05-000017",
                "Time": "2025-05-05T20:53:46.823Z",
                "timestamp": "2025-05-05T20:53:46.823Z",
                "id": "_t45opYBdKg8ipu2-PwP",
                "type": "",
                "score": 1.0039761,
                "payload": {
                    "@timestamp": "2025-05-05T20:53:46.823Z",
                    "@version": "1",
                    "data_stream.dataset": "suricata",
                    "data_stream.namespace": "so",
                    "data_stream.type": "logs",
                    "destination.ip": "192.168.10.101",
                    "destination.port": 139,
                    "ecs.version": "8.0.0",
                    "event.category": "network",
                    "event.dataset": "suricata.alert",
                    "event.ingested": "2025-05-05T20:53:47.254Z",
                    "event.module": "suricata",
                    "event.severity": 1,
                    "event.severity_label": "low",
                    "message": "{\"timestamp\":\"2025-05-05T20:53:46.823080+0000\",\"flow_id\":704444060668638,\"in_iface\":\"bond0\",\"event_type\":\"alert\",\"src_ip\":\"192.168.10.125\",\"src_port\":1361,\"dest_ip\":\"192.168.10.101\",\"dest_port\":139,\"proto\":\"TCP\",\"pkt_src\":\"wire/pcap\"}",
                    "network.packet_source": "wire/pcap",
                    "network.transport": "TCP",
                    "observer.name": "soagsa",
                    "rule.category": "Generic Protocol Command Decode",
                    "rule.metadata.signature_severity": ["Informational"],
                    "rule.name": "GPL NETBIOS SMB IPC$ unicode share access",
                    "source.ip": "192.168.10.125",
                    "source.port": 1361
                }
            }]
        },
        status=200
    )

    # Get the alerts list page
    response = client.get("/alerts")
    
    # Check response - should render without errors
    assert response.status_code == 200
    assert b"GPL NETBIOS SMB IPC$ unicode share access" in response.data
    assert b"192.168.10.125:1361" in response.data
    assert b"192.168.10.101:139" in response.data
    assert b"TCP" in response.data
    assert b"soagsa" in response.data

def test_create_job_data_alternate_format(app):
    """Test the _create_job_data function with alternate format."""
    with app.app_context():
        from src.routes.alerts import _create_job_data
        
        # Create a test alert with no alert object and direct payload fields
        alert = {
            "id": "test-alert-1",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "source.ip": "192.168.1.1",
                "source.port": 80,
                "destination.ip": "192.168.1.2",
                "destination.port": 443,
                "network.transport": "TCP",
                "network.packet_source": "eth0",
                "observer.name": "test-sensor"
            }
        }
        
        # Call function
        job_data = _create_job_data(alert)
        
        # Check results
        assert job_data["type"] == "pcap"
        assert job_data["nodeId"] == "test-sensor"
        assert job_data["sensorId"] == "test-sensor"
        assert job_data["filter"]["srcIp"] == "192.168.1.1"
        assert job_data["filter"]["dstIp"] == "192.168.1.2"
        assert job_data["filter"]["srcPort"] == 80
        assert job_data["filter"]["dstPort"] == 443
        assert job_data["filter"]["protocol"] == "tcp"