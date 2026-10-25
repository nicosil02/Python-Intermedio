"""Transcripción manual de la muestra de evaluación (Parte 2, paso 1).

    python referencias.py html                         # crea referencias.html para transcribir en el navegador
    python referencias.py importar referencias.json    # pasa lo transcrito a texto_referencia de los CSV

La página muestra cada imagen o audio con un cuadro de texto VACÍO: la referencia se escribe mirando
o escuchando el original, nunca copiando la salida del OCR o del ASR. Lo escrito se guarda solo en el
navegador y se descarga como referencias.json, que queda en datos/ como respaldo de la transcripción.
"""
import html, json, sys
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent

# Elegidos antes de calcular cualquier métrica: los 3 tipos de documento y una fuente distinta por clip.
# doc_r05 (carta de Miguel Grau, 1879) se cambió por doc_022 porque la persona que transcribe no pudo leerla:
# el cambio no depende de ningún resultado de los modelos.
MUESTRA_DOCS = {
    "doc_002": "impreso · Constitución de 1828, portada",
    "doc_003": "impreso · Constitución de 1856, encabezado",
    "doc_004": "impreso · Gazeta del Gobierno de Lima, 1810 (tipografía antigua)",
    "doc_009": "foto · placa del Teatro Colón, Lima",
    "doc_013": "foto · placa del terremoto de 2001, Arequipa",
    "doc_016": "foto · placa de la Casa Amorós, Trujillo",
    "doc_018": "manuscrito · carta de Bachmann a Palma, 1912 (cursiva)",
    "doc_021": "manuscrito · carta de Vallejo a Eguren, 1917",
    "doc_025": "manuscrito · Libro de Bautismos de Lampa, 1871 (portada)",
    "doc_022": "manuscrito · carta a un hermano, 1860 (letra rápida)",
}
MUESTRA_CLIPS = {
    "clip_001": "calle, Av. Riva Agüero (El Agustino), tráfico de fondo",
    "clip_007": "entrevista grabada en wav, 2 voces",
    "clip_010": "docente universitario, ambiente interior",
    "clip_012": "señora de Pomabamba, acento andino",
    "clip_013": "fiesta patronal de Chuyas, con música y gente",
    "clip_014": "coordinadora de grupo, 4 voces",
    "clip_015": "Marcha del Orgullo, ruido de marcha",
    "clip_016": "activista, entrevista breve",
    "clip_018": "ciudadano en la calle, 3 voces",
    "clip_023": "testimonio grabado con buena calidad",
}

REGLAS = """
<li>Escribe <b>exactamente lo que se ve o se oye</b>, sin corregir la ortografía del original (si dice «Relijion», escribe «Relijion»).</li>
<li>Documentos: respeta los saltos de línea si quieres; los espacios y saltos no cuentan en la métrica. Lo que no puedas leer, márcalo <code>[?]</code>.</li>
<li>Audio: solo palabras habladas, sin marcas de quién habla. Muletillas («eh», «este») sí se escriben. Lo inaudible, <code>[?]</code>.</li>
<li>Nombres de <b>personas privadas</b> (entrevistados y gente que nombran): escribe <code>[PERSONA]</code>. Figuras públicas (Palma, Grau, Vallejo…) sí van con su nombre.</li>
<li>Lo que va entre corchetes no se cuenta al calcular CER y WER.</li>
<li>No abras la salida del OCR ni del ASR mientras transcribes: la referencia tiene que ser independiente.</li>
"""


def crear_html():
    items = []
    for i, desc in MUESTRA_DOCS.items():
        img = f"datos/raw/documentos/{i}.jpg"
        media = f'<a href="{img}" target="_blank"><img src="{img}" loading="lazy"></a><p class="hint">Clic en la imagen para abrirla en grande y hacer zoom.</p>'
        items.append((i, "documento", desc, media))
    for i, desc in MUESTRA_CLIPS.items():
        aud = next((RAIZ / "datos/raw/audio").glob(f"{i}.*")).relative_to(RAIZ).as_posix()
        media = (f'<audio controls preload="none" src="{aud}"></audio>'
                 '<p class="hint">Velocidad: <button onclick="vel(this,0.75)">0,75×</button> <button onclick="vel(this,1)">1×</button> · '
                 'atrás 5 s: <kbd>Ctrl</kbd>+<kbd>←</kbd> dentro del cuadro de texto</p>')
        items.append((i, "audio", desc, media))
    tarjetas = "".join(
        f'<section id="{i}"><h2>{i} <span>{html.escape(d)}</span></h2><div class="media">{m}</div>'
        f'<textarea data-id="{i}" placeholder="Transcribe aquí…"></textarea><p class="cnt" data-cnt="{i}"></p></section>'
        for i, _, d, m in items)
    indice = "".join(f'<a href="#{i}" data-nav="{i}">{i}</a>' for i, *_ in items)
    pagina = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Referencias manuales</title>
<style>
body{{font:15px/1.5 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:16px;background:#fafafa;color:#222}}
nav{{position:sticky;top:0;background:#fafafa;padding:8px 0;border-bottom:1px solid #ddd;z-index:2}}
nav a{{display:inline-block;margin:2px;padding:2px 6px;border-radius:4px;background:#eee;color:#222;text-decoration:none;font-size:12px}}
nav a.ok{{background:#2e7d32;color:#fff}}
section{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px;margin:20px 0}}
h2{{font-size:17px;margin:0 0 8px}} h2 span{{font-weight:400;color:#666;font-size:14px}}
.media img{{max-width:100%;max-height:640px;border:1px solid #ccc}} audio{{width:100%}}
textarea{{width:100%;min-height:220px;font:14px/1.5 ui-monospace,monospace;box-sizing:border-box;padding:8px}}
.hint,.cnt{{font-size:12px;color:#777;margin:4px 0}} button{{cursor:pointer}}
</style></head><body>
<h1>Transcripción manual · muestra de evaluación</h1>
<ul>{REGLAS}</ul>
<p>Lo que escribes se guarda solo en este navegador. Al terminar (o para hacer un respaldo), pulsa
<button onclick="bajar()"><b>Descargar referencias.json</b></button> y guárdalo en <code>tarea_2/datos/</code>.
Para retomar en otro navegador: <input type="file" accept=".json" onchange="cargar(this.files[0])"></p>
<nav>{indice}</nav>{tarjetas}
<script>
const K = "t2_referencias";
let datos = {{}};
try {{ datos = JSON.parse(localStorage.getItem(K) || "{{}}"); }} catch (e) {{}}
function marcar(id) {{
  const t = (datos[id] || "").trim();
  document.querySelector(`[data-nav="${{id}}"]`).classList.toggle("ok", t.length > 0);
  document.querySelector(`[data-cnt="${{id}}"]`).textContent = t ? `${{t.length}} caracteres · ${{t.split(/\\s+/).length}} palabras` : "";
}}
document.querySelectorAll("textarea").forEach(ta => {{
  const id = ta.dataset.id;
  ta.value = datos[id] || ""; marcar(id);
  ta.addEventListener("input", () => {{ datos[id] = ta.value; try {{ localStorage.setItem(K, JSON.stringify(datos)); }} catch (e) {{}} marcar(id); }});
  ta.addEventListener("keydown", e => {{
    const au = ta.closest("section").querySelector("audio");
    if (!au || !e.ctrlKey) return;
    if (e.key === "ArrowLeft") {{ au.currentTime = Math.max(0, au.currentTime - 5); e.preventDefault(); }}
    if (e.key === " ") {{ au.paused ? au.play() : au.pause(); e.preventDefault(); }}
  }});
}});
function vel(b, v) {{ b.closest("section").querySelector("audio").playbackRate = v; }}
function bajar() {{
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(datos, null, 1)], {{type: "application/json"}}));
  a.download = "referencias.json"; a.click();
}}
function cargar(f) {{
  f.text().then(t => {{ datos = JSON.parse(t); try {{ localStorage.setItem(K, t); }} catch (e) {{}} location.reload(); }});
}}
</script></body></html>"""
    (RAIZ / "referencias.html").write_text(pagina, encoding="utf-8")
    print("referencias.html:", len(items), "archivos")


def importar(ruta):
    refs = {k: v.strip() for k, v in json.loads(Path(ruta).read_text(encoding="utf-8")).items() if v.strip()}
    for csv, muestra in (("datos/documentos.csv", MUESTRA_DOCS), ("datos/transcripciones.csv", MUESTRA_CLIPS)):
        df = pd.read_csv(RAIZ / csv, dtype={"texto_referencia": str})
        df["texto_referencia"] = df.id.map(refs).where(df.id.isin(muestra), "")
        df.to_csv(RAIZ / csv, index=False)
        faltan = [i for i in muestra if i not in refs]
        print(csv, f"{len(muestra) - len(faltan)}/{len(muestra)} referencias", "· faltan: " + ", ".join(faltan) if faltan else "")


if __name__ == "__main__":
    crear_html() if sys.argv[1] == "html" else importar(sys.argv[2])
