"""Descarga el corpus de la Tarea 2 desde Wikimedia Commons y arma datos/fuentes.csv.

    python descargar.py

Todo sale de Wikimedia Commons, con licencia libre (dominio público, CC0, CC BY o CC BY-SA) que se
lee de la propia ficha del archivo. Las páginas de los PDF se bajan como imagen a 2000 px de ancho,
que es lo que Commons genera a pedido. Se respeta una pausa de 1,5 s entre solicitudes y se usa un
User-Agent que identifica el proyecto.

Algunas fotos se recortan para dejar solo el documento (columna recorte).

Salida: datos/raw/documentos/*.jpg, datos/raw/audio/* (fuera de Git) y datos/fuentes.csv
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from PIL import Image

RAIZ = Path(__file__).resolve().parent
RAW_DOC, RAW_AUDIO = RAIZ / "datos" / "raw" / "documentos", RAIZ / "datos" / "raw" / "audio"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "nicosil02-tarea2/2026 (https://github.com/nicosil02/Python-Intermedio; curso Python Intermedio)"}
PAUSA = 1.5
ANCHO = 2000

# id: (tipo, archivo en Commons, página del PDF o None, recorte o None)
# El recorte va en fracciones del ancho y alto (izquierda, arriba, derecha, abajo).
DOCUMENTOS = {
    # Impresos nítidos: páginas de texto de publicaciones peruanas en dominio público y una carta a máquina
    "doc_001": ("impreso", "Constitucion politica. De la Republica peruana jurada en Lima el 20 de noviembre de 1823 (IA constitucionpoli00peru).pdf", 9, None),
    "doc_002": ("impreso", "Constitución Política de la República Peruana (1828).pdf", 7, None),
    "doc_003": ("impreso", "Constitución Política del Perú (1856).pdf", 5, None),
    "doc_004": ("impreso", "Gazeta del gobierno de Lima. - Sabado 3 de noviembre de 1810 (IA gazetadelgobiern00peru).pdf", 3, None),
    "doc_005": ("impreso", "Gaceta del Gobierno de Lima independiente (IA gacetadelgobiern00brow).pdf", 5, None),
    "doc_006": ("impreso", "Tradiciones peruanas - Tomo I (1893).pdf", 21, None),
    "doc_007": ("impreso", "Amauta Núm. 1.pdf", 5, None),
    "doc_008": ("impreso", "4000004161-0016 - Carta de Carlos J. Bachmann. 1914 julio 4, Maldonado; para Ricardo Palma, Lima.pdf", 1, None),
    # Fotos con inclinación o sombra: placas y letreros fotografiados en la calle
    "doc_009": ("foto", "Placa conmemorativa del Teatro Colón en Lima.jpg", None, None),
    "doc_010": ("foto", "Pasaje Acisclo Villarán - Placa conmemorativa.jpg", None, None),
    "doc_011": ("foto", "Placa de la Casa Federico Elguera, Calle La Virreyna, Lima.jpg", None, None),
    "doc_012": ("foto", "Placa conmemorativa Mercado Minorista La Parada.jpg", None, None),
    "doc_013": ("foto", "Placa d'homenatge a les víctimes del terratrèmol de 2001 d'Arequipa.jpg", None, None),
    "doc_014": ("foto", "Capilla de Nuestra Señora de Loreto - Cusco - Peru - letrero (2013).jpg", None, None),
    "doc_015": ("foto", "Paraninfo Universitario - Cusco - Peru - letrero (2013).jpg", None, None),
    "doc_016": ("foto", "Placa de la Casa Amorós de Trujillo.jpg", None, None),
    # Manuscritos: cartas de la Biblioteca Nacional del Perú, una carta de 1880 y libros parroquiales de Lampa (Puno)
    "doc_017": ("manuscrito", "4000004161-0003 - Carta de Carlos J. Bachmann. 1912 junio 10, Riberalta; para Ricardo Palma, Lima.pdf", 1, None),
    "doc_018": ("manuscrito", "4000004161-0003 - Carta de Carlos J. Bachmann. 1912 junio 10, Riberalta; para Ricardo Palma, Lima.pdf", 2, None),
    "doc_019": ("manuscrito", "4000004161-0003 - Carta de Carlos J. Bachmann. 1912 junio 10, Riberalta; para Ricardo Palma, Lima.pdf", 3, None),
    "doc_020": ("manuscrito", "4000004161-0003 - Carta de Carlos J. Bachmann. 1912 junio 10, Riberalta; para Ricardo Palma, Lima.pdf", 4, None),
    "doc_021": ("manuscrito", "Carta de César Vallejo a José María Eguren.pdf", 1, None),
    "doc_022": ("manuscrito", "AAMSM carta a hermano 31072010.jpg", None, (0.353, 0.155, 0.917, 0.905)),
    "doc_023": ("manuscrito", "Libro de Bautismos en la Gran Villa de Lampa 1655-1722.jpg", None, None),
    "doc_024": ("manuscrito", "Libro de Bautismos en la Gran Villa de Lampa 1832.jpg", None, None),
    "doc_025": ("manuscrito", "Libro de Bautismos en la Gran Villa de Lampa 1871.jpg", None, None),
}

# Reservas por si algún documento sale ilegible y hay que reemplazarlo (mismo tipo)
RESERVAS = {
    "doc_r01": ("impreso", "Mercurio peruano (IA mercurioperuano07limauoft).pdf", 15, None),
    "doc_r02": ("impreso", "4000004161-0016 - Carta de Carlos J. Bachmann. 1914 julio 4, Maldonado; para Ricardo Palma, Lima.pdf", 2, None),
    "doc_r03": ("foto", "Carta de Felipe Santiago Salaverry a la seva esposa abans de la seva mort a Arequipa.jpg", None, None),
    "doc_r04": ("foto", "Santo Domingo - Cusco - Peru - letrero.jpg", None, None),
}

# Entrevistas y testimonios en español peruano
AUDIOS = {
    "clip_001": "Entrevista 1 en la Av. Rivagüero - El Agustino.ogg",
    "clip_002": "Entrevista 2 en la Av. Rivagüero - El Agustino.ogg",
    "clip_003": "Entrevista-Aurora Coronado-organización de mujeres indígenas-fiestas patrias.ogg",
    "clip_004": "Entrevista a Luz Merida-Organización de mujeres indígenas-fiestas patrias-protesta.ogg",
    "clip_005": "Testimonio Lucinda Quispealaya - Junín.ogg",
    "clip_006": "Entrevista 1,.wav",
    "clip_007": "Entrevista 2.wav",
    "clip_008": "Entrevista 3.wav",
    "clip_009": "Entrevista 4.wav",
    "clip_010": "ENTREVISTA A UN DOCENTE DE LA SAN MARCOS.ogg",
    "clip_011": "Entrevista a la señora Aurelia, mujer shuyasina.ogg",
    "clip_012": "Entrevista a la señora Dina Espinoza, mujer pomabambina.ogg",
    "clip_013": "Entrevista a María Romero, organizadora de la fiesta patronal de Tayta Palli de Chuyas.ogg",
    "clip_014": "Entrevista a una de las coordinadores del grupo AAXS.ogg",
    "clip_015": "ENTREVISTA MARCHA DEL ORGULLO.ogg",
    "clip_016": "ENTREVISTA A ACTIVISTA DE LA ORGANIZACIÓN \"SOPA PARA LA REINA\".ogg",
    "clip_017": "Entrevista realizada a dos jóvenes pertenecientes a la comunidad LGBT.ogg",
    "clip_018": "Entrevista a ciudadano peruano.ogg",
    "clip_019": "UNMSM Entrevistas en la marcha 2 VIDEO por Cristopher Serrano Pérez.ogg",
    "clip_020": "Testimonio 2 - Salas, pantallas y archivos.ogg",
    "clip_021": "Testimonio 4 - Salas, pantallas y archivos.ogg",
    "clip_022": "Testimonio 8 - Salas, pantallas y archivos.ogg",
    "clip_023": "Testimonio 7 - Salas, pantallas y archivos.ogg",
}


def api(**params):
    params["format"] = "json"
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    time.sleep(PAUSA)
    return json.load(urllib.request.urlopen(req, timeout=60))


def bajar(url, destino):
    time.sleep(PAUSA)
    req = urllib.request.Request(url, headers=UA)
    destino.write_bytes(urllib.request.urlopen(req, timeout=300).read())


def texto_plano(valor):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", valor or ""))).strip()


def ficha(titulo, pagina=None):
    """URL de descarga, licencia y autor de un archivo de Commons."""
    params = dict(action="query", titles="File:" + titulo, prop="imageinfo",
                  iiprop="url|extmetadata|size|mime")
    if pagina is not None:
        params.update(iiurlwidth=ANCHO, iiurlparam=f"page{pagina}-{ANCHO}px")
    elif not titulo.lower().endswith((".ogg", ".wav", ".opus", ".oga")):
        params.update(iiurlwidth=ANCHO)
    info = next(iter(api(**params)["query"]["pages"].values()))["imageinfo"][0]
    meta = info.get("extmetadata", {})
    return {
        "url": info.get("thumburl") or info["url"],
        "fuente_url": info["descriptionurl"],
        "licencia": texto_plano(meta.get("LicenseShortName", {}).get("value")),
        "autor": texto_plano(meta.get("Artist", {}).get("value"))[:200],
        "duracion_seg": info.get("duration"),
    }


def main():
    RAW_DOC.mkdir(parents=True, exist_ok=True)
    RAW_AUDIO.mkdir(parents=True, exist_ok=True)
    filas = []
    for id_, (tipo, titulo, pagina, recorte) in {**DOCUMENTOS, **RESERVAS}.items():
        f = ficha(titulo, pagina)
        destino = RAW_DOC / f"{id_}.jpg"
        if not destino.exists():
            bajar(f["url"], destino)
            if recorte:
                im = Image.open(destino)
                im.crop(tuple(int(v * t) for v, t in zip(recorte, im.size * 2))).save(destino, quality=95)
        filas.append({"id": id_, "modalidad": "documento", "tipo": tipo, "titulo": titulo, "pagina": pagina,
                      "fuente_url": f["fuente_url"], "licencia": f["licencia"], "autor": f["autor"], "recorte": recorte,
                      "acceso": f"Wikimedia Commons; descargar con descargar.py ({ANCHO} px)",
                      "reserva": id_ in RESERVAS})
        print(id_, tipo, f["licencia"], titulo[:60])
    for id_, titulo in AUDIOS.items():
        f = ficha(titulo)
        destino = RAW_AUDIO / f"{id_}{Path(titulo).suffix.lower()}"
        if not destino.exists():
            bajar(f["url"], destino)
        filas.append({"id": id_, "modalidad": "audio", "tipo": "entrevista", "titulo": titulo, "pagina": None,
                      "fuente_url": f["fuente_url"], "licencia": f["licencia"], "autor": f["autor"],
                      "acceso": "Wikimedia Commons; descargar con descargar.py (archivo original)",
                      "reserva": False, "duracion_seg": f["duracion_seg"]})
        print(id_, f["licencia"], f"{(f['duracion_seg'] or 0) / 60:.1f} min", titulo[:60])
    fuentes = pd.DataFrame(filas)
    fuentes["fecha_extraccion"] = pd.Timestamp.now(tz="America/Lima").strftime("%Y-%m-%d")
    fuentes.to_csv(RAIZ / "datos" / "fuentes.csv", index=False)
    audio = fuentes[fuentes.modalidad == "audio"]
    print(f"\n{(fuentes.modalidad == 'documento').sum()} documentos, {len(audio)} audios, "
          f"{audio.duracion_seg.sum() / 60:.1f} min de audio")


if __name__ == "__main__":
    main()
