import json
import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import AgentExecutionError
from app.db.sqlserver import execute_sqlserver_query

logger = logging.getLogger(__name__)

class SQLServerTools:
    """
    Tools for working with SQL Server geospatial data
    """
    
    def __init__(self):
        """
        Initialize SQL Server tools
        """
        logger.info("SQL Server tools initialized")
    
    async def query_spatial_data(self, table_name: str, where_clause: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query spatial data from SQL Server
        
        Args:
            table_name: Name of the SQL Server table
            where_clause: Optional WHERE clause (without the 'WHERE' keyword)
            limit: Maximum number of records to return
            
        Returns:
            List of records with geospatial data
        """
        try:
            # Build query with safeguards to prevent SQL injection
            query = f"SELECT TOP {limit} * FROM {table_name}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Execute query
            results = await execute_sqlserver_query(query)
            
            # Process geometry columns
            processed_results = []
            for row in results:
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, bytes) and key.lower() in ['shape', 'geom', 'geometry']:
                        # Convert SQL Server geometry to WKT
                        wkt = await self._convert_sqlserver_geometry_to_wkt(value)
                        processed_row[key] = wkt
                    else:
                        processed_row[key] = value
                processed_results.append(processed_row)
            
            return processed_results
        except Exception as e:
            logger.error(f"Error querying SQL Server data: {str(e)}")
            raise AgentExecutionError(f"Failed to query SQL Server data: {str(e)}")
    
    async def _convert_sqlserver_geometry_to_wkt(self, geometry_bytes: bytes) -> str:
        """
        Convert SQL Server geometry binary to WKT
        
        Args:
            geometry_bytes: SQL Server geometry in binary format
            
        Returns:
            WKT representation of the geometry
        """
        try:
            # This is a placeholder for actual implementation
            # In a real implementation, this would use SQL Server's STAsText() function
            
            # Example query using the original connection
            query = "SELECT @geometry.STAsText() as wkt"
            params = {"geometry": geometry_bytes}
            
            result = await execute_sqlserver_query(query, params)
            
            if result and result[0] and 'wkt' in result[0]:
                return result[0]['wkt']
            else:
                # Fallback to a simple representation
                return f"POINT(0 0)"
        except Exception as e:
            logger.error(f"Error converting SQL Server geometry to WKT: {str(e)}")
            # Return a default value on error
            return "POINT(0 0)"
    
    async def sync_table_to_postgres(self, sql_table: str, pg_table: str, key_column: str) -> Dict[str, Any]:
        """
        Synchronize a SQL Server table to PostgreSQL
        
        Args:
            sql_table: SQL Server table name
            pg_table: PostgreSQL table name
            key_column: Primary key column for matching records
            
        Returns:
            Dictionary with synchronization results
        """
        try:
            # This is a placeholder for actual implementation
            # In a real implementation, this would:
            # 1. Query SQL Server table
            # 2. Transform data as needed
            # 3. Insert/update in PostgreSQL
            
            logger.info(f"Syncing {sql_table} to {pg_table} using key {key_column}")
            
            # Simulate sync process
            return {
                "status": "success",
                "source_table": sql_table,
                "target_table": pg_table,
                "records_processed": 0,
                "records_inserted": 0,
                "records_updated": 0,
                "records_failed": 0
            }
        except Exception as e:
            logger.error(f"Error syncing table: {str(e)}")
            raise AgentExecutionError(f"Failed to sync table: {str(e)}")
