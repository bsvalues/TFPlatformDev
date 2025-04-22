import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import ipaddress
from fastapi import Request

from services.common.database import get_db_session
from services.common.models import AuditLog, User, SpatialFeature

# Configure logging
logger = logging.getLogger(__name__)

def create_audit_log(log_data: Dict[str, Any], request: Optional[Request] = None) -> int:
    """
    Create a new audit log entry
    
    Args:
        log_data: Audit log data
        request: FastAPI request object (optional)
        
    Returns:
        ID of the created log
    """
    try:
        # Extract required fields
        action = log_data.get("action")
        entity_type = log_data.get("entity_type")
        entity_id = log_data.get("entity_id")
        
        if not action or not entity_type or not entity_id:
            raise ValueError("action, entity_type, and entity_id are required")
        
        # Extract optional fields
        before_state = log_data.get("before_state")
        after_state = log_data.get("after_state")
        user_id = log_data.get("user_id")
        feature_id = log_data.get("feature_id")
        
        # Get IP address from request if available
        ip_address = None
        if request:
            ip_address = request.client.host if hasattr(request.client, "host") else None
        
        with get_db_session() as db:
            # Look up user by username
            if isinstance(user_id, str) and not user_id.isdigit():
                user = db.query(User).filter(User.username == user_id).first()
                user_id = user.id if user else None
            
            # Look up feature by feature_id if string
            if isinstance(feature_id, str) and not feature_id.isdigit():
                feature = db.query(SpatialFeature).filter(SpatialFeature.feature_id == feature_id).first()
                feature_id = feature.id if feature else None
            
            # Create audit log
            audit_log = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                user_id=user_id,
                feature_id=feature_id,
                ip_address=ip_address,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            return audit_log.id
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")
        raise

def get_audit_log(log_id: int) -> Optional[Dict[str, Any]]:
    """
    Get details of a specific audit log entry
    
    Args:
        log_id: ID of the audit log
        
    Returns:
        Audit log details
    """
    try:
        with get_db_session() as db:
            audit_log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
            
            if not audit_log:
                return None
            
            # Get user information
            user = db.query(User).filter(User.id == audit_log.user_id).first() if audit_log.user_id else None
            
            # Get feature information
            feature = db.query(SpatialFeature).filter(SpatialFeature.id == audit_log.feature_id).first() if audit_log.feature_id else None
            
            return {
                "id": audit_log.id,
                "action": audit_log.action,
                "entity_type": audit_log.entity_type,
                "entity_id": audit_log.entity_id,
                "before_state": audit_log.before_state,
                "after_state": audit_log.after_state,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name
                } if user else None,
                "feature": {
                    "id": feature.id,
                    "feature_id": feature.feature_id,
                    "feature_type": feature.feature_type
                } if feature else None,
                "ip_address": audit_log.ip_address,
                "timestamp": audit_log.timestamp.isoformat() if audit_log.timestamp else None
            }
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        raise

def search_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[Union[int, str]] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Search audit logs with filters
    
    Args:
        entity_type: Filter by entity type
        entity_id: Filter by entity ID
        user_id: Filter by user ID
        action: Filter by action
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        limit: Maximum number of logs to return
        offset: Offset for pagination
        
    Returns:
        List of audit logs
    """
    try:
        with get_db_session() as db:
            # Build query
            query = db.query(AuditLog)
            
            # Apply filters
            if entity_type:
                query = query.filter(AuditLog.entity_type == entity_type)
            
            if entity_id:
                query = query.filter(AuditLog.entity_id == entity_id)
            
            if user_id:
                # Handle user_id as string (username)
                if isinstance(user_id, str) and not user_id.isdigit():
                    user = db.query(User).filter(User.username == user_id).first()
                    if user:
                        query = query.filter(AuditLog.user_id == user.id)
                    else:
                        # No matching user, return empty result
                        return []
                else:
                    query = query.filter(AuditLog.user_id == user_id)
            
            if action:
                query = query.filter(AuditLog.action == action)
            
            if start_date:
                try:
                    start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    query = query.filter(AuditLog.timestamp >= start_datetime)
                except ValueError:
                    logger.warning(f"Invalid start_date format: {start_date}")
            
            if end_date:
                try:
                    end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    query = query.filter(AuditLog.timestamp <= end_datetime)
                except ValueError:
                    logger.warning(f"Invalid end_date format: {end_date}")
            
            # Apply pagination
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
            
            # Execute query
            audit_logs = query.all()
            
            # Format results
            results = []
            for log in audit_logs:
                # Get user information
                user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
                
                # Get feature information
                feature = db.query(SpatialFeature).filter(SpatialFeature.id == log.feature_id).first() if log.feature_id else None
                
                results.append({
                    "id": log.id,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name
                    } if user else None,
                    "feature": {
                        "id": feature.id,
                        "feature_id": feature.feature_id,
                        "feature_type": feature.feature_type
                    } if feature else None,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                })
            
            return results
    except Exception as e:
        logger.error(f"Error searching audit logs: {str(e)}")
        raise

def get_changes_by_feature(
    feature_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get change history for a specific feature
    
    Args:
        feature_id: ID of the feature
        limit: Maximum number of changes to return
        offset: Offset for pagination
        
    Returns:
        List of changes
    """
    try:
        with get_db_session() as db:
            # Find feature by feature_id
            feature = db.query(SpatialFeature).filter(SpatialFeature.feature_id == feature_id).first()
            
            if not feature:
                return []
            
            # Build query
            query = db.query(AuditLog).filter(AuditLog.feature_id == feature.id)
            
            # Apply pagination
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
            
            # Execute query
            audit_logs = query.all()
            
            # Format results
            results = []
            for log in audit_logs:
                # Get user information
                user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
                
                # Calculate changes if before_state and after_state are available
                changes = []
                if log.before_state and log.after_state:
                    # Compare properties
                    before_props = log.before_state.get("properties", {})
                    after_props = log.after_state.get("properties", {})
                    
                    # Find added, removed, and modified properties
                    all_keys = set(before_props.keys()) | set(after_props.keys())
                    
                    for key in all_keys:
                        before_value = before_props.get(key)
                        after_value = after_props.get(key)
                        
                        if key not in before_props:
                            changes.append({
                                "type": "added",
                                "property": key,
                                "value": after_value
                            })
                        elif key not in after_props:
                            changes.append({
                                "type": "removed",
                                "property": key,
                                "value": before_value
                            })
                        elif before_value != after_value:
                            changes.append({
                                "type": "modified",
                                "property": key,
                                "before": before_value,
                                "after": after_value
                            })
                    
                    # Check for geometry changes
                    before_geom = log.before_state.get("geometry")
                    after_geom = log.after_state.get("geometry")
                    
                    if before_geom != after_geom:
                        changes.append({
                            "type": "geometry_modified",
                            "details": "Geometry was modified"
                        })
                
                results.append({
                    "id": log.id,
                    "action": log.action,
                    "changes": changes,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "display_name": user.display_name
                    } if user else None,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                })
            
            return results
    except Exception as e:
        logger.error(f"Error getting feature changes: {str(e)}")
        raise

def log_api_request(
    request: Request,
    user_id: Optional[str] = None,
    action: str = "api_request"
) -> None:
    """
    Log an API request as an audit event
    
    Args:
        request: FastAPI request object
        user_id: ID of the user making the request
        action: Action to log
    """
    try:
        # Extract request details
        method = request.method
        url = str(request.url)
        client_host = request.client.host if hasattr(request.client, "host") else None
        
        # Create log data
        log_data = {
            "action": action,
            "entity_type": "api",
            "entity_id": 0,  # Placeholder
            "user_id": user_id,
            "before_state": None,
            "after_state": {
                "method": method,
                "url": url,
                "headers": dict(request.headers)
            },
            "ip_address": client_host
        }
        
        # Create audit log asynchronously
        create_audit_log(log_data)
    except Exception as e:
        logger.error(f"Error logging API request: {str(e)}")
        # Don't raise exception, just log it
