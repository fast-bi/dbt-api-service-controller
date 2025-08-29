from apiflask import APIBlueprint
import subprocess
import logging

logger = logging.getLogger(__name__)

bp = APIBlueprint('health', __name__, url_prefix='/health')

def check_helm_connectivity():
    """Check if Helm is properly configured and can connect to the cluster."""
    try:
        # Check if Helm can list releases
        result = subprocess.run(
            ['helm', 'list', '--output', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Helm connectivity check failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Helm connectivity check failed: {str(e)}")
        return False

@bp.route('/liveness', methods=['GET'])
@bp.doc(
    summary='Liveness probe',
    description='Check if the application is alive.',
    responses={
        200: 'Application is running'
    }
)
def liveness():
    """Check if the application is alive."""
    return {
        "status": "alive",
        "message": "Application is running"
    }

@bp.route('/readiness', methods=['GET'])
@bp.doc(
    summary='Readiness probe',
    description='Check if the application is ready to handle requests.',
    responses={
        200: 'Application is ready',
        503: 'Application is not ready'
    }
)
def readiness():
    """Check if the application is ready to handle requests."""
    try:
        # Check Helm connectivity
        if not check_helm_connectivity():
            raise Exception("Helm is not properly configured or cannot connect to the cluster")
        
        return {
            "status": "ready",
            "message": "Application is ready to handle requests",
            "checks": {
                "helm": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "message": "Application is not ready",
            "checks": {
                "helm": str(e)
            }
        }, 503

@bp.route('/startup', methods=['GET'])
@bp.doc(
    summary='Startup probe',
    description='Check if the application has completed its startup sequence.',
    responses={
        200: 'Application has completed startup',
        503: 'Application has not completed startup'
    }
)
def startup():
    """Check if the application has completed its startup sequence."""
    try:
        # Check Helm connectivity
        if not check_helm_connectivity():
            raise Exception("Helm is not properly configured or cannot connect to the cluster")
        
        return {
            "status": "started",
            "message": "Application has completed startup",
            "checks": {
                "helm": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return {
            "status": "not_started",
            "message": "Application has not completed startup",
            "checks": {
                "helm": str(e)
            }
        }, 503 