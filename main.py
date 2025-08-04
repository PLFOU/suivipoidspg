import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from datetime import date, timedelta

DB_PATH = "poids_tracker.db"

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM measures ORDER BY date", conn, parse_dates=['date'])
    conn.close()
    return df

def insert_data(selected_date, poids):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO measures (date, poids)
        VALUES (?, ?)
    """, (selected_date.isoformat(), poids))
    conn.commit()
    conn.close()

def create_full_date_range(df):
    if df.empty:
        return pd.DataFrame(columns=["date", "poids"])
    start = df['date'].min()
    end = df['date'].max()
    full_range = pd.DataFrame({"date": pd.date_range(start, end)})
    merged = full_range.merge(df, how='left', on='date')
    return merged

def weekly_fixed_avg(df):
    df = df.set_index('date')
    # Groupe par semaine fixe (lundi au dimanche)
    weekly = df['poids'].resample('W-MON').mean().reset_index().sort_values('date')
    return weekly

def rolling_avg(df, window=7):
    df = df.sort_values('date').set_index('date')
    rolling = df['poids'].rolling(window=window, min_periods=1).mean().reset_index()
    return rolling

def objectif_line(start_date, end_date, start_weight, end_weight):
    dates = pd.date_range(start_date, end_date)
    poids = pd.Series(np.linspace(start_weight, end_weight, len(dates)))
    return pd.DataFrame({"date": dates, "objectif": poids})

# --- Interface Streamlit ---

st.title("📊 Suivi du poids")

with st.form("add_poids_form"):
    st.subheader("Ajouter une mesure de poids")
    selected_date = st.date_input("Date", value=date.today())
    poids = st.number_input("Poids (kg)", min_value=0.0, step=0.1, format="%.2f")
    submit = st.form_submit_button("Ajouter")
    if submit:
        insert_data(selected_date, poids)
        st.success(f"Poids {poids} kg ajouté pour le {selected_date}.")
        st.experimental_rerun()

df = load_data()

if df.empty:
    st.warning("Aucune donnée enregistrée pour l'instant.")
else:
    # Compléter avec toutes les dates (poids manquant = NaN)
    df_full = create_full_date_range(df)

    # Calcul des moyennes
    weekly_avg = weekly_fixed_avg(df_full)
    rolling_avg_7 = rolling_avg(df_full)

    # Courbe objectif
    start_obj_date = pd.to_datetime("2025-02-07")
    end_obj_date = pd.to_datetime("2025-08-31")
    objectif = objectif_line(start_obj_date, end_obj_date, 85.5, 70)

    # Figure Plotly
    fig = go.Figure()

    # Poids quotidien
    fig.add_trace(go.Scatter(
        x=df_full['date'], y=df_full['poids'],
        mode='lines+markers',
        name='Poids quotidien',
        line=dict(color='blue'),
        connectgaps=True  # pour relier les jours sans données (interpolé)
    ))

    # Moyenne hebdo fixe (lundi)
    fig.add_trace(go.Scatter(
        x=weekly_avg['date'], y=weekly_avg['poids'],
        mode='lines+markers',
        name='Moyenne hebdo (lundi-dimanche)',
        line=dict(color='orange', width=3)
    ))

    # Moyenne glissante 7 jours
    fig.add_trace(go.Scatter(
        x=rolling_avg_7['date'], y=rolling_avg_7['poids'],
        mode='lines',
        name='Moyenne glissante 7j',
        line=dict(color='green', dash='dash')
    ))

    # Objectif
    fig.add_trace(go.Scatter(
        x=objectif['date'], y=objectif['objectif'],
        mode='lines',
        name='Objectif',
        line=dict(color='red', dash='dot')
    ))

    fig.update_layout(
        title="Évolution du poids avec moyennes et objectif",
        xaxis_title="Date",
        yaxis_title="Poids (kg)",
        legend_title="Légende",
        hovermode="x unified",
        template="plotly_white",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # Affichage tableau
    st.subheader("Données brutes")
    st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)
