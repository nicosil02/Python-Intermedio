"""Dashboard de documentos y entrevistas peruanas procesados con OCR, ASR y un LLM.

Correr en local, desde la carpeta tarea_2:
    streamlit run app.py

La app solo lee los CSV y JSON que dejan los notebooks 01 y 02: no carga ningún modelo.
"""

import html
import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------- configuracion
st.set_page_config(page_title="Voces y documentos peruanos", page_icon="📜", layout="wide")

CARPETA = Path(__file__).parent
DATOS = CARPETA / "datos"
EJEMPLOS = DATOS / "ejemplos"

TIPOS = {"impreso": "Impreso", "foto": "Foto de celular", "manuscrito": "Manuscrito"}
CAMPOS_DOC = ["tema", "resumen", "emisor", "destinatario", "fecha", "lugar", "monto"]
CAMPOS_AUDIO = ["tema", "resumen", "numero_hablantes", "citas_clave"]
CAMPOS_AUDITORIA = ["tema", "resumen", "emisor", "destinatario", "fecha", "lugar", "monto",
                    "numero_hablantes", "citas_clave"]

# modelos de la línea base que pide la consigna (primera fila de cada tabla del notebook 02)
BASE_OCR = "PaddleOCR por defecto (base)"
BASE_ASR = "faster-whisper small · CPU (base)"

# salidas de los modelos alternativos sobre la muestra de evaluación
SALIDAS_OCR = {BASE_OCR: "ocr_paddle_base", "Tesseract 5 (spa)": "ocr_tesseract"}
SALIDAS_ASR = {BASE_ASR: "asr_whisper_small_cpu",
               "faster-whisper large-v3-turbo · GPU": "asr_whisper_turbo_gpu",
               "MMS mms-1b-all spa · GPU": "asr_mms_gpu"}


# ------------------------------------------------------------------ carga datos
@st.cache_data
def cargar():
    documentos = pd.read_csv(DATOS / "documentos.csv").fillna({"texto_ocr": "", "texto_referencia": ""})
    audios = pd.read_csv(DATOS / "transcripciones.csv").fillna({"texto_asr": "", "texto_referencia": ""})
    fuentes = pd.read_csv(DATOS / "fuentes.csv")
    llm = pd.read_csv(DATOS / "extraccion_llm.csv")
    llm["campos"] = llm.campos_json.map(json.loads)
    m_ocr = pd.read_csv(DATOS / "metricas_ocr.csv")
    m_asr = pd.read_csv(DATOS / "metricas_asr.csv")
    auditoria = pd.read_csv(DATOS / "auditoria_llm.csv", dtype=str).fillna("")
    salidas = {nombre: json.loads((DATOS / "evaluacion" / f"{archivo}.json").read_text(encoding="utf-8"))
               for nombre, archivo in {**SALIDAS_OCR, **SALIDAS_ASR}.items()}
    return documentos, audios, fuentes, llm, m_ocr, m_asr, auditoria, salidas


documentos, audios, fuentes, llm, m_ocr, m_asr, auditoria, salidas = cargar()
fuentes_id = fuentes.set_index("id")
campos_llm = dict(zip(llm.id, llm.campos))
audios["minutos"] = audios.duracion_seg / 60
audios["condicion"] = audios.id.map(m_asr.drop_duplicates("id").set_index("id").condicion)

# texto de la Parte 1 como tercera salida de OCR, para comparar en el explorador
salidas["PaddleOCR config. Parte 1"] = {i: {"texto": t} for i, t in zip(documentos.id, documentos.texto_ocr)}


def tasa_global(df):
    """Errores totales entre caracteres o palabras de referencia: la métrica global del notebook 02."""
    return df.errores.sum() / df.n_ref.sum()


def resaltar(texto, palabra):
    """Escapa el texto y marca la palabra buscada, para mostrarlo con st.markdown."""
    texto = html.escape(texto)
    if palabra:
        texto = re.sub(f"({re.escape(html.escape(palabra))})", r"<mark>\1</mark>", texto, flags=re.IGNORECASE)
    return texto.replace("\n", "<br>")


def caja(texto, palabra=""):
    st.markdown(f'<div style="max-height:380px;overflow-y:auto;padding:0.8rem;border:1px solid #8884;'
                f'border-radius:0.5rem;font-size:0.92rem">{resaltar(texto, palabra)}</div>',
                unsafe_allow_html=True)


def tabla_campos(campos, nombres):
    filas = []
    for c in nombres:
        v = campos.get(c)
        if isinstance(v, list):
            v = " · ".join(f"“{x}”" for x in v) if v else None
        filas.append({"campo": c, "valor extraído": "— (no aparece en el texto)" if v in (None, "") else str(v)})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


def resultado_auditoria(i):
    fila = auditoria[auditoria.id == i]
    if fila.empty:
        return
    fila = fila.iloc[0]
    malos = [c for c in CAMPOS_AUDITORIA if fila[c] == "0"]
    if malos:
        st.warning(f"Auditoría humana: {len(malos)} campo(s) incorrecto(s) ({', '.join(malos)}). {fila.errores}")
    else:
        st.success("Auditoría humana: todos los campos correctos." + (f" Nota: {fila.errores}" if fila.errores else ""))


def ficha_fuente(i):
    f = fuentes_id.loc[i]
    autor = "" if pd.isna(f.autor) else f" · Autor: {f.autor}"
    st.caption(f"Fuente: [Wikimedia Commons]({f.fuente_url}) · Licencia: {f.licencia}{autor} · "
               f"Extraído el {f.fecha_extraccion}")


# ----------------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar en los textos OCR y ASR", placeholder="por ejemplo: Lima, cine, fiesta")
tipos_elegidos = st.sidebar.multiselect("Tipo de documento", list(TIPOS), default=list(TIPOS), format_func=TIPOS.get)
modelos_ocr = st.sidebar.multiselect("Modelos de OCR", list(m_ocr.modelo.unique()), default=list(m_ocr.modelo.unique()))
modelos_asr = st.sidebar.multiselect("Modelos de ASR", list(m_asr.modelo.unique()), default=list(m_asr.modelo.unique()))
dur_max = float(audios.minutos.max())
rango = st.sidebar.slider("Duración del clip (minutos)", 0.0, round(dur_max + 0.5, 1),
                          (0.0, round(dur_max + 0.5, 1)), step=0.5)
st.sidebar.caption("Los filtros actualizan los indicadores, los gráficos, las tablas y las listas de los exploradores.")

docs_f = documentos[documentos.tipo.isin(tipos_elegidos)]
aud_f = audios[audios.minutos.between(*rango)]
if busqueda:
    docs_f = docs_f[docs_f.texto_ocr.str.contains(busqueda, case=False, regex=False)]
    aud_f = aud_f[aud_f.texto_asr.str.contains(busqueda, case=False, regex=False)]
m_ocr_f = m_ocr[m_ocr.modelo.isin(modelos_ocr) & m_ocr.tipo.isin(tipos_elegidos)]
m_asr_f = m_asr[m_asr.modelo.isin(modelos_asr)]

# ----------------------------------------------------------------------- portada
st.title("¿Se pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto buscable?")
st.markdown(
    "Corpus de **25 documentos peruanos** (impresos, fotos de celular y manuscritos) y **22 clips de entrevistas** "
    "en español peruano, todos de Wikimedia Commons con licencia libre. Los documentos se leyeron con **PaddleOCR**, "
    "los audios se transcribieron con **faster-whisper** y se separaron por hablante, y un **LLM (Gemini)** extrajo "
    "campos estructurados de cada texto. En una muestra de 10 documentos y 10 clips transcritos a mano se midió el "
    "error de cada modelo (CER y WER), y 20 extracciones del LLM se revisaron a mano. Los nombres de personas "
    "privadas están reemplazados por seudónimos. Todo se calculó antes en los notebooks: la app solo lee los resultados."
)

acierto = (auditoria[CAMPOS_AUDITORIA] == "1").all(axis=1)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Documentos procesados", f"{len(docs_f)} de {len(documentos)}")
c2.metric("Minutos de audio transcritos", f"{aud_f.minutos.sum():.1f}", help=f"De {audios.minutos.sum():.1f} min en total")
cer_base = m_ocr_f[m_ocr_f.modelo == BASE_OCR]
wer_base = m_asr_f[m_asr_f.modelo == BASE_ASR]
c3.metric("CER línea base (10 docs)", f"{tasa_global(cer_base):.0%}" if len(cer_base) else "—",
          help="PaddleOCR sin personalizar. Proporción de caracteres mal leídos; menos es mejor.")
c4.metric("WER línea base (10 clips)", f"{tasa_global(wer_base):.0%}" if len(wer_base) else "—",
          help="faster-whisper small en CPU. Proporción de palabras mal transcritas; menos es mejor.")
c5.metric("Acuerdo LLM-humano", f"{acierto.mean():.0%}", help=f"{acierto.sum()}/{len(acierto)} extracciones "
          "completamente correctas en la auditoría manual")

tab_res, tab_doc, tab_aud, tab_fuentes = st.tabs(["📊 Resultados", "📄 Documentos", "🎙️ Audios", "📚 Fuentes y licencias"])

# -------------------------------------------------------------------- resultados
with tab_res:
    st.subheader("Error de cada modelo en la muestra evaluada")
    st.caption("CER y WER: proporción de caracteres o palabras con error frente a la transcripción manual (menos es mejor). "
               "RTF: segundos de cómputo por segundo de audio (menos es más rápido).")
    col1, col2 = st.columns(2)
    with col1:
        if len(m_ocr_f):
            cer_tipo = (m_ocr_f.groupby(["tipo", "modelo"], sort=False)
                        .apply(tasa_global, include_groups=False).rename("CER").reset_index())
            cer_tipo["tipo"] = cer_tipo.tipo.map(TIPOS)
            fig = px.bar(cer_tipo, x="tipo", y="CER", color="modelo", barmode="group",
                         title="CER por tipo de documento",
                         labels={"tipo": "", "CER": "CER (caracteres con error)"})
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(legend=dict(orientation="h", y=-0.2, title=None))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Ningún modelo de OCR o tipo de documento seleccionado.")
    with col2:
        if len(m_asr_f):
            wer_cond = (m_asr_f.groupby(["condicion", "modelo"], sort=False)
                        .apply(tasa_global, include_groups=False).rename("WER").reset_index())
            fig = px.bar(wer_cond, x="condicion", y="WER", color="modelo", barmode="group",
                         title="WER por condición de grabación",
                         labels={"condicion": "", "WER": "WER (palabras con error)"})
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(legend=dict(orientation="h", y=-0.3, title=None))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Ningún modelo de ASR seleccionado.")

    col3, col4 = st.columns(2)
    with col3:
        if len(m_asr_f):
            pv = m_asr_f.groupby("modelo").agg(errores=("errores", "sum"), n_ref=("n_ref", "sum"),
                                               RTF=("rtf", "mean")).reset_index()
            pv["WER"] = pv.errores / pv.n_ref
            fig = px.scatter(pv, x="RTF", y="WER", color="modelo", size=[18] * len(pv), log_x=True,
                             title="WER frente a velocidad (RTF)")
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(legend=dict(orientation="h", y=-0.3, title=None))
            st.plotly_chart(fig, width="stretch")
    with col4:
        fig = px.histogram(aud_f, x="minutos", nbins=12, title="Duración de los clips",
                           labels={"minutos": "minutos", "count": "clips"})
        fig.update_layout(yaxis_title="clips")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Buscar en todo el corpus")
    st.caption("La tabla respeta la búsqueda y los filtros de la barra lateral. Los textos ya están seudonimizados.")
    tabla = pd.concat([
        docs_f.assign(modalidad="documento", texto=docs_f.texto_ocr, modelo=docs_f.modelo_ocr,
                      detalle=docs_f.tipo.map(TIPOS))[["id", "modalidad", "detalle", "modelo", "texto"]],
        aud_f.assign(modalidad="audio", texto=aud_f.texto_asr, modelo=aud_f.modelo_asr,
                     detalle=aud_f.minutos.map("{:.1f} min".format))[["id", "modalidad", "detalle", "modelo", "texto"]],
    ], ignore_index=True)
    tabla["tema (LLM)"] = tabla.id.map(lambda i: campos_llm.get(i, {}).get("tema"))
    st.dataframe(tabla, hide_index=True, width="stretch", height=320,
                 column_config={"texto": st.column_config.TextColumn(width="large")})
    st.download_button("Descargar tabla en CSV", tabla.to_csv(index=False).encode("utf-8"),
                       "corpus_filtrado.csv", "text/csv")

# -------------------------------------------------------------------- documentos
with tab_doc:
    if docs_f.empty:
        st.info("Ningún documento coincide con la búsqueda y los filtros.")
    else:
        etiqueta = {i: f"{i} · {TIPOS[t]} · {campos_llm.get(i, {}).get('tema') or ''}"
                    for i, t in zip(docs_f.id, docs_f.tipo)}
        i = st.selectbox(f"Documento ({len(docs_f)} disponibles con los filtros)", list(etiqueta), format_func=etiqueta.get)
        doc = documentos.set_index("id").loc[i]
        izq, der = st.columns([2, 3])
        with izq:
            imagen = EJEMPLOS / f"{i}.jpg"
            if imagen.exists():
                st.image(str(imagen), width="stretch")
            else:
                st.info("La imagen no se publica porque el documento menciona a personas privadas. "
                        "Se puede consultar el texto seudonimizado.")
            ficha_fuente(i)
        with der:
            st.markdown(f"**Texto OCR** · {doc.modelo_ocr}")
            caja(doc.texto_ocr, busqueda)
            st.markdown("**Campos extraídos por el LLM**")
            tabla_campos(campos_llm.get(i, {}), CAMPOS_DOC)
            resultado_auditoria(i)

        cer_doc = m_ocr[m_ocr.id == i]
        if len(cer_doc):
            st.markdown("**Este documento está en la muestra evaluada: texto de referencia y CER de cada modelo**")
            st.dataframe(cer_doc[["modelo", "CER", "errores", "n_ref"]].rename(columns={"n_ref": "caracteres"}),
                         hide_index=True, width="stretch", column_config={"CER": st.column_config.NumberColumn(format="percent")})
            ref, modelo_cmp = st.columns(2)
            with ref:
                st.markdown("Transcripción manual (referencia)")
                caja(doc.texto_referencia, busqueda)
            with modelo_cmp:
                elegido = st.selectbox("Comparar con", list(cer_doc.modelo), key="cmp_ocr")
                caja(salidas[elegido].get(i, {}).get("texto", ""), busqueda)

# ------------------------------------------------------------------------ audios
with tab_aud:
    if aud_f.empty:
        st.info("Ningún clip coincide con la búsqueda y los filtros.")
    else:
        etiqueta = {i: f"{i} · {m:.1f} min · {campos_llm.get(i, {}).get('tema') or ''}"
                    for i, m in zip(aud_f.id, aud_f.minutos)}
        i = st.selectbox(f"Clip ({len(aud_f)} disponibles con los filtros)", list(etiqueta), format_func=etiqueta.get)
        clip = audios.set_index("id").loc[i]
        izq, der = st.columns([3, 2])
        with izq:
            sonido = EJEMPLOS / f"{i}.mp3"
            if sonido.exists():
                st.audio(str(sonido), format="audio/mpeg")
            else:
                st.info("El audio no se publica porque menciona a personas por su nombre. "
                        "La transcripción está seudonimizada.")
            ficha_fuente(i)
            st.markdown(f"**Transcripción por hablante** · {clip.n_hablantes} hablante(s) detectado(s) · {clip.modelo_asr}")
            turnos = re.split(r"(\[HABLANTE_\d+\])", clip.texto_asr)
            texto = "\n".join(f"{a} {b.strip()}" for a, b in zip(turnos[1::2], turnos[2::2])) or clip.texto_asr
            caja(texto, busqueda)
        with der:
            st.markdown("**Campos extraídos por el LLM**")
            tabla_campos(campos_llm.get(i, {}), CAMPOS_AUDIO)
            resultado_auditoria(i)

        wer_clip = m_asr[m_asr.id == i]
        if len(wer_clip):
            st.markdown("**Este clip está en la muestra evaluada: comparación de modelos**")
            st.dataframe(wer_clip[["modelo", "WER", "errores", "n_ref", "rtf"]].rename(columns={"n_ref": "palabras"}),
                         hide_index=True, width="stretch", column_config={"WER": st.column_config.NumberColumn(format="percent")})
            ref, modelo_cmp = st.columns(2)
            with ref:
                st.markdown("Transcripción manual (referencia)")
                caja(clip.texto_referencia, busqueda)
            with modelo_cmp:
                elegido = st.selectbox("Comparar con", list(wer_clip.modelo), key="cmp_asr")
                caja(salidas[elegido].get(i, {}).get("texto", ""), busqueda)

# ---------------------------------------------------------------------- fuentes
with tab_fuentes:
    st.markdown("Fuente, licencia y fecha de extracción de cada archivo del corpus. Las imágenes y los audios que se "
                "muestran en la app son copias reducidas en `datos/ejemplos/`, solo de archivos con licencia que "
                "permite redistribuirlos y sin nombres de personas.")
    publicadas = {f.stem for f in EJEMPLOS.glob("*.*")}
    vista = fuentes[fuentes.en_corpus].assign(en_la_app=lambda d: d.id.isin(publicadas))
    st.dataframe(vista[["id", "modalidad", "tipo", "licencia", "autor", "fecha_extraccion", "en_la_app", "fuente_url"]],
                 hide_index=True, width="stretch",
                 column_config={"fuente_url": st.column_config.LinkColumn("fuente"),
                                "en_la_app": st.column_config.CheckboxColumn("imagen o audio en la app")})
