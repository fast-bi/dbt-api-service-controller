from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime
import subprocess
import random
import string
import hashlib

def generate_short_name(project_name, git_branch=None, max_length=30):
    """Generate a shortened but unique name for Kubernetes resources."""
    # Create a base name from project name (max 20 chars)
    base = project_name[:20].lower().replace('_', '-')
    
    if git_branch:
        # Create a hash of the git branch (8 chars)
        branch_hash = hashlib.md5(git_branch.encode()).hexdigest()[:8]
        # Combine with a separator
        return f"{base}-{branch_hash}"
    return base

class DeploymentCreateSchema(Schema):
    # Required fields
    project_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=63),
        metadata={
            'title': 'Project Name',
            'description': 'The name of the DBT project. Must be a valid Kubernetes resource name.',
            'example': 'fastbi-demo-project'
        }
    )
    namespace = fields.String(
        required=True,
        validate=validate.Length(min=1, max=63),
        metadata={
            'title': 'Namespace',
            'description': 'The Kubernetes namespace where the DBT project will be deployed.',
            'example': 'dbt-server'
        }
    )
    customer = fields.String(
        required=True,
        validate=validate.Length(min=1, max=63),
        metadata={
            'title': 'Customer',
            'description': 'The customer identifier for the DBT project.',
            'example': 'fastbi'
        }
    )
    domain = fields.String(
        required=True,
        validate=validate.Length(min=1, max=63),
        metadata={
            'title': 'Domain',
            'description': 'The domain name for the DBT project deployment.',
            'example': 'fast.bi'
        }
    )

    # Environment settings
    environment = fields.String(
        required=False,
        validate=validate.OneOf(['e2e', 'prod']),
        load_default='prod',
        metadata={
            'title': 'Environment',
            'description': 'The deployment environment. Must be either e2e (end-to-end testing) or prod (production).',
            'example': 'prod'
        }
    )
    git_branch = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={
            'title': 'Git Branch',
            'description': 'The Git branch to use for the DBT project deployment.',
            'example': 'DD_250507_6MBRB'
        }
    )
    cloud_provider = fields.String(
        required=False,
        validate=validate.OneOf(['aws', 'gcp', 'azure', 'self-managed']),
        load_default='gcp',
        metadata={
            'title': 'Cloud Provider',
            'description': 'The cloud provider for the deployment. Must be either aws or gcp.',
            'example': 'gcp'
        }
    )
    datawarehouse_type = fields.String(
        required=False,
        validate=validate.OneOf(['', 'bigquery', 'snowflake', 'redshift', 'fabric']),
        load_default='',
        metadata={
            'title': 'Data Warehouse Type',
            'description': 'The type of data warehouse being used.',
            'example': 'bigquery'
        }
    )
    https_enabled = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            'title': 'HTTPS Enabled',
            'description': 'Whether to enable HTTPS for the deployment.',
            'example': False
        }
    )

    # Repository and authentication
    dbt_repo_name = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='',
        metadata={
            'title': 'DBT Repository Name',
            'description': 'The name of the DBT repository.',
            'example': 'fastbi-dbt-models'
        }
    )
    gitlink_secret = fields.String(
        required=False,
        validate=validate.Length(min=1, max=2048),  # Increased max length for Git URLs with tokens
        load_default='',
        metadata={
            'title': 'GitLink Secret',
            'description': 'The Git repository URL with credentials.',
            'example': 'https://username:token@gitlab.com/org/repo.git'
        }
    )
    gitlink_deploy_key = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='EMPTY',
        metadata={
            'title': 'GitLink Deploy Key',
            'description': 'The deploy key for Git repository access.',
            'example': 'EMPTY'
        }
    )
    secret_dbt_package_repo_token = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='',
        metadata={
            'title': 'DBT Package Repository Token',
            'description': 'The token for accessing private DBT packages.',
            'example': 'glpat-xxxxx'
        }
    )
    secret_package_repo_token_name = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='',
        metadata={
            'title': 'Package Repository Token Name',
            'description': 'The name of the token in the package repository.',
            'example': 'fastbi_agent_access_token'
        }
    )
    basic_auth = fields.String(
        required=False,
        validate=validate.Length(min=0, max=255),
        load_default='',
        metadata={
            'title': 'Basic Auth',
            'description': 'Basic authentication string if needed.',
            'example': ''
        }
    )
    basic_auth_user = fields.String(
        required=False,
        validate=validate.Length(min=1, max=63),
        load_default='',
        metadata={
            'title': 'Basic Auth Username',
            'description': 'The username for basic authentication.',
            'example': 'user-name'
        }
    )
    basic_auth_password = fields.String(
        required=False,
        validate=validate.Length(min=8, max=63),
        load_default='',
        metadata={
            'title': 'Basic Auth Password',
            'description': 'The password for basic authentication. Must be at least 8 characters long.',
            'example': 'secure-password'
        }
    )

    # Image configuration
    repository = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='europe-central2-docker.pkg.dev/fast-bi-common/bi-platform/',
        metadata={
            'title': 'Container Image Repository',
            'description': 'The container image repository to use for the deployment.',
            'example': 'europe-central2-docker.pkg.dev/fast-bi-common/bi-platform/'
        }
    )
    image = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='tsb-dbt-core-api-server',
        metadata={
            'title': 'Container Image Name',
            'description': 'The container image name to use for the deployment.',
            'example': 'tsb-dbt-core-api-server'
        }
    )
    tag = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={
            'title': 'Container Image Tag',
            'description': 'The container image tag to use for the deployment.',
            'example': 'v0.0.7.1'
        }
    )
    service_account = fields.String(
        required=False,
        validate=validate.Regexp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        load_default=None,
        metadata={
            'title': 'Service Account',
            'description': 'The service account email for GCP deployments.',
            'example': 'dbt-sa@fast-bi-demo.iam.gserviceaccount.com'
        }
    )

    # Server configuration
    worker_num = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=20),
        load_default=10,
        metadata={
            'title': 'Worker Number',
            'description': 'The number of worker processes for the DBT server.',
            'example': 1
        }
    )
    max_requests = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=100),
        load_default=35,
        metadata={
            'title': 'Max Requests',
            'description': 'The maximum number of concurrent requests.',
            'example': 5
        }
    )
    enable_ddtrace = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            'title': 'Enable Datadog Tracing',
            'description': 'Whether to enable Datadog tracing.',
            'example': True
        }
    )
    debug = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            'title': 'Debug Mode',
            'description': 'Whether to enable debug mode.',
            'example': True
        }
    )
    celery_log_level = fields.String(
        required=False,
        validate=validate.OneOf(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
        load_default='ERROR',
        metadata={
            'title': 'Celery Log Level',
            'description': 'The log level for Celery tasks.',
            'example': 'DEBUG'
        }
    )

    # CI/CD configuration
    cicd_env_key = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='ENV',
        metadata={
            'title': 'CI/CD Environment Key',
            'description': 'The environment key for CI/CD configuration.',
            'example': 'ENV'
        }
    )
    cicd_env_value = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='prod',
        metadata={
            'title': 'CI/CD Environment Value',
            'description': 'The environment value for CI/CD configuration.',
            'example': 'prod'
        }
    )
    app_version = fields.String(
        required=False,
        validate=validate.Length(min=1, max=255),
        load_default='1.0.0',
        metadata={
            'title': 'Application Version',
            'description': 'The version of the application being deployed.',
            'example': '1.0.0'
        }
    )

    # Resource configuration
    cpu_request = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+m$|^\d+$'),
        load_default='1500m',
        metadata={
            'title': 'CPU Request',
            'description': 'The CPU request for the DBT server pod.',
            'example': '600m'
        }
    )
    memory_request = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+[MG]i$'),
        load_default='2Gi',
        metadata={
            'title': 'Memory Request',
            'description': 'The memory request for the DBT server pod.',
            'example': '1Gi'
        }
    )
    cpu_limit = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+m$|^\d+$'),
        load_default='3500m',
        metadata={
            'title': 'CPU Limit',
            'description': 'The CPU limit for the DBT server pod.',
            'example': '600m'
        }
    )
    memory_limit = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+[MG]i$'),
        load_default='6Gi',
        metadata={
            'title': 'Memory Limit',
            'description': 'The memory limit for the DBT server pod.',
            'example': '1Gi'
        }
    )
    storage_size = fields.String(
        required=False,
        validate=validate.Regexp(r'^\d+[MG]i$'),
        load_default='1Gi',
        metadata={
            'title': 'Storage Size',
            'description': 'The storage size for the DBT server pod.',
            'example': '1Gi'
        }
    )

    # Data warehouse configuration
    data_warehouse_platform = fields.String(
        required=False,
        validate=validate.OneOf(['', 'bigquery', 'snowflake', 'redshift', 'fabric']),
        load_default='',
        metadata={
            'title': 'Data Warehouse Platform',
            'description': 'Alias for datawarehouse_type. The data warehouse platform being used.',
            'example': 'bigquery'
        }
    )

    @post_load
    def generate_hashed_credentials(self, data, **kwargs):
        """Generate hashed credentials if basic auth is provided, or autogenerate if missing."""
        # Generate shortened names for Kubernetes resources
        data['k8s_name'] = generate_short_name(
            data['project_name'],
            data.get('git_branch')
        )
        
        # Autogenerate username if not provided
        if not data.get('basic_auth_user'):
            rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            data['basic_auth_user'] = f'dbt_server_agent_{rand_str}'
        # Autogenerate password if not provided
        if not data.get('basic_auth_password'):
            data['basic_auth_password'] = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        if data.get('basic_auth_user') and data.get('basic_auth_password'):
            try:
                # Use htpasswd to generate hashed credentials
                result = subprocess.run(
                    ['htpasswd', '-nbB', data['basic_auth_user'], data['basic_auth_password']],
                    capture_output=True,
                    text=True,
                    check=True
                )
                data['hashed_credentials'] = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                raise ValidationError(f"Failed to generate hashed credentials: {e.stderr}")
        else:
            data['hashed_credentials'] = ''
        return data

    @validates('data_warehouse_platform')
    def sync_data_warehouse_fields(self, value):
        """Ensure data_warehouse_platform and datawarehouse_type are in sync."""
        if value and hasattr(self, 'context'):
            data = self.context.get('data', {})
            if isinstance(data, dict) and not data.get('datawarehouse_type'):
                data['datawarehouse_type'] = value
        return value

    @validates('datawarehouse_type')
    def sync_datawarehouse_fields(self, value):
        """Ensure datawarehouse_type and data_warehouse_platform are in sync."""
        if value and hasattr(self, 'context'):
            data = self.context.get('data', {})
            if isinstance(data, dict) and not data.get('data_warehouse_platform'):
                data['data_warehouse_platform'] = value
        return value

class DeploymentUpdateSchema(Schema):
    """Schema for updating a deployment. Only allows updating specific fields."""
    tag = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={
            'title': 'Container Image Tag',
            'description': 'The container image tag to use for the deployment.',
            'example': 'latest'
        }
    )
    worker_num = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=20),
        metadata={
            'title': 'Worker Number',
            'description': 'The number of worker processes for the DBT server.',
            'example': 10
        }
    )
    max_requests = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=100),
        metadata={
            'title': 'Max Requests',
            'description': 'The maximum number of concurrent requests.',
            'example': 35
        }
    )
    debug = fields.Boolean(
        required=False,
        metadata={
            'title': 'Debug Mode',
            'description': 'Whether to enable debug mode.',
            'example': False
        }
    )
    celery_log_level = fields.String(
        required=False,
        validate=validate.OneOf(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
        metadata={
            'title': 'Celery Log Level',
            'description': 'The log level for Celery tasks.',
            'example': 'ERROR'
        }
    )

class DeploymentResponseSchema(Schema):
    status = fields.String(
        required=True,
        validate=validate.OneOf(['success', 'error']),
        metadata={
            'title': 'Response Status',
            'description': 'The status of the deployment operation.',
            'example': 'success'
        }
    )
    message = fields.String(
        required=True,
        metadata={
            'title': 'Response Message',
            'description': 'A descriptive message about the deployment operation.',
            'example': 'Deployment dbt-server-demo created successfully'
        }
    )
    details = fields.Dict(
        required=True,
        metadata={
            'title': 'Response Details',
            'description': 'Additional details about the deployment operation.',
            'example': {
                'release_name': 'dbt-server-demo',
                'namespace': 'dbt-server',
                'status': 'deployed'
            }
        }
    ) 