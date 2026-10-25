"""Seudonimiza las transcripciones que vienen de Colab antes de guardarlas en el repo.

    python seudonimizar_eval.py ruta/a/modelos_resultados.zip

Descomprime el zip en datos/evaluacion/ y aplica a cada salida de OCR y ASR los mismos reemplazos que la
Parte 1 (modelos/seudonimos.json, fuera de Git), también en minúsculas porque MMS no usa mayúsculas.
Al final avisa si queda alguna palabra parecida a un nombre real, para revisarla a mano.
"""
import json, re, sys, zipfile
from pathlib import Path
from rapidfuzz import fuzz
import voz

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ / "datos" / "evaluacion"
# nombres que algún modelo escribió tan deformados que la comparación difusa no los atrapa (revisión manual)
DEFORMADOS = {"clip_007": ["casramie"]}

DESTINO.mkdir(parents=True, exist_ok=True)
zipfile.ZipFile(sys.argv[1]).extractall(DESTINO)
nombres = json.loads((RAIZ / "modelos" / "seudonimos.json").read_text(encoding="utf-8"))
for ruta in sorted([*DESTINO.glob("asr_*.json"), *DESTINO.glob("ocr_*.json")]):
    salidas = json.loads(ruta.read_text(encoding="utf-8"))
    for id_, v in salidas.items():
        reemplazos = nombres.get(id_, {})
        if reemplazos:
            v["texto"] = voz.seudonimizar(v["texto"], reemplazos)
            v["texto"] = voz.seudonimizar(v["texto"], {k.lower(): s for k, s in reemplazos.items()})
        for palabra in DEFORMADOS.get(id_, []):
            v["texto"] = v["texto"].replace(palabra, "[PERSONA_1]")
        for nombre in reemplazos:
            for parte in (p for p in nombre.split() if len(p) >= 4):
                for w in re.findall(r"\w+", v["texto"]):
                    if fuzz.ratio(parte.lower(), w.lower()) >= 85:
                        print("REVISAR", ruta.name, id_, w)
    ruta.write_text(json.dumps(salidas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(ruta.name, "seudonimizado")
