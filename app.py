# dash_mortalidad_colombia.py
"""
Dash app: Mortalidad Colombia 2019
Preambulo: librerias y carga de datos (usted ya provee los archivos en carpeta 'datos')
Ejecutar: python dash_mortalidad_colombia.py
"""

# ****************************************************************************
# 00 - Librerías
# ****************************************************************************
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import folium
from folium import Choropleth, LayerControl, GeoJsonTooltip
import numpy as np
import pandas as pd

from dash import Dash, dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc

# ****************************************************************************
# 01 - Bases (preambulo entregado por el usuario)
# ****************************************************************************
# Lectura de las bases que contienen la información relevante a las muertes
# por departamento en el año 2019
mortalidad = pd.read_excel('datos\\Anexo1.NoFetal2019_CE_15-03-23.xlsx')
codigos = pd.read_excel('datos\\Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx')
municipios = pd.read_excel('datos\\Divipola_CE_.xlsx')

# Adecúa el código del departamento y municipio para poder hacer un join con la información
# del mapa
mortalidad['COD_DEPARTAMENTO'] = mortalidad['COD_DEPARTAMENTO'].apply(
    lambda x: f"0{x}" if len(str(x)) == 1 else str(x)
)
mortalidad['COD_MUNICIPIO'] = mortalidad['COD_MUNICIPIO'].astype(str).str.zfill(3)

# Selecciona las columnas que nos interesan
municipios = municipios[['COD_DEPARTAMENTO', 'COD_MUNICIPIO', 'MUNICIPIO']]
municipios['COD_DEPARTAMENTO'] = municipios['COD_DEPARTAMENTO'].astype(str).str.zfill(2)
municipios['COD_MUNICIPIO'] = municipios['COD_MUNICIPIO'].astype(str).str.zfill(3)

# Une las dos bases
base = mortalidad.merge(municipios, on=['COD_DEPARTAMENTO', 'COD_MUNICIPIO'], how='left')
base = pd.merge(base, codigos, left_on='COD_MUERTE', right_on='Código de la CIE-10 cuatro caracteres', how='left')

# Adecua los valores de la columna sexo del dataframe.
base['SEXO'] = base['SEXO'].map({
    1: 'Masculino',
    2: 'Femenino',
    3: 'Indeterminado'
})

# Rangos de edad para la variable grupo de edad
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
    'Menor de 1 mes',
    '1 a 11 meses',
    '1 a 4 años',
    '5 a 14 años',
    '15 a 19 años',
    '20 a 29 años',
    '30 a 44 años',
    '45 a 59 años',
    '60 a 84 años',
    '85 a 100+ años',
    'Sin información'
]

base['RANGO_EDAD'] = np.select(condiciones, valores, default='Sin información')

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

# Importa el shape de departamentos de Colombia
dep_col = gpd.read_file('datos\\shapes\\departamento\\MGN_DPTO_POLITICO.shp')
# Asegurarse que el código del shape sea string y zfill(2)
dep_col['DPTO_CCDGO'] = dep_col['DPTO_CCDGO'].astype(str).str.zfill(2)

# Une la información calculada con el mapa
resultado_mapa = pd.merge(dep_col, dep_muertes, left_on='DPTO_CCDGO', right_on='COD_DEPARTAMENTO', how='left')

# Nombre de los departamentos
seleccionado = resultado_mapa[['DPTO_CCDGO', 'DPTO_CNMBR']]

# Complementa la información de base, con el nombre de los departamentos.
base = pd.merge(base, seleccionado, left_on='COD_DEPARTAMENTO', right_on='DPTO_CCDGO', how='left')

# Para gráficos con Plotly necesitaremos geojson del shape
dep_col_4326 = dep_col.to_crs(epsg=4326)
geojson_dep = dep_col_4326.__geo_interface__

# ****************************************************************************
# 02 - Preparar figuras y tablas (agregaciones)
# ****************************************************************************
# 1) Mapa de muertes por departamento
mapa_fig = px.choropleth(
    resultado_mapa,
    geojson=geojson_dep,
    locations='DPTO_CCDGO',
    color='Total_muer_dep',
    featureidkey='properties.DPTO_CCDGO',
    projection='mercator',
    hover_name='DPTO_CNMBR',
    labels={'Total_muer_dep': 'Total muertes'},
)
mapa_fig.update_geos(fitbounds="locations", visible=False)
mapa_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))

# 2) Total de muertes por mes en Colombia (grafico de lineas)
if 'MES' in base.columns:
    meses_order = sorted(base['MES'].dropna().unique())
    muertes_mes = base.groupby('MES').size().reindex(meses_order).reset_index(name='Total')
    linea_fig = px.line(muertes_mes, x='MES', y='Total', markers=True, title='Total muertes por mes')
else:
    # intentar crear a partir de una columna HORA/FECHA si no existe MES
    linea_fig = go.Figure()
    linea_fig.add_annotation(text='Columna MES no encontrada en la tabla', showarrow=False)

# 3) Top 5 ciudades más violentas (por total de muertes)
if 'MUNICIPIO' in base.columns:
    top5_ciudades = base.groupby('MUNICIPIO').size().reset_index(name='Total').sort_values('Total', ascending=False).head(5)
    barras_top5 = px.bar(top5_ciudades, x='MUNICIPIO', y='Total', title='Top 5 ciudades (muertes)')
else:
    barras_top5 = go.Figure(); barras_top5.add_annotation(text='Columna MUNICIPIO no encontrada', showarrow=False)

# 4) Pie chart: Top 10 ciudades
if 'MUNICIPIO' in base.columns:
    top10_ciudades = base.groupby('MUNICIPIO').size().reset_index(name='Total').sort_values('Total', ascending=False).head(10)
    pie_top10 = px.pie(top10_ciudades, values='Total', names='MUNICIPIO', title='Top 10 municipios (participaci\u00f3n)')
else:
    pie_top10 = go.Figure(); pie_top10.add_annotation(text='Columna MUNICIPIO no encontrada', showarrow=False)

# 5) Tabla: 10 principales causas de muerte
# Asumo que la columna con descripción del código de muerte existe en la tabla unida (por ejemplo 'Nombre' o similar)
# Intentaremos buscar una columna que parezca contener la descripción del CIE
possible_desc_cols = [c for c in base.columns if 'nombre' in c.lower() or 'descripcion' in c.lower() or 'descr' in c.lower() or 'CIE' in c]
if possible_desc_cols:
    desc_col = possible_desc_cols[0]
    causas10 = base.groupby(desc_col).size().reset_index(name='Total').sort_values('Total', ascending=False).head(10)
else:
    # si no existe, intentamos con la columna creada por el merge
    if 'Nombre' in base.columns:
        causas10 = base.groupby('Nombre').size().reset_index(name='Total').sort_values('Total', ascending=False).head(10)
    else:
        causas10 = pd.DataFrame({'Causa':[], 'Total':[]})

# 6) Barras apiladas: total de muertes por sexo en cada departamento
stack_df = base.groupby(['DPTO_CNMBR', 'SEXO']).size().reset_index(name='Total')
stack_fig = px.bar(stack_df, x='DPTO_CNMBR', y='Total', color='SEXO', title='Muertes por sexo y departamento')
stack_fig.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})

# 7) Histograma: Distribucion de muertes por rango de edad
hist_fig = px.histogram(base, x='RANGO_EDAD', title='Distribuci\u00f3n de muertes por rango de edad')

# ****************************************************************************
# 03 - Dash app layout
# ****************************************************************************
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

nav = dbc.NavbarSimple(
    brand='Mortalidad Colombia 2019',
    color='dark',
    dark=True,
    children=[
        dbc.NavItem(dbc.NavLink('Inicio', href='/')),
        dbc.NavItem(dbc.NavLink('Exploraci\u00f3n', href='/exploracion')),
        dbc.NavItem(dbc.NavLink('Causas y demograf\u00eda', href='/causas')),
    ]
)

# Page 1 (Inicio)
page_1 = dbc.Container([
    html.H1('Dashboard de Mortalidad - 2019', className='mt-4'),
    html.H5('Autores: [Luis Alejandro Jimenez G2]- [Cristhian Buitrago G1]'),
    html.P('Introducci\u00f3n: Este dashboard explora la mortalidad en Colombia 2019, con mapas y gr\u00e1ficos.'),
    html.H6('Objetivos'),
    html.Ul([
        html.Li('Proveer una visi\u00f3n geogr\u00e1fica de la distribuci\u00f3n de muertes.'),
        html.Li('Identificar las causas m\u00e1s frecuentes.'),
        html.Li('Comparar variables demogr\u00e1ficas (sexo, edad).')
    ]),
    html.Hr(),
    dcc.Link('Ir a Exploraci\u00f3n', href='/exploracion'), html.Br(),
    dcc.Link('Ir a Causas y demograf\u00eda', href='/causas')
], fluid=True)

# Page 2 (Exploración)
page_2 = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3('Exploraci\u00f3n'), width=8),
        dbc.Col(dcc.Link('Inicio', href='/'), width=2),
        dbc.Col(dcc.Link('Causas y demograf\u00eda', href='/causas'), width=2)
    ], align='center'),
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

# Page 3 (Causas y demografia)
# Prepare DataTable for causas10
if not causas10.empty:
    table_causes = dash_table.DataTable(
        columns=[{"name": causas10.columns[0], "id": causas10.columns[0]}, {"name": "Total", "id": "Total"}],
        data=causas10.to_dict('records'),
        style_table={'overflowX': 'auto'},
    )
else:
    table_causes = html.P('No se encontr\xf3 columna de descripci\xf3n de causa en los datos.')

page_3 = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3('Causas y demograf\u00eda'), width=8),
        dbc.Col(dcc.Link('Inicio', href='/'), width=2),
        dbc.Col(dcc.Link('Exploraci\u00f3n', href='/exploracion'), width=2)
    ], align='center'),
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

# Simple page router
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    nav,
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/exploracion':
        return page_2
    elif pathname == '/causas':
        return page_3
    else:
        return page_1


# ****************************************************************************
# 04 - Run server
# ****************************************************************************
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))  # Render asigna PORT automáticamente
    app.run(host="0.0.0.0", port=port, debug=False)
