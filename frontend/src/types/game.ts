import { ObjectId } from "mongodb";

export type Game = {
  _id: ObjectId;
  user_id: string;
  print_date: string;
  puzzle_id: number;
  solution: string;
  game_data: {
    boardState: {
      0: string;
      1: string;
      2: string;
      3: string;
      4: string;
      5: string;
    }
    currentRowIndex: 1 | 2 | 3 | 4 | 5 | 6;
    hardMode: boolean;
    status: "WIN" | "FAIL" | "IN_PROGRESS";
  }
  fetched_at: Date;
}
