import chess
import chess.engine
import chess.pgn
import sqlite3
import argparse

def process_pgn(pgn_path: str, engine_path: str, analysis_time: float = 0.1, database_path: str = 'puzzles.db') -> None:
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mate_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_url TEXT,
            fen TEXT,
            n INTEGER
        )
    """)
    connection.commit()

    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine, open(pgn_path, "r", encoding="utf-8") as pgn_file:
        games_processed = 0
        mate_positions_found = 0

        for game in iter(lambda: chess.pgn.read_game(pgn_file), None):
            games_processed += 1
            game_url = game.headers.get("Site", "Unknown")
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
                try:
                    analysis = engine.analyse(board, chess.engine.Limit(time=analysis_time))
                except Exception as error:
                    print(f"Error analyzing game {games_processed}: {error}")
                    continue

                score = analysis["score"].pov(board.turn)
                if score.mate() is not None:
                    try:
                        deep_score = engine.analyse(board, chess.engine.Limit(depth=30))["score"].pov(board.turn)
                    except Exception as error:
                        print(f"Error in deep analysis for game {games_processed}: {error}")
                        continue
                    mate_depth = deep_score.mate()
                    if mate_depth is not None and mate_depth > 0:
                        mate_positions_found += 1
                        cursor.execute(
                            "INSERT INTO mate_positions (game_url, fen, n) VALUES (?, ?, ?)",
                            (game_url, board.fen(), abs(mate_depth))
                        )
                        connection.commit()

        print(f"Processed {games_processed} games, found {mate_positions_found} mate positions.")
    connection.close()


parser = argparse.ArgumentParser(description="Search a PGN file for mate positions using Stockfish analysis.")
parser.add_argument("--pgn", type=str, default='lichess_games.pgn',
                    help="Path to the PGN file containing chess games.")
parser.add_argument("--engine", type=str, default='stockfish/stockfish-ubuntu-x86-64-avx2',
                    help="Path to the Stockfish engine executable.")
parser.add_argument("--time", type=float, default=0.1,
                    help="Analysis time per position in seconds.")
args = parser.parse_args()
process_pgn(args.pgn, args.engine, args.time)
