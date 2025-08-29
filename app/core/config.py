import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for the DBT API Service."""
    
    # Flask Configuration
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    
    # Kubernetes Configuration
    KUBERNETES_NAMESPACE = os.getenv('KUBERNETES_NAMESPACE', 'dbt-server')
    KUBERNETES_CONTEXT = os.getenv('KUBERNETES_CONTEXT', None)
    
    # Helm Configuration
    HELM_REPO_NAME = os.getenv('HELM_REPO_NAME', 'kube-core')
    HELM_REPO_URL = os.getenv('HELM_REPO_URL', 'https://kube-core.github.io/helm-charts')
    HELM_CHART_VERSION = os.getenv('HELM_CHART_VERSION', '0.1.0')
    
    # Airflow Configuration
    AIRFLOW_URL = os.getenv('AIRFLOW_URL', '')
    AIRFLOW_USER = os.getenv('AIRFLOW_USER', '')
    AIRFLOW_PASSWORD = os.getenv('AIRFLOW_PASSWORD', '')
    
    # API Configuration
    API_TITLE = 'DBT API Service'
    API_VERSION = '1.0'
    OPENAPI_VERSION = '3.0.2'
    OPENAPI_JSON_PATH = 'openapi.json'
    OPENAPI_URL_PREFIX = '/'
    OPENAPI_REDOC_PATH = '/redoc'
    OPENAPI_REDOC_URL = 'https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js'
    OPENAPI_SWAGGER_UI_PATH = '/docs'
    OPENAPI_SWAGGER_UI_URL = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    @classmethod
    def init_app(cls, app):
        """Initialize the application with this configuration."""
        # Log configuration values
        logger.info("Loading configuration:")
        logger.info(f"HELM_REPO_NAME: {cls.HELM_REPO_NAME}")
        logger.info(f"HELM_REPO_URL: {cls.HELM_REPO_URL}")
        logger.info(f"HELM_CHART_VERSION: {cls.HELM_CHART_VERSION}")
        logger.info(f"KUBERNETES_NAMESPACE: {cls.KUBERNETES_NAMESPACE}")
        logger.info(f"AIRFLOW_URL: {cls.AIRFLOW_URL}")
        pass 