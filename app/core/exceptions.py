from fastapi import HTTPException, status

class DatabaseConnectionError(Exception):
    """Exception raised when database connection fails"""
    pass


class SQLServerConnectionError(Exception):
    """Exception raised when SQL Server connection fails"""
    pass


class AuthenticationError(HTTPException):
    """Exception raised for authentication errors"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(HTTPException):
    """Exception raised when user doesn't have required permissions"""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ResourceNotFoundError(HTTPException):
    """Exception raised when requested resource is not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class MCPServerError(Exception):
    """Exception raised when MCP server encounters an error"""
    pass


class AgentExecutionError(Exception):
    """Exception raised when an AI agent execution fails"""
    pass
