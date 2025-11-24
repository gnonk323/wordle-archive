import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
from models import Game
from sync_engine import run_sync
from typing import Dict

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
  client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
  await init_beanie(database=client.wordle_app, document_models=[Game])
  yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost", "http://localhost:8080"], 
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "Wordle Archive API is running"}

@app.post("/sync")
async def sync_user_games():
  """Frontend sends the cookie, backend calculates missing dates and fills the DB"""
  try:
    cookie = os.getenv("NYT_COOKIE")
    # TODO: find a reasonable way to pass cookie from frontend
    result = await run_sync(cookie)
    return result
  except ValueError as e:
    return { "status": "error", "message": str(e) }
  except Exception as e:
    return { "status": "error", "message": "Internal server error during sync" }


@app.get("/games")
async def get_user_games() -> Dict:
  user_id = os.getenv("USER_ID")
  
  games = (
    await Game.find({
      "user_id": user_id,
      "game_data.status": {"$in": ["WIN", "FAIL"]}
    })
    .sort(-Game.print_date_date)
    .to_list()
  )

  latest = (
    await Game.find(Game.user_id == user_id)
    .sort(-Game.fetched_at)
    .first_or_none()
  )

  last_synced_at = latest.fetched_at if latest else None

  return {
    "user_id": user_id,
    "last_synced_at": last_synced_at,
    "games": games
  }