# -*- coding: utf-8 -*-
"""
09_exportar_tableau.py
Prepara subzonas_completo.csv para importación limpia en Tableau:
  - Nombres de columnas: snake_case, sin tildes, sin espacios
  - Tipos: numéricos float, booleanos como 0/1, textos como string
  - Nuevas columnas: categoria_precio, categoria_score
  - Redondeo a 2 decimales
  - Encoding utf-8-sig, separador coma
  - Verificación de caracteres problemáticos para Tableau
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import re
import unicodedata
import pandas as pd
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_OUTPUT = Path("data/output")
INPUT_CSV  = DIR_OUTPUT / "subzonas_completo.csv"
OUTPUT_CSV = DIR_OUTPUT / "TABLEAU_CABATECH_MASTER.csv"

# ── Umbrales ──────────────────────────────────────────────────────────────────
UMBRAL_PREMIUM   = 4000   # USD/m²
UMBRAL_MEDIO     = 2000   # USD/m²
UMBRAL_SCORE_ALTO = 65
UMBRAL_SCORE_BAJO = 40

# =============================================================================
# 1. CARGAR
# =============================================================================
print("=" * 60)
print("  CABATECH — Exportación para Tableau")
print("=" * 60)

df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
print(f"\n✓ Cargado: {INPUT_CSV}")
print(f"  Shape original: {df.shape[0]} filas × {df.shape[1]} columnas")
print(f"  Tipos originales: {dict(df.dtypes.value_counts())}")


# =============================================================================
# 2. LIMPIAR NOMBRES DE COLUMNAS
#    → snake_case, sin tildes, sin espacios, todo minúsculas
# =============================================================================
print("\n" + "─" * 60)
print("  [1] Limpiando nombres de columnas")
print("─" * 60)

def limpiar_nombre_col(nombre: str) -> str:
    """Quita tildes, pasa a minúsculas, reemplaza espacios/puntos por _, colapsa __."""
    # Quitar tildes
    nfkd = unicodedata.normalize("NFKD", nombre)
    sin_tilde = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Minúsculas
    limpio = sin_tilde.lower()
    # Reemplazar cualquier caracter no alfanumérico (excepto _) por _
    limpio = re.sub(r"[^a-z0-9_]", "_", limpio)
    # Colapsar múltiples _ consecutivos
    limpio = re.sub(r"_+", "_", limpio)
    # Quitar _ al inicio y final
    return limpio.strip("_")

renombres = {}
for col in df.columns:
    col_limpio = limpiar_nombre_col(col)
    if col_limpio != col:
        renombres[col] = col_limpio

if renombres:
    df = df.rename(columns=renombres)
    print(f"  Columnas renombradas: {len(renombres)}")
    for orig, nuevo in renombres.items():
        print(f"    {orig} → {nuevo}")
else:
    print("  ✓ Todos los nombres ya están limpios")

# Verificar que no queden duplicados tras limpiar
assert len(df.columns) == len(set(df.columns)), "ERROR: hay columnas duplicadas tras renombrar"


# =============================================================================
# 3. CONVERTIR TIPOS
# =============================================================================
print("\n" + "─" * 60)
print("  [2] Convirtiendo tipos de datos")
print("─" * 60)

# ── Booleanos → int (0/1) ──────────────────────────────────────────────────
# Tableau no tiene tipo booleano nativo; 0/1 se comporta como dimensión y medida
cols_bool = df.select_dtypes(include="bool").columns.tolist()
if cols_bool:
    for col in cols_bool:
        df[col] = df[col].astype(int)
    print(f"  Bool → int (0/1): {cols_bool}")
else:
    print("  Sin columnas bool")

# ── Strings: asegurar tipo str limpio ────────────────────────────────────────
# Convertir StringDtype (pandas ExtensionArray) a str Python puro para CSV limpio
cols_str = df.select_dtypes(include=["object", "string"]).columns.tolist()
for col in cols_str:
    df[col] = df[col].astype(str).replace("nan", pd.NA)
    df[col] = df[col].where(df[col].notna(), other="")
print(f"  String (object/StringDtype) → str Python: {len(cols_str)} columnas")

# ── Numéricos: forzar float donde corresponde ─────────────────────────────────
# Detectar columnas que deberían ser numéricas pero quedaron object
cols_posibles_num = [c for c in df.columns if c not in cols_str]
n_convertidos = 0
for col in cols_posibles_num:
    if df[col].dtype == object:
        convertido = pd.to_numeric(df[col], errors="coerce")
        if convertido.notna().sum() > len(df) * 0.5:  # más del 50% son números
            df[col] = convertido
            n_convertidos += 1
if n_convertidos:
    print(f"  Object → float64 (conversión forzada): {n_convertidos} columnas")


# =============================================================================
# 4. LIMPIAR VALORES STRING (caracteres problemáticos para Tableau/CSV)
# =============================================================================
print("\n" + "─" * 60)
print("  [3] Limpiando valores de texto")
print("─" * 60)

# Caracteres que rompen CSV o Tableau: saltos de línea, tabulaciones, comillas dobles anidadas
CHARS_PROBLEMATICOS = {"\n": " ", "\r": " ", "\t": " ", '"': "'"}

cols_str_finales = df.select_dtypes(include=["object", "str"]).columns.tolist()
n_fixes = 0
for col in cols_str_finales:
    for char_malo, reemplazo in CHARS_PROBLEMATICOS.items():
        mask = df[col].str.contains(char_malo, regex=False, na=False)
        if mask.any():
            df.loc[mask, col] = df.loc[mask, col].str.replace(char_malo, reemplazo, regex=False)
            n_fixes += mask.sum()

if n_fixes:
    print(f"  ⚠ Caracteres problemáticos reemplazados: {n_fixes} celdas")
else:
    print("  ✓ Sin caracteres problemáticos en texto")

# Normalizar tildes en VALORES de texto (opcional: conservar para legibilidad en Tableau)
# Decisión: CONSERVAR tildes en valores (Tableau soporta UTF-8 correctamente)
# Solo normalizar la forma Unicode (NFC = composición canónica, la más compatible)
for col in cols_str_finales:
    df[col] = df[col].apply(
        lambda x: unicodedata.normalize("NFC", x) if isinstance(x, str) else x
    )
print("  ✓ Valores Unicode normalizados a NFC")


# =============================================================================
# 5. NUEVAS COLUMNAS DERIVADAS
# =============================================================================
print("\n" + "─" * 60)
print("  [4] Agregando columnas derivadas")
print("─" * 60)

# ── categoria_precio: basada en precio_m2 ────────────────────────────────────
def clasificar_precio(pm2):
    if pd.isna(pm2):
        return ""
    if pm2 > UMBRAL_PREMIUM:
        return "Premium"
    elif pm2 >= UMBRAL_MEDIO:
        return "Medio"
    else:
        return "Economico"

df["categoria_precio"] = df["precio_m2"].apply(clasificar_precio)

dist_precio = df["categoria_precio"].value_counts().to_dict()
print(f"  categoria_precio (umbral Premium >${UMBRAL_PREMIUM}, Medio >${UMBRAL_MEDIO}):")
for cat, n in sorted(dist_precio.items()):
    print(f"    {cat:<12} {n:>3} subzonas")

# ── categoria_score: basada en score_inversion ───────────────────────────────
def clasificar_score(sc):
    if pd.isna(sc):
        return ""
    if sc > UMBRAL_SCORE_ALTO:
        return "Alto"
    elif sc >= UMBRAL_SCORE_BAJO:
        return "Medio"
    else:
        return "Bajo"

df["categoria_score"] = df["score_inversion"].apply(clasificar_score)

dist_score = df["categoria_score"].value_counts().to_dict()
print(f"  categoria_score (Alto >{UMBRAL_SCORE_ALTO}, Medio >{UMBRAL_SCORE_BAJO}):")
for cat, n in sorted(dist_score.items()):
    print(f"    {cat:<12} {n:>3} subzonas")


# =============================================================================
# 6. REDONDEAR DECIMALES
# =============================================================================
print("\n" + "─" * 60)
print("  [5] Redondeando decimales a 2 posiciones")
print("─" * 60)

cols_float = df.select_dtypes(include="float64").columns.tolist()
df[cols_float] = df[cols_float].round(2)
print(f"  ✓ {len(cols_float)} columnas float redondeadas")


# =============================================================================
# 7. ORDEN DE COLUMNAS (lógico, para facilitar exploración en Tableau)
# =============================================================================
ORDEN_COLS = [
    # Identificadores
    "barrio", "subzona", "lat", "lon",
    # Clasificaciones
    "categoria", "categoria_precio", "categoria_score", "perfil",
    "emergente", "clase_gentrif", "zona_cur",
    # Precio y rentabilidad
    "precio_m2", "precio_venta_m2", "rentabilidad", "roi", "cap_rate",
    "sharpe", "volatilidad", "var95", "prob_positivo", "payback",
    "proyeccion", "margen", "costo_total", "ingresos",
    # Constructivo
    "pisos", "n_pisos", "altura_max", "m2_vendibles", "ff5",
    # Score compuesto
    "score_inversion", "score_original", "score_delta",
    "score_transporte", "score_fot", "score_densidad",
    "score_equipamiento", "score_absorcion",
    # Scores auxiliares
    "score", "score_desarrollo", "accesibilidad",
    "idx_gentrificacion", "gv", "gp", "gc", "gt",
    # Capa 1 — Transporte
    "dist_subte_m", "cant_estaciones_800m", "linea_subte_cercana",
    "estacion_cercana", "subte_5min", "subte_10min",
    # Capa 2 — FOT/FOS/CUR
    "fot_promedio", "fot_mediana", "fot_maximo",
    "fos_promedio", "fos_maximo",
    "altura_max_promedio", "altura_max_absoluta",
    "dist_cur_dominante", "n_distritos_cur", "m2_edif_estimado",
    # Capa 3 — Densidad
    "poblacion", "viviendas", "hogares", "hogares_nbi",
    "densidad_pob_km2", "densidad_viv_km2", "pct_nbi", "pob_por_hogar",
    # Capa 4 — POIs
    "area_km2", "idx_equipamiento",
    "poi_escuelas", "poi_universidades", "poi_hospitales", "poi_clinicas",
    "poi_restaurantes", "poi_cafes", "poi_comercios", "poi_bancos",
    "poi_farmacias", "poi_parques", "poi_gastronomia",
    # Capa 5 — Absorción
    "stock_avisos", "precio_m2_zonaprop", "precio_usd_zonaprop", "sup_prom_zonaprop",
]

# Incluir solo las que existen, agregar al final las que no están en el orden definido
cols_en_orden = [c for c in ORDEN_COLS if c in df.columns]
cols_restantes = [c for c in df.columns if c not in cols_en_orden]
df = df[cols_en_orden + cols_restantes]

if cols_restantes:
    print(f"\n  Columnas no categorizadas (al final): {cols_restantes}")


# =============================================================================
# 8. GUARDAR
# =============================================================================
print("\n" + "─" * 60)
print("  [6] Guardando")
print("─" * 60)

df.to_csv(OUTPUT_CSV, encoding="utf-8-sig", sep=",", index=False)
size_kb = OUTPUT_CSV.stat().st_size / 1024
print(f"  ✓ {OUTPUT_CSV}")
print(f"    {df.shape[0]} filas × {df.shape[1]} columnas  |  {size_kb:.1f} KB")


# =============================================================================
# 9. VERIFICACIÓN FINAL PARA TABLEAU
# =============================================================================
print("\n" + "=" * 60)
print("  VERIFICACIÓN PARA TABLEAU")
print("=" * 60)

# ── 9a. Tipos finales ─────────────────────────────────────────────────────────
tipo_conteo = df.dtypes.value_counts().to_dict()
print(f"\n  Tipos de datos finales:")
for tipo, n in sorted(tipo_conteo.items(), key=lambda x: -x[1]):
    print(f"    {str(tipo):<15} {n:>2} columnas")

# ── 9b. Nulos por sección ─────────────────────────────────────────────────────
print(f"\n  Nulos por capa:")
grupos_nulos = {
    "Score":      ["score_inversion","score_absorcion","score_fot"],
    "Transporte": ["dist_subte_m","linea_subte_cercana"],
    "FOT/CUR":    ["fot_promedio","m2_edif_estimado"],
    "Densidad":   ["densidad_pob_km2","pct_nbi"],
    "POIs":       ["idx_equipamiento","poi_escuelas"],
    "Absorción":  ["stock_avisos","precio_m2_zonaprop"],
}
for grupo, cols in grupos_nulos.items():
    cols_ok = [c for c in cols if c in df.columns]
    nulos = {c: int(df[c].isna().sum()) for c in cols_ok}
    estado = "✓" if all(v == 0 for v in nulos.values()) else "⚠"
    print(f"    {estado} {grupo:<15} {nulos}")

# ── 9c. Caracteres que rompen Tableau ─────────────────────────────────────────
print(f"\n  Verificación de caracteres problemáticos en strings:")
CHARS_TEST = ["\n", "\r", "\t", "\x00", '"""']
hay_problema = False
cols_str_check = df.select_dtypes(include=["object", "str"]).columns
for col in cols_str_check:
    for char in CHARS_TEST:
        mask = df[col].str.contains(char, regex=False, na=False)
        if mask.any():
            print(f"    ⚠ '{col}' tiene {mask.sum()} celdas con '{repr(char)}'")
            hay_problema = True
if not hay_problema:
    print("    ✓ Sin caracteres problemáticos")

# ── 9d. Columnas con nombres potencialmente problemáticos ────────────────────
print(f"\n  Verificación de nombres de columna (Tableau-safe):")
cols_raras = [c for c in df.columns
              if re.search(r"[^a-z0-9_]", c) or c[0].isdigit()]
if cols_raras:
    print(f"    ⚠ Columnas con caracteres no estándar: {cols_raras}")
else:
    print(f"    ✓ Todos los nombres son snake_case válidos")

# ── 9e. Distribución de categorías nuevas ────────────────────────────────────
print(f"\n  Distribución categoria_precio:")
print("   ", df["categoria_precio"].value_counts().to_dict())
print(f"  Distribución categoria_score:")
print("   ", df["categoria_score"].value_counts().to_dict())

# ── 9f. Resumen columnas para Tableau (para documentación) ───────────────────
print(f"\n  Columnas disponibles en Tableau ({len(df.columns)} total):")
SECCIONES = [
    ("Dimensiones geográficas", ["barrio","subzona","lat","lon"]),
    ("Dimensiones categóricas", ["categoria","categoria_precio","categoria_score",
                                  "perfil","emergente","clase_gentrif","zona_cur",
                                  "linea_subte_cercana","dist_cur_dominante"]),
    ("Medidas de precio",       ["precio_m2","precio_venta_m2","precio_m2_zonaprop",
                                  "precio_usd_zonaprop"]),
    ("Medidas de rentabilidad", ["roi","cap_rate","sharpe","rentabilidad",
                                  "var95","payback","margen"]),
    ("Score compuesto",         ["score_inversion","score_transporte","score_fot",
                                  "score_densidad","score_equipamiento","score_absorcion"]),
    ("Transporte",              ["dist_subte_m","cant_estaciones_800m",
                                  "subte_5min","subte_10min"]),
    ("Normativa (FOT/FOS)",     ["fot_promedio","fos_promedio","m2_edif_estimado",
                                  "altura_max_promedio"]),
    ("Demografía",              ["poblacion","densidad_pob_km2","pct_nbi"]),
    ("POIs",                    ["idx_equipamiento","poi_escuelas","poi_hospitales",
                                  "poi_comercios","poi_restaurantes"]),
    ("Absorción mercado",       ["stock_avisos","sup_prom_zonaprop"]),
]
for seccion, cols in SECCIONES:
    presentes = [c for c in cols if c in df.columns]
    print(f"    {seccion:<30} {presentes}")

print()
print("=" * 60)
print(f"  ✓ Listo para Tableau: {OUTPUT_CSV.name}")
print("=" * 60)
print()
