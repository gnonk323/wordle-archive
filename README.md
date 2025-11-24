# wordle-archive

A little app I wrote to run on my homelab to sync my Wordle stats from the NYT.

Keeps games I've played as MongoDB documents containing the print date, puzzle ID, guesses, game status, etc.

Syncs data by finding the most recently synced game and if there is a gap between then and now, grabs the puzzle data from the NYT and saves it to my database. First, because the archive data is not accessible via date, it uses the endpoint `https://www.nytimes.com/svc/wordle/v2/{date}.json` to get the ID which is then used alongside my NYT ID and cookies to query my personal archive data at `https://www.nytimes.com/svc/games/state/wordleV2/latests?puzzle_ids={ids}`. First, I figure out which dates I need, then loop on the first endpoint to gather the corresponding IDs. Then, I request the archive data in batches of 20 from the second endpoint, parse it, and save it to my database.

The dashboard has some summary info like the number of puzzles I've played, win-rate, and average guesses used. It also has a graph of guesses used over time.

<img width="3600" height="2016" alt="image" src="https://github.com/user-attachments/assets/001c1151-dfe2-40c9-a274-eb9afb6c9bd0" />
