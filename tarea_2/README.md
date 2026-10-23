# Tarea 2 · Voces y documentos peruanos

**Pregunta:** ¿se pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

Trabajo en curso. Avance por partes en los issues #9 (corpus y extracción), #7 (evaluación) y #8 (dashboard).

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb     # OCR, transcripción, limpieza y EDA
├── 02_evaluacion.ipynb     # CER/WER, LLM y comparación de modelos
├── app.py                  # Dashboard Streamlit
├── datos/                  # CSV publicados (el corpus crudo va en datos/raw/, fuera de Git)
├── modelos/                # Configuraciones ligeras
└── evidencias_ia/          # Capturas de la conversación con el asistente
```
