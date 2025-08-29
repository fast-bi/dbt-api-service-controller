from apiflask import APIFlask
from flask_cors import CORS
from app.core.security import token_auth
from app.core.logging import setup_logging

def create_app(config_object=None):
    app = APIFlask(
        __name__,
        title='DBT API Service',
        version='1.0.0'
    )
    
    # Load configuration
    if config_object:
        app.config.from_object(config_object)
    
    # Enable CORS
    CORS(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from app.api.routes import deployments, projects, status, health
    app.register_blueprint(deployments.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(status.bp)
    app.register_blueprint(health.bp)
    
    return app 