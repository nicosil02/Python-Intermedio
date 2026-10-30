"""Descarga datos abiertos del MEF y los reduce a lo que usa el proyecto.

- DETALLE_INVERSIONES.csv: cada inversion publica con ubicacion (lat/lon) y fechas.
- {anio}-Gasto*.csv: gasto de todo el Estado (3-10 GB por anio). Se descarga a una
  carpeta temporal y se agrega a municipalidad x mes x rubro x funcion.

Uso: python scripts/obtener_datos.py inversiones
     python scripts/obtener_datos.py gasto <carpeta_temporal> 2022 2023 ...
"""
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/"
RAIZ = Path(__file__).resolve().parents[1]
ORIG = RAIZ / "datos" / "originales"
PROC = RAIZ / "datos" / "procesados"
MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO",
         "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
CLAVES = ["ANO_EJE", "SEC_EJEC", "EJECUTORA_NOMBRE", "UBIGEO", "CATEGORIA_GASTO",
          "RUBRO_NOMBRE", "FUNCION_NOMBRE", "GENERICA_NOMBRE"]


def inversiones():
    # DETALLE trae las inversiones activas; CIERRE, las ya cerradas. Sin CIERRE los
    # anios antiguos salen subrepresentados.
    ORIG.mkdir(parents=True, exist_ok=True)
    for nombre in ["DETALLE_INVERSIONES.csv", "CIERRE_INVERSIONES.csv"]:
        df = pd.read_csv(BASE + nombre, dtype=str, encoding="utf-8-sig")
        df.to_csv(ORIG / nombre, index=False)
        print(f"{nombre}: {len(df):,} filas ({date.today()})")


def gasto(anio, carpeta):
    # Los anios cerrados vienen en formato mensual (MES_EJE); 2025 y 2026, en formato
    # "Devengado-Diario" con una columna por mes.
    nombre = f"{anio}-Gasto.csv" if anio < 2025 else f"{anio}-Gasto-Devengado-Diario.csv"
    csv = Path(carpeta) / nombre
    # El servidor corta las conexiones largas: curl reintenta y retoma (-C -) donde quedo.
    subprocess.run(["curl", "-sS", "-L", "--retry", "50", "--retry-all-errors", "-C", "-",
                    "-o", str(csv), BASE + nombre], check=True)
    partes = []
    lector = pd.read_csv(csv, dtype=str, chunksize=500_000, encoding="utf-8-sig")
    for i, ch in enumerate(lector):
        ch = ch[ch["NIVEL_GOBIERNO"] == "M"].copy()
        ch["UBIGEO"] = (ch["DEPARTAMENTO_EJECUTORA"] + ch["PROVINCIA_EJECUTORA"]
                        + ch["DISTRITO_EJECUTORA"])
        if "MES_EJE" in ch:
            ch["MES"] = ch["MES_EJE"].astype(int)
            ch["DEVENGADO"] = ch["MONTO_DEVENGADO"].astype(float)
            ch["PIM"] = ch["MONTO_PIM"].astype(float)
            largo = ch[CLAVES + ["MES", "DEVENGADO", "PIM"]]
        else:
            cols = {f"MONTO_DEVENGADO_{m}": i + 1 for i, m in enumerate(MESES)}
            largo = ch.melt(id_vars=CLAVES + ["MONTO_PIM"], value_vars=list(cols),
                            var_name="MES", value_name="DEVENGADO")
            largo["MES"] = largo["MES"].map(cols)
            largo["DEVENGADO"] = largo["DEVENGADO"].astype(float)
            # El PIM es anual: se asigna solo a enero para no multiplicarlo por 12.
            largo["PIM"] = largo["MONTO_PIM"].astype(float).where(largo["MES"] == 1, 0.0)
            largo = largo.drop(columns="MONTO_PIM")
        partes.append(largo.groupby(CLAVES + ["MES"], as_index=False)[["DEVENGADO", "PIM"]].sum())
        print(f"{anio}: bloque {i + 1}", flush=True)
    df = pd.concat(partes).groupby(CLAVES + ["MES"], as_index=False)[["DEVENGADO", "PIM"]].sum()
    PROC.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROC / f"gasto_municipal_{anio}.parquet", index=False)
    print(f"{anio}: listo, {len(df):,} filas ({date.today()})")


if __name__ == "__main__":
    if sys.argv[1] == "inversiones":
        inversiones()
    else:
        for a in sys.argv[3:]:
            gasto(int(a), sys.argv[2])
