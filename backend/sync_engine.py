import re
from typing import Dict, List
from models import Game
from datetime import date, timedelta, datetime
import requests


BASIC_INFO_URL = "https://www.nytimes.com/svc/wordle/v2/{date}.json"
STATE_INFO_URL = "https://www.nytimes.com/svc/games/state/wordleV2/latests?puzzle_ids={ids}"


def get_user_id_from_cookie(cookie_str: str) -> str:
  match = re.search(r'regi_id=(\d+)', cookie_str)
  if match:
    user_id = match.group(1)
    print(f"Extracted user ID: {user_id}")
    return user_id
  raise ValueError("Could not find 'regi_id' in the provided cookie string.")


def parse_cookies(cookie_str: str) -> Dict[str, str]:
  return dict(item.split("=", 1) for item in cookie_str.split("; "))


async def get_last_synced_date(user_id: str) -> date:
  """Queries MongoDB for the most recent game date for this user."""
  # Sort by print_date descending and get the first one
  latest_game = await Game.find(Game.user_id == user_id).sort("-print_date").first_or_none()
  
  if not latest_game:
    # Return the day BEFORE NYT Wordle started if no data exists
    print(f"No latest sync found, loading everything.")
    return date(2021, 6, 18)
  
  latest_sync = date.fromisoformat(latest_game.print_date)
  print(f"Last synced date: {latest_sync}")
  return latest_sync


def fetch_nyt_ids_for_range(start_date: date, end_date: date) -> Dict[int, Dict]:
  """Returns a dict mapping { puzzle_id: { print_date: 'YYYY-MM-DD', solution: string } }"""
  puzzle_map: Dict[int, Dict] = {}
  current_date = start_date

  print(f"Fetching NYT game IDs for range {start_date} to {end_date}...")

  while current_date <= end_date:
    date_str = current_date.strftime("%Y-%m-%d")
    try:
      response = requests.get(BASIC_INFO_URL.format(date=date_str), timeout=5)
      response.raise_for_status()
      data = response.json()
      p_id = data.get("id")
      if p_id is not None:
        puzzle_map[int(p_id)] = {
          "print_date": date_str,
          "solution": data.get("solution")
        }
    except Exception as e:
      print(f"Error fetching ID for date {date_str}: {e}")

    current_date += timedelta(days=1)

  print("Done.")
  return puzzle_map

def fetch_game_states(ids: List[int], cookies: Dict) -> List[Dict]:
  """Fetches the actual game data for a list of game IDs"""
  if not ids: return []

  print(f"Fetching game data for {len(ids)} ids: {ids}")

  id_str = ",".join(map(str, ids))
  url = STATE_INFO_URL.format(ids=id_str)

  try:
    response = requests.get(url, cookies=cookies, timeout=10)
    response.raise_for_status()
    states = response.json().get("states", [])
    print(f"Found data for {len(states)} games.")
    return response.json().get("states", [])
  except Exception as e:
    print(f"Error fetching states: {e}")
    return []
  

async def run_sync(nyt_cookie: str):
  print(f"Syncing game data...")

  user_id = get_user_id_from_cookie(nyt_cookie)
  cookie_dict = parse_cookies(nyt_cookie)

  last_date = await get_last_synced_date(user_id)
  today = date.today()
  start_date = last_date + timedelta(days=1)

  if start_date > today:
    return { "status": "already_up_to_date", "added": 0 }
  
  puzzle_map = fetch_nyt_ids_for_range(start_date, today)
  puzzle_ids = list(puzzle_map.keys())

  if not puzzle_ids:
    return { "status": "no_ids_found", "added": 0 }
  
  BATCH_SIZE = 20
  new_docs = []

  for i in range(0, len(puzzle_ids), BATCH_SIZE):
    batch_ids = puzzle_ids[i:i+BATCH_SIZE]
    states = fetch_game_states(batch_ids, cookie_dict)

    for state in states:
      p_id_int = int(state.get("puzzle_id"))
      p_info = puzzle_map.get(p_id_int)
      p_date_str = p_info["print_date"]
      solution = p_info.get("solution")
      p_date_date = datetime.strptime(p_date_str, "%Y-%m-%d").date()

      if p_date_str:
        new_docs.append(Game(
          user_id=user_id,
          print_date=p_date_str,
          print_date_date=p_date_date,
          solution=solution,
          puzzle_id=p_id_int,
          game_data=state["game_data"]
        ))
        print(f"Added {p_id_int} ({p_date_str}) to new_docs")

  if new_docs:
    try:
      print(f"Inserting {len(new_docs)} new documents...")
      await Game.insert_many(new_docs)
    except Exception as e:
      print(f"Bulk write warning: {e}")

  return { "status": "success", "added": len(new_docs), "last_synced_at": datetime.today() }