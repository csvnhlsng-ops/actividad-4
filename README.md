
# Objetivos:
- Proveer una visión geográfica de la mortalidad.
- Identificar las causas principales.
- Comparar características demográficas (sexo, edad).

#  Autores

Cristhian Camilo Buitrago Bejarano G1
Luis Alejandro Jiménez G2

#  Análisis de Mortalidad en Colombia – 2019

### Proyecto académico desarrollado en **Dash (Plotly)** como parte de la Maestría en Inteligencia Artificial.

---

##  Descripción general

Este proyecto presenta una aplicación interactiva desarrollada en **Dash (Plotly)** que permite explorar, analizar y visualizar la mortalidad registrada en Colombia durante el año **2019**, según las bases de datos oficiales del **DANE**.

El dashboard incluye visualizaciones dinámicas y análisis descriptivos que permiten comprender la distribución de las muertes por:

- **Departamento**
- **Sexo**
- **Grupo etario**
- **Causas principales (CIE-10)**
- **Variación temporal mensual**

Además, se incorpora un mapa geográfico que utiliza datos espaciales del shapefile oficial del **Marco Geoestadístico Nacional (MGN)** para representar la concentración de fallecimientos a nivel departamental.

---

##  Estructura del proyecto

Actividad_4/
│
├── app.py # Aplicación principal en Dash
├── requirements.txt # Dependencias del entorno
├── README.md # Descripción y documentación del proyecto
│
├── datos/ # Carpeta con fuentes de datos
│ ├── Anexo1.NoFetal2019_CE_15-03-23.xlsx
│ ├── Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx
│ ├── Divipola_CE_.xlsx
│ └── shapes/
│ └── departamento/
│ ├── MGN_DPTO_POLITICO.shp
│ ├── MGN_DPTO_POLITICO.dbf
│ ├── MGN_DPTO_POLITICO.prj
│ └── MGN_DPTO_POLITICO.shx
│
└── assets/ # (opcional) recursos estáticos, estilos o íconos

---
##  Requisitos

Este proyecto utiliza **Python 3.10+** y las siguientes librerías principales:

- `dash`
- `plotly`
- `pandas`
- `geopandas`
- `numpy`
- `openpyxl`
- `dash-bootstrap-components`
- `folium` (para pruebas de mapas)

Puedes instalar todas las dependencias con:

```bash
pip install -r requirements.txt

# Nota sobre el uso de IA

El desarrollo de esta aplicación contó con el acompañamiento de herramientas de 
Inteligencia Artificial generativa (IA), utilizadas como apoyo para: depuración y 
optimización del código, redacción técnica y documentación, estructuración narrativa 
de los análisis visuales.

