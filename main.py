from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
def startup():
    print("Python service started")

@app.get("/")
def root():
    return {"message": "Hello from Python"}

@app.get("/test")
def test():
    return {"status": "test endpoint working"}
