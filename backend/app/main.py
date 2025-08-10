from fastapi import FastAPI

from .api import api_router

app = FastAPI(title="Forge 1 Backend")
app.include_router(api_router)


