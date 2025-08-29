from apiflask import APIBlueprint, abort
import logging
import subprocess
import json
from app.core.security import token_auth

logger = logging.getLogger(__name__)

bp = APIBlueprint('projects', __name__, url_prefix='/api/v1/projects')

def get_helm_release_status(release_name):
    """Get detailed status of a Helm release using helm status command."""
    try:
        cmd = ['helm', 'status', release_name, '--output', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Failed to get status for release {release_name}: {result.stderr}")
            return None
            
        status_data = json.loads(result.stdout)
        return status_data.get('info', {}).get('status', 'unknown')
    except Exception as e:
        logger.warning(f"Error getting status for release {release_name}: {str(e)}")
        return 'unknown'

def get_helm_release_dependencies(release_name):
    """Get dependencies of a Helm release."""
    try:
        cmd = ['helm', 'get', 'manifest', release_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Failed to get manifest for release {release_name}: {result.stderr}")
            return []
            
        # Parse manifest to find dependencies
        dependencies = []
        manifest_lines = result.stdout.split('\n')
        for line in manifest_lines:
            if 'kind:' in line:
                resource_type = line.split('kind:')[1].strip()
                if resource_type not in dependencies:
                    dependencies.append(resource_type)
        
        return dependencies
    except Exception as e:
        logger.warning(f"Error getting dependencies for release {release_name}: {str(e)}")
        return []

def check_helm_release_exists(release_name):
    """Check if a Helm release exists."""
    try:
        cmd = ['helm', 'status', release_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def get_release_info(release_name):
    """Get detailed information about a Helm release."""
    # Get values
    cmd = ['helm', 'get', 'values', release_name, '--output', 'json']
    values_result = subprocess.run(cmd, capture_output=True, text=True)
    
    values = {}
    if values_result.returncode == 0:
        try:
            values = json.loads(values_result.stdout)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse values for release {release_name}")
    
    # Get status and dependencies
    status = get_helm_release_status(release_name)
    dependencies = get_helm_release_dependencies(release_name)
    
    return values, status, dependencies

@bp.route('', methods=['GET'])
@bp.auth_required(token_auth)
@bp.doc(
    summary='List DBT projects',
    description='List all available DBT projects from Helm releases.',
    responses={
        200: 'List of DBT projects'
    }
)
def list_projects():
    """List all DBT projects from Helm releases."""
    try:
        # Get all Helm releases
        cmd = ['helm', 'list', '--all', '--output', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get Helm releases: {result.stderr}")
            abort(500, message="Failed to get Helm releases")
            
        releases = json.loads(result.stdout)
        
        # Filter and format DBT server releases
        dbt_servers = []
        for release in releases:
            if release['name'].startswith('dbt-server-'):
                values, status, dependencies = get_release_info(release['name'])
                
                server_info = {
                    'name': release['name'],
                    'namespace': release.get('namespace', 'default'),
                    'status': status,
                    'chart': release.get('chart', ''),
                    'version': release.get('app_version', ''),
                    'last_deployed': release.get('updated', ''),
                    'values': values,
                    'dependencies': dependencies,
                    'can_delete': True  # Flag for UI to show delete option
                }
                
                dbt_servers.append(server_info)
        
        return dbt_servers
        
    except Exception as e:
        logger.error(f"Error listing DBT projects: {str(e)}")
        abort(500, message=str(e))

@bp.route('/<string:name>/exists', methods=['GET'])
@bp.auth_required(token_auth)
@bp.doc(
    summary='Check if a Helm release exists',
    description='Check if a specific Helm release exists in the cluster.',
    responses={
        200: 'Release existence status',
        404: 'Release not found'
    }
)
def check_release_exists(name):
    """Check if a specific Helm release exists."""
    exists = check_helm_release_exists(name)
    if exists:
        values, status, dependencies = get_release_info(name)
        return {
            'exists': True,
            'name': name,
            'status': status,
            'dependencies': dependencies
        }
    return {
        'exists': False,
        'name': name
    }, 404

@bp.route('/all', methods=['GET'])
@bp.auth_required(token_auth)
@bp.doc(
    summary='List all Helm releases',
    description='List all Helm releases in the cluster, including non-DBT projects.',
    responses={
        200: 'List of all Helm releases'
    }
)
def list_all_releases():
    """List all Helm releases in the cluster."""
    try:
        # Get all Helm releases
        cmd = ['helm', 'list', '--all', '--all-namespaces', '--output', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get Helm releases: {result.stderr}")
            abort(500, message="Failed to get Helm releases")
            
        releases = json.loads(result.stdout)
        
        # Format all releases
        all_releases = []
        for release in releases:
            values, status, dependencies = get_release_info(release['name'])
            
            release_info = {
                'name': release['name'],
                'namespace': release.get('namespace', 'default'),
                'status': status,
                'chart': release.get('chart', ''),
                'version': release.get('app_version', ''),
                'last_deployed': release.get('updated', ''),
                'dependencies': dependencies,
                'can_delete': True  # Flag for UI to show delete option
            }
            
            all_releases.append(release_info)
        
        return all_releases
        
    except Exception as e:
        logger.error(f"Error listing Helm releases: {str(e)}")
        abort(500, message=str(e)) 