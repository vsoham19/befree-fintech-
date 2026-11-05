class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "bad_request", details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "extraction_failed", details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
