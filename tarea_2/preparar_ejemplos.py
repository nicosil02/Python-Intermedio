"""Copia ligera y publicable del corpus para el dashboard (datos/ejemplos/).

    python preparar_ejemplos.py

- Imágenes: todos los documentos del corpus salvo los que tuvieron nombres seudonimizados
  (modelos/seudonimos.json), reducidos a 900 px de ancho en JPEG.
- Audio: solo los clips de EJEMPLOS_AUDIO, que no mencionan nombres de personas, en MP3 mono de 32 kbps.
Todos tienen licencia de dominio público, CC0 o CC BY / BY-SA (ver datos/fuentes.csv), que permiten redistribuir.
Requiere el corpus original en datos/raw/ (se recupera con descargar.py) y ffmpeg en el PATH.
"""
import json
import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "datos" / "ejemplos"
EJEMPLOS_AUDIO = ["clip_013", "clip_016", "clip_020", "clip_021", "clip_022", "clip_023"]

SALIDA.mkdir(parents=True, exist_ok=True)
con_nombres = {k for k, v in json.loads((RAIZ / "modelos" / "seudonimos.json").read_text(encoding="utf-8")).items() if v}
fuentes = pd.read_csv(RAIZ / "datos" / "fuentes.csv").set_index("id")

documentos = pd.read_csv(RAIZ / "datos" / "documentos.csv")
for i, archivo in zip(documentos.id, documentos.archivo):
    if i in con_nombres:
        continue
    img = Image.open(RAIZ / archivo).convert("RGB")
    img.thumbnail((900, 1400))
    img.save(SALIDA / f"{i}.jpg", quality=70, optimize=True)
    # versión reducida, suficiente para ver el tipo de documento

audios = pd.read_csv(RAIZ / "datos" / "transcripciones.csv").set_index("id")
for i in EJEMPLOS_AUDIO:
    assert i not in con_nombres, i
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(RAIZ / audios.archivo_audio[i]),
                    "-ac", "1", "-ar", "22050", "-b:a", "32k", str(SALIDA / f"{i}.mp3")], check=True)
    # mono a 32 kbps: unos 240 KB por minuto

archivos = sorted([*SALIDA.glob("*.jpg"), *SALIDA.glob("*.mp3")])
print(f"{len(archivos)} archivos, {sum(f.stat().st_size for f in archivos) / 1e6:.1f} MB en {SALIDA.name}/")
print("licencias:", fuentes.loc[[f.stem for f in archivos], "licencia"].value_counts().to_dict())
