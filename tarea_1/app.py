"""Dashboard del clasificador de titulares de El Comercio.

Correr en local, desde la carpeta tarea_1:
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from transformers import pipeline

# ---------------------------------------------------------------- configuracion
st.set_page_config(page_title="Clasificador de titulares", page_icon="🗞️", layout="wide")

# Los datos y el modelo se buscan junto a este archivo, no en la carpeta desde
# donde se lanza la app.
CARPETA = Path(__file__).parent

NOMBRES = {"politica": "Política", "economia": "Economía",
           "deportes": "Deportes", "ciencia_tecnologia": "Ciencia y tecnología"}

# Los pesos (más de 500 MB) no están en GitHub. Si no están en modelo/, como en
# Streamlit Cloud, se descargan del Hugging Face Hub.
MODELO_LOCAL = CARPETA / "modelo"
MODELO = (str(MODELO_LOCAL) if (MODELO_LOCAL / "model.safetensors").exists()
          else "nicosil02/distilbert-titulares-elcomercio")

# F1 macro de DistilBERT en el test reservado, salida de 02_clasificacion.ipynb
F1_TEST = 0.868


# ------------------------------------------------------------------ carga datos
@st.cache_data
def cargar():
    noticias = pd.read_csv(CARPETA / "datos" / "noticias.csv")
    auditoria = pd.read_csv(CARPETA / "datos" / "auditoria_20.csv")
    return noticias, auditoria


# @st.cache_resource carga el modelo una sola vez y no en cada clic
@st.cache_resource
def cargar_clasificador():
    return pipeline("text-classification", model=MODELO, top_k=None)


noticias, auditoria = cargar()

# ----------------------------------------------------------------------- filtros
st.sidebar.header("Filtros")

medios = sorted(noticias["medio"].unique())
medios_elegidos = st.sidebar.multiselect("Medio", medios, default=medios)

categorias = list(NOMBRES)
categorias_elegidas = st.sidebar.multiselect(
    "Categoría", categorias, default=categorias, format_func=NOMBRES.get
)

filtrado = noticias[
    noticias["medio"].isin(medios_elegidos) & noticias["etiqueta"].isin(categorias_elegidas)
]

# ------------------------------------------------------------------------ titulo
st.title("¿Se pueden convertir titulares peruanos en un clasificador de noticias?")
st.markdown(
    f"Se recolectaron {len(noticias)} noticias de **El Comercio** publicadas entre el "
    f"{noticias['fecha'].min()} y el {noticias['fecha'].max()}, en cuatro categorías. "
    "Un LLM local (Qwen2.5-1.5B-Instruct) etiquetó cada noticia a partir de su titular "
    "y su bajada, y con esas etiquetas se ajustó **DistilBERT multilingüe**, que "
    "clasifica un titular nuevo en milisegundos."
)

# ---------------------------------------------------------------------- metricas
aciertos = int(auditoria["correcto"].sum())

c1, c2, c3 = st.columns(3)
c1.metric("Noticias recolectadas", f"{len(noticias)}",
          help=f"{len(filtrado)} con los filtros actuales")
c2.metric("F1 macro en test", f"{F1_TEST:.3f}", help="DistilBERT ajustado, 57 titulares de test")
c3.metric("Concordancia LLM vs. auditoría humana", f"{aciertos / len(auditoria):.0%}",
          help=f"{aciertos} de {len(auditoria)} etiquetas revisadas a mano")

st.divider()

# ---------------------------------------------------------- probador en vivo
st.subheader("Prueba el clasificador con un titular nuevo")

titular = st.text_input(
    "Titular", placeholder="Ej. BCR mantiene su tasa de referencia en 4,25% por tercer mes"
)

if st.button("Clasificar", type="primary"):
    if not titular.strip():
        st.warning("Escribe o pega un titular.")
    else:
        resultados = cargar_clasificador()(titular)[0]
        probabilidades = pd.DataFrame(resultados).assign(
            categoria=lambda t: t["label"].map(NOMBRES)
        )
        mejor = probabilidades.iloc[0]
        st.success(f"Categoría predicha: **{mejor['categoria']}** · "
                   f"probabilidad {mejor['score']:.1%}")

        fig = px.bar(
            probabilidades.sort_values("score"), x="score", y="categoria", orientation="h",
            labels={"score": "Probabilidad", "categoria": ""}, range_x=[0, 1],
        )
        fig.update_layout(template="plotly_white", height=250)
        st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------- grafico
if filtrado.empty:
    st.warning("No hay noticias que cumplan los filtros. Ajusta la selección.")
    st.stop()

st.subheader("Noticias por categoría")

por_categoria = (
    filtrado["etiqueta"].map(NOMBRES).value_counts().rename_axis("categoria")
    .reset_index(name="noticias").sort_values("noticias")
)
fig = px.bar(
    por_categoria, x="noticias", y="categoria", orientation="h", text="noticias",
    labels={"noticias": "Noticias", "categoria": ""},
)
fig.update_layout(template="plotly_white", height=300)
st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------------- tabla
st.subheader("Noticias recolectadas")

st.dataframe(
    filtrado[["fecha", "etiqueta", "titular", "bajada", "seccion_original", "url"]],
    width="stretch",
    hide_index=True,
    column_config={"url": st.column_config.LinkColumn("url")},
)

st.download_button(
    "Descargar noticias filtradas (CSV)",
    filtrado.to_csv(index=False).encode("utf-8"),
    "noticias_filtradas.csv",
    "text/csv",
)
