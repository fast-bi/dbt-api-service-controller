# DBT API Service Controller

A CI/CD workflow image for managing dedicated dbt project API server deployments in Kubernetes, providing pre-warmed dbt environments for efficient task execution in data orchestration workflows.

## Overview

This Docker image provides a RESTful API service for managing dbt API server deployments in Kubernetes environments. It's designed to be used in CI/CD pipelines when users choose the "API" operator in data orchestration workflows. The service creates dedicated, pre-warmed dbt project API servers that are ready to execute dbt tasks efficiently, eliminating cold start delays and providing consistent performance for data transformation workflows.

## Architecture

### Core Components

**API Service Controller**: Manages the lifecycle of dbt API server deployments through RESTful endpoints with OpenAPI documentation.

**Kubernetes Integration Manager**: Handles Helm chart deployments using kube-core/raw for deterministic resource management and cleanup.

**Airflow Connection Manager**: Manages Airflow connections for seamless integration with orchestration workflows and automatic cleanup.

**Resource Naming Engine**: Provides collision-free, deterministic naming for all Kubernetes and Airflow resources based on project and branch information.

**Helm Chart Orchestrator**: Manages dbt API server deployments using Helm charts with automatic PVC cleanup and resource management.

## Docker Image

### Base Image
- **Base**: Python 3.11.11-slim-bullseye

### Build

```bash
# Build the image
./build.sh

# Or manually
docker build -t dbt-api-service-controller .
```

### Build Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `build_for` | Target platform for the build | `linux/amd64` |

### Environment Variables

The container expects the following environment variables:

- `SECRET_KEY` - Secret key for API authentication
- `AIRFLOW_URL` - Airflow instance URL for connection management
- `AIRFLOW_USER` - Airflow username for API access
- `AIRFLOW_PASSWORD` - Airflow password for API access
- `KUBERNETES_NAMESPACE` - Kubernetes namespace for deployments (default: dbt-server)
- `FLASK_ENV` - Flask environment (production/development)
- `DEBUG` - Debug mode flag

### Configuration Files

The image supports configuration through the following files:

- `dbt-api-service-controller.yaml`: Kubernetes deployment configuration
- `charts/template_values.yaml`: Helm chart template values
- `app/api/`: API route definitions and schemas
- `app/services/`: Business logic and service implementations

## Main Functionality

### Automated DBT Server Deployment

The image orchestrates a complete dbt API server deployment workflow:

1. **Request Validation**: Validates deployment requests and project parameters
2. **Resource Naming**: Generates deterministic, collision-free resource names
3. **Helm Chart Deployment**: Deploys dbt API server using kube-core/raw Helm chart
4. **Airflow Integration**: Creates and manages Airflow connections for orchestration
5. **Health Monitoring**: Monitors deployment status and server readiness
6. **Resource Cleanup**: Handles automatic cleanup of PVCs and connections on deletion

### Resource Naming Convention

**Kubernetes Resources** (Helm release, StatefulSet, Service, PVC):
```
dbt-server-<project_name>-<git_branch>
```
- All lowercase
- Non-alphanumeric characters replaced with dashes
- Git branch is optional

**Airflow Connection IDs**:
```
<project_name>_<git_branch>
```
- All lowercase
- Non-alphanumeric characters replaced with underscores
- Git branch is optional

### API Endpoints

- **POST /api/v1/deployments**: Create new dbt API server deployment
- **GET /api/v1/deployments**: List all deployments
- **GET /api/v1/deployments/{name}**: Get deployment details
- **DELETE /api/v1/deployments/{name}**: Delete deployment and cleanup resources
- **GET /docs**: Swagger UI documentation
- **GET /openapi.json**: OpenAPI specification

### Error Handling

- Comprehensive request validation with detailed error messages
- Graceful handling of Kubernetes API failures
- Automatic rollback on deployment failures
- Detailed logging for troubleshooting deployment issues
- Proper cleanup of resources on deployment deletion

### Maintenance Tasks

- **Deployment Health Monitoring**: Checks dbt server availability and performance
- **Resource Management**: Manages Kubernetes resources with proper limits and requests
- **Connection Cleanup**: Automatically removes Airflow connections on deployment deletion
- **PVC Management**: Handles persistent volume cleanup and storage optimization

## Testing

### Health Checks

The image includes built-in health checks:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' dbt-api-service-controller

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' dbt-api-service-controller
```

### API Testing

```bash
# Test API endpoint
curl -X GET http://localhost:6798/api/v1/deployments

# Create deployment
curl -X POST http://localhost:6798/api/v1/deployments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-key" \
  -d '{"project_name": "test-project", "git_branch": "main"}'

# Delete deployment
curl -X DELETE http://localhost:6798/api/v1/deployments/dbt-server-test-project-main \
  -H "Authorization: Bearer your-secret-key"
```

## Troubleshooting

### Common Issues

#### Issue: Helm Chart Deployment Failure
**Problem**: Failed to deploy dbt API server using Helm chart

**Solution**: Verify Kubernetes cluster access and Helm chart availability

#### Issue: Airflow Connection Creation Failure
**Problem**: Cannot create Airflow connection for dbt API server

**Solution**: Check Airflow credentials and API endpoint accessibility

#### Issue: Resource Naming Collision
**Problem**: Duplicate resource names causing deployment conflicts

**Solution**: The system automatically generates unique names; verify project and branch parameters

#### Issue: PVC Cleanup Failure
**Problem**: Persistent volumes not cleaned up after deployment deletion

**Solution**: Check Kubernetes permissions and PVC retention policies

#### Issue: API Authentication Failure
**Problem**: Invalid or missing authentication token

**Solution**: Verify SECRET_KEY environment variable and Authorization header

### Getting Help

- **Documentation**: [Fast.BI Documentation](https://wiki.fast.bi)
- **Issues**: [GitHub Issues](https://github.com/fast-bi/dbt-api-service-controller/issues)
- **Email**: support@fast.bi

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Fast.BI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This project is part of the FastBI platform infrastructure.

## Support and Maintain by Fast.BI

For support and questions, contact: support@fast.bi