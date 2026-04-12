#!/usr/bin/env python3
"""
Análisis de Google Trends para candidatos presidenciales de Perú.
Extrae datos de interés de búsqueda, genera gráficos y tablas comparativas.

Uso:
    python peru_trends.py          # Datos reales de Google Trends
    python peru_trends.py --demo   # Datos de demostración (sin conexión)
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Configuración de candidatos en dos batches (máx 5 keywords por request)
BATCH_1 = [
    "Jorge Nieto Montesinos",
    "Ricardo Belmont",
    "Carlos Espá",
    "Keiko Fujimori",
    "Rafael López Aliaga",
]

BATCH_2 = [
    "Roberto Sánchez",
    "Carlos Álvarez",
    "Alfonso López Chau",
]

ALL_CANDIDATES = BATCH_1 + BATCH_2
OUTPUT_DIR = "output"

# Colores distintivos para cada candidato
COLORS = [
    "#4285F4",  # Google Blue
    "#EA4335",  # Google Red
    "#FBBC04",  # Google Yellow
    "#34A853",  # Google Green
    "#FF6D01",  # Orange
    "#46BDC6",  # Teal
    "#7B1FA2",  # Purple
    "#C2185B",  # Pink
]


def generate_demo_data(timeframe):
    """Genera datos simulados para demostración cuando la API no está disponible."""
    if "1-d" in timeframe:
        periods = 24
        freq = "h"
    else:
        periods = 7 * 24
        freq = "h"

    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq=freq)
    np.random.seed(42)

    data = {}
    # Simular distintos niveles de interés por candidato
    base_levels = [25, 15, 10, 100, 80, 20, 12, 35]
    for i, candidate in enumerate(ALL_CANDIDATES):
        base = base_levels[i]
        noise = np.random.normal(0, base * 0.2, periods)
        trend = np.linspace(0, base * 0.1, periods)
        values = np.clip(base + noise + trend, 0, 100).round(2)
        data[candidate] = values

    df = pd.DataFrame(data, index=dates)
    df.index.name = "date"
    return df


def fetch_trends(timeframe, geo="PE"):
    """Descarga datos de Google Trends en dos batches y los combina."""
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl="es-PE", tz=300)

    # Batch 1
    print(f"  Descargando batch 1 ({len(BATCH_1)} keywords)...")
    pytrends.build_payload(BATCH_1, cat=0, timeframe=timeframe, geo=geo)
    df1 = pytrends.interest_over_time()
    if df1.empty:
        print("  ADVERTENCIA: Batch 1 retornó datos vacíos.")
        return pd.DataFrame()

    time.sleep(2)  # Pausa para no saturar la API

    # Batch 2
    print(f"  Descargando batch 2 ({len(BATCH_2)} keywords)...")
    pytrends.build_payload(BATCH_2, cat=0, timeframe=timeframe, geo=geo)
    df2 = pytrends.interest_over_time()
    if df2.empty:
        print("  ADVERTENCIA: Batch 2 retornó datos vacíos.")
        return pd.DataFrame()

    # Eliminar columna isPartial si existe
    for df in [df1, df2]:
        if "isPartial" in df.columns:
            df.drop(columns=["isPartial"], inplace=True)

    # Normalización global: ambos batches deben estar en escala 0-100
    # relativa al máximo global de todos los candidatos
    max1 = df1.max().max()
    max2 = df2.max().max()
    global_max = max(max1, max2) if max(max1, max2) > 0 else 1

    df1_norm = (df1 / global_max * 100).round(2)
    df2_norm = (df2 / global_max * 100).round(2)

    # Combinar en un solo DataFrame
    combined = df1_norm.join(df2_norm, how="outer")
    return combined


def save_csv(df, filename):
    """Guarda el DataFrame como CSV."""
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path)
    print(f"  CSV guardado: {path}")


def generate_chart(df, filename, title):
    """Genera un gráfico de líneas estilo Google Trends."""
    fig, ax = plt.subplots(figsize=(14, 6))

    for i, col in enumerate(df.columns):
        color = COLORS[i % len(COLORS)]
        ax.plot(df.index, df[col], label=col, color=color, linewidth=2)

    ax.set_xlabel("Tiempo", fontsize=11)
    ax.set_ylabel("Interés relativo (0-100)", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Leyenda abajo
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        fontsize=9,
        frameon=False,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout()

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Gráfico guardado: {path}")


def generate_markdown_table(df, filename):
    """Genera tabla markdown con estadísticas por candidato."""
    stats = []
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        stats.append({
            "Candidato": col,
            "Último valor": series.iloc[-1],
            "Promedio 24h": round(series.mean(), 2),
            "Máximo 24h": series.max(),
        })

    stats_df = pd.DataFrame(stats)
    stats_df.sort_values("Último valor", ascending=False, inplace=True)
    stats_df.reset_index(drop=True, inplace=True)

    # Generar markdown
    lines = []
    lines.append("# Tendencias de búsqueda - Candidatos Perú")
    lines.append("")
    lines.append("| Candidato | Último valor | Promedio | Máximo |")
    lines.append("|-----------|:-----------:|:-------:|:------:|")
    for _, row in stats_df.iterrows():
        lines.append(
            f"| {row['Candidato']} | {row['Último valor']} "
            f"| {row['Promedio 24h']} | {row['Máximo 24h']} |"
        )
    lines.append("")

    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Tabla guardada: {path}")


def run_analysis(timeframe, csv_name, chart_name, chart_title,
                 table_name=None, demo_mode=False):
    """Ejecuta el pipeline completo para un timeframe dado."""
    print(f"\n{'='*60}")
    print(f"Timeframe: {timeframe}")
    print(f"{'='*60}")

    if demo_mode:
        print("  [DEMO] Usando datos simulados.")
        df = generate_demo_data(timeframe)
    else:
        try:
            df = fetch_trends(timeframe)
        except Exception as e:
            print(f"  ERROR conectando a Google Trends: {e}")
            print("  Usando datos de demostración como fallback...")
            df = generate_demo_data(timeframe)

    if df.empty:
        print("  No se obtuvieron datos. Saltando esta corrida.")
        return

    save_csv(df, csv_name)
    generate_chart(df, chart_name, chart_title)

    if table_name:
        generate_markdown_table(df, table_name)


def main():
    demo_mode = "--demo" in sys.argv
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if demo_mode:
        print("Modo demostración activado (--demo).")
    else:
        print("Conectando a Google Trends (usa --demo para datos simulados).")

    # Corrida 1: últimas 24 horas
    run_analysis(
        timeframe="now 1-d",
        csv_name="trends_data.csv",
        chart_name="trends_chart.png",
        chart_title="Google Trends Perú - Candidatos (Últimas 24 horas)",
        table_name="trends_table.md",
        demo_mode=demo_mode,
    )

    if not demo_mode:
        time.sleep(3)  # Pausa entre corridas

    # Corrida 2: últimos 7 días
    run_analysis(
        timeframe="now 7-d",
        csv_name="trends_7d_data.csv",
        chart_name="trends_7d_chart.png",
        chart_title="Google Trends Perú - Candidatos (Últimos 7 días)",
        demo_mode=demo_mode,
    )

    print(f"\n{'='*60}")
    print(f"Análisis completado. Archivos en la carpeta '{OUTPUT_DIR}/'.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
