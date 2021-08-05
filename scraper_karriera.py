# Import general libraries
import datetime
import pandas as pd

from bs4 import BeautifulSoup as soup
import time
import csv

import requests
requests.packages.urllib3.disable_warnings()
import random

# Improt Selenium packages
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException as NoSuchElementException
from selenium.common.exceptions import WebDriverException as WebDriverException
from selenium.common.exceptions import ElementNotVisibleException as ElementNotVisibleException
from selenium.webdriver.chrome.options import Options


def request_page(url_string, verification, robust):
    """HTTP GET Request to URL.
    Args:
        url_string (str): The URL to request.
        verification: Boolean certificate is to be verified
        robust: If to be run in robust mode to recover blocking
    Returns:
        HTML code
    """
    if robust:
        loop = False
        first = True
        # Scrape contents in recovery mode
        c = 0
        while loop or first:
            first = False
            try:
                uclient = requests.get(url_string, timeout = 60, verify = verification)
                page_html = uclient.text
                loop = False
                return page_html
            except requests.exceptions.ConnectionError:
                c += 10
                print("Request blocked, .. waiting and continuing...")
                time.sleep(random.randint(10,60) + c)
                loop = True
                continue
            except (requests.exceptions.ReadTimeout,requests.exceptions.ConnectTimeout):
                print("Request timed out, .. waiting one minute and continuing...")
                time.sleep(60)
                loop = True
                continue
    else:
        uclient = requests.get(url_string, timeout = 60, verify = verification)
        page_html = uclient.text
        loop = False
        return page_html

def request_page_fromselenium(url_string, driver, robust):
    """ Request HTML source code from Selenium web driver to circumvent mechanisms
    active with HTTP requests
    Args:
        Selenium web driver
        URL string
    Returns:
        HTML code
    """
    if robust:
        loop = False
        first = True
        # Scrape contents in recovery mode
        c = 0
        while loop or first:
            first = False
            try:
                open_webpage(driver, url_string)
                time.sleep(5)
                page_html = driver.page_source
                loop = False
                return page_html
            except WebDriverException:
                c += 10
                print("Web Driver problem, .. waiting and continuing...")
                time.sleep(random.randint(10,60) + c)
                loop = True
                continue
    else:
        open_webpage(driver, url_string)
        time.sleep(5)
        page_html = driver.page_source
        loop = False
        return page_html

def set_driver(webdriverpath, headless):
    """Opens a webpage in Chrome.
    Args:
        url of webpage.
    Returns:
        open and maximized window of Chrome with webpage.
    """
    options = Options()
    if headless:

        options.add_argument("--headless")
    elif not headless:
        options.add_argument("--none")
    return webdriver.Chrome(webdriverpath, chrome_options = options)

def create_object_soup(object_link, verification, robust):
    """ Create page soup out of an object link for a product
    Args:
        Object link
        certificate verification parameter
        robustness parameter
    Returns:
        tuple of beautiful soup object and object_link
    """
    object_soup = soup(request_page(object_link, verification, robust), 'html.parser')
    return (object_soup, object_link)

def make_soup(link, verification):
    """ Create soup of listing-specific webpage
    Args:
        object_id
    Returns:
        soup element containing listings-specific information
    """
    return soup(request_page(link, verification), 'html.parser')

def reveal_all_items(driver):
    """ Reveal all items on the categroy web page of Albert Heijn by clicking "continue"
    Args:
        Selenium web driver
    Returns:
        Boolean if all items have been revealed
    """
    hidden = True
    while hidden:
        try:
           time.sleep(random.randint(5,7))
           driver.find_element_by_css_selector('section#listing-home div.col-md-6.customlistinghome > a').click()
        except (NoSuchElementException, ElementNotVisibleException):
           hidden = False
    return True

def open_webpage(driver, url):
    """Opens web page
    Args:
        web driver from previous fct and URL
    Returns:
        opened and maximized webpage
    """
    driver.set_page_load_timeout(60)
    driver.get(url)
    driver.maximize_window()

def extract_listings_pages(first_page_html):
    """ Extract pages using pagecount field on karriera page
    Args:
        URL
        Robustness parameter
        Certification verification parameter
    Returns:
        listings
    """
    # Extract pages
    pc_soup = soup(first_page_html, 'html.parser')
    pc_list = pc_soup.findAll('div',{'class': 'pagination-nav'})[0].findAll('a', {'class': 'g-button no-text number'})
    # Extract days online
    return ['http://karriera.al/' + pc['href'] for pc in pc_list]

def make_jobs_list(base_url, robust, driver):
    """ Extract item URL links + front information and return list of
    all item links on web page
    Args:
        Base URL
        Categroy tuples
        Certificate verification parameter
        Robustness parameter
        Selenium web driver
    Returns:
        Dictionary with item URLs
    """
    print("Start retrieving item links...")
    on_repeat = False
    first_run = True
    front_contents = []
    while on_repeat or first_run:
        first_run = False
        open_webpage(driver, base_url)
        # Extract first page_html
        first_page_html = driver.page_source
        # Extract page count and loop over pages
        pages = [driver.current_url]
        pages = pages + extract_listings_pages(first_page_html)
        # Loop over pages
        for page in pages:
            time.sleep(1)
            # Within each page extract list of link, views, job city and days online
            open_webpage(driver, page)
            page_html = driver.page_source
            page_soup = soup(page_html, 'html.parser')
            front_content_container = page_soup.findAll('div', {'class': 'result-left col-sm-8 col-xs-12'})[0].table.tbody.findAll('tr')
            for container in front_content_container:
                container_content = container.findAll('td')
                link = 'http://karriera.al' + container_content[0].a['href']
                job_city = container_content[1].text
                days_online = container_content[2].text
                views  = container_content[3].text
                front_content = [link, job_city, days_online, views]
                front_contents.append(front_content)
            print('Retrieved', len(front_contents), 'item links!')
    return front_contents


def create_elements(front_content_container, verification, robust):
    """Extracts the relevant information form the html container, i.e. object_id,
    Args:
        A container element + region, city, districts, url_string.
    Returns:
        A dictionary containing the information for one listing.
    """
    object_soup = create_object_soup(front_content_container[0], verification, robust)[0]
    object_link = front_content_container[0]
    # Insert information from above
    job_city = front_content_container[1]
    days_online = front_content_container[2]
    views = front_content_container[3]
    # Parse contents
    try:
        content_container = object_soup.findAll('body', {'class': 'al'})[0].findAll('div', {'id': 'wrapper'})[0].findAll('div', {'class': 'post-job'})[0]
    except:
        content_container = []
    try:
        company_name = content_container.findAll('div', {'class': 'job-txt'})[0].h5.text
    except:
        company_name = ""
    try:
        contact_details_container = content_container.findAll('div', {'class': 'job-txt'})[0].ul.findAll('li')
        contact_details = '|'.join([i.text for i in contact_details_container])
    except:
        contact_details = ''
    try:
        company_details_container = content_container.findAll('div', {'class':'row job-inside clear'})[0]
        assert company_details_container.a.text == 'Rreth nesh'
        company_details = company_details_container.p.text
    except:
        company_details = ""
    try:
        object_id_container = object_link.split('/')
        object_id = object_id_container[5]
    except:
        object_id = ""
    try:
        job_category_container = content_container.findAll('div', {'class': 'col-sm-6 col-xs-12'})[0]
        assert job_category_container.a.text == 'Kategoria'
        job_category = job_category_container.span.text
    except:
        job_category = ""
    try:
        contract_type_container = content_container.findAll('div', {'class': 'col-sm-6 col-xs-12'})[1]
        assert contract_type_container.a.text == 'Lloji i punës'
        contract_type = contract_type_container.span.text
    except:
        contract_type = ""
    # Flexibly extract job description
    job_description = ""
    for i in range(0,5):
        try:
            job_description_container = content_container.findAll('div', {'class': 'col-sm-12 col-xs-12'})[i]
            assert job_description_container.a.text == 'Përshkrimi i Punës'
            job_description = job_description_container.p.text
            break
        except AssertionError:
            job_description = ""
    # Flexibly extract job title
    job_title = ""
    for i in range(0,5):
        try:
            job_title_container = content_container.findAll('div', {'class': 'col-sm-12 col-xs-12'})[i]
            assert job_title_container.a.text == 'Titulli i postimit *'
            job_title = job_title_container.span.text
            break
        except AssertionError:
            job_title = ""
    # Flexibly extract requirements
    requirements = ""
    for i in range(0,5):
        try:
            requirements_container = content_container.findAll('div', {'class': 'col-sm-12 col-xs-12'})[i]
            assert requirements_container.a.text == 'Kërkesat e profilit'
            requirements = requirements_container.p.text
            break
        except:
            requirements = ""
     # Flexibly extract salary
    salary = ""
    for i in range(0,5):
        try:
            salary_container = content_container.findAll('div', {'class': 'col-sm-12 col-xs-12'})[i]
            assert salary_container.a.text == 'Paga'
            salary = salary_container.span.text
            break
        except:
            salary = ""
    # Flexibly extract additional information
    add_information = ""
    for i in range(0,5):
        try:
            add_information_container = content_container.findAll('div', {'class': 'col-sm-12 col-xs-12'})[i]
            assert add_information_container.a.text == 'Tjetër (Opsionale)'
            add_information = add_information_container.p.text
            break
        except:
            add_information = ""
    page_html = object_soup.prettify()
    # Create a dictionary as output
    return dict([("object_link", object_link),
                 ("job_city", job_city),
                 ("days_online", days_online),
                 ("views", views),
                 ("company_name", company_name),
                 ("company_details", company_details),
                 ("contact_details", contact_details),
                 ("object_id", object_id),
                 ("job_title", job_title),
                 ("job_category", job_category),
                 ("contract_type", contract_type),
                 ("job_description", job_description),
                 ("requirements", requirements),
                 ("salary", salary),
                 ("page_html", page_html),
                 ("add_information", add_information)])

def scrape_karriera(verification, robust, front_contents):
    """Scraper for karriera job portal based on specified parameters.
    In the following we would like to extract all the containers containing
    the information on one listing. For this purpose we try to parse through
    the html text and search for all elements of interest.
    Args:
        verification
        robust
        item_links
    Returns:
        Appended pandas dataframe with crawled content.
    """
    # Define dictionary for output
    input_dict = {}
    frames = []
    counter = 0
    #skipper = 0
    # Loop links
    for front_content in front_contents:
        time.sleep(random.randint(1,2))
        print('Parsing URL', front_content[0])
        # Set scraping time
        now = datetime.datetime.now()
        try:
            input_dict.update(create_elements(front_content, verification, robust))
            time.sleep(0.5)
            # Create a dataframe
            df = pd.DataFrame(data = input_dict, index =[now])
            df.index.names = ['scraping_time']
            frames.append(df)
        except requests.exceptions.ConnectionError:
            error_message = "Connection was interrupted, waiting a few moments before continuing..."
            print(error_message)
            time.sleep(random.randint(2,5) + counter)
            continue
    return pd.concat(frames).drop_duplicates(subset = 'object_link')

def main():
    """ Note: Set parameters in this function
    """
    # Set time stamp
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set scraping parameters
    base_url = 'http://karriera.al/al/result'
    robust = True
    webdriverpath = r"C:\Users\\Calogero\Documents\GitHub\job_portal_scraper_medium_js\chromedriver.exe"

    # Set up a web driver
    driver = set_driver(webdriverpath, False)

    # Start timer
    start_time = time.time() # Capture start and end time for performance

    # Set verification setting for certifiates of webpage. Check later also certification
    verification = True

    # Execute functions for scraping
    start_time = time.time() # Capture start and end time for performance
    item_links = make_jobs_list(base_url, robust, driver)
    driver.close()
    appended_data = scrape_karriera(verification, robust, item_links)

    # Split off HTML code for Giannis and team
    appended_data = appended_data.drop("page_html",1)

    # Write output to Excel
    print("Writing to Excel file...")
    time.sleep(1)
    file_name = '_'.join(['C:\\Users\\Calogero\\Documents\\GitHub\\job_portal_scraper_medium_js\\data\\daily_scraping\\' +
    str(now_str), 'karriera.xlsx'])
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
    appended_data.to_excel(writer, sheet_name = 'jobs')
    writer.save()

     # Write to CSV
    print("Writing to CSV file...")
    appended_data.to_csv(file_name.replace('.xlsx', '.csv'), sep =";",quoting=csv.QUOTE_ALL)

    end_time = time.time()
    duration = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))


    # For interaction and error handling
    final_text = "Your query was successful! Time elapsed:" + str(duration)
    print(final_text)
    time.sleep(0.5)

# Execute scraping
if __name__ == "__main__":
    main()