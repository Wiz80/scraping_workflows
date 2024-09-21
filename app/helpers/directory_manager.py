# app/helpers/directory_manager.py

import os
from urllib.parse import urlparse

def create_directory_structure(base_url: str, subsite: str = "main") -> str:
    """
    Crea una estructura de directorios basada en el base_url y el subsite.
    
    Args:
        base_url (str): URL base del sitio web.
        subsite (str, optional): Subsite. Por defecto es "main".
    
    Returns:
        str: Ruta al directorio creado.
    """
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc.replace('.', '_')
    directory = os.path.join("scraped_data", domain, subsite)
    
    os.makedirs(directory, exist_ok=True)
    
    return directory
