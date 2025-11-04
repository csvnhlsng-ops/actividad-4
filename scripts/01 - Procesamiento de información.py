import geopandas as gpd
import plotly.express as px
import numpy as np
import pandas as pd


mortalidad = pd.read_excel('datos\\Anexo1.NoFetal2019_CE_15-03-23.xlsx')
codigos = pd.read_excel('datos\\Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx')

base = pd.merge(mortalidad, codigos, left_on='COD_MUERTE', right_on='Código de la CIE-10 cuatro caracteres', how='left')


dep_col = gpd.read_file('datos\\shapes\\departamento\\MGN_DPTO_POLITICO.shp')
print(dep_col)

dep_col.plot(figsize = (8,8), edgecolor = 'white', color = 'lightgray')

#base['COD_DEPARTAMENTO'] = base['COD_DEPARTAMENTO'].astype(str).str.zfill(2)
base['COD_DEPARTAMENTO'] = base['COD_DEPARTAMENTO'].apply(
    lambda x: f"0{x}" if len(str(x)) == 1 else str(x)
    )

#from siuba import _, group_by, mutate, select, ungroup
#dep_muertes = (
#    base
#    >> group_by(_.COD_DEPARTAMENTO)
#    >> mutate(Total = _.AÑO.size)      # Cuenta filas por departamento
#    >> group_by(_.COD_DEPARTAMENTO, _.AÑO)
#    >> mutate(Total_año = _.AÑO.size)  # Cuenta filas por dpto y año
#    >> ungroup()
#    >> select(_.COD_DEPARTAMENTO, _.AÑO, _.Total, _.Total_año)
#    >> _.drop_duplicates()
#    )

# Agrupar y sumar valores:
#df_group = df.groupby('COD_DEPARTAMENTO')['Muertes'].sum().reset_index()

# Contar filas por grupo
#df_group = df.groupby('COD_DEPARTAMENTO').size().reset_index(name='Conteo')

# Calcular multiples estadísticas
#df_group = df.groupby('COD_DEPARTAMENTO')['Muertes'].agg(['sum', 'mean', 'count']).reset_index()

# Agrupar por varias columnas
#df_group = df.groupby(['COD_DEPARTAMENTO', 'AÑO'])['Muertes'].sum().reset_index()


base['AÑO'].min()
base['AÑO'].max()

#dep_muertes = (
#    base
#    .pipe(lambda df: df.assign(Total_muertes = df.groupby('COD_DEPARTAMENTO')['COD_DEPARTAMENTO'].transform('count')))
#    .pipe(lambda df: df.assign(Total_año = df.groupby(['COD_DEPARTAMENTO', 'AÑO'])['AÑO'].transform('count')))
#    .pipe(lambda df: df[['COD_DEPARTAMENTO', 'AÑO', 'Total', 'Total_año']].drop_duplicates())
#)


# Total general de muertes
total_muertes = len(base)

# Total por departamento
dep_totales = base.groupby('COD_DEPARTAMENTO').size().reset_index(name='Total_muer_dep')

# Unir resultados con el total global
dep_muertes = (
    dep_totales
    .assign(Total_muertes=total_muertes)
    .assign(Proporcion_muertes=lambda x: np.round(x['Total_muer_dep'] / x['Total_muertes'], 3) * 100)
)

resultado_mapa = pd.merge(dep_col, dep_muertes, left_on = 'DPTO_CCDGO', right_on = 'COD_DEPARTAMENTO', how = 'left')


import geopandas as gpd
import folium
from folium import Choropleth, LayerControl, GeoJsonTooltip

# --- 1. Cargar (si no lo tienes ya cargado) ---
# resultado_mapa = gpd.read_file("data/departamentos_colombia.shp")

# --- 2. Crear mapa base centrado en Colombia ---
m = folium.Map(location=[4.5, -74.1], zoom_start=5, tiles="CartoDB positron")

# --- 3. Crear mapa coroplético ---
Choropleth(
    geo_data=resultado_mapa,
    data=resultado_mapa,
    columns=["DPTO_CNMBR", "Proporcion_muertes"],  # clave y variable
    key_on="feature.properties.DPTO_CNMBR",        # vincula shapefile con dataframe
    fill_color="YlOrRd",                           # paleta de color (Rojos y Amarillos)
    fill_opacity=0.7,
    line_opacity=0.3,
    nan_fill_color="white",                        # color para valores faltantes
    legend_name="Proporción de muertes (%)"
).add_to(m)

# --- 4. Añadir etiquetas emergentes (tooltip) ---
tooltip = GeoJsonTooltip(
    fields=["DPTO_CNMBR", "Total_muer_dep", "Total_muertes", "Proporcion_muertes"],
    aliases=["Departamento:", "Muertes Dpto:", "Total Nacional:", "Proporción (%):"],
    localize=True,
    sticky=False
)
folium.GeoJson(
    resultado_mapa,
    tooltip=tooltip,
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"}  # solo para tooltips
).add_to(m)

# --- 5. Control de capas y mostrar mapa ---
LayerControl().add_to(m)
m


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# -------------------------------------------------------------------------
# CONFIGURACIÓN DEL RENDERER (clave para Positron / VS Code)
# -------------------------------------------------------------------------
# Abre cada figura en el navegador predeterminado
pio.renderers.default = "browser"

# -------------------------------------------------------------------------
# 🔹 1. Gráfico de líneas: total de muertes por mes en Colombia
# -------------------------------------------------------------------------
muertes_mes = base.groupby("MES").size().reset_index(name="Total_muertes")
fig_lineas = px.line(
    muertes_mes,
    x="MES",
    y="Total_muertes",
    markers=True,
    title="Total de muertes por mes en Colombia (2019)",
    labels={"MES": "Mes", "Total_muertes": "Número de muertes"}
)
fig_lineas.update_layout(xaxis=dict(dtick=1))
fig_lineas.show()

# -------------------------------------------------------------------------
# 🔹 2. Gráfico de barras: 5 ciudades más violentas (homicidios)
# -------------------------------------------------------------------------
# Filtramos homicidios: Códigos X95–X99 (armas de fuego y agresiones)
codigos_homicidios = ["X95", "X96", "X97", "X98", "X99"]
homicidios = base[base["Código de la CIE-10 tres caracteres"].isin(codigos_homicidios)]
ciudades_violentas = (
    homicidios.groupby("COD_MUNICIPIO")
    .size()
    .reset_index(name="Total_homicidios")
    .sort_values("Total_homicidios", ascending=False)
    .head(5)
)
fig_barras_violencia = px.bar(
    ciudades_violentas,
    x="COD_MUNICIPIO",
    y="Total_homicidios",
    color="Total_homicidios",
    title="Top 5 ciudades más violentas de Colombia (homicidios)",
    labels={"COD_MUNICIPIO": "Código de Municipio", "Total_homicidios": "Total de homicidios"},
    text_auto=True
)

# -------------------------------------------------------------------------
# 🔹 3. Gráfico circular: 10 ciudades con menor índice de mortalidad
# -------------------------------------------------------------------------
muertes_ciudad = base.groupby("COD_MUNICIPIO").size().reset_index(name="Total_muertes")
ciudades_menor_mortalidad = muertes_ciudad.sort_values("Total_muertes", ascending=True).head(10)
fig_pie = px.pie(
    ciudades_menor_mortalidad,
    values="Total_muertes",
    names="COD_MUNICIPIO",
    title="10 ciudades con menor índice de mortalidad",
    hole=0.3
)

# -------------------------------------------------------------------------
# 🔹 4. Tabla: 10 principales causas de muerte
# -------------------------------------------------------------------------
causas = (
    base.groupby([
        "Código de la CIE-10 tres caracteres",
        "Descripción  de códigos mortalidad a tres caracteres"
    ])
    .size()
    .reset_index(name="Total_casos")
    .sort_values("Total_casos", ascending=False)
    .head(10)
)

fig_tabla = go.Figure(
    data=[
        go.Table(
            header=dict(
                values=["Código", "Nombre de causa", "Total de casos"],
                fill_color="lightgray",
                align="left"
            ),
            cells=dict(
                values=[
                    causas["Código de la CIE-10 tres caracteres"],
                    causas["Descripción  de códigos mortalidad a tres caracteres"],
                    causas["Total_casos"]
                ],
                fill_color="white",
                align="left"
            )
        )
    ]
)
fig_tabla.update_layout(title="Principales 10 causas de muerte en Colombia (2019)")

# -------------------------------------------------------------------------
# 🔹 5. Barras apiladas: total de muertes por sexo y departamento
# -------------------------------------------------------------------------
sexo_dep = (
    base.groupby(["COD_DEPARTAMENTO", "SEXO"])
    .size()
    .reset_index(name="Total_muertes")
)
fig_barras_apiladas = px.bar(
    sexo_dep,
    x="COD_DEPARTAMENTO",
    y="Total_muertes",
    color="SEXO",
    title="Muertes por sexo y departamento",
    labels={"COD_DEPARTAMENTO": "Departamento", "Total_muertes": "Total de muertes"},
    barmode="stack",
    text_auto=True
)

# -------------------------------------------------------------------------
# 🔹 6. Histograma: distribución por grupos de edad
# -------------------------------------------------------------------------
fig_hist = px.histogram(
    base,
    x="GRUPO_EDAD1",
    title="Distribución de muertes por grupo de edad",
    labels={"GRUPO_EDAD1": "Grupo de edad"},
    color_discrete_sequence=["indianred"]
)
fig_hist.update_xaxes(categoryorder="category ascending")

# -------------------------------------------------------------------------
# 🔹 Mostrar todas las figuras (si estás en Jupyter, se muestran una por una)
# -------------------------------------------------------------------------

fig_barras_violencia.show()
fig_pie.show()
fig_tabla.show()
fig_barras_apiladas.show()
fig_hist.show()