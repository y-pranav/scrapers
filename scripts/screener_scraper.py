import bs4 as bs
import requests
import re
import pandas as pd
import time
import dotenv
import os
dotenv.load_dotenv()

login_URL = 'https://www.screener.in/login/'
base_data_URL = 'https://www.screener.in/screen/raw/?sort=&order=&source_id=&query=Current+price+%3E+0&limit=50'

form_data = {
    'username': os.getenv('SCREENER_USERNAME'),
    'password': os.getenv('SCREENER_PASSWORD'),
}


form_csrf_key = 'csrfmiddlewaretoken'
cookie_csrf_key = 'csrftoken'
cookie_session_key = 'sessionid'
content_type = 'application/x-www-form-urlencoded'
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324'

def login():
    get_login_request = requests.get(login_URL)
    get_login_request_soup = bs.BeautifulSoup(get_login_request.text, 'html.parser')
    form_csrf_value = get_login_request_soup.find('input', {'name': form_csrf_key})['value']
    cookie_csrf_value = re.search(cookie_csrf_key + '=(.*?);', get_login_request.headers['Set-Cookie']).group(1)

    form_data[form_csrf_key] = form_csrf_value

    post_login_request = requests.post(login_URL, form_data, headers={
        'Cookie': cookie_csrf_key + '=' + cookie_csrf_value,
        'Content-Type': content_type,
        'User-Agent': user_agent,
        'Referer': login_URL
    }, allow_redirects=False)

    cookie_session_value = re.search(cookie_session_key + '=(.*?);', post_login_request.headers['Set-Cookie']).group(1)
    
    return cookie_csrf_value, cookie_session_value

def scrape_page(page_num, cookie_csrf_value, cookie_session_value):
    data_URL = f"{base_data_URL}&page={page_num}"
    
    get_data_request = requests.get(data_URL, headers={
        'Cookie': cookie_csrf_key + '=' + cookie_csrf_value + ';' + cookie_session_key + '=' + cookie_session_value,
        'Content-Type': content_type,
        'User-Agent': user_agent,
    })

    get_data_request_soup = bs.BeautifulSoup(get_data_request.text, 'html.parser')
    table = get_data_request_soup.find('table', {'class': 'data-table'})
    
    if not table:
        print(f"Table not found on page {page_num}")
        return None, None
    
    table_rows = table.find_all('tr')
    
    headers = [th.text.strip() for th in table_rows[0].find_all('th')]
    
    data = []
    for row in table_rows[1:]:
        cells = [td.text.strip() for td in row.find_all('td')]
        if cells:
            data.append(cells)
    
    return headers, data

def scrape_all_pages(total_pages):
    cookie_csrf_value, cookie_session_value = login()
    all_data = []
    headers = None
    
    for page in range(1, total_pages + 1):
        print(f"Scraping page {page} of {total_pages}...")
        
        page_headers, page_data = scrape_page(page, cookie_csrf_value, cookie_session_value)
        
        if page_headers and page_data:
            if headers is None:
                headers = page_headers
            all_data.extend(page_data)
        
        time.sleep(1)
    
    return headers, all_data

total_pages = 99
headers, all_data = scrape_all_pages(total_pages)

if headers and all_data:
    df = pd.DataFrame(all_data, columns=headers)
    
    df.to_csv('screener_all_data.csv', index=False)
    print(f"Data saved to screener_all_data.csv with {len(df)} rows")
else:
    print("Failed to retrieve data")