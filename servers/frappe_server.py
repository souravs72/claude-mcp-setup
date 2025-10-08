#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path
import requests
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
except ImportError:
    print("python-dotenv not installed. Using system environment variables.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Frappe Database Server")

class FrappeClient:
    def __init__(self):
        self.base_url = os.environ.get('FRAPPE_SITE_URL', '').rstrip('/')
        self.api_key = os.environ.get('FRAPPE_API_KEY')
        self.api_secret = os.environ.get('FRAPPE_API_SECRET')
        
        if not all([self.base_url, self.api_key, self.api_secret]):
            logger.error("Frappe credentials not properly configured")
            logger.info(f"FRAPPE_SITE_URL: {'✓' if self.base_url else '✗'}")
            logger.info(f"FRAPPE_API_KEY: {'✓' if self.api_key else '✗'}")
            logger.info(f"FRAPPE_API_SECRET: {'✓' if self.api_secret else '✗'}")
            return
            
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        })
        logger.info("Frappe client initialized successfully")

    def get_doc(self, doctype: str, name: str) -> dict:
        """Get a specific document"""
        response = self.session.get(f"{self.base_url}/api/resource/{doctype}/{name}")
        response.raise_for_status()
        return response.json()

    def get_list(self, doctype: str, filters: dict | None = None, 
                 fields: list[str] | None = None, limit: int = 20) -> dict:
        """Get list of documents with optional filters"""
        params = {'limit_page_length': limit}
        if filters:
            params['filters'] = json.dumps(filters)
        if fields:
            params['fields'] = json.dumps(fields)
        
        response = self.session.get(f"{self.base_url}/api/resource/{doctype}", params=params)
        response.raise_for_status()
        return response.json()

    def create_doc(self, doctype: str, data: dict) -> dict:
        """Create a new document"""
        response = self.session.post(f"{self.base_url}/api/resource/{doctype}", json=data)
        response.raise_for_status()
        return response.json()

frappe_client = FrappeClient()

@mcp.tool("frappe_get_document")
def frappe_get_document(doctype: str, name: str) -> str:
    """Get a specific document from Frappe"""
    try:
        result = frappe_client.get_doc(doctype, name)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Frappe get document error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("frappe_get_list")
def frappe_get_list(doctype: str, filters: str | None = None, 
                   fields: str | None = None, limit: int = 20) -> str:
    """Get a list of documents from Frappe with optional filters"""
    try:
        filter_dict = json.loads(filters) if filters else None
        fields_list = json.loads(fields) if fields else None
        result = frappe_client.get_list(doctype, filter_dict, fields_list, limit)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Frappe get list error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("frappe_create_document")
def frappe_create_document(doctype: str, data: str) -> str:
    """Create a new document in Frappe"""
    try:
        doc_data = json.loads(data)
        result = frappe_client.create_doc(doctype, doc_data)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Frappe create document error: {str(e)}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logger.info("Starting Frappe Database Server")
    mcp.run()