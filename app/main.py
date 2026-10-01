from app.starter import start_application

app = start_application()

if __name__ == "__main__":
    import uvicorn
    from app.config.env_config import settings
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
