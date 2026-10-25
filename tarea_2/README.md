# Tarea 2 · Voces y documentos peruanos

**Pregunta:** ¿se pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

**Dashboard público:** _(enlace de Streamlit Community Cloud)_

## Qué se hizo

1. **Corpus y extracción** (`01_extraccion.ipynb`). 25 documentos peruanos (8 impresos, 8 fotos de celular y 9 manuscritos) leídos con PaddleOCR, y 22 clips de entrevistas en español peruano (60 minutos) transcritos con faster-whisper `small` y separados por hablante. Los nombres de personas privadas se reemplazan por seudónimos (`[PERSONA_1]`, `[HABLANTE_1]`).
2. **Evaluación** (`02_evaluacion.ipynb`). Sobre 10 documentos y 10 clips transcritos a mano se mide el CER y la WER de 3 modelos de OCR y 3 de ASR. Un LLM (Gemini, con esquema JSON fijo) extrae tema, resumen, emisor, fecha, lugar, hablantes y citas de los 47 textos, y 20 extracciones sorteadas se revisan a mano.
3. **Dashboard** (`app.py`). Indicadores, gráficos, búsqueda en todos los textos y exploradores de documentos y audios. Solo lee los CSV y JSON que dejan los notebooks: no carga ningún modelo.

**Resultados (línea base):** `WER: 0.34 | CER: 0.31 | Acuerdo LLM-Humano: 14/20`

## Corpus, fuentes y licencias

Todos los archivos vienen de **Wikimedia Commons** y se descargaron el **22 y 23 de octubre de 2026**. El detalle de cada uno (enlace, autor, licencia, página o recorte) está en `datos/fuentes.csv` y en la pestaña "Fuentes y licencias" del dashboard.

| Modalidad | Licencias | Archivos |
|---|---|---|
| Documentos | Dominio público (9), CC0 (8), CC BY-SA 4.0 (7), CC BY-SA 3.0 (1) | 25 |
| Audios | CC BY-SA 4.0 (18), CC BY 4.0 (4) | 22 |

El corpus original (unos 400 MB) queda fuera de Git, en `datos/raw/`, y se vuelve a descargar con `python descargar.py`. En `datos/ejemplos/` hay copias reducidas para el dashboard. Son 23 imágenes y 6 clips, generados con `python preparar_ejemplos.py`, solo de archivos cuya licencia permite redistribuirlos y que no mencionan a personas por su nombre. Los demás se consultan como texto seudonimizado.

## Hallazgos

1. **Los manuscritos no se pueden leer sin una persona.** PaddleOCR por defecto se equivoca en el 10 % de los caracteres de los impresos, pero en el 42 % de los manuscritos, y llega al 69 % con la letra rápida de una carta familiar de 1860. La letra regular y espaciada se lee mejor que la letra suelta, sea cual sea la época.
2. **En el audio, el ruido no fue lo más difícil.** La calle con tráfico, una marcha y una fiesta con música quedaron entre los WER más bajos (13 % a 22 %). Lo peor fue una entrevista en interior tranquilo (alrededor de 60 %), porque Whisper se salta bloques enteros de habla rápida y continua. faster-whisper `large-v3-turbo` en GPU es el más preciso (WER de 31 %) y transcribe una hora en unos 2 minutos.

En la extracción con LLM, 14 de 20 casos salieron completamente correctos y ninguno inventó un emisor, un monto o una cita. El error más frecuente fue el número de hablantes, que el LLM tiene que adivinar a partir del texto.

## Limitaciones técnicas

1. **No hay un modelo de escritura a mano.** Los tres modelos de OCR están entrenados sobre todo con texto impreso. Para un archivo real de manuscritos haría falta uno especializado (por ejemplo TrOCR afinado o Transkribus) y revisión humana de cada página.
2. **La separación de hablantes es aproximada.** La diarización se hace por turnos y el LLM no sabe quién dice cada frase, por eso cuenta mal los hablantes en 3 de 10 entrevistas. Además Whisper omite tramos sin avisar, así que una transcripción puede parecer completa sin serlo.

La evaluación usa además solo 10 documentos y 10 clips transcritos por una sola persona, así que las diferencias pequeñas entre modelos (31 % frente a 34 %) dependen de pocos archivos.

## Cómo ejecutarlo en local

Desde la raíz del repositorio, con Python 3.12:

```bash
cd tarea_2
python -m venv .venv
.venv\Scripts\activate          # en macOS o Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

La app se abre en `http://localhost:8501`. `requirements.txt` solo tiene lo que usa el dashboard (Streamlit, pandas y Plotly). Los notebooks usan además PaddleOCR, faster-whisper, jiwer y google-genai, con las versiones que aparecen en sus primeras celdas. Los modelos alternativos se corrieron en Google Colab (`modelos_colab.ipynb`).

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb      # OCR, transcripción, seudonimización y EDA
├── 02_evaluacion.ipynb      # CER/WER, extracción con LLM, auditoría y decisión
├── modelos_colab.ipynb      # modelos alternativos en Colab (GPU)
├── app.py                   # dashboard Streamlit
├── requirements.txt         # dependencias del dashboard
├── descargar.py             # descarga el corpus desde Wikimedia Commons
├── preparar_ejemplos.py     # copias publicables para datos/ejemplos/
├── datos/
│   ├── documentos.csv       # texto OCR de los 25 documentos
│   ├── transcripciones.csv  # texto ASR por hablante de los 22 clips
│   ├── extraccion_llm.csv   # campos extraídos por el LLM
│   ├── fuentes.csv          # fuente, licencia y fecha de cada archivo
│   ├── metricas_ocr.csv     # CER por documento y modelo
│   ├── metricas_asr.csv     # WER por clip y modelo
│   ├── auditoria_llm.csv    # revisión manual de 20 extracciones
│   ├── evaluacion/          # salidas de cada modelo sobre la muestra
│   └── ejemplos/            # imágenes y clips publicables
├── graficos/                # gráficos de los notebooks
└── evidencias_ia/           # capturas de la conversación con el asistente
```
