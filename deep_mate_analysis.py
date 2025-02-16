import chess
import chess.engine
import sqlite3
import argparse
from tqdm import tqdm

def update_puzzles(engine_path: str, time_limit: float, depth: int, threads: int, hash_size: int, database_path: str) -> None:
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, fen, n FROM mate_positions")
    puzzles = cursor.fetchall()
    
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        engine.configure({"Threads": threads, "Hash": hash_size})
        updated_count = 0
        removed_count = 0
        total_count = len(puzzles)
        
        for puzzle in tqdm(puzzles, desc="Processing puzzles", unit="puzzle"):
            puzzle_id, fen, stored_n = puzzle
            board = chess.Board(fen)
            try:
                analysis = engine.analyse(board, chess.engine.Limit(depth=depth, time=time_limit))
            except Exception as e:
                print(f"Error analyzing puzzle id {puzzle_id}: {e}")
                continue

            score = analysis["score"].pov(board.turn)
            new_mate = score.mate()
            if new_mate is None:
                cursor.execute("DELETE FROM mate_positions WHERE id = ?", (puzzle_id,))
                conn.commit()
                removed_count += 1
                print(f"Removed puzzle id {puzzle_id}: No mate found.")
                continue

            new_n = abs(new_mate)
            if new_n != stored_n:
                cursor.execute("UPDATE mate_positions SET n = ? WHERE id = ?", (new_n, puzzle_id))
                conn.commit()
                updated_count += 1
                print(f"Updated puzzle id {puzzle_id}: n changed from {stored_n} to {new_n}")
        
        print(f"Processed {total_count} puzzles: Updated {updated_count}, Removed {removed_count}.")
    conn.close()


parser = argparse.ArgumentParser(description="Update mate puzzles with deeper analysis.")
parser.add_argument("--engine", type=str, default='../stockfish/stockfish-ubuntu-x86-64-avx2',
                    help="Path to the Stockfish engine executable.")
parser.add_argument("--time", type=float, default=60.0,
                    help="Time limit for analysis in seconds (default: 60.0).")
parser.add_argument("--depth", type=int, default=75,
                    help="Depth limit for analysis (default: 75).")
parser.add_argument("--threads", type=int, default=10,
                    help="Number of threads for Stockfish (default: 10).")
parser.add_argument("--hash", type=int, default=8192,
                    help="Hash size for Stockfish in MB (default: 8192).")
parser.add_argument("--db", type=str, default="../puzzles.db",
                    help="Path to the SQLite database (default: ../puzzles.db).")
args = parser.parse_args()
update_puzzles(args.engine, args.time, args.depth, args.threads, args.hash, args.db)
