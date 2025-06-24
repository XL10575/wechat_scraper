
def setup_fixed_chrome(headless=True):
    """修复后的Chrome启动函数"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # 基本优化选项
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 设置Chrome和ChromeDriver路径
    chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    service = Service(r"C:\Users\dream\.wdm\drivers\chromedriver\win64\137.0.7151.119\chromedriver-win32\chromedriver.exe")
    
    # 启动Chrome
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
