"""Auditoría humana de las extracciones del LLM (Parte 2, paso 3).

    python auditoria.py html                        # crea auditoria.html para revisar en el navegador
    python auditoria.py importar auditoria.json     # pasa las marcas a datos/auditoria_llm.csv

La página muestra, para cada uno de los 20 casos sorteados en 02_evaluacion.ipynb, el texto que leyó el LLM
(OCR o ASR seudonimizado) junto a los campos que extrajo. Cada campo se marca correcto o incorrecto según los
criterios del notebook. Lo marcado se guarda solo en el navegador y se descarga como auditoria.json.
"""
import html, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
LLM_DIR = RAIZ / "datos" / "evaluacion" / "llm"
CAMPOS = ["tema", "resumen", "emisor", "destinatario", "fecha", "lugar", "monto", "numero_hablantes", "citas_clave"]

CRITERIOS = """
<li><b>Correcto (✔)</b>: el contenido está sustentado en el texto, o es <code>null</code> y el dato de verdad no aparece.</li>
<li><b>Incorrecto (✘)</b>: inventa algo que no está, pone <code>null</code> habiendo un dato claro, o el tema o el resumen describen mal el contenido.</li>
<li><code>citas_clave</code>: las frases tienen que estar en el texto (se aceptan diferencias de puntuación).</li>
<li><code>numero_hablantes</code>: tiene que coincidir con las marcas <code>[HABLANTE_n]</code> distintas del texto.</li>
<li>En documentos, <code>numero_hablantes</code> y <code>citas_clave</code> deben ser <code>null</code>; en audios, <code>emisor</code>, <code>destinatario</code>, <code>fecha</code>, <code>lugar</code> y <code>monto</code> casi siempre también.</li>
<li>Si marcas algún ✘, escribe en «errores» qué falló (ej. «fecha inventada: el texto no dice 1828»).</li>
"""


def sorteo():
    """Los mismos 20 casos que sortea 02_evaluacion.ipynb (semilla 2026)."""
    docs = pd.read_csv(RAIZ / "datos/documentos.csv").id
    clips = pd.read_csv(RAIZ / "datos/transcripciones.csv").id
    rng = np.random.default_rng(2026)
    return [*rng.choice(sorted(docs), 10, replace=False), *rng.choice(sorted(clips), 10, replace=False)]


def crear_html():
    textos = {**dict(pd.read_csv(RAIZ / "datos/documentos.csv")[["id", "texto_ocr"]].values),
              **dict(pd.read_csv(RAIZ / "datos/transcripciones.csv")[["id", "texto_asr"]].values)}
    tarjetas, indice = [], []
    for i in map(str, sorteo()):
        indice.append(f'<a href="#{i}" data-nav="{i}">{i}</a>')
        cache = LLM_DIR / f"{i}.json"
        if not cache.exists():
            tarjetas.append(f'<section id="{i}"><h2>{i}</h2><p class="hint">Extracción pendiente (se completa cuando se renueve la cuota de la API).</p></section>')
            continue
        campos = json.loads(cache.read_text(encoding="utf-8"))["campos"]
        filas = "".join(
            f'<tr><th>{c}</th><td><pre>{html.escape(json.dumps(campos.get(c), ensure_ascii=False, indent=1))}</pre></td>'
            f'<td class="m"><label><input type="radio" name="{i}|{c}" value="1">✔</label>'
            f'<label><input type="radio" name="{i}|{c}" value="0">✘</label></td></tr>' for c in CAMPOS)
        tarjetas.append(
            f'<section id="{i}"><h2>{i} <span>{campos["modalidad"]}</span></h2><div class="dos">'
            f'<div><h3>Texto que leyó el LLM</h3><pre class="txt">{html.escape(str(textos.get(i, "")))}</pre></div>'
            f'<div><h3>Campos extraídos</h3><table>{filas}</table>'
            f'<textarea data-id="{i}" placeholder="errores (solo si marcaste algún ✘)"></textarea></div></div></section>')
    pagina = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Auditoría LLM</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:16px;background:#fafafa;color:#222}}
nav{{position:sticky;top:0;background:#fafafa;padding:8px 0;border-bottom:1px solid #ddd;z-index:2}}
nav a{{display:inline-block;margin:2px;padding:2px 6px;border-radius:4px;background:#eee;color:#222;text-decoration:none;font-size:12px}}
nav a.ok{{background:#2e7d32;color:#fff}}
section{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;margin:20px 0}}
h2{{font-size:17px;margin:0 0 8px}} h2 span{{font-weight:400;color:#666;font-size:14px}} h3{{font-size:14px;margin:4px 0}}
.dos{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} @media(max-width:800px){{.dos{{grid-template-columns:1fr}}}}
pre{{white-space:pre-wrap;word-break:break-word;margin:0;font-size:13px}} .txt{{background:#f4f4f4;padding:8px;max-height:560px;overflow:auto}}
table{{width:100%;border-collapse:collapse}} th,td{{border-bottom:1px solid #eee;padding:4px;vertical-align:top;text-align:left;font-size:13px}}
th{{width:110px}} .m{{width:90px;white-space:nowrap}} label{{margin-right:6px;cursor:pointer}}
textarea{{width:100%;min-height:60px;margin-top:8px;box-sizing:border-box;font:13px system-ui}}
.hint{{font-size:13px;color:#777}}
</style></head><body>
<h1>Auditoría humana · 20 extracciones del LLM</h1>
<ul>{CRITERIOS}</ul>
<p>Lo que marcas se guarda solo en este navegador. Al terminar, pulsa
<button onclick="bajar()"><b>Descargar auditoria.json</b></button>.</p>
<nav>{''.join(indice)}</nav>{''.join(tarjetas)}
<script>
const K = "t2_auditoria", CAMPOS = {json.dumps(CAMPOS)};
let datos = {{}};
try {{ datos = JSON.parse(localStorage.getItem(K) || "{{}}"); }} catch (e) {{}}
const guardar = () => {{ try {{ localStorage.setItem(K, JSON.stringify(datos)); }} catch (e) {{}} }};
function marcar(id) {{
  const n = document.querySelector(`[data-nav="${{id}}"]`);
  n && n.classList.toggle("ok", CAMPOS.every(c => datos[id] && datos[id][c] !== undefined));
}}
document.querySelectorAll("input[type=radio]").forEach(r => {{
  const [id, c] = r.name.split("|");
  if (datos[id] && datos[id][c] === r.value) r.checked = true;
  r.addEventListener("change", () => {{ (datos[id] ||= {{}})[c] = r.value; guardar(); marcar(id); }});
}});
document.querySelectorAll("textarea").forEach(t => {{
  const id = t.dataset.id;
  t.value = (datos[id] && datos[id].errores) || "";
  t.addEventListener("input", () => {{ (datos[id] ||= {{}}).errores = t.value; guardar(); }});
}});
document.querySelectorAll("[data-nav]").forEach(n => marcar(n.dataset.nav));
function bajar() {{
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(datos, null, 1)], {{type: "application/json"}}));
  a.download = "auditoria.json"; a.click();
}}
</script></body></html>"""
    (RAIZ / "auditoria.html").write_text(pagina, encoding="utf-8")
    print("auditoria.html:", sum(1 for i in sorteo() if (LLM_DIR / f"{i}.json").exists()), "de 20 casos con extracción")


def importar(ruta):
    marcas = json.loads(Path(ruta).read_text(encoding="utf-8"))
    filas = [{"id": i, **{c: marcas.get(i, {}).get(c, "") for c in CAMPOS}, "errores": marcas.get(i, {}).get("errores", "").strip()}
             for i in map(str, sorteo())]
    df = pd.DataFrame(filas)
    df.to_csv(RAIZ / "datos/auditoria_llm.csv", index=False)
    completos = df[CAMPOS].ne("").all(axis=1)
    print(f"datos/auditoria_llm.csv: {completos.sum()}/20 casos revisados por completo")


if __name__ == "__main__":
    crear_html() if sys.argv[1] == "html" else importar(sys.argv[2])
