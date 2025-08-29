from apiflask import APIBlueprint
from app.api.routes.deployments import deploy_dbt_server, list_deployments, delete_deployment
from app.api.routes.health import liveness, readiness, startup
from app.api.routes.status import get_status
from app.api.routes.projects import list_projects
from app.core.security import token_auth

def setup_routes(app):
    """Setup all API routes."""
    
    # Create API blueprints
    deployments_bp = APIBlueprint('deployments', __name__, url_prefix='/api/v1/deployments')
    health_bp = APIBlueprint('health', __name__, url_prefix='/health')
    status_bp = APIBlueprint('status', __name__, url_prefix='/api/v1/status')
    projects_bp = APIBlueprint('projects', __name__, url_prefix='/api/v1/projects')
    
    # Register routes for deployments
    deployments_bp.post('')(token_auth.login_required(deploy_dbt_server))
    deployments_bp.get('')(token_auth.login_required(list_deployments))
    deployments_bp.delete('/<deployment_id>')(token_auth.login_required(delete_deployment))
    
    # Register routes for health checks (no auth required)
    health_bp.get('/liveness')(liveness)
    health_bp.get('/readiness')(readiness)
    health_bp.get('/startup')(startup)
    
    # Register routes for status
    status_bp.get('')(token_auth.login_required(get_status))
    
    # Register routes for projects
    projects_bp.get('')(token_auth.login_required(list_projects))
    
    # Register blueprints with the app
    app.register_blueprint(deployments_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(projects_bp) 