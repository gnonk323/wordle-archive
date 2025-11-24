from beanie import Document, Indexed
from datetime import datetime
from typing import Optional, Dict, Any
from datetime import date

class Game(Document):
  user_id: Indexed(str) # Create an index for fast user lookups
  print_date: str 
  print_date_date: date
  solution: str
  puzzle_id: int
  game_data: Dict[str, Any]
  fetched_at: datetime = datetime.now()

  class Settings:
    name = "user_games"
    # Unique constraint: One user cannot have two games for the same date
    indexes = [
      [("user_id", 1), ("print_date", 1)]
    ]