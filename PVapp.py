import requests
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Clipping FV – Comunidad de Madrid (PVGIS)",
                   page_icon="🔆", layout="wide")

st.title("🔆 ¿Cuánto pierdo por clipping?  Fotovoltaica + Inversor")
st.caption("Serie horaria desde PVGIS | Modelo FV sencillo | Simulación de clipping por ratio DC/AC")

# ========================== Sidebar ==========================
with st.sidebar:
    st.header("Parámetros de entrada")

    # Diccionario con provincias españolas y coordenadas (aprox capital)
provincias = {
    "Madrid": (40.4168, -3.7038),
    "Barcelona": (41.3874, 2.1686),
    "Valencia": (39.4699, -0.3763),
    "Sevilla": (37.3891, -5.9845),
    "Zaragoza": (41.6488, -0.8891),
    "Málaga": (36.7213, -4.4214),
    "Murcia": (37.9834, -1.1299),
    "Palma de Mallorca": (39.5696, 2.6502),
    "Las Palmas": (28.1235, -15.4363),
    "Bilbao": (43.2630, -2.9350),
    "A Coruña": (43.3623, -8.4115),
    "Oviedo": (43.3619, -5.8494),
    "Santander": (43.4623, -3.8099),
    "Valladolid": (41.6523, -4.7245),
    "Salamanca": (40.9701, -5.6635),
    "Toledo": (39.8628, -4.0273),
    "Ciudad Real": (38.9863, -3.9291),
    "Albacete": (38.9943, -1.8585),
    "Alicante": (38.3452, -0.4810),
    "Cádiz": (36.5297, -6.2927),
    "Granada": (37.1773, -3.5986),
    "Córdoba": (37.8882, -4.7794),
    "Badajoz": (38.8794, -6.9707),
    "León": (42.5987, -5.5671),
    "Burgos": (42.3439, -3.6969),
    "San Sebastián": (43.3183, -1.9812),
    "Pamplona": (42.8125, -1.6458),
    "Logroño": (42.4660, -2.4456),
    "Huesca": (42.1401, -0.4089),
    "Lleida": (41.6176, 0.6200),
    "Tarragona": (41.1189, 1.2445),
    "Girona": (41.9794, 2.8214),
    "Castellón": (39.9864, -0.0513),
    "Ceuta": (35.8894, -5.3213),
    "Melilla": (35.2923, -2.9381)
}

opcion = st.selectbox("Selecciona provincia", list(provincias.keys()) + ["Personalizada…"])

if opcion == "Personalizada…":
    lat = st.number_input("Latitud", value=40.4168, format="%.5f")
    lon = st.number_input("Longitud", value=-3.7038, format="%.5f")
else:
    lat, lon = provincias[opcion]


    year = st.number_input("Año (PVGIS)", 2005, 2025, 2022, 1)

    # Geometría del generador (para pedir G(i) a PVGIS)
    tilt = st.slider("Inclinación (°)", 0, 60, 25)
    az   = st.slider("Azimut (°) 0=Sur; +Este, -Oeste", -90, 90, 0)

    # Generador FV
    kwp   = st.number_input("Potencia pico DC (kWp)", 0.5, 10000.0, 10.0, 0.5)
    PR    = st.slider("Performance Ratio", 0.60, 0.95, 0.85, 0.01)
    gamma = st.number_input("Coef. temperatura γ (1/°C)", -0.0100, -0.0010, -0.0045, step=0.0001, format="%.4f")
    NOCT  = st.number_input("NOCT (°C)", 35.0, 60.0, 45.0, 0.5)

    # Inversor
    dc_ac = st.slider("Ratio DC/AC", 1.00, 1.60, 1.20, 0.05)
    eta   = st.slider("Eficiencia inversor η", 0.90, 0.995, 0.97, 0.001)

    st.markdown("---")
    st.caption("Fuente: PVGIS (endpoint seriescalc, base SARAH). Modelo educativo (no bancable).")

# ========================== Helpers ==========================
@st.cache_data(show_spinner=True, ttl=60*60)
@st.cache_data(show_spinner=True, ttl=60*60)
@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_pvgis_series(lat: float, lon: float, year: int, tilt: float, az: float) -> pd.DataFrame:
    url = (
        "https://re.jrc.ec.europa.eu/api/seriescalc"
        f"?lat={lat:.5f}&lon={lon:.5f}"
        f"&startyear={year}&endyear={year}"
        "&radDatabase=PVGIS-SARAH"        # 
        "&outputformat=json"
        f"&angle={tilt:.1f}&aspect={az:.1f}"
        "&pvcalculation=0"
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["outputs"]["hourly"])

    # Renombrar a nombres claros si existen
    rename = {
        "G(hor)": "GHI",
        "G(h)":   "GHI",
        "Gb(n)":  "DNI",
        "Gd(h)":  "DIF",
        "G(i)":   "G_TILT",
        "T2m":    "T2m",
        "time":   "time"
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # ---- Parseo robusto de tiempo ----
    t = df["time"].astype(str)

    # Caso 1: formato compacto de PVGIS: YYYYMMDD:HHMM (ej. 20220101:0010)
    mask_compacto = t.str.match(r"^\d{8}:\d{4}$")
    if mask_compacto.all():
        dt = pd.to_datetime(t, format="%Y%m%d:%H%M", utc=True)

    # Caso 2: ISO (ej. 2022-01-01T00:10Z)
    elif t.str.contains("T").any():
        dt = pd.to_datetime(t, utc=True, errors="raise")

    # Fallback: intenta inferir
    else:
        dt = pd.to_datetime(t, utc=True, errors="coerce")

    df = df.drop(columns=["time"]).assign(time=dt).set_index("time").sort_index()

    # Columnas mínimas necesarias
    if "G_TILT" not in df.columns:
        st.warning("PVGIS no devolvió G(i); se aproxima con GHI (simplificado).")
        if "GHI" in df.columns:
            df["G_TILT"] = df["GHI"].clip(lower=0)
        else:
            df["G_TILT"] = 0.0

    if "T2m" not in df.columns:
        df["T2m"] = 20.0

    # Asegura que existan las columnas usadas aguas abajo
    for c in ["GHI", "DNI", "DIF"]:
        if c not in df.columns:
            df[c] = np.nan

    return df[["GHI", "DNI", "DIF", "G_TILT", "T2m"]]

def pv_dc_from_irr(df: pd.DataFrame, kwp: float, PR: float, gamma: float, NOCT: float) -> pd.DataFrame:
    """Modelo FV sencillo para potencia DC."""
    G = df["G_TILT"].values          # W/m2
    T = df["T2m"].values             # °C
    Tcell = T + (NOCT - 20.0)/800.0 * G
    Pdc = kwp * PR * (G/1000.0) * (1.0 + gamma*(Tcell - 25.0))
    Pdc = np.clip(Pdc, 0.0, None)
    out = df.copy()
    out["T_cell"] = Tcell
    out["P_DC_kW"] = Pdc
    return out

def inverter_clip(df: pd.DataFrame, kwp: float, dc_ac: float, eta: float):
    """Aplica clipping del inversor y devuelve DF con P_AC y CLIP."""
    Pnom = kwp / dc_ac
    Pac = np.minimum(eta * df["P_DC_kW"].values, Pnom)
    clip = np.maximum(eta * df["P_DC_kW"].values - Pac, 0.0)
    out = df.copy()
    out["P_AC_kW"] = Pac
    out["CLIP_kW"] = clip
    return out, Pnom

def month_sum(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].groupby(df.index.month).sum()

# ========================== Pipeline ==========================
with st.spinner("Descargando serie horaria de PVGIS…"):
    df_sr = fetch_pvgis_series(lat, lon, year, tilt, az)

df_dc = pv_dc_from_irr(df_sr, kwp=kwp, PR=PR, gamma=gamma, NOCT=NOCT)
df_ac, P_nom = inverter_clip(df_dc, kwp=kwp, dc_ac=dc_ac, eta=eta)

# ========================== Visual 1: día pico ==========================
col1, col2 = st.columns([1.3, 1])
with col1:
    st.subheader("Curvas del día más productivo (DC / AC / Clipping)")
    best_day = df_ac["P_DC_kW"].resample("D").sum().idxmax()
    day = df_ac.loc[str(best_day.date())].copy()
    day["hour"] = day.index.hour

    base = alt.Chart(day.reset_index()).encode(x=alt.X("hour:O", title="Hora"))
    c_dc  = base.mark_line().encode(y=alt.Y("P_DC_kW:Q", title="Potencia [kW]"), color=alt.value("#1f77b4"))
    c_ac  = base.mark_line().encode(y="P_AC_kW:Q", color=alt.value("#2ca02c"))
    c_clip= base.mark_bar(opacity=0.55).encode(y="CLIP_kW:Q", color=alt.value("#d62728"))

    st.altair_chart((c_dc + c_ac + c_clip).properties(height=320), use_container_width=True)

with col2:
    st.subheader("Resumen del día pico")
    st.metric("P_inv_nom [kW]", f"{P_nom:.2f}")
    st.metric("Energía DC [kWh]", f"{day['P_DC_kW'].sum():.1f}")
    st.metric("Clipping [kWh]", f"{day['CLIP_kW'].sum():.1f}")
    st.metric("Energía AC [kWh]", f"{day['P_AC_kW'].sum():.1f}")
st.caption(f"Día pico: {best_day.date()} · DC/AC={dc_ac:.2f} · η={eta:.3f} · P_inv_nom={P_nom:.2f} kW")

st.markdown("---")

# ========================== Visual 2: heatmap DC/AC ==========================
st.subheader("Heatmap — Pérdidas por clipping [kWh/mes] vs. DC/AC")
dcac_vec = np.round(np.arange(1.00, 1.65, 0.05), 2)
rows = []
for r in dcac_vec:
    tmp, _ = inverter_clip(df_dc, kwp=kwp, dc_ac=float(r), eta=eta)
    msum = month_sum(tmp, "CLIP_kW")
    for mes, val in msum.items():
        rows.append({"Mes": int(mes), "DC/AC": float(r), "Clip_kWh_mes": float(val)})
heat = pd.DataFrame(rows)

heat_chart = (
    alt.Chart(heat)
    .mark_rect()
    .encode(
        x=alt.X("DC/AC:O"),
        y=alt.Y("Mes:O"),
        color=alt.Color("Clip_kWh_mes:Q", scale=alt.Scale(scheme="viridis")),
        tooltip=["Mes","DC/AC",alt.Tooltip("Clip_kWh_mes:Q", format=".1f")]
    )
    .properties(height=360)
)
st.altair_chart(heat_chart, use_container_width=True)

st.markdown("---")

# ========================== Visual 3: resumen mensual ==========================
st.subheader("Resumen mensual (kWh)")
summary = pd.DataFrame({
    "E_DC_kWh": month_sum(df_ac, "P_DC_kW"),
    "E_AC_kWh": month_sum(df_ac, "P_AC_kW"),
    "Clip_kWh": month_sum(df_ac, "CLIP_kW"),
})
summary.index.name = "Mes"
st.dataframe(summary.style.format("{:.1f}"), use_container_width=True)

# Descarga CSV
csv = summary.to_csv(index=True).encode("utf-8")
st.download_button("⬇️ Descargar resumen mensual (CSV)", data=csv,
                   file_name="resumen_mensual_clipping.csv", mime="text/csv")

st.caption("Sugerencia: graba un vídeo corto moviendo el slider DC/AC y súbelo a LinkedIn junto al enlace de tu app.")

# --- Footer fijo abajo ---
st.markdown("""
<style>
.footer {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  width: 100%;
  text-align: center;
  padding: 6px 0;
  font-size: 13px;
  color: #666;
  background: rgba(255,255,255,0.75);
  border-top: 1px solid #eee;
}
</style>
<div class="footer">Made by Jordan</div>
""", unsafe_allow_html=True)





