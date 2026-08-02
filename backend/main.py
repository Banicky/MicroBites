from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search(request: SearchRequest):
    print(request.query)
    return {"responseQuery": request.query}