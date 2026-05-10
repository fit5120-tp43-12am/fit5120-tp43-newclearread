from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.api import router
from routes.text import router as text_router
from routes.morpheme import router as morpheme_router
from routes.dictionary import router as dictionary_router

app = FastAPI()

# Allow the frontend to call this backend during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Keep CORS open while the frontend and backend are developed separately.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the text-processing routes under the shared API prefix.
app.include_router(text_router, prefix="/api")
app.include_router(morpheme_router, prefix="/api")
app.include_router(dictionary_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "Backend is running!"}


def test():
    return {"message": "Hello from backend!"}

