from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import Dict, Any
import os
from playwright.async_api import async_playwright
from app.captcha.captcha_solver import solve_captcha
from app.helpers.get_content import download_pdf_via_requests, save_scraped_content, create_directory_structure
from app.helpers.get_delta import GetDelta

import logging


async def run_playwright_scraper(base_url: str):
    pages_to_scrape = ["/"]
    visited_pages = set()
    scraped_content = {}

    with sync_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while pages_to_scrape:
            current_page = pages_to_scrape.pop(0)
            if current_page in visited_pages:
                continue
            
            url = base_url + current_page
            page.goto(url)
            html_content = page.content()

            # Extract just visible text
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator="\n", strip=True)
            scraped_content[url] = text_content
            visited_pages.add(current_page)

            # Find all internal links to add to pages_to_scrape
            links = page.query_selector_all("a[href^='/']")
            for link in links:
                href = link.get_attribute("href")
                if href and href not in visited_pages:
                    pages_to_scrape.append(href)

        browser.close()
    return scraped_content


async def scrape_page(url: str, base_url: str, subsites: Dict[str, Any] = {}) -> float:
    """
    Scrapea una página web, extrae el texto y lo guarda en un archivo .txt.
    Calcula el delta entre el texto anterior y el nuevo.
    
    Args:
        url (str): URL de la página a scrapear.
        base_url (str): URL base del sitio web.
        subsites (Dict[str, Any], optional): Diccionario de subsites. Por defecto es {}.
    
    Returns:
        float: Delta entre el texto antiguo y el nuevo.
    """
    getdelta = GetDelta()

    # Manejar la estructura de directorios
    if subsites:
        subsite = list(subsites.values())[0]
    else:
        subsite = "main"  # Nombre por defecto si no hay subsites

    # Crear la estructura de directorios
    directory = create_directory_structure(base_url, subsite=subsite)

    # Sanitizar la URL para usarla como nombre de archivo
    filename = os.path.join(directory, getdelta.sanitize_filename(url))

    try:
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

            # Navegar a la URL
            await page.goto(url, wait_until='networkidle')

            # Esperar a que se cargue completamente el cuerpo de la página
            await page.wait_for_selector("body")

            # Scroll para cargar contenido dinámico
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await page.wait_for_timeout(2000)  # Espera adicional después del scroll

            # Obtener el contenido HTML y extraer el texto visible
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator="\n", strip=True)

            await browser.close()

        # Guardar el texto extraído en un archivo
        getdelta.save_pdf_text_to_file(text_content, filename)
        logging.info(f"Text file saved successfully: {filename}")

        # Obtener el texto anterior si existe
        old_text = getdelta.get_existing_text(filename)

        # Calcular el delta entre el texto viejo y el nuevo
        delta = getdelta.calculate_text_delta(old_text, text_content)

        # Actualizar el archivo de texto con el nuevo contenido
        getdelta.save_pdf_text_to_file(text_content, filename)

        return delta

    except Exception as e:
        logging.error(f"An error occurred while scraping {url}: {e}")
        return 0.0  # En caso de error, no se detecta cambio

async def scrape_pdf(pdf_url: str, base_url: str, subsites: str) -> float:
    getdelta = GetDelta()
    
    subsite = list(subsites.values())[0]
    # Crear la estructura de directorios
    directory = create_directory_structure(base_url, subsite=subsite)
    
    # Limpiar la URL para usarla como nombre de archivo
    filename = f"{directory}/{getdelta.sanitize_filename(pdf_url)}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=[
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

        try:
            # Intentar navegar a la página del PDF
            response = await page.goto(pdf_url, wait_until='networkidle', timeout=60000)

            if response is None or response.status != 200:
                logging.error(f"Error al navegar a {pdf_url}: Status {response.status if response else 'None'}")
                return 0.0
            
            # Comprobar si aparece un CAPTCHA
            captcha_present = await page.evaluate('''() => {
                return !!document.querySelector('.g-recaptcha');
            }''')

            if captcha_present:
                logging.info("CAPTCHA detectado, intentando resolverlo...")
                await solve_captcha(page)
                logging.info("CAPTCHA resuelto, continuando con el scraping...")

            text = download_pdf_via_requests(pdf_url=pdf_url)

        except Exception as e:
            logging.error(f"Error al intentar scrapeo: {e}")
            return 0.0  # En caso de error, no se detecta cambio
        finally:
            await browser.close()

    # Guardar el texto del PDF en un archivo
    getdelta.save_pdf_text_to_file(text, filename)
    logging.info(f"Text file saved succesfully: {filename}")
    
    # Obtener el texto anterior si existe
    old_text = getdelta.get_existing_text(filename)

    # Calcular el delta entre el texto viejo y el nuevo
    delta = getdelta.calculate_text_delta(old_text, text)

    # Actualizar el archivo de texto con el nuevo contenido
    getdelta.save_pdf_text_to_file(text, filename)

    return delta
