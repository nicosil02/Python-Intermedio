"""Llena la caché de OCR (JSON) y ASR (CSV, SRT y TXT) con la misma configuración del notebook 01.

    python precalcular.py . asr        # transcribe los clips que falten
    python precalcular.py . ocr 3      # OCR de los 3 documentos siguientes que falten

En la laptop (7,7 GB de RAM, sin GPU) correr el OCR y el ASR dentro del notebook lo dejaba sin
memoria. Este script hace lo mismo que las secciones 2 y 3 del notebook, pero en procesos separados
y por tandas: lo ya hecho queda guardado y no se repite si algo se corta. Después, el notebook solo
lee esa caché.
"""
import json, sys, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
RAIZ = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(RAIZ))
import voz
que = sys.argv[2]  # "ocr" o "asr"
RAW_DOC, RAW_AUDIO = RAIZ / "datos/raw/documentos", RAIZ / "datos/raw/audio"
OCR_DIR, ASR_DIR = RAW_DOC / "ocr", RAW_AUDIO / "salidas"
for d in (OCR_DIR, ASR_DIR): d.mkdir(parents=True, exist_ok=True)
fuentes = pd.read_csv(RAIZ / "datos/fuentes.csv")
T0 = time.perf_counter()
def log(*a): print(f"[{(time.perf_counter()-T0)/60:5.1f} min]", *a, flush=True)

if que == "ocr":
    from paddleocr import PaddleOCR
    CONFIG = dict(lang="es", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
                  text_detection_model_name="PP-OCRv5_mobile_det", text_det_limit_side_len=1280, text_det_limit_type="max")
    ocr = PaddleOCR(**CONFIG)
    tope = int(sys.argv[3]) if len(sys.argv) > 3 else 99
    for i in fuentes[fuentes.modalidad == "documento"].id:
        crudo = OCR_DIR / f"{i}.json"
        if crudo.exists() and json.loads(crudo.read_text(encoding="utf-8")).get("config") == CONFIG: continue
        if tope == 0: break
        tope -= 1
        t0 = time.perf_counter()
        r = ocr.predict(str(RAW_DOC / f"{i}.jpg"))[0]
        r.save_to_img(str(OCR_DIR / f"{i}_cajas.jpg"))
        res = {"rec_texts": list(r["rec_texts"]), "rec_scores": [float(s) for s in r["rec_scores"]],
               "rec_boxes": np.asarray(r["rec_boxes"]).tolist(), "segundos": time.perf_counter() - t0, "config": CONFIG}
        crudo.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        log(i, len(res["rec_texts"]), "líneas", round(res["segundos"]), "s")
else:
    asr = voz.Transcriptor("faster-whisper-small", device="cpu")
    for i in fuentes[fuentes.modalidad == "audio"].id:
        salida = ASR_DIR / f"{i}.csv"
        if salida.exists(): continue
        audio = voz.cargar_audio(next(RAW_AUDIO.glob(f"{i}.*")))
        t0 = time.perf_counter()
        segs = asr.segmentos(audio, idioma="es")
        t_asr = time.perf_counter() - t0
        segs = voz.diarizar(audio, segs, device="cpu") if segs else []
        tabla = voz.a_tabla(segs); tabla["segundos_asr"] = t_asr
        tabla.to_csv(salida, index=False)
        (ASR_DIR / f"{i}.srt").write_text(voz.a_srt(segs), encoding="utf-8")
        (ASR_DIR / f"{i}.txt").write_text(voz.a_texto(segs), encoding="utf-8")
        log(i, f"{len(audio)/voz.SR:.0f}s audio", f"{t_asr:.0f}s ASR", len(segs), "segs",
            tabla.hablante.nunique() if len(tabla) else 0, "hablantes")
log("FIN", que)
