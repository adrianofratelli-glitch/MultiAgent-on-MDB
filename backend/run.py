import uvicorn

from app.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    # O bind do Uvicorn falha sem derrubar ou reutilizar um processo existente.
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)
