#!/usr/bin/env python3
"""
Frappe MCP Server - Production Ready
Provides integration with Frappe/ERPNext via REST API
"""
import json
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown
from servers.config import load_env_file, FrappeConfig, validate_config, ConfigurationError
from servers.base_client import BaseClient, handle_errors

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "frappe_server.log"
logger = setup_logging("FrappeServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Frappe Integration Server")


class FrappeClient(BaseClient):
    """Frappe API client with authentication and error handling."""
    
    def __init__(self, config: FrappeConfig):
        super().__init__(
            base_url=config.site_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            logger=logger
        )
        
        self.config = config
        
        # Set authentication headers
        self.session.headers.update({
            'Authorization': f'token {config.api_key}:{config.api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info("Frappe client initialized successfully")
    
    def get_document(self, doctype: str, name: str) -> dict:
        """
        Get a specific document.
        
        Args:
            doctype: Document type (e.g., 'Customer', 'Sales Order')
            name: Document name/ID
            
        Returns:
            Document data as dictionary
        """
        logger.debug(f"Fetching document: {doctype}/{name}")
        
        response = self.get(f"/api/resource/{doctype}/{name}")
        data = response.json()
        
        logger.info(f"Successfully retrieved {doctype}: {name}")
        return data
    
    def get_list(
        self,
        doctype: str,
        filters: Optional[dict] = None,
        fields: Optional[list] = None,
        limit: int = 20,
        order_by: Optional[str] = None
    ) -> dict:
        """
        Get list of documents with optional filters.
        
        Args:
            doctype: Document type
            filters: Filter conditions as dictionary
            fields: List of fields to retrieve
            limit: Maximum number of records
            order_by: Sort order (e.g., 'creation desc')
            
        Returns:
            List of documents
        """
        logger.debug(f"Fetching list: {doctype} (limit: {limit})")
        
        params = {'limit_page_length': limit}
        
        if filters:
            params['filters'] = json.dumps(filters)
            logger.debug(f"Filters: {filters}")
        
        if fields:
            params['fields'] = json.dumps(fields)
        
        if order_by:
            params['order_by'] = order_by
        
        response = self.get(f"/api/resource/{doctype}", params=params)
        data = response.json()
        
        count = len(data.get('data', []))
        logger.info(f"Retrieved {count} {doctype} documents")
        
        return data
    
    def create_document(self, doctype: str, data: dict) -> dict:
        """
        Create a new document.
        
        Args:
            doctype: Document type
            data: Document data as dictionary
            
        Returns:
            Created document data
        """
        logger.debug(f"Creating document: {doctype}")
        
        response = self.post(f"/api/resource/{doctype}", json=data)
        result = response.json()
        
        doc_name = result.get('data', {}).get('name', 'Unknown')
        logger.info(f"Created {doctype}: {doc_name}")
        
        return result
    
    def update_document(self, doctype: str, name: str, data: dict) -> dict:
        """
        Update an existing document.
        
        Args:
            doctype: Document type
            name: Document name/ID
            data: Fields to update
            
        Returns:
            Updated document data
        """
        logger.debug(f"Updating document: {doctype}/{name}")
        
        response = self.put(f"/api/resource/{doctype}/{name}", json=data)
        result = response.json()
        
        logger.info(f"Updated {doctype}: {name}")
        return result
    
    def delete_document(self, doctype: str, name: str) -> dict:
        """
        Delete a document.
        
        Args:
            doctype: Document type
            name: Document name/ID
            
        Returns:
            Deletion confirmation
        """
        logger.debug(f"Deleting document: {doctype}/{name}")
        
        response = self.delete(f"/api/resource/{doctype}/{name}")
        
        logger.info(f"Deleted {doctype}: {name}")
        return {"success": True, "message": f"Deleted {doctype}/{name}"}


# Initialize client
try:
    config = FrappeConfig()
    validate_config(config, logger)
    
    log_server_startup(logger, "Frappe Server", {
        "Site URL": config.site_url,
        "Timeout": config.timeout,
        "Max Retries": config.max_retries
    })
    
    frappe_client = FrappeClient(config)
    
except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    frappe_client = None
except Exception as e:
    logger.critical(f"Failed to initialize Frappe client: {e}", exc_info=True)
    frappe_client = None


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def frappe_get_document(doctype: str, name: str) -> str:
    """
    Get a specific document from Frappe.
    
    Args:
        doctype: Document type (e.g., 'Customer', 'Sales Order')
        name: Document name/ID
        
    Returns:
        JSON string with document data
    """
    if not frappe_client:
        return json.dumps({"error": "Frappe client not initialized"})
    
    result = frappe_client.get_document(doctype, name)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def frappe_get_list(
    doctype: str,
    filters: Optional[str] = None,
    fields: Optional[str] = None,
    limit: int = 20,
    order_by: Optional[str] = None
) -> str:
    """
    Get a list of documents from Frappe.
    
    Args:
        doctype: Document type
        filters: JSON string of filter conditions
        fields: JSON array of fields to retrieve
        limit: Maximum number of records (default: 20)
        order_by: Sort order (e.g., 'creation desc')
        
    Returns:
        JSON string with list of documents
    """
    if not frappe_client:
        return json.dumps({"error": "Frappe client not initialized"})
    
    filter_dict = json.loads(filters) if filters else None
    fields_list = json.loads(fields) if fields else None
    
    result = frappe_client.get_list(doctype, filter_dict, fields_list, limit, order_by)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def frappe_create_document(doctype: str, data: str) -> str:
    """
    Create a new document in Frappe.
    
    Args:
        doctype: Document type
        data: JSON string with document data
        
    Returns:
        JSON string with created document
    """
    if not frappe_client:
        return json.dumps({"error": "Frappe client not initialized"})
    
    doc_data = json.loads(data)
    result = frappe_client.create_document(doctype, doc_data)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def frappe_update_document(doctype: str, name: str, data: str) -> str:
    """
    Update an existing document in Frappe.
    
    Args:
        doctype: Document type
        name: Document name/ID
        data: JSON string with fields to update
        
    Returns:
        JSON string with updated document
    """
    if not frappe_client:
        return json.dumps({"error": "Frappe client not initialized"})
    
    doc_data = json.loads(data)
    result = frappe_client.update_document(doctype, name, doc_data)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def frappe_delete_document(doctype: str, name: str) -> str:
    """
    Delete a document from Frappe.
    
    Args:
        doctype: Document type
        name: Document name/ID
        
    Returns:
        JSON string with deletion confirmation
    """
    if not frappe_client:
        return json.dumps({"error": "Frappe client not initialized"})
    
    result = frappe_client.delete_document(doctype, name)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    try:
        if not frappe_client:
            logger.error("Server starting with errors - some features unavailable")
        
        logger.info("Starting Frappe MCP Server...")
        mcp.run()
        
    except KeyboardInterrupt:
        log_server_shutdown(logger, "Frappe Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if frappe_client:
            frappe_client.close()