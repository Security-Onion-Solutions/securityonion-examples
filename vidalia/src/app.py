# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

from flask import Flask, render_template, redirect, url_for
import logging
from src.template_filters import nl2br, format_timestamp
from src.config import Config
from src.services.so_api import SecurityOnionAPI
from src.routes.alerts import bp as alerts_bp
from src.routes.grid import bp as grid_bp
from src.routes.cases import bp as cases_bp

def create_app():
    # Configure logging first
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    app = Flask(__name__)
    
    # Register template filters
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['format_timestamp'] = format_timestamp
    
    # Load and validate configuration
    Config.validate()
    app.config.from_object(Config)
    
    # Set Flask logger level
    app.logger.setLevel(app.config['LOG_LEVEL'])
    
    # Initialize Security Onion API client
    print(f"\nConnecting to Security Onion API at: {app.config['SO_API_URL']}")
    print(f"Using client ID: {app.config['SO_CLIENT_ID']}")
    print(f"Client secret length: {len(app.config['SO_CLIENT_SECRET']) if app.config['SO_CLIENT_SECRET'] else 0} chars")
    
    app.so_api = SecurityOnionAPI(
        base_url=app.config['SO_API_URL'],
        client_id=app.config['SO_CLIENT_ID'],
        client_secret=app.config['SO_CLIENT_SECRET']
    )
    
    # Register blueprints
    app.register_blueprint(alerts_bp)
    app.register_blueprint(grid_bp)
    app.register_blueprint(cases_bp)
    
    # Basic error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
        
    # Redirect index to alerts page
    @app.route('/')
    def index():
        return redirect(url_for('alerts.list_alerts'))
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
