import requests
import logging
import re
import os
import fitz
from fastapi import HTTPException
from urllib.parse import urlparse
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


def create_directory_structure(base_url: str, subsite: str) -> str:
    """
    Crea la estructura de directorios basada en la URL base y la consulta.
    
    Args:
    - base_url (str): La URL del sitio base.
    - subsite (str): La consulta utilizada para el scraping.

    Returns:
    - str: La ruta completa donde se guardará el archivo.
    """
    # Extraer el nombre del sitio desde la URL
    site_name = base_url.split("//")[-1].split("/")[0].replace("www.", "")
    
    # Crear el directorio base dentro de la carpeta cache/scraped_sites
    base_dir = os.path.join("app/cache/scraped_sites", site_name)
    
    # Crear el subdirectorio basado en la consulta
    subsite_dir = os.path.join(base_dir, subsite.replace(" ", "_").lower())
    
    # Crear los directorios si no existen
    os.makedirs(subsite_dir, exist_ok=True)
    
    return subsite_dir


def clean_text(text):
    # Eliminar saltos de línea innecesarios que no forman parte de los párrafos
    # Reemplazar múltiples saltos de línea seguidos por un único espacio
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Mantiene los saltos de línea entre párrafos
    text = re.sub(r'\n+', ' ', text)  # Elimina los saltos de línea adicionales dentro de los párrafos

    # Eliminar múltiples espacios en blanco
    text = re.sub(r'\s+', ' ', text)

    # Eliminar espacios en blanco innecesarios al inicio y final del texto
    text = text.strip()

    return text

def download_pdf_via_requests(pdf_url: str, download_path: str = 'app/cache/download.pdf') -> str:
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(download_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        logging.info(f"PDF descargado y guardado en {download_path}")
    else:
        raise HTTPException(status_code=500, detail="No se pudo descargar el PDF")

    # Verificar si el archivo existe y no está vacío
    if not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
        raise HTTPException(status_code=500, detail=f"El archivo PDF no se descargó correctamente o está vacío: {download_path}")

    # Extraer el texto del PDF descargado
    with fitz.open(download_path) as pdf:
        text = ""
        for page in pdf:
            text += page.get_text()
    
    text = clean_text(text=text)
    logging.info(f"Text extracted succesfully from : {pdf_url}")
    return text

def save_scraped_content(url, content):

    parsed_url = urlparse(url)
    site_name = parsed_url.netloc.replace("www.", "")  # Remove 'www.' if present

    # Define the file name using the site name
    file_name = f"{site_name}_scraped_content.txt"

    # Ensure the directory exists where the file will be saved
    if not os.path.exists("scraped_sites"):
        os.makedirs("scraped_sites")

    # Full path to the file
    file_path = os.path.join("scraped_sites", file_name)

    # Write the content to the file, including the URL as a header
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"\n\nURL: {url}\n")
        f.write(f"Content:\n{content}\n")
        f.write("-" * 80)  # Separator between pages for readability

async def check_and_click_pagination(page: Page, next_selector: str) -> bool:
    """
    Esta función busca el botón de paginación en la página.
    Si encuentra el botón, hace clic en él y espera a que la nueva página cargue.
    
    Args:
    - page (Page): La instancia de la página de Playwright.

    Returns:
    - bool: True si se encontró y se hizo clic en el botón de paginación, False si no se encontró el botón.
    """
    try:
        # Buscar el botón de paginación con la clase específica
        pagination_button = await page.query_selector(next_selector)
        
        if pagination_button:
            # Verificar si el botón es visible antes de hacer clic
            is_visible = await pagination_button.is_visible()
            if is_visible:
                # Hacer clic en el botón y esperar a que la nueva página cargue
                await pagination_button.click()
                await page.wait_for_selector("body")  # Espera a que el contenido cargue
                return True
            else:
                return False
        return False
    except PlaywrightTimeoutError:
        return False
