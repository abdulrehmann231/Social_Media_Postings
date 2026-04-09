from fastapi import FastAPI

app = FastAPI(title="Social Media Posting Agent")


@app.get("/health")
def health():
    return {"status": "ok"}
