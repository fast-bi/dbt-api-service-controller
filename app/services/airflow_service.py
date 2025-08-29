import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class AirflowService:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info(f"Initialized AirflowService with base URL: {self.base_url}")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to the Airflow API."""
        url = urljoin(f"{self.base_url}/", endpoint)
        logger.info(f"Making {method} request to {url}")
        if data:
            logger.debug(f"Request data: {data}")
        
        try:
            response = self.session.request(method, url, json=data)
            response.raise_for_status()
            logger.info(f"Request successful: {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise

    def create_connection(self, connection_data: Dict[str, Any]) -> Dict:
        """Create a new Airflow connection."""
        logger.info(f"Creating new connection: {connection_data.get('connection_id')}")
        return self._make_request('POST', 'api/v1/connections', data=connection_data)

    def update_connection(self, connection_id: str, connection_data: Dict[str, Any]) -> Dict:
        """Update an existing Airflow connection."""
        logger.info(f"Updating connection: {connection_id}")
        return self._make_request('PATCH', f'api/v1/connections/{connection_id}', data=connection_data)

    def get_connection(self, connection_id: str) -> Dict:
        """Get an Airflow connection by ID."""
        logger.info(f"Getting connection: {connection_id}")
        return self._make_request('GET', f'api/v1/connections/{connection_id}')

    def delete_connection(self, connection_id: str) -> None:
        """Delete an Airflow connection."""
        logger.info(f"Deleting connection: {connection_id}")
        url = urljoin(f"{self.base_url}/", f"api/v1/connections/{connection_id}")
        # Use plain requests.delete to avoid session headers
        response = requests.delete(url, auth=self.auth, headers={'Accept': 'application/json'})
        if response.status_code not in (204, 404):
            logger.error(f"Failed to delete connection: {response.status_code} {response.text}")
            response.raise_for_status()

    def create_dbt_connection(
        self,
        connection_id: str,
        host: str,
        login: str,
        password: str,
        description: str
    ) -> Dict:
        """Create a DBT-specific Airflow connection."""
        logger.info(f"Creating DBT connection: {connection_id}")
        connection_data = {
            "conn_type": "http",
            "connection_id": connection_id,
            "description": description,
            "host": host,
            "login": login,
            "password": password,
            "port": None,
            "schema": "",
            "extra": ""
        }
        return self.create_connection(connection_data) 