# -*- coding: utf-8 -*-
"""
04_pois_osm.py
Capa 4: POIs urbanos desde OpenStreetMap (Overpass API)
Descarga, procesa y calcula índice de equipamiento por barrio CABA.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import time
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, shape
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Bounding box CABA (lon_min, lat_min, lon_max, lat_max) ────────────────────
# Formato Overpass: (lat_min, lon_min, lat_max, lon_max) = sur, oeste, norte, este
BBOX_OVERPASS = "-34.7059,-58.5315,-34.5265,-58.3351"

# ── Categorías de POIs y sus pesos para idx_equipamiento ─────────────────────
CATEGORIAS = {
    "escuelas":      ("amenity", "school",      3.0),
    "universidades": ("amenity", "university",  4.0),
    "hospitales":    ("amenity", "hospital",    5.0),
    "clinicas":      ("amenity", "clinic",      2.0),
    "restaurantes":  ("amenity", "restaurant",  1.0),
    "cafes":         ("amenity", "cafe",        1.0),
    "bancos":        ("amenity", "bank",        2.0),
    "farmacias":     ("amenity", "pharmacy",    2.0),
    "comercios":     ("shop",    None,          0.5),
    "parques":       ("leisure", "park",        3.0),
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TIMEOUT_SEG  = 90
MAX_REINTENTOS = 3
PAUSA_ENTRE_QUERIES = 3   # segundos entre llamadas para no saturar la API

# =============================================================================
# 1. FUNCIÓN DE DESCARGA CON REINTENTOS
# =============================================================================

def construir_query(tag_key, tag_value, bbox):
    """Construye query Overpass para nodos y ways de un tipo de POI."""
    if tag_value:
        filtro = f'["{tag_key}"="{tag_value}"]'
    else:
        filtro = f'["{tag_key}"]'

    return f"""
[out:json][timeout:{TIMEOUT_SEG}];
(
  node{filtro}({bbox});
  way{filtro}({bbox});
  relation{filtro}({bbox});
);
out center tags;
"""

def descargar_pois(categoria, tag_key, tag_value, bbox):
    """Descarga POIs de Overpass con reintentos. Retorna lista de features."""
    query = construir_query(tag_key, tag_value, bbox)

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=TIMEOUT_SEG + 10,
                headers={"User-Agent": "CABATECH/1.0 (analisis-inmobiliario-caba)"}
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("elements", [])

        except requests.exceptions.Timeout:
            print(f"  ⚠ Timeout en intento {intento}/{MAX_REINTENTOS} para '{categoria}'")
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Error en intento {intento}/{MAX_REINTENTOS}: {e}")

        if intento < MAX_REINTENTOS:
            espera = PAUSA_ENTRE_QUERIES * intento
            print(f"  → Reintentando en {espera}s...")
            time.sleep(espera)

    print(f"  ✗ Fallaron todos los intentos para '{categoria}' — se omite")
    return []

# =============================================================================
# 2. CONVERTIR ELEMENTOS OVERPASS A GEODATAFRAME
# =============================================================================

def elementos_a_geodataframe(elementos, categoria):
    """
    Convierte lista de elementos Overpass a GeoDataFrame.
    - Nodos: usan su lat/lon directamente.
    - Ways/Relations: usan el campo 'center' que retorna Overpass con 'out center'.
    """
    registros = []

    for el in elementos:
        tipo = el.get("type")
        tags = el.get("tags", {})

        if tipo == "node":
            lat = el.get("lat")
            lon = el.get("lon")
        elif tipo in ("way", "relation"):
            center = el.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")
        else:
            continue

        if lat is None or lon is None:
            continue

        registros.append({
            "osm_id":    el.get("id"),
            "osm_type":  tipo,
            "categoria": categoria,
            "nombre":    tags.get("name", ""),
            "amenity":   tags.get("amenity", ""),
            "shop":      tags.get("shop", ""),
            "leisure":   tags.get("leisure", ""),
            "geometry":  Point(lon, lat),
        })

    return gpd.GeoDataFrame(registros, geometry="geometry", crs="EPSG:4326")

# =============================================================================
# 3. DESCARGA DE TODAS LAS CATEGORÍAS
# =============================================================================
print("=" * 60)
print("DESCARGA DE POIs — OpenStreetMap / Overpass API")
print("=" * 60)

gdfs_pois = []

for categoria, (tag_key, tag_value, peso) in CATEGORIAS.items():
    desc_tag = f"{tag_key}={tag_value}" if tag_value else f"{tag_key}=*"
    print(f"\n▸ [{categoria}]  {desc_tag}")

    elementos = descargar_pois(categoria, tag_key, tag_value, BBOX_OVERPASS)
    print(f"  → {len(elementos)} elementos descargados de Overpass")

    if elementos:
        gdf_cat = elementos_a_geodataframe(elementos, categoria)
        gdfs_pois.append(gdf_cat)
        print(f"  ✓ {len(gdf_cat)} POIs con geometría válida")

    time.sleep(PAUSA_ENTRE_QUERIES)

if not gdfs_pois:
    print("\n✗ No se descargó ningún POI. Verificar conexión a internet.")
    sys.exit(1)

# Unificar todos los POIs
gdf_pois = pd.concat(gdfs_pois, ignore_index=True)
print(f"\n✓ Total POIs descargados: {len(gdf_pois)}")
print(gdf_pois["categoria"].value_counts().to_string())

# =============================================================================
# 4. GUARDAR POIs EN data/raw/
# =============================================================================
ruta_pois_geojson = DIR_RAW / "pois_caba.geojson"
gdf_pois.to_file(ruta_pois_geojson, driver="GeoJSON")
print(f"\n✓ GeoJSON guardado: {ruta_pois_geojson}")

# =============================================================================
# 5. CARGAR BARRIOS Y CALCULAR ÁREA EN KM²
# =============================================================================
print()
print("=" * 60)
print("SPATIAL JOIN — POIs × BARRIOS")
print("=" * 60)

gdf_barrios = gpd.read_file(DIR_RAW / "caba_48_barrios.geojson")
gdf_barrios_proj = gdf_barrios.to_crs("EPSG:22185")
gdf_barrios_proj["area_km2"] = gdf_barrios_proj.geometry.area / 1_000_000

# Join espacial: asignar cada POI a un barrio
gdf_pois_proj = gdf_pois.to_crs("EPSG:22185")
join = gpd.sjoin(gdf_pois_proj, gdf_barrios_proj[["barrio", "geometry"]], how="left", predicate="within")

# POIs que cayeron fuera de los polígonos (bordes)
n_fuera = join["barrio"].isna().sum()
if n_fuera > 0:
    print(f"  ⚠ {n_fuera} POIs fuera de los polígonos de barrio (descartados)")
join = join.dropna(subset=["barrio"])

print(f"  ✓ {len(join)} POIs asignados a barrios")

# =============================================================================
# 6. CONTAR POIs POR BARRIO Y CATEGORÍA
# =============================================================================
pivot = (
    join.groupby(["barrio", "categoria"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# Asegurar que todas las columnas existen aunque no haya POIs de esa categoría
for cat in CATEGORIAS:
    if cat not in pivot.columns:
        pivot[cat] = 0

# Columna gastronomia = restaurantes + cafes
pivot["gastronomia"] = pivot["restaurantes"] + pivot["cafes"]

# =============================================================================
# 7. CALCULAR idx_equipamiento
# =============================================================================
# Merge con áreas
df_areas = gdf_barrios_proj[["barrio", "area_km2"]].copy()
pivot = pivot.merge(df_areas, on="barrio", how="left")

pivot["idx_equipamiento_raw"] = (
    pivot.get("escuelas",      0) * 3.0 +
    pivot.get("hospitales",    0) * 5.0 +
    pivot.get("universidades", 0) * 4.0 +
    pivot.get("clinicas",      0) * 2.0 +
    pivot.get("gastronomia",   0) * 1.0 +
    pivot.get("comercios",     0) * 0.5 +
    pivot.get("bancos",        0) * 2.0 +
    pivot.get("farmacias",     0) * 2.0 +
    pivot.get("parques",       0) * 3.0
) / pivot["area_km2"]

# Normalizar 0-100
raw_min = pivot["idx_equipamiento_raw"].min()
raw_max = pivot["idx_equipamiento_raw"].max()
pivot["idx_equipamiento"] = (
    (pivot["idx_equipamiento_raw"] - raw_min) / (raw_max - raw_min) * 100
).round(1)

# Ordenar columnas finales
cols_orden = (
    ["barrio", "area_km2", "idx_equipamiento"] +
    list(CATEGORIAS.keys()) + ["gastronomia"]
)
cols_presentes = [c for c in cols_orden if c in pivot.columns]
df_final = pivot[cols_presentes].sort_values("idx_equipamiento", ascending=False)
df_final["area_km2"] = df_final["area_km2"].round(2)

# Guardar
ruta_csv = DIR_PROCESSED / "pois_barrios.csv"
df_final.to_csv(ruta_csv, encoding="utf-8-sig", index=False)
print(f"✓ Guardado: {ruta_csv}")

# =============================================================================
# 8. RESUMEN FINAL
# =============================================================================
print()
print("=" * 60)
print("RESUMEN — ÍNDICE DE EQUIPAMIENTO URBANO (0-100)")
print("=" * 60)

print("\n▸ TOP 10 — MEJOR EQUIPADOS:")
cols_show = ["barrio", "idx_equipamiento", "escuelas", "hospitales",
             "gastronomia", "comercios", "farmacias", "parques"]
cols_show = [c for c in cols_show if c in df_final.columns]
print(df_final[cols_show].head(10).to_string(index=False))

print("\n▸ BOTTOM 10 — MENOR EQUIPAMIENTO:")
print(df_final[cols_show].tail(10).sort_values("idx_equipamiento").to_string(index=False))

print("\n▸ ESTADÍSTICAS:")
print(f"  Promedio idx:  {df_final['idx_equipamiento'].mean():.1f}")
print(f"  Mediana idx:   {df_final['idx_equipamiento'].median():.1f}")
print(f"  Máximo:        {df_final['idx_equipamiento'].max():.1f}  ({df_final.iloc[0]['barrio']})")
print(f"  Mínimo:        {df_final['idx_equipamiento'].min():.1f}  ({df_final.iloc[-1]['barrio']})")
print(f"\n  Total POIs en CABA: {len(join):,}")
for cat in CATEGORIAS:
    if cat in pivot.columns:
        total = int(pivot[cat].sum())
        print(f"    {cat:<15}: {total:>5}")

print()
print("=" * 60)
print("✓ SCRIPT COMPLETADO SIN ERRORES")
print("=" * 60)
