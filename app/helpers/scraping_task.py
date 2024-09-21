# app/helpers/start_scraping_tasks.py

import os
import asyncio
import logging
from typing import Dict, Any
from app.helpers.scrape import scrape_pdf, scrape_page
from app.helpers.tree_scraped import TreeScraped

JSON_SCRAPED_PATH = "app/cache/scraped_sites.json"
JSON_PENDING_PATH = "app/cache/pending_urls.json"

async def start_scraping_tasks(
    base_url: str,
    extract: str = '/',
    subsites: Dict[str, Any] = {}
) -> bool:
    tree_scraped = TreeScraped()
    scraped_sites = tree_scraped.load_json_file(JSON_SCRAPED_PATH, default_value=[])
    pending_urls = tree_scraped.load_json_file(JSON_PENDING_PATH, default_value={})

    # Verificar si subsites está vacío
    if subsites:
        subsite_key, subsite_value = next(iter(subsites.items()), (None, None))
    else:
        subsite_key, subsite_value = None, None

    # Encontrar la entrada del sitio y subsite en scraped_sites
    site_entry = next((entry for entry in scraped_sites if entry["site"] == base_url), None)

    if subsites:
        subsite_entry = None
        if site_entry and "subsites" in site_entry:
            subsite_entry = next((sub for sub in site_entry["subsites"] if sub.get(subsite_key) == subsite_value), None)

        # Verificar si hay URLs pendientes para el subsite específico
        if (base_url in pending_urls and
            "subsites" in pending_urls[base_url] and
            subsite_key in pending_urls[base_url]["subsites"] and
            subsite_value in pending_urls[base_url]["subsites"][subsite_key]):

            current_pending = pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"]
        else:
            logging.info("No hay URLs pendientes para procesar.")
            return False
    else:
        subsite_entry = None
        # Verificar si hay URLs pendientes sin subsites
        if (base_url in pending_urls and
            "pending_urls" in pending_urls[base_url]):

            current_pending = pending_urls[base_url]["pending_urls"]
        else:
            logging.info("No hay URLs pendientes para procesar.")
            return False

    for url in current_pending[:]:  # Iterar sobre una copia para modificar la lista
        try:
            # Procesar la URL
            if extract == 'pdf':
                delta = await scrape_pdf(pdf_url=url, base_url=base_url, subsites=subsites)
            else:
                delta = await scrape_page(url=url, base_url=base_url, subsites=subsites)

            # Actualizar scraped_sites.json
            if subsites:
                if subsite_entry:
                    subsite_entry["urls"].append(url)
                else:
                    new_subsite = {
                        subsite_key: subsite_value,
                        "urls": [url]
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
            else:
                if site_entry:
                    site_entry["urls"].append(url)
                else:
                    new_site_entry = {
                        "site": base_url,
                        "urls": [url]
                    }
                    scraped_sites.append(new_site_entry)

            tree_scraped.save_json_file(JSON_SCRAPED_PATH, scraped_sites)

            # Remover la URL de pending_urls
            if subsites:
                pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"].remove(url)
            else:
                pending_urls[base_url]["pending_urls"].remove(url)
            
            tree_scraped.save_json_file(JSON_PENDING_PATH, pending_urls)

            logging.info(f"Scraped exitosamente: {url} | Delta: {delta}")

        except Exception as scrape_error:
            logging.error(f"Error scraping URL {url}: {scrape_error}")
            # Opcional: agregar a failed_urls
            if subsites:
                failed = pending_urls[base_url]["subsites"][subsite_key][subsite_value].setdefault("failed_urls", [])
            else:
                failed = pending_urls[base_url].setdefault("failed_urls", [])
            failed.append(url)
            # Remover de pending_urls para evitar reintentos inmediatos
            if subsites:
                pending_urls[base_url]["subsites"][subsite_key][subsite_value]["pending_urls"].remove(url)
            else:
                pending_urls[base_url]["pending_urls"].remove(url)
            tree_scraped.save_json_file(JSON_PENDING_PATH, pending_urls)

    return True
