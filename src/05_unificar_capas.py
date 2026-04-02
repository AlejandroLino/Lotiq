# -*- coding: utf-8 -*-
"""
05_unificar_capas.py
Unificación de capas:
  base subzonas + Capa 1 (transporte) + Capa 2 (FOT/FOS/CUR) +
  Capa 3 (densidad) + Capa 4 (POIs) + Capa 5 (absorción ZonaProp)
Score = 50% base + 15% transporte + 15% equipamiento + 10% FOT + 5% densidad + 5% absorción
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import unicodedata
import pandas as pd
import geopandas as gpd
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_OUTPUT    = Path("data/output")
DIR_OUTPUT.mkdir(parents=True, exist_ok=True)

# ── Pesos del score compuesto (6 componentes) ─────────────────────────────────
PESO_SCORE_BASE   = 0.50   # score original del dataset
PESO_TRANSPORTE   = 0.15   # Capa 1 — accesibilidad subte
PESO_FOT          = 0.10   # Capa 2 — potencial constructivo
PESO_DENSIDAD     = 0.05   # Capa 3 — densidad poblacional (inverso)
PESO_EQUIPAMIENTO = 0.15   # Capa 4 — POIs urbanos
PESO_ABSORCION    = 0.05   # Capa 5 — liquidez de mercado (más stock = más liquidez)

# =============================================================================
# 0. FUNCIÓN DE NORMALIZACIÓN PARA MERGE POR NOMBRE DE BARRIO
# =============================================================================

# Aliases generales (tildes, abreviaciones)
_ALIAS_BASE = {
    "paternal":          "la paternal",
    "villa gral. mitre": "villa general mitre",
    "boca":              "la boca",
    "montserrat":        "monserrat",
}

# Aliases específicos de ZonaProp: micro-zonas → barrio oficial CABA
# ZonaProp usa subdivisiones comerciales que no coinciden con los 48 barrios
_ALIAS_ZONAPROP = {
    # Balvanera y sub-zonas
    "abasto":               "balvanera",   # El Abasto pertenece a Balvanera
    "once":                 "balvanera",   # Once está en Balvanera
    "congreso":             "balvanera",   # Congreso está en Balvanera
    # Palermo y sub-zonas
    "barrio parque":        "palermo",     # Barrio Parque es una micro-zona de Palermo
    "palermo soho":         "palermo",
    "palermo hollywood":    "palermo",
    "palermo chico":        "palermo",
    # San Nicolás y sub-zonas
    "centro / microcentro": "san nicolas", # Microcentro = San Nicolás
    "tribunales":           "san nicolas", # Tribunales está en San Nicolás
    # Almagro sub-zonas
    "almagro sur":          "almagro",
    # Caballito sub-zonas
    "caballito norte":      "caballito",
    "caballito sur":        "caballito",
    # Núñez sub-zonas
    "lomas de nunez":       "nunez",
    # Recoleta sub-zonas
    "barrio norte":         "recoleta",    # Barrio Norte = zona norte de Recoleta
    # Belgrano sub-zonas (ya normalizadas por script 08)
    "belgrano r":           "belgrano",
    "belgrano c":           "belgrano",
}

_ALIAS_TODO = {**_ALIAS_BASE, **_ALIAS_ZONAPROP}


def normalizar_barrio(nombre):
    """Quita tildes, pasa a minúsculas y normaliza espacios para usarlo como key."""
    nfkd = unicodedata.normalize("NFKD", str(nombre))
    sin_tilde = "".join(c for c in nfkd if not unicodedata.combining(c))
    clave = sin_tilde.lower().strip()
    return _ALIAS_TODO.get(clave, clave)


# =============================================================================
# 1. CARGAR ARCHIVOS FUENTE
# =============================================================================
print("=" * 60)
print("CARGANDO ARCHIVOS FUENTE")
print("=" * 60)

df_sub = pd.read_csv(DIR_RAW / "168_subzonas_proptech.csv", encoding="utf-8-sig")
df_tra = pd.read_csv(DIR_PROCESSED / "transporte_subte_barrios.csv", encoding="utf-8-sig")
df_fot = pd.read_csv(DIR_PROCESSED / "fot_fos_barrios.csv", encoding="utf-8-sig")
df_den = pd.read_csv(DIR_PROCESSED / "censo_densidad_barrios.csv", encoding="utf-8-sig")
df_poi = pd.read_csv(DIR_PROCESSED / "pois_barrios.csv", encoding="utf-8-sig")
df_abs = pd.read_csv(DIR_PROCESSED / "absorcion_barrios.csv", encoding="utf-8-sig")

print(f"✓ Subzonas base:        {len(df_sub):>3} filas  |  {len(df_sub.columns)} columnas")
print(f"✓ Transporte (Capa 1):  {len(df_tra):>3} filas  |  {len(df_tra.columns)} columnas")
print(f"✓ FOT/FOS   (Capa 2):   {len(df_fot):>3} filas  |  {len(df_fot.columns)} columnas")
print(f"✓ Densidad  (Capa 3):   {len(df_den):>3} filas  |  {len(df_den.columns)} columnas")
print(f"✓ POIs      (Capa 4):   {len(df_poi):>3} filas  |  {len(df_poi.columns)} columnas")
print(f"✓ Absorción (Capa 5):   {len(df_abs):>3} filas  |  {len(df_abs.columns)} columnas")

# =============================================================================
# 2. NORMALIZAR CLAVES DE MERGE
# =============================================================================
df_sub["_key"] = df_sub["barrio"].apply(normalizar_barrio)
df_tra["_key"] = df_tra["barrio"].apply(normalizar_barrio)
df_fot["_key"] = df_fot["barrio"].apply(normalizar_barrio)
df_den["_key"] = df_den["barrio"].apply(normalizar_barrio)
df_poi["_key"] = df_poi["barrio"].apply(normalizar_barrio)
df_abs["_key"] = df_abs["barrio"].apply(normalizar_barrio)

# Capa 5: ZonaProp tiene micro-zonas → agregar al nivel de barrio oficial
# Antes del merge, consolidar: sumar stock, promediar precio/m²
df_abs_agg = df_abs.groupby("_key").agg(
    stock_avisos      = ("stock_avisos",      "sum"),
    precio_m2_zonaprop= ("precio_m2_mediana", "mean"),   # promedio de medianas por sub-zona
    precio_usd_zonaprop=("precio_usd_mediana","mean"),
    sup_prom_zonaprop  =("sup_promedio_m2",   "mean"),
).reset_index()
df_abs_agg["precio_m2_zonaprop"]  = df_abs_agg["precio_m2_zonaprop"].round(0)
df_abs_agg["precio_usd_zonaprop"] = df_abs_agg["precio_usd_zonaprop"].round(0)
df_abs_agg["sup_prom_zonaprop"]   = df_abs_agg["sup_prom_zonaprop"].round(1)

# Verificar cobertura antes de mergear
barrios_sub     = set(df_sub["_key"])
sin_match_tra   = barrios_sub - set(df_tra["_key"])
sin_match_fot   = barrios_sub - set(df_fot["_key"])
sin_match_den   = barrios_sub - set(df_den["_key"])
sin_match_poi   = barrios_sub - set(df_poi["_key"])
sin_match_abs   = barrios_sub - set(df_abs_agg["_key"])
con_match_abs   = barrios_sub & set(df_abs_agg["_key"])

print()
print("✓ Cobertura transporte: 48/48 OK" if not sin_match_tra else
      f"⚠ Sin match transporte: {sin_match_tra}")
print(f"✓ Cobertura FOT/FOS:    {48 - len(sin_match_fot)}/48 OK" +
      (f"  — sin datos: {sin_match_fot}" if sin_match_fot else ""))
print("✓ Cobertura densidad:   48/48 OK" if not sin_match_den else
      f"⚠ Sin match densidad: {sin_match_den}")
print("✓ Cobertura POIs:       48/48 OK" if not sin_match_poi else
      f"⚠ Sin match POIs: {sin_match_poi}")
print(f"✓ Cobertura absorción:  {len(con_match_abs)}/48 barrios con datos ZonaProp" +
      (f"\n  Sin datos: {sorted(sin_match_abs)}" if sin_match_abs else ""))

# =============================================================================
# 3. SELECCIONAR Y RENOMBRAR COLUMNAS DE CADA CAPA ANTES DEL MERGE
# =============================================================================

# Capa 1 — Transporte
cols_tra = {
    "dist_subte_m":         "dist_subte_m",
    "cant_estaciones_800m": "cant_estaciones_800m",
    "linea_subte_cercana":  "linea_subte_cercana",
    "estacion_cercana":     "estacion_cercana",
    "subte_5min":           "subte_5min",
    "subte_10min":          "subte_10min",
}
df_tra_sel = df_tra[["_key"] + list(cols_tra.keys())].rename(columns=cols_tra)

# Capa 2 — FOT/FOS/CUR
cols_fot = {
    "fot_promedio":        "fot_promedio",
    "fot_mediana":         "fot_mediana",
    "fot_maximo":          "fot_maximo",
    "fos_promedio":        "fos_promedio",
    "fos_maximo":          "fos_maximo",
    "altura_max_promedio": "altura_max_promedio",
    "altura_max_absoluta": "altura_max_absoluta",
    "dist_cur_dominante":  "dist_cur_dominante",
    "n_distritos_cur":     "n_distritos_cur",
    "m2_edif_estimado":    "m2_edif_estimado",
}
df_fot_sel = df_fot[["_key"] + list(cols_fot.keys())].rename(columns=cols_fot)

# Capa 3 — Densidad/Censo
cols_den = {
    "poblacion":        "poblacion",
    "viviendas":        "viviendas",
    "hogares":          "hogares",
    "hogares_nbi":      "hogares_nbi",
    "densidad_pob_km2": "densidad_pob_km2",
    "densidad_viv_km2": "densidad_viv_km2",
    "pct_nbi":          "pct_nbi",
    "pob_por_hogar":    "pob_por_hogar",
}
df_den_sel = df_den[["_key"] + list(cols_den.keys())].rename(columns=cols_den)

# Capa 4 — POIs
cols_poi = {
    "area_km2":         "area_km2",
    "idx_equipamiento": "idx_equipamiento",
    "escuelas":         "poi_escuelas",
    "universidades":    "poi_universidades",
    "hospitales":       "poi_hospitales",
    "clinicas":         "poi_clinicas",
    "restaurantes":     "poi_restaurantes",
    "cafes":            "poi_cafes",
    "comercios":        "poi_comercios",
    "bancos":           "poi_bancos",
    "farmacias":        "poi_farmacias",
    "parques":          "poi_parques",
    "gastronomia":      "poi_gastronomia",
}
df_poi_sel = df_poi[["_key"] + list(cols_poi.keys())].rename(columns=cols_poi)

# Capa 5 — Absorción ZonaProp
cols_abs = {
    "stock_avisos":       "stock_avisos",
    "precio_m2_zonaprop": "precio_m2_zonaprop",
    "precio_usd_zonaprop":"precio_usd_zonaprop",
    "sup_prom_zonaprop":  "sup_prom_zonaprop",
}
df_abs_sel = df_abs_agg[["_key"] + list(cols_abs.keys())].rename(columns=cols_abs)

# =============================================================================
# 4. MERGE
# =============================================================================
print()
print("=" * 60)
print("MERGEANDO CAPAS")
print("=" * 60)

# Eliminar columnas del CSV base que serán reemplazadas por los datos calculados
cols_a_eliminar = [
    "dist_subte", "subte_5min", "subte_10min", "linea_subte",
    "estacion_subte", "dist_hospital", "hospital_cercano"
]
df_sub = df_sub.drop(columns=[c for c in cols_a_eliminar if c in df_sub.columns])

df = df_sub.merge(df_tra_sel, on="_key", how="left")
df = df.merge(df_fot_sel,    on="_key", how="left")
df = df.merge(df_den_sel,    on="_key", how="left")
df = df.merge(df_poi_sel,    on="_key", how="left")
df = df.merge(df_abs_sel,    on="_key", how="left")

nulos_tra = df["dist_subte_m"].isna().sum()
nulos_fot = df["fot_promedio"].isna().sum()
nulos_den = df["densidad_pob_km2"].isna().sum()
nulos_poi = df["idx_equipamiento"].isna().sum()
nulos_abs = df["stock_avisos"].isna().sum()
print(f"✓ Merge completado: {len(df)} filas")
print(f"  Nulos transporte:  {nulos_tra}")
print(f"  Nulos FOT/FOS:     {nulos_fot}  (barrios sin datos CUR)")
print(f"  Nulos densidad:    {nulos_den}")
print(f"  Nulos POIs:        {nulos_poi}")
print(f"  Nulos absorción:   {nulos_abs}  (barrios sin avisos en snapshot)")

df = df.drop(columns=["_key"])

# =============================================================================
# 5. RECALCULAR SCORE_INVERSION (6 componentes)
# =============================================================================
print()
print("=" * 60)
print("RECALCULANDO SCORE DE INVERSIÓN — 6 COMPONENTES")
print("=" * 60)

# Guardar score original
df["score_original"] = df["score"]

# ── Score transporte: inversamente proporcional a distancia al subte ──────────
dist_min = df["dist_subte_m"].min()
dist_max = df["dist_subte_m"].max()
df["score_transporte"] = (
    (dist_max - df["dist_subte_m"]) / (dist_max - dist_min) * 100
).round(1)

# ── Score FOT: proporcional al FOT promedio (más FOT = más edificable) ─────────
fot_valido = df["fot_promedio"].dropna()
fot_min, fot_max = fot_valido.min(), fot_valido.max()
df["score_fot"] = (
    (df["fot_promedio"].fillna(fot_valido.mean()) - fot_min) / (fot_max - fot_min) * 100
).round(1)

# ── Score equipamiento: idx_equipamiento ya normalizado 0-100 ─────────────────
df["score_equipamiento"] = df["idx_equipamiento"]

# ── Score densidad: invertido (menor densidad = mayor disponibilidad de suelo) ─
den_valido = df["densidad_pob_km2"].dropna()
den_min, den_max = den_valido.min(), den_valido.max()
df["score_densidad"] = (
    (den_max - df["densidad_pob_km2"].fillna(den_valido.mean())) / (den_max - den_min) * 100
).round(1)

# ── Score absorción: proporcional al stock (más stock = más liquidez) ─────────
# Imputar NaN con la mediana (barrios sin data tienen liquidez media)
stock_valido = df["stock_avisos"].dropna()
stock_mediana = stock_valido.median()
df["stock_avisos_imp"] = df["stock_avisos"].fillna(stock_mediana)
stock_min = df["stock_avisos_imp"].min()
stock_max = df["stock_avisos_imp"].max()
df["score_absorcion"] = (
    (df["stock_avisos_imp"] - stock_min) / (stock_max - stock_min) * 100
).round(1)
df = df.drop(columns=["stock_avisos_imp"])  # columna auxiliar

# ── Score compuesto final ──────────────────────────────────────────────────────
df["score_inversion"] = (
    df["score_original"]     * PESO_SCORE_BASE   +
    df["score_transporte"]   * PESO_TRANSPORTE   +
    df["score_fot"]          * PESO_FOT          +
    df["score_densidad"]     * PESO_DENSIDAD     +
    df["score_equipamiento"] * PESO_EQUIPAMIENTO +
    df["score_absorcion"]    * PESO_ABSORCION
).round(1)

# Delta vs score original (solo comparativo, no indicador)
df["score_delta"] = (df["score_inversion"] - df["score_original"]).round(1)

print(f"  Pesos: base {PESO_SCORE_BASE:.0%}  transporte {PESO_TRANSPORTE:.0%}"
      f"  equipamiento {PESO_EQUIPAMIENTO:.0%}  FOT {PESO_FOT:.0%}"
      f"  densidad {PESO_DENSIDAD:.0%}  absorcion {PESO_ABSORCION:.0%}")
print()
print(f"  Score base         ({PESO_SCORE_BASE:.0%}): prom {df['score_original'].mean():.1f}")
print(f"  Score transporte   ({PESO_TRANSPORTE:.0%}): prom {df['score_transporte'].mean():.1f}")
print(f"  Score FOT          ({PESO_FOT:.0%}): prom {df['score_fot'].mean():.1f}"
      f"  [FOT prom real: {fot_valido.mean():.2f}]")
print(f"  Score densidad      ({PESO_DENSIDAD:.0%}): prom {df['score_densidad'].mean():.1f}")
print(f"  Score equipamiento ({PESO_EQUIPAMIENTO:.0%}): prom {df['score_equipamiento'].mean():.1f}")
print(f"  Score absorción     ({PESO_ABSORCION:.0%}): prom {df['score_absorcion'].mean():.1f}"
      f"  [stock prom: {stock_valido.mean():.0f} avisos/barrio]")
print()
print(f"  ▶ Score final promedio: {df['score_inversion'].mean():.1f}")

# =============================================================================
# 6. GUARDAR CSV
# =============================================================================
print()
print("=" * 60)
print("GUARDANDO OUTPUTS")
print("=" * 60)

ruta_csv = DIR_OUTPUT / "subzonas_completo.csv"
df.to_csv(ruta_csv, encoding="utf-8-sig", index=False)
print(f"✓ CSV: {ruta_csv}  ({len(df)} filas × {len(df.columns)} columnas)")

# =============================================================================
# 7. GENERAR GEOJSON — JOIN CON POLÍGONOS DE BARRIOS
# =============================================================================
gdf_barrios = gpd.read_file(DIR_RAW / "caba_48_barrios.geojson")
gdf_barrios["_key"] = gdf_barrios["barrio"].apply(normalizar_barrio)
df["_key"] = df["barrio"].apply(normalizar_barrio)

gdf_out = gdf_barrios[["_key", "geometry"]].merge(
    df.drop(columns=["lat", "lon"], errors="ignore"),
    on="_key",
    how="right"
)
gdf_out = gpd.GeoDataFrame(gdf_out.drop(columns=["_key"]), geometry="geometry", crs="EPSG:4326")

n_sin_geom = gdf_out["geometry"].isna().sum()
if n_sin_geom:
    print(f"⚠ {n_sin_geom} subzonas sin geometría de barrio asignada")

ruta_geojson = DIR_OUTPUT / "subzonas_completo.geojson"
gdf_out.to_file(ruta_geojson, driver="GeoJSON")
print(f"✓ GeoJSON: {ruta_geojson}  ({len(gdf_out)} features)")
df = df.drop(columns=["_key"])  # quitar clave auxiliar del GeoJSON

# =============================================================================
# 8. RESUMEN
# =============================================================================
print()
print("=" * 60)
print(f"DATASET MASTER — {len(df.columns)} COLUMNAS TOTALES")
print("=" * 60)

# Mostrar columnas agrupadas por capa
GRUPOS = {
    "Base (dataset original)":  ["barrio","subzona","precio_m2","rentabilidad","roi","volatilidad",
                                  "sharpe","prob_positivo","var95","score","proyeccion","payback",
                                  "categoria","emergente","zona_cur","altura_max","pisos","cap_rate",
                                  "ff5","n_pisos","m2_vendibles","costo_total","ingresos","margen",
                                  "perfil","precio_venta_m2","idx_gentrificacion","clase_gentrif",
                                  "gv","gp","gc","gt","score_desarrollo","accesibilidad","lat","lon"],
    "Capa 1 — Transporte":      ["dist_subte_m","cant_estaciones_800m","linea_subte_cercana",
                                  "estacion_cercana","subte_5min","subte_10min"],
    "Capa 2 — FOT/FOS/CUR":     ["fot_promedio","fot_mediana","fot_maximo","fos_promedio",
                                  "fos_maximo","altura_max_promedio","altura_max_absoluta",
                                  "dist_cur_dominante","n_distritos_cur","m2_edif_estimado"],
    "Capa 3 — Densidad":        ["poblacion","viviendas","hogares","hogares_nbi",
                                  "densidad_pob_km2","densidad_viv_km2","pct_nbi","pob_por_hogar"],
    "Capa 4 — POIs":            ["area_km2","idx_equipamiento","poi_escuelas","poi_universidades",
                                  "poi_hospitales","poi_clinicas","poi_restaurantes","poi_cafes",
                                  "poi_comercios","poi_bancos","poi_farmacias","poi_parques",
                                  "poi_gastronomia"],
    "Capa 5 — Absorción":       ["stock_avisos","precio_m2_zonaprop","precio_usd_zonaprop",
                                  "sup_prom_zonaprop"],
    "Score compuesto":          ["score_original","score_transporte","score_fot","score_densidad",
                                  "score_equipamiento","score_absorcion","score_inversion","score_delta"],
}

total_verificado = 0
for grupo, cols in GRUPOS.items():
    presentes = [c for c in cols if c in df.columns]
    total_verificado += len(presentes)
    print(f"  {grupo:<35} {len(presentes):>2} cols")

# Columnas no categorizadas (si las hay)
todas = set(df.columns)
categorizadas = {c for cols in GRUPOS.values() for c in cols}
sin_categoria = todas - categorizadas
if sin_categoria:
    print(f"  Sin categorizar:{' ' * 21} {len(sin_categoria):>2} cols  → {sorted(sin_categoria)}")
print(f"  {'─'*40}")
print(f"  TOTAL:{' ' * 31} {len(df.columns):>2} cols")

# =============================================================================
# 9. TOP 5 / BOTTOM 5 POR SCORE_INVERSION
# =============================================================================
print()
print("=" * 60)
print("TOP 5 — MAYOR SCORE DE INVERSIÓN FINAL")
print("=" * 60)
cols_rank = ["barrio", "subzona", "categoria", "precio_m2", "roi",
             "score_inversion", "dist_subte_m", "fot_promedio",
             "stock_avisos", "precio_m2_zonaprop"]
print(df.nlargest(5, "score_inversion")[cols_rank].to_string(index=False))

print()
print("=" * 60)
print("BOTTOM 5 — MENOR SCORE DE INVERSIÓN FINAL")
print("=" * 60)
print(df.nsmallest(5, "score_inversion")[cols_rank].to_string(index=False))

# =============================================================================
# 10. MAYORES CAMBIOS DE SCORE (nueva Capa 5 vs versión anterior)
# =============================================================================
print()
print("=" * 60)
print("TOP 5 — SUBIERON MÁS CON CAPA 5")
print("=" * 60)
cols_delta = ["barrio", "subzona", "score_original", "score_inversion",
              "score_delta", "stock_avisos", "precio_m2_zonaprop"]
print(df.nlargest(5, "score_delta")[cols_delta].to_string(index=False))

print()
print("=" * 60)
print("TOP 5 — BAJARON MÁS CON CAPA 5")
print("=" * 60)
print(df.nsmallest(5, "score_delta")[cols_delta].to_string(index=False))

print()
print("=" * 60)
print("✓ SCRIPT COMPLETADO SIN ERRORES")
print("=" * 60)
