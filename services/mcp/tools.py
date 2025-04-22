import os
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
import aiohttp

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SpatialQueryTool:
    """
    Tool for performing spatial queries and operations
    """
    async def buffer(self, feature_id: str, distance: float) -> Dict[str, Any]:
        """
        Create a buffer around a geometry
        
        Args:
            feature_id: ID of the feature
            distance: Buffer distance in meters
            
        Returns:
            Buffer result
        """
        try:
            # Make API call to spatial query service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "buffer",
                        "parameters": {
                            "feature_id": feature_id,
                            "operation": "buffer",
                            "distance": distance
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error creating buffer: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Buffer task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for buffer task to complete")
        except Exception as e:
            logger.error(f"Error creating buffer: {str(e)}")
            raise
    
    async def intersect(self, feature_id: str, target_feature_id: str) -> Dict[str, Any]:
        """
        Find the intersection of two geometries
        
        Args:
            feature_id: ID of the first feature
            target_feature_id: ID of the second feature
            
        Returns:
            Intersection result
        """
        try:
            # Make API call to spatial query service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "intersection",
                        "parameters": {
                            "feature_id": feature_id,
                            "operation": "intersect",
                            "target_feature_id": target_feature_id
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error finding intersection: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Intersection task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for intersection task to complete")
        except Exception as e:
            logger.error(f"Error finding intersection: {str(e)}")
            raise
    
    async def distance(self, feature_id: str, target_feature_id: str) -> Dict[str, Any]:
        """
        Calculate the distance between two geometries
        
        Args:
            feature_id: ID of the first feature
            target_feature_id: ID of the second feature
            
        Returns:
            Distance result
        """
        try:
            # Make API call to spatial query service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "distance",
                        "parameters": {
                            "feature_id": feature_id,
                            "operation": "distance",
                            "target_feature_id": target_feature_id
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error calculating distance: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Distance task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for distance task to complete")
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            raise
    
    async def area(self, feature_id: str) -> Dict[str, Any]:
        """
        Calculate the area of a geometry
        
        Args:
            feature_id: ID of the feature
            
        Returns:
            Area result
        """
        try:
            # Make API call to spatial query service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "area",
                        "parameters": {
                            "feature_id": feature_id,
                            "operation": "area"
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error calculating area: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Area task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for area task to complete")
        except Exception as e:
            logger.error(f"Error calculating area: {str(e)}")
            raise

class DataConversionTool:
    """
    Tool for converting data between different formats
    """
    async def convert_format(self, data: Any, source_format: str, target_format: str) -> Dict[str, Any]:
        """
        Convert data between different formats
        
        Args:
            data: Data to convert
            source_format: Source format
            target_format: Target format
            
        Returns:
            Conversion result
        """
        try:
            # Make API call to data conversion service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "convert",
                        "parameters": {
                            "source_data": data,
                            "source_format": source_format,
                            "target_format": target_format
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error converting format: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Format conversion task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for format conversion task to complete")
        except Exception as e:
            logger.error(f"Error converting format: {str(e)}")
            raise
    
    async def transform_coordinates(self, data: Any, source_crs: str, target_crs: str) -> Dict[str, Any]:
        """
        Transform coordinates between different coordinate systems
        
        Args:
            data: Data to transform
            source_crs: Source coordinate reference system
            target_crs: Target coordinate reference system
            
        Returns:
            Transformation result
        """
        try:
            # Make API call to data conversion service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_insight/spatial/analysis",
                    json={
                        "analysis_type": "convert",
                        "parameters": {
                            "source_data": data,
                            "source_crs": source_crs,
                            "target_crs": target_crs
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if task was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error transforming coordinates: {result.get('detail')}")
                    
                    task_id = result.get("task_id")
                    
                    # Wait for task to complete
                    max_retries = 10
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check task status
                        async with session.get(
                            f"http://localhost:8000/terra_insight/agents/tasks/{task_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            task = status_result.get("task", {})
                            
                            if task.get("status") == "completed":
                                return task.get("result", {})
                            
                            if task.get("status") == "failed":
                                raise ValueError(f"Coordinate transformation task failed: {task.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for coordinate transformation task to complete")
        except Exception as e:
            logger.error(f"Error transforming coordinates: {str(e)}")
            raise

class FeatureRetrievalTool:
    """
    Tool for retrieving features
    """
    async def get_feature(self, feature_id: str) -> Dict[str, Any]:
        """
        Get a feature by ID
        
        Args:
            feature_id: ID of the feature
            
        Returns:
            Feature data
        """
        try:
            # Make API call to feature service
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:8000/terra_map/features/{feature_id}"
                ) as response:
                    result = await response.json()
                    
                    # Check if feature was found
                    if result.get("status") != "success":
                        raise ValueError(f"Error retrieving feature: {result.get('detail')}")
                    
                    return result.get("feature", {})
        except Exception as e:
            logger.error(f"Error retrieving feature: {str(e)}")
            raise

class SQLServerQueryTool:
    """
    Tool for querying SQL Server (JCHARRISPACS)
    """
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a query on SQL Server
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query result
        """
        try:
            # Make API call to ETL service for SQL Server query
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/terra_flow/etl/jobs",
                    json={
                        "source": "jcharrispacs",
                        "target": "postgresql",
                        "source_params": {
                            "query": query,
                            "params": params
                        },
                        "target_params": {
                            "table_name": "tmp_query_result",
                            "if_exists": "replace"
                        }
                    }
                ) as response:
                    result = await response.json()
                    
                    # Check if job was created
                    if result.get("status") != "success":
                        raise ValueError(f"Error executing SQL Server query: {result.get('detail')}")
                    
                    job_id = result.get("job_id")
                    
                    # Wait for job to complete
                    max_retries = 20
                    retry_count = 0
                    while retry_count < max_retries:
                        await asyncio.sleep(1)
                        
                        # Check job status
                        async with session.get(
                            f"http://localhost:8000/terra_flow/etl/jobs/{job_id}"
                        ) as status_response:
                            status_result = await status_response.json()
                            
                            if status_result.get("status") != "success":
                                retry_count += 1
                                continue
                            
                            job = status_result.get("job", {})
                            
                            if job.get("status") == "completed":
                                return job.get("result", {})
                            
                            if job.get("status") == "failed":
                                raise ValueError(f"SQL Server query failed: {job.get('error_message')}")
                            
                            retry_count += 1
                    
                    raise TimeoutError("Timed out waiting for SQL Server query to complete")
        except Exception as e:
            logger.error(f"Error executing SQL Server query: {str(e)}")
            raise
