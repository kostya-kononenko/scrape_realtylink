from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urljoin
import time
import asyncio
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
import json
import os


BASE_URL = "https://realtylink.org/"
HOME_URL = urljoin(BASE_URL, "en/properties~for-rent")

driver = webdriver.Chrome()
driver.set_window_size(1920, 1080)
driver.get(HOME_URL)


@dataclass
class RealEstate:
    general_link: str
    title: str
    region: str
    address: str
    description: str
    links_to_photos: list
    price: str
    number_of_bedrooms: str
    number_of_bathrooms: str
    real_estate_area: str

    def __post_init__(self):
        data_dict = asdict(self)
        file_path = "real_estate_data.json"
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, "r") as file:
                existing_data = json.load(file)
        else:
            existing_data = []
        existing_data.append(data_dict)
        with open(file_path, "w") as file:
            json.dump(existing_data, file, indent=2)


def get_foto_link(url, number_pages):
    try:
        button_one = driver.find_element(
            By.XPATH, '//*[@id="overview"]/div[2]/div[1]/div/div[3]/button'
        )
        button_one.click()
        time.sleep(2)
        list_of_links = []

        if number_pages > 0:
            for i in range(number_pages):
                button_two = driver.find_element(
                    By.XPATH, '//*[@id="gallery"]/div[2]/div[1]'
                )
                button_two.click()
                img_src = driver.find_element(
                    By.ID,
                    "fullImg").get_attribute("src")
                list_of_links.append(img_src)
            driver.back()
            return list_of_links
    except Exception as e:
        print(f"Exception during button click: {e}")


async def parse_one_element(url):
    async with httpx.AsyncClient() as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/58.0.3029.110 Safari/537.3"
        }
        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                number_of_foto = int(
                    soup.select_one(".btn-primary.photo-btn").text.strip()
                )
            except (ValueError, TypeError, AttributeError):
                number_of_foto = 0
            cac_element = soup.select_one("div.cac")
            if cac_element and cac_element.text.strip():
                result_text = cac_element.text.strip()
            else:
                result_text = None
            RealEstate(
                general_link=url,
                title=soup.select_one(
                    '[data-id="PageTitle"]').text,
                region=soup.select_one(
                    'h2[itemprop="address"].pt-1')
                .text[
                    soup.select_one(
                        'h2[itemprop="address"].pt-1').text.find(",") + 1 :
                ]
                .lstrip()
                .strip(),
                address=soup.select_one(
                    'h2[itemprop="address"].pt-1').text.strip(),
                description=soup.select_one(
                    'div[itemprop="description"]').text.strip()
                if soup.select_one(
                    'div[itemprop="description"]')
                else None,
                number_of_bedrooms=result_text,
                number_of_bathrooms=soup.select_one("div.sdb").text.strip(),
                real_estate_area=soup.select_one(
                    "div.carac-value").text.strip(),
                price=soup.select(
                    "span.text-nowrap")[1].text.replace(" ", ""),
                links_to_photos=get_foto_link(
                    url, number_of_foto),
            )
        else:
            print(f"The request failed: {response.status_code}")
            return None


async def main(new_page_url):
    parsed_data = await parse_one_element(new_page_url)


def click_all_element():
    try:
        max_elements = 60
        current_element = 0
        continue_flag = True
        while continue_flag:
            links = driver.find_elements(
                By.CLASS_NAME, "shell")
            for i in range(len(links)):
                if current_element >= max_elements:
                    continue_flag = False
                    break
                links = driver.find_elements(By.CLASS_NAME, "shell")
                link_text = links[i].text
                links[i].click()
                try:
                    WebDriverWait(driver, 10).until(
                        EC.staleness_of(links[i])
                        if link_text
                        else EC.staleness_of(links[i])
                    )
                    time.sleep(2)
                    new_page_url = driver.current_url
                    asyncio.run(main(new_page_url))
                    driver.back()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((
                            By.CLASS_NAME, "shell"))
                    )
                    current_element += 1
                except TimeoutException:
                    print("TimeoutException: Long wait for new page to load")
            try:
                next_page = driver.find_element(
                    By.XPATH,
                    "/html/body/main/div[8]/div/div[1]/ul/li[4]"
                )
                next_page.click()
                time.sleep(2)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "shell"))
                )
            except NoSuchElementException:
                continue_flag = False
    except KeyboardInterrupt:
        pass
    finally:
        driver.quit()


click_all_element()
