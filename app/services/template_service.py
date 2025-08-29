from typing import Dict, Any
import yaml
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import os
from pathlib import Path
import subprocess

class TemplateService:
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent.parent / "charts"

    def generate_htpasswd(self, username: str, password: str) -> str:
        """Generate htpasswd entry using htpasswd command."""
        try:
            result = subprocess.run(
                ["htpasswd", "-nb", username, password],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to generate htpasswd: {e.stderr}")

    def generate_deployment_values(
        self,
        project_name: str,
        namespace: str,
        customer: str,
        domain: str,
        environment: str,
        git_branch: str,
        dbt_repo_name: str,
        gitlink_secret: str,
        gitlink_deploy_key: str,
        secret_dbt_package_repo_token: str,
        secret_package_repo_token_name: str,
        basic_auth_user: str,
        basic_auth_password: str,
        cloud_provider: str,
        datawarehouse_type: str,
        service_account: str,
        worker_num: int,
        max_requests: int,
        enable_ddtrace: bool,
        debug: bool,
        celery_log_level: str,
        cpu_request: str,
        memory_request: str,
        cpu_limit: str,
        memory_limit: str,
        storage_size: str,
        https_enabled: bool,
        repository: str,
        image: str,
        tag: str):
        """Generate deployment values using Jinja2 template."""
        template_path = self.template_dir / "template_values.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Generate htpasswd entry
        hashed_credentials = self.generate_htpasswd(basic_auth_user, basic_auth_password)

        # Create Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Prepare context
        context = {
            "project_name": project_name,
            "namespace": namespace,
            "customer": customer,
            "domain": domain,
            "environment": environment,
            "git_branch": git_branch,
            "dbt_repo_name": dbt_repo_name,
            "gitlink_secret": gitlink_secret,
            "gitlink_deploy_key": gitlink_deploy_key,
            "secret_dbt_package_repo_token": secret_dbt_package_repo_token,
            "secret_package_repo_token_name": secret_package_repo_token_name,
            "basic_auth_user": basic_auth_user,
            "basic_auth_password": basic_auth_password,
            "hashed_credentials": hashed_credentials,
            "cloud_provider": cloud_provider,
            "datawarehouse_type": datawarehouse_type,
            "service_account": service_account,
            "worker_num": worker_num,
            "max_requests": max_requests,
            "enable_ddtrace": enable_ddtrace,
            "debug": debug,
            "celery_log_level": celery_log_level,
            "cpu_request": cpu_request,
            "memory_request": memory_request,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
            "storage_size": storage_size,
            "image": {
                "repository": repository,
                "image": image,
                "tag": tag
            },
            "cicd_env_key": f"CICD_ENV_{environment.upper()}",
            "cicd_env_value": environment,
            "app_version": "1.0.0",
            "https_enabled": https_enabled
        }

        # Render template
        template = env.get_template("template_values.yaml")
        rendered = template.render(**context)

        # Parse YAML
        try:
            return yaml.safe_load(rendered)
        except yaml.YAMLError as e:
            raise Exception(f"Failed to parse rendered template: {e}") 