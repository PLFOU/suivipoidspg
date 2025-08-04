import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import streamlit as st

DB_FILE = "poids_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS measures (
                    date TEXT PRIMARY KEY,
                    poids REAL,
                    taille REAL,
                    poitrine REAL
                )''')
    conn.commit()
    conn.close()

def add_measurement(date_str, poids, taille, poitrine):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO measures (date, poids, taille, poitrine) VALUES (?, ?, ?, ?)",
              (date_str.isoformat(), poids, taille, poitrine))
    conn.commit()
    conn.close()

def get_measurements():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM measures ORDER BY date", conn, parse_dates=["date"])
    conn.close()
    return df

def plot_weight_graph(df):
    df = df.dropna(subset=["poids"])
    df = df.sort_values("date")
    df["poids"] = df["poids"].astype(float)

    # Moyenne glissante sur 7 jours
    df["glissante_7j"] = df["poids"].rolling(window=7).mean()

    # Moyenne hebdo fixe du lundi au dimanche
    df["semaine"] = df["date"].dt.to_period("W-MON")
    weekly = df.groupby("semaine")["poids"].mean().reset_index()
    weekly["date"] = weekly["semaine"].dt.start_time

    # Tendance (régression linéaire)
    x = (df["date"] - df["date"].min()).dt.days.values.reshape(-1, 1)
    y = df["poids"].values
    if len(x) >= 2:
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit(x, y)
        df["tendance"] = model.predict(x)

    # Courbe objectif
    objectif_start = datetime.date(2025, 2, 7)
    objectif_end = datetime.date(2025, 9, 1)
    objectif_x = pd.date_range(objectif_start, objectif_end)
    objectif_y = np.linspace(85.5, 70, len(objectif_x))

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["date"], df["poids"], label="Poids quotidien", color="blue")
    ax.plot(df["date"], df["glissante_7j"], label="Moyenne glissante 7j", color="orange")
    ax.plot(weekly["date"], weekly["poids"], label="Moyenne hebdo fixe", color="green", marker="o")
    if "tendance" in df:
        ax.plot(df["date"], df["tendance"], label="Tendance", linestyle="--", color="purple")
    ax.plot(objectif_x, objectif_y, label="Objectif", linestyle=":", color="red")

    ax.set_ylabel("Poids (kg)")
    ax.set_xlabel("Date")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)
