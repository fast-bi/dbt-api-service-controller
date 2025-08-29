import sys
import logging
from apiflask import APIFlask
from flask_cors import CORS
from app.api import setup_routes
from app.core.config import Config
from app.core.logging import StreamToLogger
from app.core.security import token_auth

def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename="app.log",
        filemode='a'
    )
    
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl

    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl

def create_app():
    """Create and configure the Flask application."""
    app = APIFlask(__name__, title='DBT API Service', version='1.0')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Setup logging
    stream_handler = StreamToLogger(logging.getLogger('app'), logging.INFO)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    
    # Enable CORS
    CORS(app)
    
    # Configure OpenAPI documentation
    app.config['OPENAPI_VERSION'] = '3.0.2'
    app.config['OPENAPI_JSON_PATH'] = 'openapi.json'
    app.config['OPENAPI_URL_PREFIX'] = '/'
    app.config['OPENAPI_REDOC_PATH'] = '/redoc'
    app.config['OPENAPI_REDOC_URL'] = 'https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js'
    app.config['OPENAPI_SWAGGER_UI_PATH'] = '/docs'
    app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
    app.config['OPENAPI_SWAGGER_UI_VERSION'] = '4.15.5'
    
    # Configure security scheme for OpenAPI
    app.config['OPENAPI_SECURITY_SCHEMES'] = {
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT'
        }
    }
    app.config['OPENAPI_SECURITY'] = [{'bearerAuth': []}]
    
    app.title = 'DBT API Service'
    app.description = 'API service for managing DBT deployments in Kubernetes'
    app.version = '1.0.0'
    
    # Setup routes
    setup_routes(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return {'message': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return {'message': 'Internal server error'}, 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=6798) 