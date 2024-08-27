from selenium_recaptcha_solver import RecaptchaSolver
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Configuración de las opciones de Chrome
options = Options()
options.add_argument("--window-size=1920,1080")
options.add_argument('--no-sandbox')
options.add_argument("--disable-extensions")
options.add_argument("--user-agent=Mozilla/5.0")

# Inicializa el WebDriver
driver = webdriver.Chrome(options=options)

# Inicializa el solucionador de reCAPTCHA
solver = RecaptchaSolver(driver=driver)

# Navega a la página de demo de reCAPTCHA
driver.get('https://www.google.com/recaptcha/api2/demo')

# Localiza el iframe de reCAPTCHA y resuélvelo
recaptcha_iframe = driver.find_element(By.XPATH, '//iframe[@title="reCAPTCHA"]')
solver.click_recaptcha_v2(iframe=recaptcha_iframe)
