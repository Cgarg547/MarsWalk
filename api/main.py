from fastapi import FastAPI

app = FastAPI(
    title="MarsWalk API",
    description="Explainable Mars mission-planning API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "project": "MarsWalk",
        "status": "online",
        "region": "Jezero Crater",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}