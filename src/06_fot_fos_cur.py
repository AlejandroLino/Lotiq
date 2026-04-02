# -*- coding: utf-8 -*-
"""
06_fot_fos_cur.py
Capa 2: FOT / FOS / CUR — Normativa urbanística por barrio CABA
Descarga el dataset de Código Urbanístico de BA Data, reprojecta a WGS84,
hace join espacial con los 48 barrios y calcula métricas de edificabilidad.
Fuente: https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/codigo-urbanistico/codigo-urbanistico.geojson
"""

import sys
import io
import json
import urllib.request
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path

# Forzar UTF-8 en stdout para compatibilidad Windows
sys.stdout.reconfigure(encoding="utf-8")

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

CRS_GEO = "EPSG:4326"

URL_CUR = (
    "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
    "secretaria-de-desarrollo-urbano/codigo-urbanistico/"
    "codigo-urbanistico.geojson"
)

RUTA_CUR_RAW   = DIR_RAW / "codigo_urbanistico_caba.geojson"
RUTA_BARRIOS   = DIR_RAW / "caba_48_barrios.geojson"
RUTA_OUTPUT    = DIR_PROCESSED / "fot_fos_barrios.csv"

# Lote tipo para cálculo de m2 edificables estimados
LOTE_TIPO_M2 = 200

# =============================================================================
# 1. DESCARGA
# =============================================================================
print("=" * 60)
print("CAPA 2: FOT / FOS / CUR")
print("=" * 60)

if RUTA_CUR_RAW.exists():
    print(f"✓ Archivo ya descargado: {RUTA_CUR_RAW}")
else:
    print(f"→ Descargando Código Urbanístico desde BA Data...")
    print(f"  URL: {URL_CUR}")
    try:
        req = urllib.request.Request(URL_CUR, headers={"User-Agent": "CABATECH/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            contenido = resp.read()
        RUTA_CUR_RAW.write_bytes(contenido)
        tam_mb = len(contenido) / 1_048_576
        print(f"✓ Descargado: {tam_mb:.1f} MB → {RUTA_CUR_RAW}")
    except Exception as e:
        print(f"✗ Error en descarga: {e}")
        sys.exit(1)

# =============================================================================
# 2. CARGA Y VALIDACIÓN CUR
# =============================================================================
print("\n→ Cargando GeoJSON de Código Urbanístico...")

# El archivo de BA Data está en formato NDJSON (un Feature JSON por línea).
# La línea 0 viene truncada (sin inicio de Feature válido) — se descarta.
# Líneas 1..N son Features completos — se envuelven como FeatureCollection.

with open(RUTA_CUR_RAW, "r", encoding="utf-8") as f:
    lineas = f.readlines()

print(f"  Formato: NDJSON ({len(lineas)} líneas totales)")

# Parseo línea a línea con manejo de errores
# Cada línea válida es un Feature JSON completo
features_ok = []
errores_json = 0
descartadas = 0
for linea in lineas:
    linea = linea.strip()
    if not linea or '"type": "Feature"' not in linea:
        descartadas += 1
        continue
    try:
        # Las líneas terminan con coma trailing (ej. "...} },") — quitarla antes de parsear
        feat = json.loads(linea.rstrip(", "))
        features_ok.append(feat)
    except json.JSONDecodeError:
        errores_json += 1

print(f"  Features parseados: {len(features_ok):,}  |  Errores JSON: {errores_json}  |  Descartadas: {descartadas}")

# Construir GeoDataFrame desde lista de features
gdf_cur = gpd.GeoDataFrame.from_features(features_ok)
print(f"✓ GeoDataFrame creado: {len(gdf_cur):,} features")
print(f"  Columnas: {list(gdf_cur.columns)}")
print(f"  CRS detectado: {gdf_cur.crs}")

# Muestra de las primeras filas (sin geometría)
cols_preview = ["gid", "smp", "barrio", "dist_cpu_1", "fot_em_1",
                "fot_pl_1", "fot_sl_1", "alicuota", "plano_l"]
cols_preview = [c for c in cols_preview if c in gdf_cur.columns]
print(f"\n  Primeras 5 filas:")
print(gdf_cur[cols_preview].head().to_string(index=False))

# Estadísticas básicas de campos clave
print("\n  Estadísticas campos FOT/FOS/Altura (muestra completa):")
campos_num = ["fot_em_1", "fot_pl_1", "alicuota", "plano_l"]
campos_num = [c for c in campos_num if c in gdf_cur.columns]
for campo in campos_num:
    serie = pd.to_numeric(gdf_cur[campo], errors="coerce")
    nulos = serie.isna().sum()
    ceros = (serie == 0).sum()
    print(f"  {campo:15s} | min={serie.min():.2f}  max={serie.max():.2f}"
          f"  media={serie.mean():.2f}  nulos={nulos}  ceros={ceros}")

# =============================================================================
# 3. NORMALIZACIÓN DE NOMBRES DE BARRIO
# =============================================================================
# El dataset CUR ya trae campo 'barrio' — no se necesita spatial join.
# Solo hay que normalizar los nombres para el merge con la lista oficial de 48 barrios.

import unicodedata

def normalizar_barrio(nombre):
    """Normaliza nombre de barrio: sin tildes, minúsculas, strip.
    Aliases manuales para casos con abreviatura o nombre distinto."""
    ALIAS = {
        "paternal":          "la paternal",
        "villa gral. mitre": "villa general mitre",
        "gral. mitre":       "villa general mitre",
        "montserrat":        "monserrat",  # CUR usa 'montserrat', oficial es 'monserrat'
        "boca":              "la boca",    # CUR usa 'BOCA', oficial es 'La Boca'
    }
    if not isinstance(nombre, str):
        return ""
    n = unicodedata.normalize("NFKD", nombre)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower().strip()
    return ALIAS.get(n, n)

# Cargar barrios oficiales para obtener lista de 48 nombres canónicos
print("\n→ Cargando lista oficial de 48 barrios...")
gdf_barrios = gpd.read_file(RUTA_BARRIOS)

col_barrio = None
for candidato in ["BARRIO", "barrio", "NOM_BAR", "NOMBRE", "nombre"]:
    if candidato in gdf_barrios.columns:
        col_barrio = candidato
        break

if col_barrio is None:
    print(f"✗ Columna de barrio no encontrada. Columnas: {list(gdf_barrios.columns)}")
    sys.exit(1)

assert len(gdf_barrios) == 48, f"✗ Se esperaban 48 barrios, hay {len(gdf_barrios)}"
print(f"✓ 48 barrios oficiales cargados (columna: '{col_barrio}')")

# Normalizar nombres en el dataset oficial (columna de referencia)
gdf_barrios["barrio_norm"] = gdf_barrios[col_barrio].apply(normalizar_barrio)

# Normalizar el campo barrio del CUR
gdf_cur["barrio_norm"] = gdf_cur["barrio"].apply(normalizar_barrio)

barrios_cur = sorted(gdf_cur["barrio_norm"].dropna().unique())
barrios_ofic = sorted(gdf_barrios["barrio_norm"].unique())
sin_match = [b for b in barrios_cur if b not in barrios_ofic]
print(f"  Barrios en CUR: {len(barrios_cur)}  |  Sin match oficial: {len(sin_match)}")
if sin_match:
    print(f"  Sin match: {sin_match}")

# Trabajo con el campo normalizado
join = gdf_cur[["barrio_norm", "dist_cpu_1", "fot_em_1", "fot_pl_1",
                "fot_sl_1", "alicuota", "plano_l"]].copy()

# Convertir campos numéricos
for campo in ["fot_em_1", "fot_pl_1", "fot_sl_1", "alicuota", "plano_l"]:
    join[campo] = pd.to_numeric(join[campo], errors="coerce")

# Excluir valores negativos de FOT (datos erróneos)
fot_neg = (join["fot_em_1"] < 0).sum()
if fot_neg > 0:
    print(f"  Advertencia: {fot_neg} parcelas con FOT negativo — excluidas del cálculo")
    join.loc[join["fot_em_1"] < 0, "fot_em_1"] = np.nan

print(f"✓ {len(join):,} parcelas listas para agregación")

# =============================================================================
# 6. AGREGACIÓN POR BARRIO
# =============================================================================
print("\n→ Calculando métricas por barrio...")

def dist_dominante(series):
    """Devuelve el valor más frecuente de una serie, ignorando nulos."""
    s = series.dropna()
    return s.mode().iloc[0] if len(s) > 0 else None

def altura_promedio_sin_ceros(series):
    """Promedio de plano_l excluyendo ceros (cero = sin restricción, no es altura real)."""
    s = series[series > 0]
    return round(s.mean(), 2) if len(s) > 0 else np.nan

resumen_cur = join.groupby("barrio_norm").apply(
    lambda g: pd.Series({
        "n_parcelas":              len(g),
        "fot_promedio":            round(g["fot_em_1"].mean(), 3),
        "fot_mediana":             round(g["fot_em_1"].median(), 3),
        "fot_maximo":              round(g["fot_em_1"].max(), 3),
        "fot_minimo":              round(g["fot_em_1"].min(), 3),
        "fos_promedio":            round(g["alicuota"].mean(), 4),
        "fos_minimo":              round(g["alicuota"].min(), 4),
        "fos_maximo":              round(g["alicuota"].max(), 4),
        "altura_max_promedio":     altura_promedio_sin_ceros(g["plano_l"]),
        "altura_max_mediana":      round(g["plano_l"][g["plano_l"] > 0].median(), 2)
                                   if (g["plano_l"] > 0).any() else np.nan,
        "altura_max_absoluta":     round(g["plano_l"].max(), 2),
        "pct_parcelas_sin_altura": round((g["plano_l"] == 0).mean() * 100, 1),
        "dist_cur_dominante":      dist_dominante(g["dist_cpu_1"]),
        "n_distritos_cur":         g["dist_cpu_1"].nunique(),
    }),
    include_groups=False
).reset_index()

# Merge con lista oficial de 48 barrios usando nombre normalizado
# → garantiza que el output tenga el nombre oficial correcto (con tildes, capitalización)
barrios_ref = gdf_barrios[[col_barrio, "barrio_norm"]].rename(
    columns={col_barrio: "barrio"}
)
resumen = barrios_ref.merge(resumen_cur, on="barrio_norm", how="left").drop(
    columns="barrio_norm"
)

# m2 edificables estimados con lote tipo
resumen["m2_edif_estimado"] = (resumen["fot_promedio"] * LOTE_TIPO_M2).round(1)

print(f"✓ Métricas calculadas para {len(resumen_cur)} barrios con datos CUR")

# =============================================================================
# 7. VALIDACIÓN FINAL
# =============================================================================
assert len(resumen) == 48, f"✗ Se esperaban 48 barrios en output, hay {len(resumen)}"
nulos_fot = resumen["fot_promedio"].isna().sum()
if nulos_fot > 0:
    barrios_sin = resumen[resumen["fot_promedio"].isna()]["barrio"].tolist()
    print(f"  Advertencia: {nulos_fot} barrios sin datos CUR → {barrios_sin}")
    print(f"  (Estos barrios tendrán NaN — no se imputarán)")
print("✓ Validación: 48 barrios en output")

# =============================================================================
# 8. GUARDAR OUTPUT
# =============================================================================
print(f"\n→ Guardando {RUTA_OUTPUT}...")
resumen.to_csv(RUTA_OUTPUT, encoding="utf-8-sig", sep=",", index=False)
print(f"✓ Guardado: {RUTA_OUTPUT} ({len(resumen)} filas × {len(resumen.columns)} columnas)")
print(f"  Columnas: {list(resumen.columns)}")

# =============================================================================
# 9. RANKINGS
# =============================================================================
print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MAYOR FOT PROMEDIO (más edificable)")
print("=" * 60)
top10_alto = resumen.nlargest(10, "fot_promedio")[
    ["barrio", "fot_promedio", "fot_maximo", "fos_promedio",
     "altura_max_promedio", "dist_cur_dominante", "n_parcelas", "m2_edif_estimado"]
]
print(top10_alto.to_string(index=False))

print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MENOR FOT PROMEDIO (menos edificable)")
print("=" * 60)
top10_bajo = resumen.nsmallest(10, "fot_promedio")[
    ["barrio", "fot_promedio", "fot_maximo", "fos_promedio",
     "altura_max_promedio", "dist_cur_dominante", "n_parcelas", "m2_edif_estimado"]
]
print(top10_bajo.to_string(index=False))

print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MAYOR ALTURA MÁXIMA PROMEDIO")
print("=" * 60)
top10_altura = resumen.dropna(subset=["altura_max_promedio"]).nlargest(
    10, "altura_max_promedio"
)[["barrio", "altura_max_promedio", "altura_max_absoluta",
   "fot_promedio", "dist_cur_dominante"]]
print(top10_altura.to_string(index=False))

print("\n" + "=" * 60)
print("RESUMEN GENERAL")
print("=" * 60)
print(f"  FOT promedio CABA:          {resumen['fot_promedio'].mean():.3f}")
print(f"  FOT máximo (barrio):        {resumen['fot_maximo'].max():.3f}  — {resumen.loc[resumen['fot_maximo'].idxmax(), 'barrio']}")
print(f"  FOT mínimo (barrio):        {resumen['fot_promedio'].min():.3f}  — {resumen.loc[resumen['fot_promedio'].idxmin(), 'barrio']}")
print(f"  FOS promedio CABA:          {resumen['fos_promedio'].mean():.4f} ({resumen['fos_promedio'].mean()*100:.1f}%)")
print(f"  Altura promedio CABA:       {resumen['altura_max_promedio'].mean():.1f} m")
print(f"  m2 edificables (lote 200):  {resumen['m2_edif_estimado'].mean():.0f} m2 promedio")
print(f"  Total parcelas procesadas:  {resumen['n_parcelas'].sum():,}")

print("\n✓ Capa 2 (FOT/FOS/CUR) completada exitosamente")
