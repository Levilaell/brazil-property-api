class APIError(Exception):
    """Base API exception"""
    status_code = 500
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        
    def __str__(self):
        return self.message
        
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['error'] = self.__class__.__name__
        return rv


class ValidationError(APIError):
    """Raised when request validation fails"""
    status_code = 400
    
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


class DatabaseError(APIError):
    """Raised when database operations fail"""
    status_code = 503
    
    def __init__(self, message):
        super().__init__(message)


class NotFoundError(APIError):
    """Raised when a resource is not found"""
    status_code = 404
    
    def __init__(self, message):
        super().__init__(message)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded"""
    status_code = 429
    
    def __init__(self, message, retry_after=60):
        super().__init__(message)
        self.retry_after = retry_after


class ExternalServiceError(APIError):
    """Raised when external service fails"""
    status_code = 502
    
    def __init__(self, message, service_name=None):
        super().__init__(message)
        self.service_name = service_name