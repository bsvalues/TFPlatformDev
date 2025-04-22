from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models.audit import AuditLog, DataCorrection
from app.db.models.geospatial import SpatialFeature
from app.db.models.user import User
from app.db.postgres import get_db
from app.mcp.agents.audit_agent import AuditAgent

router = APIRouter()

@router.get("/logs", status_code=status.HTTP_200_OK)
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date for filtering logs"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering logs"),
    user_id: Optional[str] = Query(None, description="Filter logs by user ID"),
    action: Optional[str] = Query(None, description="Filter logs by action type"),
    resource_type: Optional[str] = Query(None, description="Filter logs by resource type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get audit logs with optional filters
    """
    try:
        query = db.query(AuditLog)
        
        # Apply filters
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
            
        # Count total
        total = query.count()
        
        # Apply pagination
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "logs": [log.to_dict() for log in logs]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving audit logs: {str(e)}"
        )


@router.post("/correction", status_code=status.HTTP_201_CREATED)
async def submit_correction(
    feature_id: str = Query(..., description="ID of the feature to correct"),
    correction_type: str = Query(..., description="Type of correction"),
    corrected_value: Dict[str, Any] = Query(..., description="Corrected value"),
    reason: Optional[str] = Query(None, description="Reason for correction"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
) -> Dict[str, Any]:
    """
    Submit a data correction
    """
    try:
        # Check if feature exists
        feature = db.query(SpatialFeature).filter(SpatialFeature.id == feature_id).first()
        if not feature:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature with ID {feature_id} not found"
            )
            
        # Get original value based on correction type
        original_value = None
        if correction_type == "geometry":
            # Get GeoJSON geometry from PostGIS
            geometry_result = db.execute(
                f"SELECT ST_AsGeoJSON(geometry) as geom FROM spatialfeature WHERE id = '{feature.id}'"
            ).fetchone()
            
            if geometry_result:
                original_value = {"geometry": eval(geometry_result.geom)}
        elif correction_type == "properties":
            original_value = {"properties": feature.properties}
        else:
            original_value = {correction_type: getattr(feature, correction_type, None)}
            
        # Create correction record
        correction = DataCorrection(
            user_id=current_user.id,
            feature_id=feature_id,
            correction_type=correction_type,
            reason=reason,
            original_value=original_value,
            corrected_value=corrected_value,
            status="pending"
        )
        
        db.add(correction)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="correction_submitted",
            resource_type="SpatialFeature",
            resource_id=feature_id,
            before_state=original_value,
            after_state=corrected_value,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        
        db.add(audit_log)
        db.commit()
        
        # Run AI agent to validate correction
        audit_agent = AuditAgent()
        validation_result = await audit_agent.validate_correction(
            feature_id=feature_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value
        )
        
        # Update correction with validation results
        correction.status = "approved" if validation_result.get("valid", False) else "needs_review"
        db.commit()
        
        return {
            "correction_id": str(correction.id),
            "status": correction.status,
            "validation_result": validation_result
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting correction: {str(e)}"
        )


@router.get("/corrections", status_code=status.HTTP_200_OK)
async def get_corrections(
    status: Optional[str] = Query(None, description="Filter by correction status"),
    feature_id: Optional[str] = Query(None, description="Filter by feature ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get data corrections with optional filters
    """
    try:
        query = db.query(DataCorrection)
        
        # Apply filters
        if status:
            query = query.filter(DataCorrection.status == status)
        if feature_id:
            query = query.filter(DataCorrection.feature_id == feature_id)
            
        corrections = query.order_by(DataCorrection.created_at.desc()).all()
        
        return [correction.to_dict() for correction in corrections]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving corrections: {str(e)}"
        )


@router.put("/corrections/{correction_id}/approve", status_code=status.HTTP_200_OK)
async def approve_correction(
    correction_id: str = Path(..., description="ID of the correction to approve"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
) -> Dict[str, Any]:
    """
    Approve a data correction
    """
    try:
        # Check if correction exists
        correction = db.query(DataCorrection).filter(DataCorrection.id == correction_id).first()
        if not correction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Correction with ID {correction_id} not found"
            )
            
        # Check if correction is already approved
        if correction.status == "approved":
            return {"message": "Correction already approved", "correction_id": correction_id}
            
        # Update correction status
        correction.status = "approved"
        
        # Apply the correction to the feature
        feature = db.query(SpatialFeature).filter(SpatialFeature.id == correction.feature_id).first()
        if not feature:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature with ID {correction.feature_id} not found"
            )
            
        # Apply correction based on type
        if correction.correction_type == "geometry":
            # Apply geometry correction via PostGIS
            new_geom = correction.corrected_value.get("geometry")
            if new_geom:
                db.execute(
                    f"UPDATE spatialfeature SET geometry = ST_GeomFromGeoJSON('{new_geom}') WHERE id = '{feature.id}'"
                )
        elif correction.correction_type == "properties":
            # Update properties
            feature.properties = correction.corrected_value.get("properties")
        else:
            # Update specific attribute
            setattr(feature, correction.correction_type, correction.corrected_value.get(correction.correction_type))
            
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="correction_approved",
            resource_type="SpatialFeature",
            resource_id=feature.id,
            before_state=correction.original_value,
            after_state=correction.corrected_value,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Correction approved and applied successfully",
            "correction_id": correction_id,
            "feature_id": str(feature.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving correction: {str(e)}"
        )
