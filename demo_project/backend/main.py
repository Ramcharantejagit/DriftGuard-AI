from fastapi import FastAPI
import os

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

@app.get("/api/users")
def users():
    return [{"id": 1, "name": "Demo User"}]

@app.post("/api/login")
def login():
    print("debug login reached")
    return {"ok": True}

# TODO: add rate limiting before production
