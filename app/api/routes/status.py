from apiflask import APIBlueprint
import logging
import platform
import sys

logger = logging.getLogger(__name__)

bp = APIBlueprint('status', __name__, url_prefix='/api/v1/status')

@bp.route('', methods=['GET'])
@bp.doc(
    summary='Get service status',
    description='Get the current status of the DBT API service.',
    responses={
        200: 'Service status information'
    }
)
def get_status():
    """Get the service status."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "service": "dbt-api-service"
    } 