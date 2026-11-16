from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import posting_service
from app.config import settings

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "Production-ready FastAPI application that validates and broadcasts short messages "
        "and marketing CTAs across multiple third-party social networks, community portals, "
        "and messaging platforms (Telegram, Discord, Slack, Mastodon, Bluesky) through their official APIs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-platform integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Format input validation errors into clear, actionable responses.
    """
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid input")
        # Remove standard Pydantic prefix "Value error, " if present
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        errors.append({
            "field": field or "body",
            "message": msg,
            "type": err.get("type", "validation_error")
        })

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "details": errors
        }
    )


@app.get(
    "/",
    tags=["Health & Info"],
    summary="Root Service Health Check",
    description="Check the service status and list of registered third-party platforms."
)
async def root():
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "mock_mode": settings.MOCK_MODE,
        "platforms": [p.name for p in posting_service.platforms],
        "endpoints": {
            "posting": "POST /posting",
            "documentation": "/docs"
        }
    }


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Posting"],
    summary="Publish short message across multi-platform integrations",
    description=(
        "Validates the incoming message (max 200 characters, exactly one valid CTA link) "
        "and automatically broadcasts it to all integrated platforms (Telegram, Discord, Slack, "
        "Mastodon, Bluesky) concurrently. Failure on one platform does not interrupt the others."
    )
)
async def create_posting(payload: PostingRequest) -> PostingResponse:
    """
    Publish a short message across all integrated platforms.
    """
    response = await posting_service.post_to_all(
        message=payload.message,
        cta_url=payload.cta_url
    )
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
