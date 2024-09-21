# app/helpers/discover_urls.py

import os
import uuid
import json
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from app.helpers.tree_scraped import TreeScraped
from app.helpers.get_content import check_and_click_pagination

JSON_SCRAPED_PATH = "app/cache/scraped_sites.json"
JSON_PENDING_PATH = "app/cache/pending_urls.json"

async def discover_urls(
    base_url: str, 
    search_url: str, 
    subsites: Dict[str, Any], 
    extract: str, 
    pagination: bool = False, 
    provided_urls: List[str] = []
) -> int:
    tree_scraped = TreeScraped()
    scraped_sites = tree_scraped.load_json_file(JSON_SCRAPED_PATH, default_value=[])
    pending_urls = tree_scraped.load_json_file(JSON_PENDING_PATH, default_value={})

    # Verificar si subsites está vacío
    if subsites:
        # Extraer el valor del subsite si existe una palabra reservada en el diccionario subsites
        subsite_key, subsite_value = next(iter(subsites.items()), (None, None))
    else:
        subsite_key, subsite_value = None, None

    # Verificar si ya existe el sitio
    site_entry = next((entry for entry in scraped_sites if entry["site"] == base_url), None)
    
    if subsites:
        # Manejar el caso con subsites
        subsite_entry = None
        if site_entry and "subsites" in site_entry:
            subsite_entry = next((sub for sub in site_entry["subsites"] if sub.get(subsite_key) == subsite_value), None)

        # Si existe, obtenemos las URLs previas
        existing_urls = set(subsite_entry["urls"]) if subsite_entry else set()

        # Inicializar estructura en pending_urls usando setdefault para evitar KeyError
        pending_urls.setdefault(base_url, {}).setdefault("subsites", {}).setdefault(subsite_key, {}).setdefault(subsite_value, {"pending_urls": [], "failed_urls": []})

        current_pending = set(pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"])
    else:
        # Manejar el caso sin subsites
        subsite_entry = None
        existing_urls = set(site_entry["urls"]) if site_entry else set()

        # Inicializar estructura en pending_urls usando setdefault para evitar KeyError
        pending_urls.setdefault(base_url, {"pending_urls": [], "failed_urls": []})

        current_pending = set(pending_urls[base_url]["pending_urls"])

    visited_pages = set()
    new_urls = []

    if provided_urls:
        for url in provided_urls:
            full_url = base_url + url if url.startswith("/") else url
            if full_url not in existing_urls and full_url not in visited_pages and full_url not in current_pending:
                visited_pages.add(full_url)
                new_urls.append(full_url)
    else:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--start-maximized"
            ])
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            page = await context.new_page()

            # Navegar a la URL de búsqueda
            await page.goto(search_url, wait_until='networkidle')

            while True:
                # Espera a que se cargue el cuerpo de la página
                await page.wait_for_selector("body")

                # Buscar todos los links que coincidan con el valor de 'extract'
                links = await page.query_selector_all(f"a[href*='{extract}']")

                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = base_url + href if href.startswith("/") else href
                        if full_url not in existing_urls and full_url not in visited_pages and full_url not in current_pending:
                            visited_pages.add(full_url)
                            new_urls.append(full_url)

                # Si la paginación está habilitada, verificar y hacer clic en el botón de "Next"
                if pagination:
                    if base_url == "https://arxiv.org/":
                        has_next_page = await check_and_click_pagination(page, next_selector="a.pagination-next")
                    else:
                        has_next_page = False  # Ajusta según otros sitios
                    if not has_next_page:
                        break  # Si no hay más páginas, salimos del bucle
                else:
                    break  # Si no hay paginación o no es el caso específico, salimos del bucle

            await browser.close()

    # Agregar nuevas URLs al pending_urls
    if new_urls:
        if subsites:
            # Caso con subsites
            pending_subsite = pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"]
            pending_subsite.extend(new_urls)
            pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"] = list(set(pending_subsite))  # Eliminar duplicados

            tree_scraped.save_json_file(JSON_PENDING_PATH, pending_urls)

            # También actualizar scraped_sites.json para evitar re-scraping
            if subsite_entry:
                updated_urls = existing_urls.union(new_urls)
                subsite_entry["urls"] = list(updated_urls)
            else:
                new_subsite = {
                    subsite_key: subsite_value,
                    "urls": new_urls
                }

                if site_entry:
                    if "subsites" not in site_entry:
                        site_entry["subsites"] = []
                    site_entry["subsites"].append(new_subsite)
                else:
                    new_site_entry = {
                        "site": base_url,
                        "subsites": [new_subsite]
                    }
                    scraped_sites.append(new_site_entry)

            tree_scraped.save_json_file(JSON_SCRAPED_PATH, scraped_sites)
        else:
            # Caso sin subsites
            pending = pending_urls[base_url]["pending_urls"]
            pending.extend(new_urls)
            pending_urls[base_url]["pending_urls"] = list(set(pending))  # Eliminar duplicados

            tree_scraped.save_json_file(JSON_PENDING_PATH, pending_urls)

            # También actualizar scraped_sites.json para evitar re-scraping
            if site_entry:
                updated_urls = existing_urls.union(new_urls)
                site_entry["urls"] = list(updated_urls)
            else:
                new_site_entry = {
                    "site": base_url,
                    "urls": new_urls
                }
                scraped_sites.append(new_site_entry)

            tree_scraped.save_json_file(JSON_SCRAPED_PATH, scraped_sites)

    return len(new_urls)
