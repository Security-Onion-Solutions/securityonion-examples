"""
Cases route handlers for read-only case operations
"""
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.services.so_api import SecurityOnionAPI
from src.config import get_api_client
import logging
import traceback

logger = logging.getLogger(__name__)

bp = Blueprint('cases', __name__, url_prefix='/cases')

@bp.route('/', methods=['GET'])
def list_cases():
    """Display list of cases with filtering and sorting"""
    api_client: SecurityOnionAPI = get_api_client()
    
    try:
        # For testing - simulate error if error=true is passed
        if request.args.get('error') == 'true':
            error_msg = 'Error retrieving cases'
            logger.error(f"{error_msg}: Simulated error for testing")
            flash(error_msg, 'danger')
            return render_template('cases/list.html', cases=[])
        
        # Get all cases
        cases = api_client.get_cases()
        
        # Handle sorting
        sort_by = request.args.get('sort', 'updated')  # Default sort by updated
        sort_dir = request.args.get('dir', 'desc')  # Default newest first
        
        # Sort cases
        reverse = sort_dir == 'desc'
        cases = sorted(cases, key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        return render_template('cases/list.html', 
                             cases=cases,
                             sort_by=sort_by,
                             sort_dir=sort_dir)
                             
    except Exception as e:
        error_msg = 'Error retrieving cases'
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 405:
                error_msg = 'Case management is not configured on the server'
            elif e.response.status_code == 500:
                error_msg = 'Error retrieving cases from server'
            else:
                error_msg = f'Error retrieving cases: {str(e)}'
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(error_msg, 'danger')  # Use Bootstrap danger class for errors
        return render_template('cases/list.html', cases=[])

@bp.route('/<case_id>', methods=['GET'])
def view_case(case_id):
    """View case details"""
    api_client: SecurityOnionAPI = get_api_client()
    try:
        # Get case (user names already resolved by service)
        case = api_client.get_case(case_id)
        return render_template('cases/view.html', case=case)
    except Exception as e:
        error_msg = 'Error retrieving case'
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 405:
                error_msg = 'Case management is not configured on the server'
            else:
                error_msg = f'Error retrieving case: {str(e)}'
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(error_msg, 'danger')  # Use Bootstrap danger class
        return redirect(url_for('cases.list_cases'))
