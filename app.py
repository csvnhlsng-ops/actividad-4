# ============================================================
# Dash App – Mortalidad en Colombia 2019
# ============================================================

"""
Dashboard analítico sobre mortalidad en Colombia 2019.
Autores: Luis Alejandro Jiménez (G2) y Cristhian Camilo Buitrago (G1)
"""

# ============================================================
# 0️⃣ Librerías
# ============================================================
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import os

# ============================================================
# 1️⃣ Lectura y preparación de datos
# ============================================================
mortalidad = pd.read_excel("datos/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
codigos = pd.read_excel("datos/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
municipios = pd.read_excel("datos/Divipola_CE_.xlsx")

# Ajuste de códigos
mortalidad["COD_DEPARTAMENTO"] = mortalidad["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
mortalidad["COD_MUNICIPIO"] = mortalidad["COD_MUNICIPIO"].astype(str).str.zfill(3)
municipios["COD_DEPARTAMENTO"] = municipios["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
municipios["COD_MUNICIPIO"] = municipios["COD_MUNICIPIO"].astype(str).str.zfill(3)

# Unión de bases
base = mortalidad.merge(municipios, on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"], how="left")
base = pd.merge(base, codigos,
                left_on="COD_MUERTE",
                right_on="Código de la CIE-10 cuatro caracteres",
                how="left")

# Asignación de sexo
base["SEXO"] = base["SEXO"].map({
    1: "Masculino",
    2: "Femenino",
    3: "Indeterminado"
})

# Clasificación por grupo etario (según DANE)
condiciones = [
    base["GRUPO_EDAD1"].between(0, 4),
    base["GRUPO_EDAD1"].between(5, 6),
    base["GRUPO_EDAD1"].between(7, 8),
    base["GRUPO_EDAD1"].between(9, 10),
    base["GRUPO_EDAD1"] == 11,
    base["GRUPO_EDAD1"].between(12, 13),
    base["GRUPO_EDAD1"].between(14, 16),
    base["GRUPO_EDAD1"].between(17, 19),
    base["GRUPO_EDAD1"].between(20, 24),
    base["GRUPO_EDAD1"].between(25, 28),
    base["GRUPO_EDAD1"] == 29
]
valores = [
    "Menor de 1 mes", "1 a 11 meses", "1 a 4 años", "5 a 14 años", "15 a 19 años",
    "20 a 29 años", "30 a 44 años", "45 a 59 años", "60 a 84 años", "85 a 100+ años",
    "Sin información"
]
base["RANGO_EDAD"] = np.select(condiciones, valores, default="Sin información")

# Totales por departamento
dep_totales = base.groupby("COD_DEPARTAMENTO").size().reset_index(name="Total_muer_dep")
total_muertes = len(base)
dep_muertes = dep_totales.assign(
    Total_muertes=total_muertes,
    Proporcion_muertes=lambda x: np.round(x["Total_muer_dep"] / x["Total_muertes"], 3) * 100
)

# Lectura del shapefile de departamentos
dep_col = gpd.read_file("datos/shapes/departamento/MGN_DPTO_POLITICO.shp")
dep_col["DPTO_CCDGO"] = dep_col["DPTO_CCDGO"].astype(str).str.zfill(2)

# Unión de información geográfica
resultado_mapa = pd.merge(dep_col, dep_muertes,
                          left_on="DPTO_CCDGO",
                          right_on="COD_DEPARTAMENTO",
                          how="left")

base = pd.merge(base,
                resultado_mapa[["DPTO_CCDGO", "DPTO_CNMBR"]],
                left_on="COD_DEPARTAMENTO",
                right_on="DPTO_CCDGO",
                how="left")

# Conversión a geojson
dep_col_4326 = dep_col.to_crs(epsg=4326)
geojson_dep = dep_col_4326.__geo_interface__

# ============================================================
# 2️⃣ Visualizaciones
# ============================================================

# --- Mapa coroplético ---
mapa_fig = px.choropleth(
    resultado_mapa,
    geojson=geojson_dep,
    locations="DPTO_CCDGO",
    color="Total_muer_dep",
    featureidkey="properties.DPTO_CCDGO",
    projection="mercator",
    hover_name="DPTO_CNMBR",
    color_continuous_scale="Reds",
    title="Mapa de Mortalidad por Departamento – 2019"
)
mapa_fig.update_geos(fitbounds="locations", visible=False)
mapa_fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))

# --- Línea mensual ---
if "MES" in base.columns:
    muertes_mes = base.groupby("MES").size().reset_index(name="Total")
    linea_fig = px.line(muertes_mes, x="MES", y="Total", markers=True, title="Muertes por mes")
else:
    linea_fig = go.Figure()
    linea_fig.add_annotation(text="Columna MES no encontrada", showarrow=False)

# --- Top 5 municipios ---
top5 = base.groupby("MUNICIPIO").size().reset_index(name="Total").sort_values("Total", ascending=False).head(5)
barras_top5 = px.bar(top5, x="MUNICIPIO", y="Total", color="Total",
                     title="Top 5 Municipios con Mayor Mortalidad")

# --- Top 10 municipios (pie) ---
top10 = base.groupby("MUNICIPIO").size().reset_index(name="Total").sort_values("Total", ascending=False).head(10)
pie_top10 = px.pie(top10, values="Total", names="MUNICIPIO", title="Top 10 Municipios (participación)")

# --- Principales causas ---
causa_col = [c for c in base.columns if "nombre" in c.lower() or "descr" in c.lower()]
if causa_col:
    causas10 = base.groupby(causa_col[0]).size().reset_index(name="Total").sort_values("Total", ascending=False).head(10)
else:
    causas10 = pd.DataFrame({"Causa": [], "Total": []})

# --- Barras apiladas por sexo ---
stack_df = base.groupby(["DPTO_CNMBR", "SEXO"]).size().reset_index(name="Total")
stack_fig = px.bar(stack_df, x="DPTO_CNMBR", y="Total", color="SEXO",
                   title="Muertes por Sexo y Departamento", barmode="stack")

# --- Histograma de edad ---
hist_fig = px.histogram(base, x="RANGO_EDAD", title="Distribución de Muertes por Grupo Etario")

# ============================================================
# 3️⃣ Layout de la aplicación Dash
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

nav = dbc.NavbarSimple(
    brand="Mortalidad Colombia 2019",
    color="dark",
    dark=True,
    children=[
        dbc.NavItem(dbc.NavLink("Inicio", href="/")),
        dbc.NavItem(dbc.NavLink("Exploración", href="/exploracion")),
        dbc.NavItem(dbc.NavLink("Causas y Demografía", href="/causas"))
    ]
)

# --- Página Inicio ---
page_1 = dbc.Container([
    html.H1("Dashboard de Mortalidad – 2019", className="mt-4"),
    html.H5("Autores: Luis Alejandro Jiménez (G2) – Cristhian Camilo Buitrago (G1)"),
    html.P("Explora las estadísticas de mortalidad en Colombia durante 2019."),
    html.H6("Objetivos:"),
    html.Ul([
        html.Li("Proveer una visión geográfica de la mortalidad."),
        html.Li("Identificar las causas principales."),
        html.Li("Comparar características demográficas (sexo, edad).")
    ]),
    html.Hr(),
    dcc.Link("Ir a Exploración", href="/exploracion"), html.Br(),
    dcc.Link("Ir a Causas y Demografía", href="/causas")
], fluid=True)

# --- Página 2: Exploración ---
page_2 = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("Exploración Geográfica"), width=8),
        dbc.Col(dcc.Link("Inicio", href="/"), width=2),
        dbc.Col(dcc.Link("Causas y Demografía", href="/causas"), width=2)
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=mapa_fig), width=6),
        dbc.Col(dcc.Graph(figure=linea_fig), width=6)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=barras_top5), width=6),
        dbc.Col(dcc.Graph(figure=pie_top10), width=6)
    ])
], fluid=True)

# --- Página 3: Causas y Demografía ---
if not causas10.empty:
    table_causes = dash_table.DataTable(
        columns=[{"name": causas10.columns[0], "id": causas10.columns[0]},
                 {"name": "Total", "id": "Total"}],
        data=causas10.to_dict("records"),
        style_table={"overflowX": "auto"}
    )
else:
    table_causes = html.P("No se encontró información de causas.")

page_3 = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("Causas y Demografía"), width=8),
        dbc.Col(dcc.Link("Inicio", href="/"), width=2),
        dbc.Col(dcc.Link("Exploración", href="/exploracion"), width=2)
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=mapa_fig), width=6),
        dbc.Col(table_causes, width=6)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=stack_fig), width=6),
        dbc.Col(dcc.Graph(figure=hist_fig), width=6)
    ])
], fluid=True)

# --- Estructura general ---
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    nav,
    html.Div(id="page-content")
])

@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/exploracion":
        return page_2
    elif pathname == "/causas":
        return page_3
    else:
        return page_1

# ============================================================
# 4️⃣ Ejecución local / despliegue
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)

