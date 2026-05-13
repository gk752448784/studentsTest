from fastapi import FastAPI

from backend.app.api.v1.essay_corrections import router as essay_corrections_router
from backend.app.api.v1.essay_templates import router as essay_templates_router


app = FastAPI(
    title="Students Essay Correction Backend",
    version="0.1.0",
)

app.include_router(essay_corrections_router, prefix="/api/v1")
app.include_router(essay_templates_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
