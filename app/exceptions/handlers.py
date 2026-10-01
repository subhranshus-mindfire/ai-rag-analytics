from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status = getattr(exc, 'status_code', 500)
    return JSONResponse(status_code=status, content={"error": True, "message": str(exc)})

async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": True, "message": "Validation error", "details": exc.errors()})
