from apiflask import APIBlueprint, abort
from flask import current_app, request, jsonify
from datetime import datetime
from marshmallow import ValidationError
from app.api.schemas.deployment import (
    DeploymentCreateSchema,
    DeploymentResponseSchema,
    DeploymentUpdateSchema
)
from app.services.airflow_service import AirflowService
from app.core.config import Config
from app.core.security import token_auth
import subprocess
import tempfile
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os
import requests
import logging
import json
import re
import hashlib

logger = logging.getLogger(__name__)

bp = APIBlueprint('deployments', __name__, url_prefix='/api/v1/deployments')

# Initialize AirflowService with configuration from Config class
airflow_service = AirflowService(
    base_url=Config.AIRFLOW_URL,
    username=Config.AIRFLOW_USER,
    password=Config.AIRFLOW_PASSWORD
)

def sanitize_k8s_name(value):
    """Sanitize a string to be a valid Kubernetes resource name."""
    # Convert to lowercase and replace invalid chars with hyphens
    sanitized = re.sub(r'[^a-z0-9-]', '-', value.lower())
    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized

def sanitize_airflow_conn_id(value):
    """Sanitize a string to be a valid Airflow connection ID."""
    # Convert to lowercase and replace invalid chars with underscores
    sanitized = re.sub(r'[^a-z0-9_]', '_', value.lower())
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure max length of 250 chars
    return sanitized[:250]

def k8s_resource_name(project_name, git_branch=None):
    """Generate a consistent Kubernetes resource name using a hash."""
    # First sanitize the project name
    base = sanitize_k8s_name(project_name)
    
    # Create a unique string combining project name and branch
    full_name = f"{base}-{git_branch}" if git_branch else base
    
    # Generate a hash of the full name
    # Using first 8 characters of the hash to keep it short but unique
    name_hash = hashlib.md5(full_name.encode()).hexdigest()[:8]
    
    # Calculate maximum allowed length for the base name
    # Format: dbt-{project_name}-{hash}
    # We need to reserve:
    # - 4 chars for "dbt-"
    # - 1 char for "-"
    # - 8 chars for hash
    # - 1 char for "-" before hash
    # Total reserved: 14 chars
    max_base_length = 63 - 14
    
    # Truncate base name if needed
    if len(base) > max_base_length:
        base = base[:max_base_length]
    
    return f"dbt-{base}-{name_hash}"

def airflow_connection_id(project_name, git_branch=None):
    """Generate a consistent Airflow connection ID that matches k8s_resource_name exactly."""
    # Use the exact same function as k8s_resource_name
    return k8s_resource_name(project_name, git_branch)

def get_volume_name(prefix, k8s_name):
    """Generate a valid volume name that doesn't exceed 63 characters."""
    # Calculate maximum allowed length for the volume name
    # Format: {prefix}-{k8s_name}
    # We need to reserve:
    # - 1 char for "-"
    # Total reserved: 1 char
    max_k8s_name_length = 63 - len(prefix) - 1
    
    # Truncate k8s_name if needed
    if len(k8s_name) > max_k8s_name_length:
        k8s_name = k8s_name[:max_k8s_name_length]
    
    return f"{prefix}-{k8s_name}"

def render_template(template_path, output_path, context):
    """Render a Jinja2 template to a file"""
    try:
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        output = template.render(context)
        
        with open(output_path, 'w') as f:
            f.write(output)
    except Exception as e:
        current_app.logger.error(f"Error rendering template {template_path}: {str(e)}")
        raise

def render_values_file(data, chart_path):
    """Render the values.yaml file from template"""
    template_values_path = chart_path / 'template_values.yaml'
    values_path = chart_path / 'values.yaml'

    # Generate k8s name first
    k8s_name = k8s_resource_name(
        data.get('project_name', ''),
        data.get('git_branch')
    )

    # Generate volume names that don't exceed 63 characters
    datawarehouse_secrets_volume = get_volume_name('dbt-server-datawarehouse-secrets', k8s_name)
    nginx_proxy_volume = get_volume_name('dbt-server-nginx-proxy', k8s_name)

    # Log the incoming data for debugging
    current_app.logger.debug(f"Rendering values file with data: {data}")

    # Prepare context for template rendering
    context = {
        # Basic deployment info
        'project_name': data['project_name'],
        'namespace': data['namespace'],
        'customer': data['customer'],
        'domain': data['domain'],

        # Environment and cloud settings
        'environment': data.get('environment', 'prod'),
        'cloud_provider': current_app.config.get('CLOUD_PROVIDER'),
        'service_account': current_app.config.get('GCP_SERVICE_ACCOUNT'),
        
        # Git and data warehouse settings
        'git_branch': data.get('git_branch'),
        'datawarehouse_type': data.get('datawarehouse_type', ''),
        'data_warehouse_platform': data.get('data_warehouse_platform', ''),
        
        # Authentication and secrets
        'gitlink_secret': data.get('gitlink_secret', ''),
        'gitlink_deploy_key': data.get('gitlink_deploy_key', ''),
        'secret_dbt_package_repo_token': data.get('secret_dbt_package_repo_token', ''),
        'secret_package_repo_token_name': data.get('secret_package_repo_token_name', ''),
        'dbt_repo_name': data.get('dbt_repo_name', ''),
        'basic_auth_user': data.get('basic_auth_user', ''),
        'basic_auth_password': data.get('basic_auth_password', ''),
        'hashed_credentials': data.get('hashed_credentials', ''),

        # Image configuration
        'repository': data.get('repository', '4fastbi'),
        'image': data.get('image', 'dbt-api-server-core'),
        'tag': data.get('tag', 'latest'),

        # Server configuration
        'worker_num': data.get('worker_num', 10),
        'max_requests': data.get('max_requests', 35),
        'enable_ddtrace': data.get('enable_ddtrace', False),
        'debug': data.get('debug', False),
        'celery_log_level': data.get('celery_log_level', 'ERROR'),

        # CI/CD configuration
        'cicd_env_key': data.get('cicd_env_key', 'ENV'),
        'cicd_env_value': data.get('cicd_env_value', 'prod'),
        'app_version': data.get('app_version', '1.0.0'),

        # Resource configuration
        'cpu_request': data.get('cpu_request', '1500m'),
        'memory_request': data.get('memory_request', '2Gi'),
        'cpu_limit': data.get('cpu_limit', '3500m'),
        'memory_limit': data.get('memory_limit', '6Gi'),
        'storage_size': data.get('storage_size', '1Gi'),
        'k8s_name': k8s_name,
        
        # Volume names
        'datawarehouse_secrets_volume': datawarehouse_secrets_volume,
        'nginx_proxy_volume': nginx_proxy_volume
    }

    # Log the context for debugging
    current_app.logger.debug(f"Template context: {context}")

    render_template(str(template_values_path), str(values_path), context)
    return values_path

def get_helm_releases(namespace):
    """Get all helm releases in a namespace"""
    try:
        result = subprocess.run(
            ['helm', 'list', '-n', namespace, '--output', 'json'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            current_app.logger.error(f"Error listing helm releases: {result.stderr}")
            return []
        return json.loads(result.stdout)
    except Exception as e:
        current_app.logger.error(f"Error listing helm releases: {str(e)}")
        return []

def get_helm_status(release_name, namespace):
    """Get the status of a Helm release"""
    try:
        # First check if the release exists
        releases = get_helm_releases(namespace)
        release_exists = any(release['name'] == release_name for release in releases)
        
        if not release_exists:
            current_app.logger.info(f"Release {release_name} not found in namespace {namespace}")
            return None
            
        current_app.logger.info(f"Checking helm status for release {release_name} in namespace {namespace}")
        result = subprocess.run(
            ['helm', 'status', release_name, '-n', namespace],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            current_app.logger.error(f"Error getting Helm status: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        current_app.logger.error(f"Error getting Helm status: {str(e)}")
        return None

@bp.route('', methods=['POST'])
@bp.auth_required(token_auth)
@bp.input(DeploymentCreateSchema, arg_name='json_data')
@bp.output(DeploymentResponseSchema)
def deploy_dbt_server(json_data):
    """Create or update a DBT API server deployment."""
    try:
        # Generate consistent names using the same function
        k8s_name = k8s_resource_name(
            json_data.get('project_name', ''),
            json_data.get('git_branch')
        )
        
        # Use the same name for both Helm release and Airflow connection
        release_name = k8s_name
        airflow_id = k8s_name  # Use the same name for consistency

        # Get chart path
        chart_path = Path(current_app.root_path).parent / 'charts'
        
        # Log Helm configuration
        logger.info(f"Using Helm repo name: {Config.HELM_REPO_NAME}")
        logger.info(f"Using Helm repo URL: {Config.HELM_REPO_URL}")
        
        # Render values.yaml from template, pass k8s_name for all resource names
        values_file = render_values_file({**json_data, 'k8s_name': k8s_name}, chart_path)
        
        # Helm repo setup using Config class values
        repo_name = Config.HELM_REPO_NAME
        repo_url = Config.HELM_REPO_URL
        
        try:
            subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True, capture_output=True)
            subprocess.run(["helm", "repo", "update", repo_name], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Helm repo setup failed: {e.stderr.decode()}")
            return {
                'status': 'error',
                'message': 'Failed to setup Helm repository',
                'details': {'error': e.stderr.decode()}
            }, 500

        # Use k8s_name for release
        cmd = [
            'helm', 'upgrade', '-i', release_name, f'{repo_name}/raw',
            '--version', Config.HELM_CHART_VERSION,
            '--namespace', json_data['namespace'],
            '--wait',
            '--values', str(values_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            current_app.logger.error(f"Helm deployment failed: {result.stderr}")
            return {
                'status': 'error',
                'message': 'Failed to deploy application',
                'details': {'error': result.stderr}
            }, 500

        # Airflow connection
        current_app.logger.info("Attempting to create/update Airflow connection")
        if json_data.get('https_enabled', False):
            host = f"https://dbt-server-{k8s_name}.{json_data['customer']}.{json_data['domain']}/invocations"
        else:
            host = f"http://dbt-server-{k8s_name}.{json_data['namespace']}.svc.cluster.local/invocations"
        current_app.logger.info(f"Airflow connection details - ID: {airflow_id}, Host: {host}")
        airflow_connection_status = 'created'
        try:
            current_app.logger.info(f"Checking if connection {airflow_id} exists")
            airflow_service.get_connection(airflow_id)
            current_app.logger.info(f"Connection exists, updating with new details")
            airflow_service.update_connection(
                connection_id=airflow_id,
                connection_data={
                    "conn_type": "http",
                    "connection_id": airflow_id,
                    "description": f"Update at: {datetime.now()} - Configuration to call {host}",
                    "host": host,
                    "login": json_data.get('basic_auth_user', ''),
                    "password": json_data.get('basic_auth_password', ''),
                    "port": None,
                    "schema": "",
                    "extra": ""
                }
            )
            current_app.logger.info("Connection updated successfully")
            airflow_connection_status = 'updated'
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                current_app.logger.info(f"Connection does not exist, creating new connection")
                airflow_service.create_dbt_connection(
                    connection_id=airflow_id,
                    host=host,
                    login=json_data.get('basic_auth_user', ''),
                    password=json_data.get('basic_auth_password', ''),
                    description=f"Configuration to call {host}"
                )
                current_app.logger.info("New connection created successfully")
                airflow_connection_status = 'created'
            else:
                current_app.logger.error(f"Airflow API error: {str(e)}")
                current_app.logger.error(f"Response content: {e.response.text if e.response else 'No response content'}")
                airflow_connection_status = 'error'
                raise
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Airflow connection management: {str(e)}")
            airflow_connection_status = 'error'
            raise

        # Get deployment status
        status = get_helm_status(release_name, json_data['namespace'])
        return {
            'status': 'success',
            'message': f"Deployment {release_name} created/updated successfully",
            'details': {
                'release_name': release_name,
                'namespace': json_data['namespace'],
                'host': f"dbt-server-{k8s_name}.{json_data['customer']}.{json_data['domain']}",
                'status': status,
                'airflow_connection': {
                    'id': airflow_id,
                    'host': host,
                    'status': airflow_connection_status
                }
            }
        }
    except Exception as e:
        current_app.logger.error(f"Deployment failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'details': {'error': str(e)}
        }, 500

@bp.route('', methods=['GET'])
@bp.auth_required(token_auth)
def list_deployments():
    """List all DBT API server deployments."""
    try:
        # Get all Helm releases
        result = subprocess.run(
            ['helm', 'list', '-A', '--output', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        releases = yaml.safe_load(result.stdout)
        deployments = []
        
        for release in releases:
            if release['name'].startswith('dbt-server-'):
                status = get_helm_status(release['name'], release['namespace'])
                deployments.append({
                    'name': release['name'],
                    'project_name': release['name'].replace('dbt-server-', ''),
                    'namespace': release['namespace'],
                    'status': status,
                    'chart': release.get('chart', ''),
                    'version': release.get('app_version', ''),
                    'last_deployed': release.get('updated', '')
                })
        
        return deployments
    except Exception as e:
        abort(500, message=str(e))

@bp.route('/<deployment_id>', methods=['DELETE'])
@bp.auth_required(token_auth)
def delete_deployment(deployment_id):
    """Delete a DBT API server deployment."""
    try:
        # The deployment_id is already the k8s_name (no need to remove prefix)
        k8s_name = deployment_id
        namespace = 'dbt-server'
        
        # List available releases
        releases = get_helm_releases(namespace)
        release_exists = any(release['name'] == k8s_name for release in releases)
        if not release_exists:
            return {
                'status': 'error',
                'message': f"Deployment {k8s_name} not found in namespace {namespace}",
                'details': {
                    'error': 'Deployment not found',
                    'available_releases': [r['name'] for r in releases]
                }
            }, 404

        # Uninstall Helm release
        cmd = ['helm', 'uninstall', k8s_name, '-n', namespace]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            current_app.logger.error(f"Helm uninstall failed: {result.stderr}")
            return {
                'status': 'error',
                'message': 'Failed to delete deployment',
                'details': {'error': result.stderr}
            }, 500

        # Delete associated PVCs (match all PVCs for this StatefulSet)
        pvc_prefix = f"dbt-server-{k8s_name}-dbt-server-{k8s_name}-"
        get_pvc_cmd = [
            'kubectl', 'get', 'pvc', '-n', namespace, '-o', 'jsonpath={.items[*].metadata.name}'
        ]
        pvc_list_result = subprocess.run(get_pvc_cmd, capture_output=True, text=True)
        deleted_pvcs = []
        if pvc_list_result.returncode == 0:
            pvc_names = pvc_list_result.stdout.strip().split()
            for pvc in pvc_names:
                if pvc.startswith(pvc_prefix):
                    del_cmd = ['kubectl', 'delete', 'pvc', pvc, '-n', namespace, '--ignore-not-found=true']
                    del_result = subprocess.run(del_cmd, capture_output=True, text=True)
                    if del_result.returncode == 0:
                        deleted_pvcs.append(pvc)
                    else:
                        current_app.logger.warning(f"PVC deletion warning: {del_result.stderr}")
        else:
            current_app.logger.warning(f"Could not list PVCs: {pvc_list_result.stderr}")

        # Delete Airflow connection using the same name
        airflow_connection_status = 'not_found'
        airflow_error_message = None
        try:
            airflow_service.get_connection(k8s_name)  # Use the same name
            airflow_service.delete_connection(k8s_name)  # Use the same name
            airflow_connection_status = 'deleted'
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                airflow_connection_status = 'not_found'
            else:
                airflow_connection_status = 'error'
                airflow_error_message = str(e)
                current_app.logger.error(f"Error deleting Airflow connection: {str(e)}")
        except Exception as e:
            airflow_connection_status = 'error'
            airflow_error_message = str(e)
            current_app.logger.error(f"Unexpected error during Airflow connection deletion: {str(e)}")

        return {
            'status': 'success',
            'message': f"Deployment {k8s_name} and associated resources deleted successfully",
            'details': {
                'release_name': k8s_name,
                'namespace': namespace,
                'pvc_deleted': deleted_pvcs,
                'airflow_connection': {
                    'id': k8s_name,  # Use the same name
                    'status': airflow_connection_status,
                    'error': airflow_error_message
                }
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'details': {'error': str(e)}
        }, 500

@bp.route('/deployments', methods=['POST'])
@bp.auth_required(token_auth)
def create_deployment():
    try:
        data = request.get_json()
        schema = DeploymentCreateSchema()
        validated_data = schema.load(data)
        
        # ... existing deployment logic ...
        
        # After successful deployment, create/update Airflow connection
        try:
            connection_id = airflow_connection_id(
                validated_data.get('dbt_repo_name', ''),
                validated_data.get('git_branch', None)
            )
            host = f"https://dbt-server-{validated_data['project_name']}.{validated_data['customer']}.{validated_data['domain']}/invocations" if validated_data.get('https_enabled', False) else f"http://dbt-server-{validated_data['project_name']}.{validated_data['namespace']}.svc.cluster.local/invocations"
            
            logger.info(f"Creating/updating Airflow connection: {connection_id}")
            logger.info(f"Connection host: {host}")
            
            try:
                # Try to get existing connection
                airflow_service.get_connection(connection_id)
                logger.info(f"Connection {connection_id} exists, updating...")
                airflow_service.update_connection(
                    connection_id=connection_id,
                    connection_data={
                        "conn_type": "http",
                        "host": host,
                        "login": validated_data.get('basic_auth_user', ''),
                        "password": validated_data.get('basic_auth_password', ''),
                        "description": f"DBT API connection for {validated_data['project_name']}"
                    }
                )
            except Exception as e:
                if "Not Found" in str(e):
                    logger.info(f"Connection {connection_id} does not exist, creating new...")
                    airflow_service.create_dbt_connection(
                        connection_id=connection_id,
                        host=host,
                        login=validated_data.get('basic_auth_user', ''),
                        password=validated_data.get('basic_auth_password', ''),
                        description=f"DBT API connection for {validated_data['project_name']}"
                    )
                else:
                    raise
            
            logger.info(f"Successfully created/updated Airflow connection: {connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to create/update Airflow connection: {str(e)}")
            # Don't fail the deployment if Airflow connection fails
            # Just log the error and continue
        
        return jsonify({
            "message": "Deployment created successfully",
            "deployment_id": f"dbt-server-{validated_data['project_name']}",
            "details": {
                "project_name": validated_data['project_name'],
                "namespace": validated_data['namespace'],
                "airflow_connection_id": connection_id
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Deployment creation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500 