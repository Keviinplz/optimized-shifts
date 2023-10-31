from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from optimized_shifts.handlers.errors import handle_pydantic_validation_exception
from optimized_shifts.lifespan import lifespan
from optimized_shifts.routes.v1 import router as v1_router

app = FastAPI(lifespan=lifespan)
app.include_router(v1_router, prefix="/api")
app.add_exception_handler(RequestValidationError, handle_pydantic_validation_exception)  # type: ignore
