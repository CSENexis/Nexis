from fastapi import FastAPI

app = FastAPI(title="Nexis Auth API")

@app.get("/health")
def health():
    return {"status": "ok"}