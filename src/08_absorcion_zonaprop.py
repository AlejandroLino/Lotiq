# -*- coding: utf-8 -*-
"""
08_absorcion_zonaprop.py
Capa 5: Absorción de mercado — Snapshot ZonaProp

Parte 1 — Snapshot único:
  - Scrapea departamentos en venta en CABA (primeras 20 páginas)
  - Extrae: id/url, barrio, precio USD, superficie m², precio/m², ambientes, título
  - Guarda raw en data/raw/zonaprop_snapshot_YYYY-MM-DD.csv
  - Guarda agregado en data/processed/absorcion_barrios.csv

Estrategia de scraping (en orden de intento):
  1° undetected-chromedriver (bypasea Cloudflare/anti-bot)
  2° requests + headers Chrome (para entornos sin Chrome)
  En ambos casos: extrae __PRELOADED_STATE__ (JSON) o usa BeautifulSoup
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import re
import json
import time
import random
import unicodedata
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
import pandas as pd

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR_RAW       = Path("data/raw")
DIR_PROCESSED = Path("data/processed")
DIR_RAW.mkdir(parents=True, exist_ok=True)
DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

FECHA_HOY         = date.today().isoformat()
RAW_OUTPUT        = DIR_RAW / f"zonaprop_snapshot_{FECHA_HOY}.csv"
PROCESSED_OUTPUT  = DIR_PROCESSED / "absorcion_barrios.csv"

# ── Configuración ─────────────────────────────────────────────────────────────
BASE_URL        = "https://www.zonaprop.com.ar"
URL_PAGINA_1    = f"{BASE_URL}/departamentos-venta-capital-federal.html"
URL_PAGINA_N    = f"{BASE_URL}/departamentos-venta-capital-federal-pagina-{{n}}.html"
MAX_PAGINAS     = 20
DELAY_MIN       = 2.5
DELAY_MAX       = 5.0
TIMEOUT         = 20

# ── Headers Chrome real ───────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

# ── Normalización de barrios ──────────────────────────────────────────────────
ALIAS = {
    "palermo soho": "palermo",
    "palermo hollywood": "palermo",
    "palermo chico": "palermo",
    "palermo nuevo": "palermo",
    "palermo viejo": "palermo",
    "las canitas": "palermo",
    "belgrano r": "belgrano",
    "belgrano c": "belgrano",
    "nuñez": "nunez",
}

def normalizar_barrio(nombre: str) -> str:
    if not nombre:
        return "desconocido"
    nombre = nombre.strip().lower()
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"\s+", " ", nombre).strip()
    return ALIAS.get(nombre, nombre)


# ══════════════════════════════════════════════════════════════════════════════
# PARSEO DE HTML (compartido por ambas estrategias)
# ══════════════════════════════════════════════════════════════════════════════

def extraer_json_embebido(html: str) -> list:
    """Busca __PRELOADED_STATE__ u otras variables JSON en el HTML."""
    # Patrón principal de ZonaProp
    for patron in [
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;?\s*(?:window\.|</script>)',
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.*)',
    ]:
        match = re.search(patron, html, re.DOTALL)
        if match:
            # Tomar hasta el primer </script> para no romper el JSON
            raw = match.group(1)
            raw = raw.split("</script>")[0].rstrip("; \n")
            try:
                state = json.loads(raw)
                listings = _extraer_de_state(state)
                if listings:
                    return listings
            except json.JSONDecodeError:
                pass

    # Patrón alternativo: array de listings directamente
    for patron in [
        r'"(?:realEstates|postings|listings|results)"\s*:\s*(\[.*?\])\s*[,}]',
    ]:
        match = re.search(patron, html, re.DOTALL)
        if match:
            try:
                arr = json.loads(match.group(1))
                if isinstance(arr, list) and arr:
                    return arr
            except json.JSONDecodeError:
                pass

    return []


def _extraer_de_state(state: dict) -> list:
    rutas = [
        ["listStore", "listings"],
        ["listings", "results"],
        ["search", "results", "listings"],
        ["realEstate", "listings"],
        ["page", "data", "listings"],
        ["initialProps", "pageProps", "listings"],
    ]
    for ruta in rutas:
        nodo = state
        try:
            for clave in ruta:
                nodo = nodo[clave]
            if isinstance(nodo, list) and nodo:
                return nodo
        except (KeyError, TypeError):
            continue
    return []


def parsear_listing_json(item: dict) -> dict | None:
    try:
        url_rel = item.get("url") or item.get("link") or item.get("seoUrl") or ""
        url = f"{BASE_URL}{url_rel}" if url_rel.startswith("/") else url_rel

        id_match = re.search(r"-(\d+)\.html", url_rel)
        listing_id = item.get("id") or item.get("listingId") or (id_match.group(1) if id_match else "")

        titulo = str(item.get("title") or item.get("name") or "")[:120]

        barrio_raw = (
            item.get("postingLocation", {}).get("subdivision", {}).get("name") or
            item.get("location", {}).get("subdivision", {}).get("name") or
            item.get("address", {}).get("neighborhood") or
            item.get("neighborhood") or ""
        )
        barrio = normalizar_barrio(barrio_raw)

        precio_usd = None
        for precio_obj in [item.get("price")] + (item.get("prices") or []):
            if not isinstance(precio_obj, dict):
                continue
            moneda = str(precio_obj.get("currency", "")).upper()
            valor = precio_obj.get("amount") or precio_obj.get("price")
            if valor and moneda in ("USD", "US$", "DÓLARES", "DOLARES", ""):
                try:
                    precio_usd = float(str(valor).replace(".", "").replace(",", "."))
                    if precio_usd > 0:
                        break
                except ValueError:
                    pass

        superficie_m2 = None
        attrs = item.get("mainFeatures") or item.get("features") or []
        if isinstance(attrs, list):
            for attr in attrs:
                k = str(attr.get("id") or attr.get("key") or "").lower()
                if any(x in k for x in ["total", "superficie", "area"]):
                    try:
                        superficie_m2 = float(str(attr.get("value", "")).replace(",", "."))
                        if superficie_m2 > 0:
                            break
                    except (ValueError, TypeError):
                        pass

        ambientes = item.get("rooms") or item.get("ambientes")
        if isinstance(attrs, list) and ambientes is None:
            for attr in attrs:
                k = str(attr.get("id") or attr.get("key") or "").lower()
                if any(x in k for x in ["room", "ambiente"]):
                    try:
                        ambientes = int(attr.get("value", 0))
                        break
                    except (ValueError, TypeError):
                        pass

        precio_m2 = None
        if precio_usd and superficie_m2 and superficie_m2 > 0:
            precio_m2 = round(precio_usd / superficie_m2, 1)

        return {
            "id": str(listing_id),
            "url": url,
            "titulo": titulo,
            "barrio": barrio,
            "precio_usd": precio_usd,
            "superficie_m2": superficie_m2,
            "precio_m2": precio_m2,
            "ambientes": ambientes,
        }
    except Exception:
        return None


def parsear_html_bs4(html: str, url_pagina: str) -> list:
    """
    Parsea listings de ZonaProp usando selectores data-qa exactos.
    Selectores validados contra HTML real (2026-03-21):
      - data-qa="POSTING_CARD_PRICE"    → precio USD
      - data-qa="POSTING_CARD_FEATURES" → spans con m² y ambientes
      - data-qa="POSTING_CARD_LOCATION" → "Barrio, Capital Federal"
    """
    soup = BeautifulSoup(html, "lxml")
    listings = []

    # Todos los cards de listing (tienen data-id + data-posting-type)
    cards = soup.find_all(attrs={"data-id": True, "data-posting-type": True})
    if not cards:
        # Fallback: cualquier elemento con data-id
        cards = soup.find_all(attrs={"data-id": True})

    for card in cards:
        try:
            listing_id = card.get("data-id") or ""
            url_rel = card.get("data-to-posting", "")
            if not url_rel:
                link = card.find("a", href=True)
                url_rel = link["href"] if link else ""
            url = f"{BASE_URL}{url_rel}" if url_rel.startswith("/") else url_pagina

            # ── Precio ─────────────────────────────────────────────────────────
            precio_usd = None
            precio_tag = card.find(attrs={"data-qa": "POSTING_CARD_PRICE"})
            if precio_tag:
                texto_precio = precio_tag.get_text(strip=True)
                # Formato: "USD 148.000" (separador de miles = punto en Argentina)
                if "USD" in texto_precio.upper() or "U$S" in texto_precio.upper():
                    nums = re.findall(r"[\d\.]+", texto_precio)
                    for n in nums:
                        try:
                            v = float(n.replace(".", ""))  # "148.000" → 148000
                            if v >= 10_000:
                                precio_usd = v
                                break
                        except ValueError:
                            pass

            # ── Features: m² y ambientes ──────────────────────────────────────
            superficie_m2 = None
            ambientes = None
            features_tag = card.find(attrs={"data-qa": "POSTING_CARD_FEATURES"})
            if features_tag:
                for span in features_tag.find_all("span"):
                    texto_span = span.get_text(strip=True)
                    # Superficie: "71 m² tot." o "71 m²"
                    if "m²" in texto_span or "m2" in texto_span.lower():
                        match = re.search(r"([\d]+)", texto_span)
                        if match and superficie_m2 is None:
                            val = float(match.group(1))
                            if 10 <= val <= 5000:
                                superficie_m2 = val
                    # Ambientes: "4 amb."
                    elif "amb" in texto_span.lower():
                        match = re.search(r"(\d+)", texto_span)
                        if match and ambientes is None:
                            ambientes = int(match.group(1))

            # ── Barrio ─────────────────────────────────────────────────────────
            barrio = "desconocido"
            loc_tag = card.find(attrs={"data-qa": "POSTING_CARD_LOCATION"})
            if loc_tag:
                # Formato: "Almagro, Capital Federal"
                texto_loc = loc_tag.get_text(strip=True)
                # Tomar la parte antes de la primera coma
                partes = texto_loc.split(",")
                barrio = normalizar_barrio(partes[0].strip())
            else:
                # Fallback: extraer barrio de la URL
                m = re.search(r"-en-([a-z-]+)-\d+\.html", url_rel)
                if m:
                    barrio = normalizar_barrio(m.group(1).replace("-", " "))

            # ── Título ────────────────────────────────────────────────────────
            titulo = ""
            desc_tag = card.find(attrs={"data-qa": "POSTING_CARD_DESCRIPTION"})
            if desc_tag:
                a = desc_tag.find("a")
                titulo = (a.get_text(strip=True) if a else desc_tag.get_text(strip=True))[:120]
            if not titulo:
                # Fallback: alt de imagen
                img = card.find("img", alt=True)
                if img:
                    titulo = img["alt"][:120]

            precio_m2 = round(precio_usd / superficie_m2, 1) if precio_usd and superficie_m2 and superficie_m2 > 0 else None

            if listing_id or url_rel:
                listings.append({
                    "id": str(listing_id),
                    "url": url,
                    "titulo": titulo,
                    "barrio": barrio,
                    "precio_usd": precio_usd,
                    "superficie_m2": superficie_m2,
                    "precio_m2": precio_m2,
                    "ambientes": ambientes,
                })
        except Exception:
            continue

    return listings


def parsear_html(html: str, url_pagina: str, n_pagina: int) -> list:
    """Parsea HTML de ZonaProp: primero JSON embebido, luego BS4."""
    items_json = extraer_json_embebido(html)
    if items_json:
        print(f"         → JSON embebido: {len(items_json)} items")
        listings = [r for r in (parsear_listing_json(i) for i in items_json) if r]
        print(f"         → Válidos: {len(listings)}")
        return listings

    print("         → Sin JSON embebido, usando BS4...")
    listings = parsear_html_bs4(html, url_pagina)
    print(f"         → BS4: {len(listings)} listings")
    return listings


def get_url(n: int) -> str:
    return URL_PAGINA_1 if n == 1 else URL_PAGINA_N.format(n=n)


# ══════════════════════════════════════════════════════════════════════════════
# ESTRATEGIA 1: undetected-chromedriver (bypasea Cloudflare)
# ══════════════════════════════════════════════════════════════════════════════

def scrapear_con_uc() -> list:
    """
    Usa undetected-chromedriver para simular un navegador Chrome real.
    Bypasea protecciones anti-bot de Cloudflare y similares.
    """
    import undetected_chromedriver as uc
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    print("\n  Iniciando Chrome (undetected-chromedriver)...")
    opciones = uc.ChromeOptions()
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-blink-features=AutomationControlled")
    opciones.add_argument("--lang=es-AR")
    opciones.add_argument("--window-size=1366,768")
    # Sin --headless para evitar detección (UC maneja esto internamente)

    driver = uc.Chrome(options=opciones, version_main=146)
    todos = []

    try:
        for n in range(1, MAX_PAGINAS + 1):
            url = get_url(n)
            print(f"  Página {n:2d}: {url}")
            driver.get(url)

            # Esperar a que cargue contenido dinámico (máx 15s)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-id], .posting-card, h2"))
                )
            except Exception:
                pass  # Continuar igual y parsear lo que haya

            time.sleep(random.uniform(2.0, 3.5))

            html = driver.page_source
            print(f"         → {len(html):,} chars")

            # Verificar si fue bloqueado
            if any(x in html.lower() for x in ["access denied", "error 403", "cloudflare", "just a moment"]):
                print(f"         → ⚠️  Página bloqueada — esperando 10s y reintentando...")
                time.sleep(10)
                driver.get(url)
                time.sleep(5)
                html = driver.page_source

            listings = parsear_html(html, url, n)
            todos.extend(listings)
            print(f"         → Acumulado: {len(todos)} listings")

            if n < MAX_PAGINAS:
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    finally:
        driver.quit()
        print("  → Chrome cerrado.")

    return todos


# ══════════════════════════════════════════════════════════════════════════════
# ESTRATEGIA 2: requests (fallback sin Chrome)
# ══════════════════════════════════════════════════════════════════════════════

def scrapear_con_requests() -> list:
    import requests
    session = requests.Session()
    session.headers.update({**HEADERS, "Referer": "https://www.google.com/"})
    todos = []
    vacias = 0

    for n in range(1, MAX_PAGINAS + 1):
        url = get_url(n)
        try:
            resp = session.get(url, timeout=TIMEOUT)
            print(f"  Página {n:2d}: HTTP {resp.status_code} — {len(resp.text):,} chars")
            if resp.status_code in (403, 429):
                vacias += 1
                if vacias >= 3:
                    print("  ⚠️  3 errores consecutivos — deteniendo.")
                    break
                if resp.status_code == 429:
                    time.sleep(30)
                continue
            if resp.status_code != 200:
                continue
            vacias = 0
            listings = parsear_html(resp.text, url, n)
            todos.extend(listings)
            print(f"         → Acumulado: {len(todos)}")
            session.headers.update({"Referer": url})
        except Exception as e:
            print(f"  ✗ Error en página {n}: {e}")
            vacias += 1
        if n < MAX_PAGINAS:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    return todos


# ══════════════════════════════════════════════════════════════════════════════
# LIMPIEZA Y AGREGACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def limpiar(listings: list) -> pd.DataFrame:
    df = pd.DataFrame(listings)
    if df.empty:
        return df
    print(f"\n✓ Listings crudos: {len(df)}")

    # Deduplicar
    antes = len(df)
    col_dedup = "id" if (df.get("id", pd.Series()).notna().any()) else "url"
    df = df.drop_duplicates(subset=[col_dedup], keep="first")
    print(f"  Deduplicados: {antes - len(df)} removidos → {len(df)} únicos")

    # Limpiar tipos
    df["precio_usd"]    = pd.to_numeric(df["precio_usd"],    errors="coerce")
    df["superficie_m2"] = pd.to_numeric(df["superficie_m2"], errors="coerce")
    df["precio_m2"]     = pd.to_numeric(df["precio_m2"],     errors="coerce")

    # Filtrar outliers
    df = df[df["precio_usd"].isna()    | ((df["precio_usd"]    >= 30_000) & (df["precio_usd"]    <= 5_000_000))]
    df = df[df["superficie_m2"].isna() | ((df["superficie_m2"] >= 15)     & (df["superficie_m2"] <= 2_000))]

    # Recalcular precio/m² limpio
    mask = df["precio_usd"].notna() & df["superficie_m2"].notna() & (df["superficie_m2"] > 0)
    df.loc[mask, "precio_m2"] = (df.loc[mask, "precio_usd"] / df.loc[mask, "superficie_m2"]).round(1)
    mask_pm2 = df["precio_m2"].notna()
    df.loc[mask_pm2, "precio_m2"] = df.loc[mask_pm2, "precio_m2"].where(
        (df.loc[mask_pm2, "precio_m2"] >= 200) & (df.loc[mask_pm2, "precio_m2"] <= 30_000)
    )

    df["fecha_snapshot"] = FECHA_HOY
    print(f"  Listings válidos: {len(df)}")
    return df


def agregar_por_barrio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df_ok = df[df["barrio"] != "desconocido"]

    agg = df_ok.groupby("barrio").agg(stock_avisos=("id", "count")).reset_index()

    for col, alias_prom, alias_med in [
        ("precio_usd", "precio_usd_promedio", "precio_usd_mediana"),
        ("precio_m2",  "precio_m2_promedio",  "precio_m2_mediana"),
    ]:
        sub = df_ok[df_ok[col].notna()].groupby("barrio").agg(
            **{alias_prom: (col, "mean"), alias_med: (col, "median")}
        ).reset_index()
        agg = agg.merge(sub, on="barrio", how="left")

    for col, alias in [("superficie_m2", "sup_promedio_m2"), ("ambientes", "ambientes_promedio")]:
        sub = df_ok[df_ok[col].notna()].groupby("barrio").agg(**{alias: (col, "mean")}).reset_index()
        agg = agg.merge(sub, on="barrio", how="left")

    # Redondear
    for col in ["precio_usd_promedio", "precio_usd_mediana"]:
        if col in agg.columns:
            agg[col] = agg[col].round(0)
    for col in ["precio_m2_promedio", "precio_m2_mediana", "sup_promedio_m2"]:
        if col in agg.columns:
            agg[col] = agg[col].round(1)
    if "ambientes_promedio" in agg.columns:
        agg["ambientes_promedio"] = agg["ambientes_promedio"].round(2)

    agg["fecha_snapshot"] = FECHA_HOY
    return agg.sort_values("stock_avisos", ascending=False).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "="*60)
    print("  CABATECH — Capa 5: Absorción ZonaProp")
    print(f"  Fecha: {FECHA_HOY} | Páginas: {MAX_PAGINAS}")
    print("="*60)

    # ── Intentar scraping con UC primero ──────────────────────────────────────
    listings = []
    metodo_usado = ""

    print("\n[Método 1] undetected-chromedriver (Chrome real)...")
    try:
        listings = scrapear_con_uc()
        metodo_usado = "undetected-chromedriver"
    except Exception as e:
        print(f"  ✗ UC falló: {e}")
        print("\n[Método 2] requests + headers Chrome (fallback)...")
        try:
            import requests  # noqa
            listings = scrapear_con_requests()
            metodo_usado = "requests"
        except Exception as e2:
            print(f"  ✗ requests también falló: {e2}")

    if not listings:
        print("\n" + "!"*60)
        print("  ✗ No se obtuvieron listings con ningún método.")
        print_alternativas()
        return

    print(f"\n✓ Método exitoso: {metodo_usado} — {len(listings)} listings crudos")

    # ── Limpiar y guardar ─────────────────────────────────────────────────────
    df_raw = limpiar(listings)
    if df_raw.empty:
        print("  ✗ DataFrame vacío después de limpieza.")
        print_alternativas()
        return

    df_raw.to_csv(RAW_OUTPUT, encoding="utf-8-sig", index=False)
    print(f"\n✓ Raw guardado: {RAW_OUTPUT} ({len(df_raw)} filas)")

    # ── Agregar por barrio ────────────────────────────────────────────────────
    df_barrios = agregar_por_barrio(df_raw)

    if not df_barrios.empty:
        df_barrios.to_csv(PROCESSED_OUTPUT, encoding="utf-8-sig", index=False)
        print(f"✓ Agregado: {PROCESSED_OUTPUT} ({len(df_barrios)} barrios)")

        print("\n" + "─"*60)
        print("  TOP 10 — Mayor stock de avisos")
        print("─"*60)
        for _, r in df_barrios.head(10).iterrows():
            pm2 = f"  USD {r['precio_m2_mediana']:,.0f}/m²" if pd.notna(r.get("precio_m2_mediana")) else ""
            print(f"  {r['barrio']:<28} {int(r['stock_avisos']):>4} avisos{pm2}")

        print("\n" + "─"*60)
        print("  TOP 10 — Menor stock (mínimo 3 avisos)")
        print("─"*60)
        bottom = df_barrios[df_barrios["stock_avisos"] >= 3].tail(10)
        for _, r in bottom.iterrows():
            pm2 = f"  USD {r['precio_m2_mediana']:,.0f}/m²" if pd.notna(r.get("precio_m2_mediana")) else ""
            print(f"  {r['barrio']:<28} {int(r['stock_avisos']):>4} avisos{pm2}")

        print("\n" + "─"*60)
        total = int(df_barrios["stock_avisos"].sum())
        pm2_global = df_raw["precio_m2"].dropna().median()
        print(f"  Total avisos:    {total:,}")
        print(f"  Barrios:         {len(df_barrios)}")
        if pd.notna(pm2_global):
            print(f"  Precio/m² med:   USD {pm2_global:,.0f}")

    print("\n✓ Capa 5 completada.\n")


def print_alternativas():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  ALTERNATIVAS SI EL SCRAPING SIGUE BLOQUEANDO               ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. PLAYWRIGHT (más moderno que Selenium)                   ║
║     pip install playwright && playwright install chromium    ║
║     Soporta stealth mode con playwright-stealth             ║
║                                                              ║
║  2. ARGENPROP (más fácil de scrapear)                       ║
║     https://www.argenprop.com/departamento/venta/           ║
║     Estructura HTML más simple, sin Cloudflare agresivo      ║
║                                                              ║
║  3. MERCADO LIBRE INMUEBLES (API pública)                   ║
║     https://developers.mercadolibre.com.ar                   ║
║     Category ID: MLA1459 (departamentos CABA)                ║
║     GET /sites/MLA/search?category=MLA1459&state=TUxBQkNBUGw ║
║                                                              ║
║  4. SCRAPINGBEE / BRIGHTDATA (proxy anti-bot)               ║
║     ~USD 0.0003/request — 20 páginas = USD 0.006 por run    ║
║                                                              ║
║  5. PROPERATI DATASET (Kaggle — datos históricos)           ║
║     properati-ar-real-estate — CABA + GBA                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
