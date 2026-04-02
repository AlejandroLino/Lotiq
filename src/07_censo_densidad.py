# -*- coding: utf-8 -*-
"""
07_censo_densidad.py
Capa 3: Densidad poblacional por barrio CABA
Fuente: Información censal por radio GCBA (Censo 2010, 3554 radios censales).
Nota: Censo 2022 de INDEC no está publicado a granularidad de barrio —
      los datos más granulares disponibles son los radios censales del Censo 2010.
URL: http://cdn.buenosaires.gob.ar/datosabiertos/datasets/informacion-censal-por-radio/CABA_rc.geojson
"""

import sys
import unicodedata
import urllib.request
import json
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

URL_RADIOS = (
    "http://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
    "informacion-censal-por-radio/CABA_rc.geojson"
)

RUTA_RADIOS_RAW = DIR_RAW / "radios_censales_caba.geojson"
RUTA_BARRIOS    = DIR_RAW / "caba_48_barrios.geojson"
RUTA_OUTPUT     = DIR_PROCESSED / "censo_densidad_barrios.csv"

# =============================================================================
# FUNCIÓN DE NORMALIZACIÓN (misma que en otros scripts)
# =============================================================================
def normalizar_barrio(nombre):
    ALIAS = {
        "paternal":          "la paternal",
        "villa gral. mitre": "villa general mitre",
        "boca":              "la boca",
        "montserrat":        "monserrat",
    }
    if not isinstance(nombre, str):
        return ""
    n = unicodedata.normalize("NFKD", nombre)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower().strip()
    return ALIAS.get(n, n)

# =============================================================================
# 1. DESCARGA
# =============================================================================
print("=" * 60)
print("CAPA 3: DENSIDAD POBLACIONAL — RADIOS CENSALES")
print("=" * 60)
print("Fuente: Información censal por radio GCBA (Censo 2010)")
print()

if RUTA_RADIOS_RAW.exists():
    print(f"✓ Archivo ya descargado: {RUTA_RADIOS_RAW}")
else:
    print(f"→ Descargando radios censales desde BA Data...")
    print(f"  URL: {URL_RADIOS}")
    try:
        req = urllib.request.Request(URL_RADIOS, headers={"User-Agent": "CABATECH/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            contenido = resp.read()
        RUTA_RADIOS_RAW.write_bytes(contenido)
        tam_mb = len(contenido) / 1_048_576
        print(f"✓ Descargado: {tam_mb:.1f} MB → {RUTA_RADIOS_RAW}")
    except Exception as e:
        print(f"✗ Error en descarga: {e}")
        sys.exit(1)

# =============================================================================
# 2. CARGA Y DIAGNÓSTICO
# =============================================================================
print("\n→ Cargando radios censales...")

# Intentar carga directa con GeoPandas
try:
    gdf_rc = gpd.read_file(RUTA_RADIOS_RAW)
    print(f"✓ Cargados {len(gdf_rc):,} radios censales")
except Exception as e:
    # Fallback: parseo NDJSON (mismo formato que codigo_urbanistico)
    print(f"  Carga directa falló ({e}) — intentando parseo NDJSON...")
    with open(RUTA_RADIOS_RAW, "r", encoding="utf-8") as f:
        lineas = f.readlines()
    features_ok = []
    for linea in lineas:
        linea = linea.strip()
        if '"type": "Feature"' not in linea:
            continue
        try:
            features_ok.append(json.loads(linea.rstrip(", ")))
        except json.JSONDecodeError:
            pass
    gdf_rc = gpd.GeoDataFrame.from_features(features_ok)
    print(f"✓ Cargados via NDJSON: {len(gdf_rc):,} radios censales")

print(f"  Columnas: {list(gdf_rc.columns)}")
print(f"  CRS: {gdf_rc.crs}")

# Vista previa de los datos
cols_prev = ["RADIO_ID", "BARRIO", "COMUNA", "POBLACION", "VIVIENDAS",
             "HOGARES", "HOGARES_NBI", "AREA_KM2"]
cols_prev = [c for c in cols_prev if c in gdf_rc.columns]
print(f"\n  Primeras 5 filas:")
print(gdf_rc[cols_prev].head().to_string(index=False))

# Convertir campos numéricos
for campo in ["POBLACION", "VIVIENDAS", "HOGARES", "HOGARES_NBI", "AREA_KM2"]:
    if campo in gdf_rc.columns:
        gdf_rc[campo] = pd.to_numeric(gdf_rc[campo], errors="coerce")

# Estadísticas globales
print(f"\n  Estadísticas totales CABA:")
print(f"  Población total:   {gdf_rc['POBLACION'].sum():,.0f}")
print(f"  Viviendas totales: {gdf_rc['VIVIENDAS'].sum():,.0f}")
print(f"  Hogares totales:   {gdf_rc['HOGARES'].sum():,.0f}")
print(f"  Hogares NBI:       {gdf_rc['HOGARES_NBI'].sum():,.0f}  ({gdf_rc['HOGARES_NBI'].sum()/gdf_rc['HOGARES'].sum()*100:.1f}%)")
print(f"  Área total:        {gdf_rc['AREA_KM2'].sum():.1f} km²")

# =============================================================================
# 3. VERIFICAR CRS Y NORMALIZAR BARRIO
# =============================================================================
# Determinar si las coordenadas son WGS84 o sistema local GCBA
primer_geom = gdf_rc.geometry.iloc[0]
x, y = primer_geom.centroid.x, primer_geom.centroid.y
print(f"\n→ CRS verificación — centroide radio 0: x={x:.4f}, y={y:.4f}")

if -180 <= x <= 180 and -90 <= y <= 90:
    print("  Coordenadas WGS84 — sin reproyección necesaria")
    if gdf_rc.crs is None:
        gdf_rc = gdf_rc.set_crs("EPSG:4326")
else:
    print(f"  Coordenadas métricas (sistema local GCBA) — este dataset usa campo BARRIO directamente")

# El dataset tiene campo BARRIO — se puede agregar sin spatial join
barrios_rc = sorted(gdf_rc["BARRIO"].dropna().unique()) if "BARRIO" in gdf_rc.columns else []
print(f"  Barrios en radios censales: {len(barrios_rc)}")

# =============================================================================
# 4. CARGAR LISTA OFICIAL DE 48 BARRIOS
# =============================================================================
print("\n→ Cargando barrios CABA oficiales...")
gdf_barrios = gpd.read_file(RUTA_BARRIOS)

col_barrio = None
for candidato in ["BARRIO", "barrio", "NOM_BAR", "NOMBRE", "nombre"]:
    if candidato in gdf_barrios.columns:
        col_barrio = candidato
        break

assert len(gdf_barrios) == 48, f"✗ Se esperaban 48 barrios, hay {len(gdf_barrios)}"
print(f"✓ 48 barrios oficiales cargados (columna: '{col_barrio}')")

gdf_barrios["barrio_norm"] = gdf_barrios[col_barrio].apply(normalizar_barrio)

# =============================================================================
# 5. DECIDIR ESTRATEGIA: JOIN POR CAMPO BARRIO o SPATIAL JOIN
# =============================================================================
if "BARRIO" in gdf_rc.columns and len(barrios_rc) > 0:
    print("\n→ Estrategia: agrupación por campo BARRIO (sin spatial join)")
    gdf_rc["barrio_norm"] = gdf_rc["BARRIO"].apply(normalizar_barrio)

    sin_match = set(gdf_rc["barrio_norm"].dropna().unique()) - set(gdf_barrios["barrio_norm"])
    if sin_match:
        print(f"  ⚠ Barrios en radios sin match oficial: {sorted(sin_match)}")
    else:
        print(f"  ✓ Todos los barrios del dataset tienen match")

    # Agrupar por barrio
    print("\n→ Calculando métricas por barrio...")
    resumen_rc = gdf_rc.groupby("barrio_norm").agg(
        n_radios         = ("POBLACION", "count"),
        poblacion        = ("POBLACION", "sum"),
        viviendas        = ("VIVIENDAS", "sum"),
        hogares          = ("HOGARES", "sum"),
        hogares_nbi      = ("HOGARES_NBI", "sum"),
        area_km2_censo   = ("AREA_KM2", "sum"),
    ).reset_index()

else:
    # Fallback: spatial join si no hay campo BARRIO
    print("\n→ Estrategia: spatial join (no hay campo BARRIO en radios)")
    if gdf_rc.crs is None or gdf_rc.crs.to_epsg() != 4326:
        print("  ✗ No se puede hacer spatial join sin CRS válido")
        sys.exit(1)
    gdf_barrios_wgs = gdf_barrios.to_crs("EPSG:4326")
    gdf_rc_pts = gdf_rc.copy()
    gdf_rc_pts["geometry"] = gdf_rc_pts.geometry.centroid
    join = gpd.sjoin(gdf_rc_pts, gdf_barrios_wgs[["barrio_norm", "geometry"]],
                     how="left", predicate="within")
    join = join[join["barrio_norm"].notna()]
    for campo in ["POBLACION", "VIVIENDAS", "HOGARES", "HOGARES_NBI", "AREA_KM2"]:
        join[campo] = pd.to_numeric(join[campo], errors="coerce")
    resumen_rc = join.groupby("barrio_norm").agg(
        n_radios         = ("POBLACION", "count"),
        poblacion        = ("POBLACION", "sum"),
        viviendas        = ("VIVIENDAS", "sum"),
        hogares          = ("HOGARES", "sum"),
        hogares_nbi      = ("HOGARES_NBI", "sum"),
        area_km2_censo   = ("AREA_KM2", "sum"),
    ).reset_index()

# =============================================================================
# 6. CALCULAR MÉTRICAS DERIVADAS
# =============================================================================
resumen_rc["densidad_pob_km2"]  = (resumen_rc["poblacion"] / resumen_rc["area_km2_censo"]).round(1)
resumen_rc["densidad_viv_km2"]  = (resumen_rc["viviendas"] / resumen_rc["area_km2_censo"]).round(1)
resumen_rc["pct_nbi"]           = (resumen_rc["hogares_nbi"] / resumen_rc["hogares"] * 100).round(2)
resumen_rc["pob_por_hogar"]     = (resumen_rc["poblacion"] / resumen_rc["hogares"]).round(2)
resumen_rc["viv_por_habitante"] = (resumen_rc["viviendas"] / resumen_rc["poblacion"]).round(4)

# Normalización de densidad para score (0-100)
dens_min = resumen_rc["densidad_pob_km2"].min()
dens_max = resumen_rc["densidad_pob_km2"].max()
resumen_rc["score_densidad"] = (
    (resumen_rc["densidad_pob_km2"] - dens_min) / (dens_max - dens_min) * 100
).round(1)

print(f"✓ Métricas calculadas para {len(resumen_rc)} barrios")

# =============================================================================
# 7. MERGE CON LISTA OFICIAL DE 48 BARRIOS
# =============================================================================
barrios_ref = gdf_barrios[[col_barrio, "barrio_norm"]].rename(columns={col_barrio: "barrio"})
resumen = barrios_ref.merge(resumen_rc, on="barrio_norm", how="left").drop(columns="barrio_norm")

# Validación
assert len(resumen) == 48, f"✗ Se esperaban 48 barrios, hay {len(resumen)}"
nulos_pob = resumen["poblacion"].isna().sum()
if nulos_pob > 0:
    sin_datos = resumen[resumen["poblacion"].isna()]["barrio"].tolist()
    print(f"  ⚠ {nulos_pob} barrios sin datos censales: {sin_datos}")
print("✓ Validación: 48 barrios en output")

# =============================================================================
# 8. GUARDAR OUTPUT
# =============================================================================
print(f"\n→ Guardando {RUTA_OUTPUT}...")
resumen.to_csv(RUTA_OUTPUT, encoding="utf-8-sig", index=False)
print(f"✓ Guardado: {RUTA_OUTPUT} ({len(resumen)} filas × {len(resumen.columns)} columnas)")
print(f"  Columnas: {list(resumen.columns)}")

# =============================================================================
# 9. RANKINGS
# =============================================================================
print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MAYOR DENSIDAD POBLACIONAL (hab/km²)")
print("=" * 60)
top_densa = resumen.dropna(subset=["densidad_pob_km2"]).nlargest(10, "densidad_pob_km2")[
    ["barrio", "poblacion", "densidad_pob_km2", "densidad_viv_km2", "pct_nbi", "n_radios"]
]
print(top_densa.to_string(index=False))

print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MENOR DENSIDAD POBLACIONAL")
print("=" * 60)
bot_densa = resumen.dropna(subset=["densidad_pob_km2"]).nsmallest(10, "densidad_pob_km2")[
    ["barrio", "poblacion", "densidad_pob_km2", "densidad_viv_km2", "pct_nbi", "n_radios"]
]
print(bot_densa.to_string(index=False))

print("\n" + "=" * 60)
print("TOP 10 BARRIOS — MAYOR % HOGARES NBI")
print("=" * 60)
top_nbi = resumen.dropna(subset=["pct_nbi"]).nlargest(10, "pct_nbi")[
    ["barrio", "pct_nbi", "hogares_nbi", "hogares", "densidad_pob_km2"]
]
print(top_nbi.to_string(index=False))

print("\n" + "=" * 60)
print("RESUMEN GENERAL CABA")
print("=" * 60)
tot_pob  = resumen["poblacion"].sum()
tot_area = resumen["area_km2_censo"].sum()
tot_hog  = resumen["hogares"].sum()
tot_nbi  = resumen["hogares_nbi"].sum()
print(f"  Población total CABA (Censo 2010):  {tot_pob:,.0f}")
print(f"  Área total (radios):                {tot_area:.1f} km²")
print(f"  Densidad promedio CABA:             {tot_pob/tot_area:,.0f} hab/km²")
print(f"  Hogares totales:                    {tot_hog:,.0f}")
print(f"  Hogares NBI:                        {tot_nbi:,.0f}  ({tot_nbi/tot_hog*100:.1f}% del total)")
print(f"  Pob. promedio por hogar:            {(tot_pob/tot_hog):.2f}")
print(f"  Barrio más denso:   {resumen.loc[resumen['densidad_pob_km2'].idxmax(), 'barrio']}"
      f"  ({resumen['densidad_pob_km2'].max():,.0f} hab/km²)")
print(f"  Barrio menos denso: {resumen.loc[resumen['densidad_pob_km2'].idxmin(), 'barrio']}"
      f"  ({resumen['densidad_pob_km2'].min():,.0f} hab/km²)")

print("\n✓ Capa 3 (Densidad poblacional) completada exitosamente")
print("  Nota: datos de Censo 2010 (publicación por radio censal más reciente disponible).")
print("  El Censo 2022 de INDEC solo está publicado a nivel nacional/provincial/comunal.")
