from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "basketball_stats.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-before-class-demo"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            jersey_number INTEGER,
            team_name TEXT NOT NULL,
            position TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            game_date TEXT NOT NULL,
            opponent TEXT NOT NULL,
            free_throws INTEGER NOT NULL DEFAULT 0,
            steals INTEGER NOT NULL DEFAULT 0,
            two_pt_makes INTEGER NOT NULL DEFAULT 0,
            three_pt_makes INTEGER NOT NULL DEFAULT 0,
            turnovers INTEGER NOT NULL DEFAULT 0,
            rebounds INTEGER NOT NULL DEFAULT 0,
            assists INTEGER NOT NULL DEFAULT 0,
            fouls INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        );
        """
    )
    db.commit()


def safe_int(form_value: str) -> int:
    try:
        value = int(form_value)
        return max(value, 0)
    except (TypeError, ValueError):
        return 0


@app.route("/")
def index() -> str:
    db = get_db()
    players = db.execute(
        """
        SELECT
            p.id,
            p.player_name,
            p.jersey_number,
            p.team_name,
            p.position,
            COUNT(gs.id) AS games_played,
            COALESCE(SUM(gs.free_throws), 0) AS free_throws,
            COALESCE(SUM(gs.steals), 0) AS steals,
            COALESCE(SUM(gs.two_pt_makes), 0) AS two_pt_makes,
            COALESCE(SUM(gs.three_pt_makes), 0) AS three_pt_makes,
            COALESCE(SUM(gs.turnovers), 0) AS turnovers,
            COALESCE(SUM(gs.rebounds), 0) AS rebounds,
            COALESCE(SUM(gs.assists), 0) AS assists,
            COALESCE(SUM(gs.fouls), 0) AS fouls,
            COALESCE(SUM(gs.free_throws + (gs.two_pt_makes * 2) + (gs.three_pt_makes * 3)), 0) AS total_points
        FROM players p
        LEFT JOIN game_stats gs ON p.id = gs.player_id
        GROUP BY p.id
        ORDER BY p.player_name;
        """
    ).fetchall()
    return render_template("index.html", players=players)


@app.route("/add_player", methods=["GET", "POST"])
def add_player() -> str:
    if request.method == "POST":
        player_name = request.form.get("player_name", "").strip()
        team_name = request.form.get("team_name", "").strip()
        jersey_number = request.form.get("jersey_number", "").strip()
        position = request.form.get("position", "").strip()

        if not player_name or not team_name:
            flash("Player name and team name are required.")
            return redirect(url_for("add_player"))

        db = get_db()
        db.execute(
            """
            INSERT INTO players (player_name, jersey_number, team_name, position)
            VALUES (?, ?, ?, ?)
            """,
            (
                player_name,
                safe_int(jersey_number) if jersey_number else None,
                team_name,
                position,
            ),
        )
        db.commit()
        flash("Player added successfully.")
        return redirect(url_for("index"))

    return render_template("add_player.html")
