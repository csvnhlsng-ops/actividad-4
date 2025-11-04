# ============================================================
# Mortalidad en Colombia 2019 - Streamlit App
# ============================================================

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import numpy as np

# ============================================================
# Configuración general de la app
# ============================================================
st.set_page_config(page_title="Mortalidad en Colombia 2019", layout="wide")

st.title("📊 Análisis de Mortalidad en Colombia – 2019")
st.markdown("**Autores:** Luis Alejandro Jiménez (G2) – Cristhian Buitrago (G1)")
st.markdown("---")

# ============================================================
# 1️⃣ Carga de datos
# ============================================================
@st.cache_data
def cargar_datos():
    mortalidad = pd.read_excel("datos/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
    codigos = pd.read_excel("datos/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
    municipios = pd.read_excel("datos/Divipola_CE_.xlsx")
    dep_col = gpd.read_file("datos/shapes/departamento/MGN_DPTO_POLITICO.shp")
    return mortalidad, codigos, municipios, dep_col

mortalidad, codigos, municipios, dep_col = cargar_datos()

# ============================================================
# 2️⃣ Limpieza y preparación de los datos
# ============================================================
mortalidad["COD_DEPARTAMENTO"] = mortalidad["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
mortalidad["COD_MUNICIPIO"] = mortalidad["COD_MUNICIPIO"].astype(str).str.zfill(3)

municipios = municipios[["COD_DEPARTAMENTO", "COD_MUNICIPIO", "MUNICIPIO"]]
municipios["COD_DEPARTAMENTO"] = municipios["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
municipios["COD_MUNICIPIO"] = municipios["COD_MUNICIPIO"].astype(str).str.zfill(3)

base = mortalidad.merge(municipios, on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"], how="left")
base = pd.merge(base, codigos, left_on="COD_MUERTE", right_on="Código de la CIE-10 cuatro caracteres", how="left")

base["SEXO"] = base["SEXO"].map({1: "Masculino", 2: "Femenino", 3: "Indeterminado"})

# Grupo de edad simplificado
condiciones = [
    base['GRUPO_EDAD1'].between(0, 4),
    base['GRUPO_EDAD1'].between(5, 6),
    base['GRUPO_EDAD1'].between(7, 8),
    base['GRUPO_EDAD1'].between(9, 10),
    base['GRUPO_EDAD1'] == 11,
    base['GRUPO_EDAD1'].between(12, 13),
    base['GRUPO_EDAD1'].between(14, 16),
    base['GRUPO_EDAD1'].between(17, 19),
    base['GRUPO_EDAD1'].between(20, 24),
    base['GRUPO_EDAD1'].between(25, 28),
    base['GRUPO_EDAD1'] == 29
]
valores = [
    "Menor de 1 mes", "1 a 11 meses", "1 a 4 años", "5 a 14 años", "15 a 19 años",
    "20 a 29 años", "30 a 44 años", "45 a 59 años", "60 a 84 años", "85+ años", "Sin información"
]
base["RANGO_EDAD"] = np.select(condiciones, valores, default="Sin información")

# ============================================================
# 3️⃣ Mapas y visualizaciones
# ============================================================

# --- Total por departamento ---
dep_totales = base.groupby("COD_DEPARTAMENTO").size().reset_index(name="Total_muertes")
dep_col["DPTO_CCDGO"] = dep_col["DPTO_CCDGO"].astype(str).str.zfill(2)
resultado_mapa = dep_col.merge(dep_totales, left_on="DPTO_CCDGO", right_on="COD_DEPARTAMENTO", how="left")

# --- Mapa ---
geojson_dep = resultado_mapa.to_crs(epsg=4326).__geo_interface__
fig_mapa = px.choropleth(
    resultado_mapa,
    geojson=geojson_dep,
    locations="DPTO_CCDGO",
    color="Total_muertes",
    hover_name="DPTO_CNMBR",
    color_continuous_scale="Reds",
    title="🗺️ Total de Muertes por Departamento (2019)"
)
fig_mapa.update_geos(fitbounds="locations", visible=False)

# --- Top 5 ciudades ---
top5 = base.groupby("MUNICIPIO").size().reset_index(name="Total").sort_values("Total", ascending=False).head(5)
fig_top5 = px.bar(top5, x="MUNICIPIO", y="Total", color="Total", title="🏙️ Top 5 Ciudades con Mayor Mortalidad")

# --- Distribución por Sexo ---
sexo_dep = base.groupby(["SEXO"]).size().reset_index(name="Total")
fig_sexo = px.pie(sexo_dep, names="SEXO", values="Total", title="⚧ Distribución de Muertes por Sexo")

# --- Distribución por Edad ---
fig_edad = px.histogram(base, x="RANGO_EDAD", title="📈 Distribución de Muertes por Grupo Etario", color_discrete_sequence=["#004c6d"])

# ============================================================
# 4️⃣ Visualización en Streamlit
# ============================================================
st.subheader("1️⃣ Mapa de Mortalidad por Departamento")
st.plotly_chart(fig_mapa, use_container_width=True)

st.subheader("2️⃣ Ciudades con Mayor Mortalidad")
st.plotly_chart(fig_top5, use_container_width=True)

st.subheader("3️⃣ Distribución de Muertes por Sexo")
st.plotly_chart(fig_sexo, use_container_width=True)

st.subheader("4️⃣ Distribución por Grupo de Edad")
st.plotly_chart(fig_edad, use_container_width=True)

st.markdown("---")
st.markdown("📘 *Fuente de datos: DANE, Mortalidad No Fetal 2019 – Procesado por Luis A. Jiménez y Cristhian Buitrago.*")
