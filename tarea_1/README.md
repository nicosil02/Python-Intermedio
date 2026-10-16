# Tarea 1. Noticias peruanas, del titular al clasificador

## Pregunta

¿Se pueden convertir titulares peruanos en un clasificador de noticias?

## Medio y fechas de extracción

Se usó El Comercio (opción B), a partir de los sitemaps de sus secciones de política, economía, deporte-total y tecnología. La descarga se hizo el 14 de octubre de 2026 y las noticias se publicaron entre el 2 y el 14 de octubre. De 400 notas descargadas quedaron 375, tras descartar 16 columnas de opinión y 9 notas de secciones fuera de las 4 categorías.

| Archivo | Contenido |
| :--- | :--- |
| [`01_recoleccion.ipynb`](01_recoleccion.ipynb) | Scraping, limpieza y EDA |
| [`02_clasificacion.ipynb`](02_clasificacion.ipynb) | Zero-shot, etiquetado con LLM, fine-tuning y evaluación |
| [`app.py`](app.py) | Dashboard de Streamlit |
| `datos/noticias.csv` | 375 noticias con 7 columnas |
| `datos/etiquetas_llm.csv` | Etiquetas y confianza del LLM |

## Resultados

| Método | F1 macro en test |
| :--- | :---: |
| Zero-shot `joeddav/xlm-roberta-large-xnli` | 0,691 |
| LLM Qwen2.5-1.5B-Instruct, titular y bajada | 0,927 |
| DistilBERT multilingüe ajustado, solo titular | **0,868** |

F1 Macro: 0.868 | Zero-shot: 0.708 | Acuerdo LLM-Humano: 19/20

El zero-shot obtiene 0,708 en la muestra de 40 titulares que pide el enunciado y 0,691 en los 57 titulares de test.

## Hallazgos

1. La supervisión débil basta para entrenar un clasificador. Sin etiquetar nada a mano, el LLM coincide en un 91,7% con la sección del diario y acierta en 19 de los 20 casos auditados. DistilBERT entrenado con esas etiquetas llega a un F1 macro de 0,868 en test, muy por encima del zero-shot, y clasifica un titular en unos 4 milisegundos frente a los 44 del LLM.
2. Deportes es la categoría más fácil y economía la más difícil. Deportes llega a un F1 de 1,000 porque sus titulares nombran clubes, jugadores y torneos que no aparecen en otras secciones. Economía queda en 0,696 porque es transversal y comparte vocabulario con las demás. Las noticias sobre El Niño se confunden con ciencia y los nombramientos en entidades del Estado se confunden con política.

## Limitaciones

1. El test es pequeño. Con 57 titulares, cada error mueve el F1 en casi 2 puntos. En ejecuciones de prueba el F1 macro de test varió entre 0,87 y 0,91 por pequeñas diferencias numéricas de la GPU.
2. El modelo hereda los errores del LLM y se limita a un medio y dos semanas. Dos de los siete errores en test venían de etiquetas equivocadas del LLM. Además, todas las noticias son de El Comercio y de la coyuntura de octubre de 2026, así que el modelo puede rendir peor con otro diario u otros temas del momento.

## Cómo ejecutar en local

Desde la carpeta `tarea_1`, con Python 3.12.

```bash
python -m venv .venv
.venv\Scripts\activate          # en Mac o Linux, source .venv/bin/activate
pip install -r requirements.txt
```

Los pesos del modelo, `modelo/model.safetensors`, pesan más de 500 MB y no están en el repositorio. Están publicados en Hugging Face como [`nicosil02/distilbert-titulares-elcomercio`](https://huggingface.co/nicosil02/distilbert-titulares-elcomercio), y la app los descarga de ahí la primera vez si no los encuentra en `modelo/`. Ejecutar `02_clasificacion.ipynb` los vuelve a generar en local.

```bash
streamlit run app.py
```

La app se abre en `http://localhost:8501`.
