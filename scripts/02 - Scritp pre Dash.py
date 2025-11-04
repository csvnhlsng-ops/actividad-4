# ****************************************************************************
# 00 - Librerías 
# ****************************************************************************

import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
# Versión de leaflet de R en Python:
import folium
from folium import Choropleth, LayerControl, GeoJsonTooltip
import numpy as np
import pandas as pd

# ****************************************************************************
# 01 - Bases
# ****************************************************************************

# Lectura de las bases que contienen la información relevante a las muertes
# por departamento en el año 2019
mortalidad = pd.read_excel('datos\\Anexo1.NoFetal2019_CE_15-03-23.xlsx')
codigos = pd.read_excel('datos\\Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx')
municipios = pd.read_excel('datos\\Divipola_CE_.xlsx')

# Adecúa el código del departamento y municipio para poder hacer un join con la información
# del mapa
#mortalidad['COD_DEPARTAMENTO'] = mortalidad['COD_DEPARTAMENTO'].astype(str).str.zfill(2)
mortalidad['COD_DEPARTAMENTO'] = mortalidad['COD_DEPARTAMENTO'].apply(
    lambda x: f"0{x}" if len(str(x)) == 1 else str(x)
    )
mortalidad['COD_MUNICIPIO'] = mortalidad['COD_MUNICIPIO'].astype(str).str.zfill(3)

# Selecciona las columnas que nos interesan
municipios = municipios[['COD_DEPARTAMENTO', 'COD_MUNICIPIO', 'MUNICIPIO']]
municipios['COD_DEPARTAMENTO'] = municipios['COD_DEPARTAMENTO'].astype(str).str.zfill(2)
municipios['COD_MUNICIPIO'] = municipios['COD_MUNICIPIO'].astype(str).str.zfill(3)

# Une las dos bases
base = mortalidad.merge(municipios, on = ['COD_DEPARTAMENTO', 'COD_MUNICIPIO'], how = 'left')
base = pd.merge(base, codigos, left_on='COD_MUERTE', right_on='Código de la CIE-10 cuatro caracteres', how='left')
#base = mortalidad.merge(
#    municipios,
#   left_on=['COD_DEPARTAMENTO', 'COD_MUNICIPIO'],
#    right_on=['COD_DEPARTAMENTO', 'COD_MUNICIPIO'],
#    how='left'
#    )

# Adecua los valores de la columna sexo del dataframe.
# https://microdatos.dane.gov.co/index.php/catalog/696/data-dictionary/F23?file_name=nofetal2019
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

# Examina si hay mas años
base['AÑO'].min()
base['AÑO'].max()

# Calcula el total de muertes en el 2019, por departamento y saca una proporción 
# demuertes por departamento

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
print(dep_col)

# Une la información calculada con el mapa
resultado_mapa = pd.merge(dep_col, dep_muertes, left_on = 'DPTO_CCDGO', right_on = 'COD_DEPARTAMENTO', how = 'left')

# Nombre de los departamentos
seleccionado = resultado_mapa[['DPTO_CCDGO', 'DPTO_CNMBR']]

# Complementa la información de base, con el nombre de los departamentos.
# Se usa los nombres del Shape para que los nobres del shape y la base sean los
# mismos
base = pd.merge(base, seleccionado, left_on = 'COD_DEPARTAMENTO', right_on = 'DPTO_CCDGO', how = 'left')


# Exporta los resultados a una sola base
#base.to_excel('datos\\base.xlsx', index = False)
with pd.ExcelWriter('Resultados.xlsx') as writer:
    base.to_excel(writer, sheet_name = 'base', index = False)
    dep_muertes.to_excel(writer, sheet_name = 'Resumen Dep', index=False)
    resultado_mapa.to_excel(writer, sheet_name = 'Mapa', index=False)


# ****************************************************************************
# 02 - Procedimientos a graficar en el Dash
# ****************************************************************************

# ****************************************************************************
# 02.1 - Mapa
# ****************************************************************************

# Mapa base centrado en Colombia
mapa = folium.Map(location=[4.5, -74.1], zoom_start=5, tiles="CartoDB positron")

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
    ).add_to(mapa)

# Añade etiquetas
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
    ).add_to(mapa)

# Control de capas y mostrar mapa
LayerControl().add_to(mapa)
mapa

# ****************************************************************************
# CONFIGURACIÓN DEL RENDERER (clave para Positron / VS Code)
# ****************************************************************************
# Abre cada figura en el navegador predeterminado
pio.renderers.default = "browser"

# ****************************************************************************
# 02.2 - Gráfico de líneas: total de muertes por mes en Colombia
# ****************************************************************************
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

# ****************************************************************************
# 02.3 Gráfico de barras: 5 ciudades más violentas (homicidios)
# ****************************************************************************
# Filtramos homicidios: Códigos X95–X99 (armas de fuego y agresiones)

#codigos_homicidios = ["X95", "X96", "X97", "X98", "X99"]
#homicidios = base[base["Código de la CIE-10 tres caracteres"].isin(codigos_homicidios)]
#https://www.ine.es/daco/daco42/sanitarias/lista_reducida_CIE10.pdf
homicidios = base[base["Código de la CIE-10 tres caracteres"].between('X85', 'Y09')]

ciudades_violentas = (
    homicidios.groupby("MUNICIPIO")
    .size()
    .reset_index(name="Total_homicidios")
    .sort_values("Total_homicidios", ascending=False)
    .head(5)
    )
fig_barras_violencia = px.bar(
    ciudades_violentas,
    x="MUNICIPIO",
    y="Total_homicidios",
    color="Total_homicidios",
    title="Top 5 ciudades más violentas de Colombia (homicidios)",
    labels={"MUNICIPIO": "Municipio", "Total_homicidios": "Total de homicidios"},
    text_auto=True)

fig_barras_violencia.show()

# ****************************************************************************
# 02.4. Gráfico circular: 10 ciudades con menor índice de mortalidad
# ****************************************************************************
muertes_ciudad = base.groupby("MUNICIPIO").size().reset_index(name="Total_muertes")
ciudades_menor_mortalidad = muertes_ciudad.sort_values("Total_muertes", ascending=True).head(10)
fig_pie = px.pie(
    ciudades_menor_mortalidad,
    values="Total_muertes",
    names="MUNICIPIO",
    title="10 ciudades con menor número de muertes",
    hole=0.3
    )

fig_pie.show()

# ****************************************************************************
# 02.5. Tabla: 10 principales causas de muerte
# ****************************************************************************
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

# ****************************************************************************
# 02.6. Barras apiladas: total de muertes por sexo y departamento
# ****************************************************************************
# Agrupamos por departamento y sexo
sexo_dep = (
    base.groupby(["DPTO_CNMBR", "SEXO"])
    .size()
    .reset_index(name="Total_muertes")
    )

# Calculamos el total por departamento (sumando ambos sexos)
totales = (
    sexo_dep.groupby("DPTO_CNMBR")["Total_muertes"]
    .sum()
    .sort_values(ascending=False)
    .index)

# Creamos el gráfico ordenando por el total
fig_barras_apiladas = px.bar(
    sexo_dep,
    x="DPTO_CNMBR",
    y="Total_muertes",
    color="SEXO",
    title="Muertes por sexo y departamento",
    labels={"DPTO_CNMBR": "Departamento", "Total_muertes": "Total de muertes"},
    barmode="stack",
    text_auto=True,
    category_orders={"DPTO_CNMBR": totales} 
    )

fig_barras_apiladas.show()

# ****************************************************************************
# 02.7. Histograma: distribución por grupos de edad
# ****************************************************************************
orden = (
    base['RANGO_EDAD']
    .value_counts()
    .sort_values(ascending=False)
    .index
    )

# 2. Creamos el histograma ordenando por la cantidad de muertes
fig_hist = px.histogram(
    base,
    x="RANGO_EDAD",
    title="Distribución de muertes por grupo de edad",
    labels={"RANGO_EDAD": "Grupo de edad"},
    color_discrete_sequence=["indianred"],
    category_orders={"RANGO_EDAD": orden}  
    )

fig_hist.show()
