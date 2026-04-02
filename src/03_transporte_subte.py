# -*- coding: utf-8 -*-
"""
03_transporte_subte.py
Capa 1: Transporte — Distancias a estaciones de subte CABA
Calcula métricas de accesibilidad al subte para 48 barrios y 168 subzonas.
CRS de cálculo: EPSG:22185 (Gauss-Krüger faja 5, Argentina) — distancias en metros reales.
"""

import sys
import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path

# Forzar UTF-8 en stdout para compatibilidad Windows
sys.stdout.reconfigure(encoding="utf-8")

# ── Rutas ────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

CRS_GEO  = "EPSG:4326"    # geográfico original
CRS_PROJ = "EPSG:22185"   # Gauss-Krüger faja 5 — metros

# ── Umbrales de caminata ──────────────────────────────────────────────────────
DIST_5MIN  = 400   # metros ≈ 5 min caminando
DIST_10MIN = 800   # metros ≈ 10 min caminando

# =============================================================================
# 1. CARGAR ESTACIONES DE SUBTE
# =============================================================================
print("=" * 60)
print("CARGANDO DATOS")
print("=" * 60)

df_est = pd.read_csv(DIR_RAW / "estaciones_de_subte.csv", encoding="utf-8-sig")
df_est["geometry"] = df_est["geometry"].apply(wkt.loads)
gdf_estaciones = gpd.GeoDataFrame(df_est, geometry="geometry", crs=CRS_GEO)
gdf_estaciones = gdf_estaciones.to_crs(CRS_PROJ)

print(f"✓ Estaciones cargadas: {len(gdf_estaciones)} | CRS → {CRS_PROJ}")
print(f"  Líneas: {sorted(gdf_estaciones['linea'].unique())}")

# =============================================================================
# 2. CARGAR BARRIOS Y SUBZONAS
# =============================================================================
gdf_barrios  = gpd.read_file(DIR_RAW / "caba_48_barrios.geojson")
gdf_subzonas = gpd.read_file(DIR_RAW / "168_subzonas_proptech.geojson")

print(f"✓ Barrios cargados:  {len(gdf_barrios)}  | CRS original: {gdf_barrios.crs}")
print(f"✓ Subzonas cargadas: {len(gdf_subzonas)} | CRS original: {gdf_subzonas.crs}")

# Validar 48 barrios
assert len(gdf_barrios) == 48, f"ERROR: se esperan 48 barrios, hay {len(gdf_barrios)}"
print("✓ Validación: 48 barrios OK")

# =============================================================================
# 3. REPROYECTAR A EPSG:22185
# =============================================================================
gdf_barrios  = gdf_barrios.to_crs(CRS_PROJ)
gdf_subzonas = gdf_subzonas.to_crs(CRS_PROJ)
print(f"✓ Reproyección a {CRS_PROJ} completada")

# =============================================================================
# 4. FUNCIÓN PRINCIPAL DE CÁLCULO
# =============================================================================

def calcular_metricas_subte(gdf_zonas, gdf_estaciones, col_nombre, es_punto=False):
    """
    Para cada zona calcula métricas de accesibilidad al subte.

    Parámetros:
        gdf_zonas     : GeoDataFrame con polígonos o puntos a analizar
        gdf_estaciones: GeoDataFrame de estaciones (puntos, proyectado)
        col_nombre    : columna de identificación de la zona
        es_punto      : True si la geometría ya es un punto (subzonas)
    """
    # Obtener centroides
    if es_punto:
        centroides = gdf_zonas.geometry
    else:
        centroides = gdf_zonas.geometry.centroid

    coords_est = list(zip(
        gdf_estaciones.geometry.x,
        gdf_estaciones.geometry.y
    ))

    resultados = []

    for idx, (nombre, centroide) in enumerate(zip(gdf_zonas[col_nombre], centroides)):

        # Distancia a cada estación
        distancias = gdf_estaciones.geometry.distance(centroide)

        # Estación más cercana
        idx_min      = distancias.idxmin()
        dist_min     = distancias[idx_min]
        linea_cercana = gdf_estaciones.loc[idx_min, "linea"]
        estacion_cercana = gdf_estaciones.loc[idx_min, "estacion"]

        # Cantidad de estaciones dentro de 800m
        cant_800m = int((distancias <= DIST_10MIN).sum())

        resultados.append({
            col_nombre:              nombre,
            "dist_subte_m":          round(dist_min, 1),
            "linea_subte_cercana":   linea_cercana,
            "estacion_cercana":      estacion_cercana,
            "cant_estaciones_800m":  cant_800m,
            "subte_5min":            bool(dist_min <= DIST_5MIN),
            "subte_10min":           bool(dist_min <= DIST_10MIN),
        })

    return pd.DataFrame(resultados)


# =============================================================================
# 5. CALCULAR PARA BARRIOS
# =============================================================================
print()
print("=" * 60)
print("CALCULANDO MÉTRICAS — 48 BARRIOS")
print("=" * 60)

df_barrios_res = calcular_metricas_subte(
    gdf_barrios, gdf_estaciones,
    col_nombre="barrio",
    es_punto=False   # polígonos → se usa centroide
)

df_barrios_res.to_csv(
    DIR_PROCESSED / "transporte_subte_barrios.csv",
    encoding="utf-8-sig", index=False
)
print(f"✓ Guardado: data/processed/transporte_subte_barrios.csv ({len(df_barrios_res)} filas)")

# =============================================================================
# 6. CALCULAR PARA SUBZONAS
# =============================================================================
print()
print("=" * 60)
print("CALCULANDO MÉTRICAS — 168 SUBZONAS")
print("=" * 60)

# Las subzonas tienen geometría POINT (centroides ya calculados)
df_subzonas_res = calcular_metricas_subte(
    gdf_subzonas, gdf_estaciones,
    col_nombre="subzona",
    es_punto=True
)

# Agregar columna barrio para contexto
df_subzonas_res.insert(0, "barrio", gdf_subzonas["barrio"].values)

df_subzonas_res.to_csv(
    DIR_PROCESSED / "transporte_subte_subzonas.csv",
    encoding="utf-8-sig", index=False
)
print(f"✓ Guardado: data/processed/transporte_subte_subzonas.csv ({len(df_subzonas_res)} filas)")

# =============================================================================
# 7. RESUMEN — BARRIOS
# =============================================================================
print()
print("=" * 60)
print("RESUMEN — BARRIOS")
print("=" * 60)

df_b = df_barrios_res.sort_values("dist_subte_m")

print("\n▸ TOP 10 BARRIOS MÁS CERCA DEL SUBTE:")
print(df_b[["barrio", "dist_subte_m", "linea_subte_cercana", "estacion_cercana", "subte_5min"]].head(10).to_string(index=False))

print("\n▸ TOP 10 BARRIOS MÁS LEJOS DEL SUBTE:")
print(df_b[["barrio", "dist_subte_m", "linea_subte_cercana", "estacion_cercana", "cant_estaciones_800m"]].tail(10).sort_values("dist_subte_m", ascending=False).to_string(index=False))

print("\n▸ ESTADÍSTICAS GENERALES — BARRIOS:")
stats = df_barrios_res["dist_subte_m"].describe()
print(f"  Promedio:  {stats['mean']:.0f} m")
print(f"  Mediana:   {stats['50%']:.0f} m")
print(f"  Mínimo:    {stats['min']:.0f} m")
print(f"  Máximo:    {stats['max']:.0f} m")
print(f"  Con subte ≤ 400m (5 min):  {df_barrios_res['subte_5min'].sum():>3} / 48  ({df_barrios_res['subte_5min'].mean()*100:.1f}%)")
print(f"  Con subte ≤ 800m (10 min): {df_barrios_res['subte_10min'].sum():>3} / 48  ({df_barrios_res['subte_10min'].mean()*100:.1f}%)")

print("\n▸ BARRIOS POR LÍNEA MÁS CERCANA:")
print(df_barrios_res["linea_subte_cercana"].value_counts().to_string())

# =============================================================================
# 8. RESUMEN — SUBZONAS
# =============================================================================
print()
print("=" * 60)
print("RESUMEN — SUBZONAS")
print("=" * 60)

df_s = df_subzonas_res.sort_values("dist_subte_m")

print("\n▸ TOP 10 SUBZONAS MÁS CERCA DEL SUBTE:")
print(df_s[["barrio", "subzona", "dist_subte_m", "linea_subte_cercana", "subte_5min"]].head(10).to_string(index=False))

print("\n▸ TOP 10 SUBZONAS MÁS LEJOS DEL SUBTE:")
print(df_s[["barrio", "subzona", "dist_subte_m", "linea_subte_cercana", "cant_estaciones_800m"]].tail(10).sort_values("dist_subte_m", ascending=False).to_string(index=False))

print("\n▸ ESTADÍSTICAS GENERALES — SUBZONAS:")
stats_s = df_subzonas_res["dist_subte_m"].describe()
print(f"  Promedio:  {stats_s['mean']:.0f} m")
print(f"  Mediana:   {stats_s['50%']:.0f} m")
print(f"  Mínimo:    {stats_s['min']:.0f} m")
print(f"  Máximo:    {stats_s['max']:.0f} m")
print(f"  Con subte ≤ 400m (5 min):  {df_subzonas_res['subte_5min'].sum():>3} / 168  ({df_subzonas_res['subte_5min'].mean()*100:.1f}%)")
print(f"  Con subte ≤ 800m (10 min): {df_subzonas_res['subte_10min'].sum():>3} / 168  ({df_subzonas_res['subte_10min'].mean()*100:.1f}%)")

print()
print("=" * 60)
print("✓ SCRIPT COMPLETADO SIN ERRORES")
print("=" * 60)
