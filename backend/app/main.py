from fastapi import FastAPI

app = FastAPI(title="MediTrack Agent API")

@app.get("/")
def root():
    return {"message": "MediTrack Agent backend is running"}