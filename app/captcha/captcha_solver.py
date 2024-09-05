import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
api_key_2captcha = os.getenv('API_KEY_2CAPTCHA')

async def get_site_key(page):
    # Busca el elemento que contiene el site_key
    site_key = await page.evaluate('''() => {
        const recaptchaElement = document.querySelector('.g-recaptcha');
        return recaptchaElement ? recaptchaElement.getAttribute('data-sitekey') : null;
    }''')
    return site_key


async def solve_captcha(page):
    # Intentar obtener el site_key
    site_key = await get_site_key(page=page)

    if not site_key:
        raise Exception("No se encontró el CAPTCHA")

    # Resolver el CAPTCHA utilizando 2Captcha
    captcha_solution = solve_recaptcha(site_key, page.url)

    # Inyectar el token en el formulario de reCAPTCHA
    await page.evaluate(f"document.getElementById('g-recaptcha-response').innerHTML='{captcha_solution}';")
    await page.click("input[type='submit']")  # Simular el envío del formulario una vez resuelto
    await page.wait_for_navigation()

def solve_recaptcha(site_key, page_url):
    # Enviar solicitud a 2Captcha para resolver el CAPTCHA
    url = "http://2captcha.com/in.php"
    params = {
        'key': api_key_2captcha,
        'method': 'userrecaptcha',
        'googlekey': site_key,  # El site_key del CAPTCHA de Google reCAPTCHA
        'pageurl': page_url,
        'json': 1
    }
    response = requests.post(url, data=params)
    captcha_id = response.json().get('request')

    # Esperar a que el CAPTCHA sea resuelto
    solve_url = f"http://2captcha.com/res.php?key={api_key_2captcha}&action=get&id={captcha_id}&json=1"
    while True:
        result = requests.get(solve_url).json()
        if result.get('status') == 1:
            return result.get('request')  # Esta es la solución del CAPTCHA
        time.sleep(5)  # Esperar 5 segundos antes de volver a intentarlo