import requests
import logging
import re
import os
import fitz
from fastapi import HTTPException
from urllib.parse import urlparse


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
