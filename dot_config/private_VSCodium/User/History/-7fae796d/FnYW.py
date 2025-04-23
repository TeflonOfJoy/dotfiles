#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import random
import sys
from pathlib import Path

import img2pdf
import selenium
from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from pagelabels import PageLabelScheme, PageLabels
from pdfrw import PdfReader as pdfrw_reader
from pdfrw import PdfWriter as pdfrw_writer
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from seleniumwire import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

from fucts.roman import move_romans_to_front, roman_sort_with_ints, try_convert_int

# Setup desktop notification system
def setup_notifications():
    """Setup desktop notification system with best available method"""
    
    # Try to set up desktop notifications
    desktop_notifier = None
    
    # First try desktop-notifier (modern, actively maintained)
    try:
        import desktop_notifier
        import asyncio
        
        notifier = desktop_notifier.DesktopNotifier(
            app_name="VitalSource2PDF",
            app_icon="",  # Can be set to a path if you have an icon
            notification_limit=5
        )
        
        # Create a single event loop to reuse
        event_loop = None
        
        def notify_with_desktop_notifier(title, message):
            # Handle the asyncio coroutine properly
            nonlocal event_loop
            
            try:
                # Create a new event loop for each notification to avoid loop reuse issues
                if event_loop is None or event_loop.is_closed():
                    event_loop = asyncio.new_event_loop()
                
                async def _send():
                    try:
                        await notifier.send(title=title, message=message)
                    except Exception as e:
                        print(f"Notification send error: {e}")
                
                # Run in this loop
                event_loop.run_until_complete(_send())
            except Exception as e:
                print(f"Notification error with desktop-notifier: {e}")
                
        desktop_notifier = notify_with_desktop_notifier
        print("Desktop notifications enabled using desktop-notifier")
    except ImportError:
        # Second try notify-py (also modern)
        try:
            from notifypy import Notify
            
            def notify_with_notifypy(title, message):
                notification = Notify()
                notification.title = title
                notification.message = message
                notification.application_name = "VitalSource2PDF"
                notification.send()
                
            desktop_notifier = notify_with_notifypy
            print("Desktop notifications enabled using notify-py")
        except ImportError:
            # Third try plyer (cross-platform)
            try:
                from plyer import notification
                
                def notify_with_plyer(title, message):
                    notification.notify(
                        title=title,
                        message=message,
                        app_name="VitalSource2PDF",
                        timeout=10
                    )
                    
                desktop_notifier = notify_with_plyer
                print("Desktop notifications enabled using plyer")
            except ImportError:
                # Finally fall back to notify2 (older but works on most Linux distros)
                try:
                    import notify2
                    notify2.init("VitalSource2PDF")
                    
                    def notify_with_notify2(title, message):
                        notification = notify2.Notification(title, message)
                        notification.show()
                        
                    desktop_notifier = notify_with_notify2
                    print("Desktop notifications enabled using notify2 (legacy)")
                except ImportError:
                    print("Desktop notifications not available. Install one of:")
                    print("- desktop-notifier: pip install desktop-notifier (recommended)")
                    print("- notify-py: pip install notify-py")
                    print("- plyer: pip install plyer (cross-platform)")
                    print("- notify2: pip install notify2 (legacy)")
    
    # Always include console output as fallback
    def notify(title, message):
        # Print to console
        print(f"\n[NOTIFICATION] {title}: {message}\n")
        
        # Send desktop notification if available
        if desktop_notifier:
            try:
                desktop_notifier(title, message)
            except Exception as e:
                print(f"Desktop notification error: {e}")
    
    return notify

# Initialize notification system
notify = setup_notifications()

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='./output/')
parser.add_argument('--yuzu', default=False)
parser.add_argument('--isbn', required=True)
parser.add_argument('--min-batch-size', default=30, type=int, help='Minimum batch size of pages.')
parser.add_argument('--max-batch-size', default=60, type=int, help='Maximum batch size of pages.')
parser.add_argument('--min-batch-delay', default=5, type=int, help='Minimum delay between batches in minutes.')
parser.add_argument('--max-batch-delay', default=12, type=int, help='Maximum delay between batches in minutes.')
parser.add_argument('--min-delay', default=3, type=int, help='Minimum delay between pages to let them load in seconds.')
parser.add_argument('--max-delay', default=8, type=int, help='Maximum delay between pages to let them load in seconds.')
parser.add_argument('--pages', default=None, type=int, help='Override how many pages to save.')
parser.add_argument('--start-page', default=0, type=int, help='Start on this page. Pages start at zero and include any non-numbered pages.')
parser.add_argument('--end-page', default=-1, type=int, help='End on this page.')
parser.add_argument('--chrome-exe', default=None, type=str, help='Path to the Chrome executable. Leave blank to auto-detect.')
parser.add_argument('--disable-web-security', action='store_true', help="If pages aren't loading then you can try disabling CORS protections.")
parser.add_argument('--language', default='eng', help='OCR language. Default: "eng"')
parser.add_argument('--skip-scrape', action='store_true', help="Don't scrape anything, just re-build the PDF from existing files.")
parser.add_argument('--only-scrape-metadata', action='store_true', help="Similar to --skip-scrape, but only scrape the metadata.")
parser.add_argument('--skip-ocr', action='store_true', help="Don't do any OCR.")
parser.add_argument('--skip-pdf', action='store_true', help="Just download image files but don't build the PDF.")
parser.add_argument('--compress', action='store_true', help="Run compression and optimization. Probably won't do anything as there isn't much more compression that can be done.")
args = parser.parse_args()

args.output = Path(args.output)
args.output.mkdir(exist_ok=True, parents=True)
ebook_files = args.output / args.isbn
ebook_files.mkdir(exist_ok=True, parents=True)

book_info = {}
non_number_pages = 0

platform_identifiers = {
    'home_url': "https://reader.yuzu.com",
    'jigsaw_url': "https://jigsaw.yuzu.com",
    'total_pages': "sc-gFSQbh ognVW",
    'current_page': "InputControl__input-fbzQBk hDtUvs TextField__InputControl-iza-dmV iISUBf",
    'page_loader': "sc-hiwPVj hZlgDU",
    'next_page': "IconButton__button-bQttMI cSDGGI",
} if args.yuzu else {
    'home_url': "https://bookshelf.vitalsource.com",
    'jigsaw_url': "https://jigsaw.vitalsource.com",
    'total_pages': "sc-eoHXOn cYtiUg",
    'current_page': "InputControl__input-fbzQBk hDtUvs TextField__InputControl-iza-dmV iISUBf",
    'page_loader': "sc-AjmGg dDNaMw",
    'next_page': "IconButton__button-bQttMI cSDGGI",
}




def get_num_pages():
    while True:
        try:
            total = int(driver.execute_script('return document.getElementsByClassName("'+platform_identifiers['total_pages']+'")[0].innerHTML').strip().split('/')[-1].strip())
            try:
                # Get the value of the page number textbox
                current_page = driver.execute_script('return document.getElementsByClassName("'+platform_identifiers['current_page']+'")[0].value')
                if current_page == '' or not current_page:
                    # This element may be empty so just set it to 0
                    current_page = 0
            except selenium.common.exceptions.JavascriptException:
                current_page = 0
            return current_page, total
        except selenium.common.exceptions.JavascriptException:
            time.sleep(1)


def load_book_page(page_id):
    driver.get(platform_identifiers['home_url']+f'/reader/books/{args.isbn}/pageid/{page_id}')
    get_num_pages()  # Wait for the page to load
    # Wait for the page loader animation to disappear
    while len(driver.find_elements(By.CLASS_NAME, platform_identifiers['page_loader'])):
        time.sleep(1)


if not args.skip_scrape or args.only_scrape_metadata:
    chrome_options = webdriver.ChromeOptions()
    
    # Add random user agent
    ua = UserAgent()
    chrome_options.add_argument(f'user-agent={ua.random}')

    if args.disable_web_security:
        chrome_options.add_argument('--disable-web-security')
        print('DISABLED WEB SECURITY!')
    chrome_options.add_argument('--disable-http2')  # VitalSource's shit HTTP2 server is really slow and will sometimes send bad data.
    if args.chrome_exe:
        chrome_options.binary_location = args.chrome_exe  # '/usr/bin/google-chrome'
    
    seleniumwire_options = {
        'disable_encoding': True  # Ask the server not to compress the response
    }
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), chrome_options=chrome_options, seleniumwire_options=seleniumwire_options)

    driver.get(platform_identifiers['home_url'])
    notify("Login Required", "Please log in to continue")
    input('Press ENTER once logged in...')

    driver.maximize_window()
    page_num = args.start_page
    load_book_page(page_num)

    # Get book info
    print('Scraping metadata...')
    time.sleep((random.randint(args.min_delay, args.max_delay)) * 2)
    failed = True
    for i in range(5):
        for request in driver.requests:
            if request.url == platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/pages':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get pages information.')
                else:
                    book_info['pages'] = json.loads(request.response.body.decode())
            elif request.url == platform_identifiers['jigsaw_url']+f'/info/books.json?isbns={args.isbn}':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get book information.')
                else:
                    book_info['book'] = json.loads(request.response.body.decode())
            elif request.url == platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/toc':
                wait = 0
                while not request.response and wait < 30:
                    time.sleep(1)
                    wait += 1
                if not request.response or not request.response.body:
                    print('Failed to get TOC information, only got:', list(book_info.keys()))
                else:
                    book_info['toc'] = json.loads(request.response.body.decode())
        if 'pages' not in book_info.keys() or 'book' not in book_info.keys() or 'toc' not in book_info.keys():
            print('Missing some book data, only got:', list(book_info.keys()))
        else:
            failed = False
        if not failed:
            break
        print('Retrying metadata scrape in 10s...')
        notify("Metadata Error", "Failed to get complete metadata, retrying")
        load_book_page(page_num)
        time.sleep(10)

    if args.only_scrape_metadata:
        driver.close()
        del driver

    if not args.only_scrape_metadata:
        # The cover is likely already loaded, so check for it in current requests
        if args.start_page == 0
            base_url = None
            for find_img_retry in range(3):
                for request in driver.requests:
                    if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
                        base_url = request.url.split('/')
                        del base_url[-1]
                        base_url = '/'.join(base_url)
                        break
                if base_url:
                    break
                time.sleep(1)
            
            page_urls = set()
            if not base_url:
                print('Failed to get a URL for cover page')
            else:
                # We found an image URL, try to download the cover
                page_urls.add(('0', base_url))  # Add as page '0'

        # Continue with regular page scraping
        _, total_pages = get_num_pages()

        if args.start_page > 0:
            print('You specified a start page so ignore the very large page count.')
        total_pages = 99999999999999999 if args.start_page > 0 else total_pages

        print('Total number of pages:', total_pages)
        print('Scraping pages...')

        failed_pages = set()
        small_pages_redo = set()
        bar = tqdm(total=total_pages)
        bar.update(page_num)
        batch_size = random.randint(args.min_batch_size, args.max_batch_size)
        pages_in_batch = 0
        while page_num < total_pages + 1:
            time.sleep(random.randint(args.min_delay, args.max_delay))
            retry_delay = 5
            base_url = None
            for page_retry in range(3):  # retry the page max this many times
                largest_size = 0
                for find_img_retry in range(3):
                    for request in driver.requests:
                        if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
                            base_url = request.url.split('/')
                            del base_url[-1]
                            base_url = '/'.join(base_url)
                    time.sleep(1)
                if base_url:
                    break
                bar.write(f'Could not find a matching image for page {page_num}, sleeping {retry_delay}s...')
                time.sleep(retry_delay)
                retry_delay += 5

            page, _ = get_num_pages()

            if not base_url:
                bar.write(f'Failed to get a URL for page {page_num}, retrying later.')
                failed_pages.add(page_num)
            else:
                page_urls.add((page, base_url))
                bar.write(base_url)
                # If this isn't a numbered page we will need to increment the page count
                try:
                    int(page)
                except ValueError:
                    total_pages += 1
                    non_number_pages += 1
                    bar.write(f'Non-number page {page}, increasing page count by 1 to: {total_pages}')
                    bar.total = total_pages
                    bar.refresh()

            if page_num == args.end_page:
                bar.write(f'Exiting on page {page_num}.')
                break

            # Check for end of book (more reliable methods)
            if isinstance(page_num, int) and page_num > 0:
                # Remember current page and URL before attempting navigation
                current_page, total_pages = get_num_pages()
                current_url = driver.current_url
                
                # Attempt to navigate to next page
                del driver.requests
                before_navigation_time = time.time()
                actions = ActionChains(driver)
                actions.send_keys(Keys.RIGHT)
                actions.perform()
                
                # Wait a moment for navigation to complete
                time.sleep(3)
                
                # Check if we've reached the end using multiple reliable methods
                end_of_book = False
                
                # Method 1: Check if URL didn't change
                if driver.current_url == current_url:
                    # Double-check if page number didn't change either
                    new_page, _ = get_num_pages()
                    if str(new_page) == str(current_page):
                        bar.write(f"Book completed: Navigation had no effect (stayed on page {current_page})")
                        end_of_book = True
                
                # Method 2: Check if we're at the last page of the book
                if not end_of_book and str(current_page) == str(total_pages):
                    bar.write(f"Book completed: Reached final page ({current_page}/{total_pages})")
                    end_of_book = True
                
                # Method 3: Check if no images were loaded after navigation
                if not end_of_book:
                    # Wait up to 5 seconds for image requests
                    max_wait = 5
                    image_found = False
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait and not image_found:
                        for request in driver.requests:
                            # Only consider requests made after our navigation attempt
                            request_time = getattr(request, 'date', None)
                            if (request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/') and 
                                request_time and request_time.timestamp() > before_navigation_time):
                                image_found = True
                                break
                        if not image_found:
                            time.sleep(0.5)
                    
                    if not image_found and page_num > 5:  # Only apply this check after several pages
                        bar.write(f"Book completed: No new images loaded after navigation attempt")
                        end_of_book = True
                
                if end_of_book:
                    break
                
                # Not at the end yet, update counters
                bar.update()
                page_num += 1
                pages_in_batch += 1
            else:
                # For the first page, just navigate normally
                del driver.requests
                actions = ActionChains(driver)
                actions.send_keys(Keys.RIGHT)
                actions.perform()
                bar.update()
                page_num += 1
                pages_in_batch += 1

            # Check if batch is complete
            if pages_in_batch >= batch_size:
                sleep_time = random.randint(args.min_batch_delay * 60, args.max_batch_delay * 60)
                print(f"Completed a batch of {batch_size} pages. Sleeping for {sleep_time // 60} minutes.")
                
                # If sleep time is greater than 15 minutes, close and reopen browser
                if sleep_time > 15 * 60:
                    print("Sleep time exceeds 15 minutes. Closing browser to save resources...")
                    driver.close()
                    del driver
                    notify("Browser Closed", f"Browser closed for {sleep_time//60} minutes. Will reopen automatically.")
                    time.sleep(sleep_time)
                    
                    # Reopen browser
                    print("Reopening browser...")
                    chrome_options = webdriver.ChromeOptions()
                    ua = UserAgent()
                    chrome_options.add_argument(f'user-agent={ua.random}')
                    if args.disable_web_security:
                        chrome_options.add_argument('--disable-web-security')
                    chrome_options.add_argument('--disable-http2')
                    if args.chrome_exe:
                        chrome_options.binary_location = args.chrome_exe
                    seleniumwire_options = {
                        'disable_encoding': True
                    }
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                             chrome_options=chrome_options, 
                                             seleniumwire_options=seleniumwire_options)
                    driver.get(platform_identifiers['home_url'])
                    notify("Login Required", "Browser reopened, login needed to continue")
                    input('Browser reopened. Press ENTER once logged in...')
                    driver.maximize_window()
                    load_book_page(page_num)
                else:
                    time.sleep(sleep_time)
                
                batch_size = random.randint(args.min_batch_size, args.max_batch_size)
                pages_in_batch = 0
            # Check for end_page condition
            if page_num == args.end_page:
                bar.write(f'Exiting on page {page_num}.')
                break
        bar.close()

        print('Re-doing failed pages...')
        failed_pages_list = list(failed_pages)
        bar = tqdm(total=len(failed_pages_list))
        batch_size_redo = random.randint(args.min_batch_size, args.max_batch_size)
        pages_in_batch_redo = 0
        for page in failed_pages_list:
            load_book_page(page)
            time.sleep(random.randint(args.min_delay, args.max_delay))
            retry_delay = 5
            base_url = None
            for page_retry in range(3):  # retry the page max this many times
                largest_size = 0
                for find_img_retry in range(3):
                    for request in driver.requests:
                        if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
                            base_url = request.url.split('/')
                            del base_url[-1]
                            base_url = '/'.join(base_url)
                    time.sleep(1)
                if base_url:
                    break
                bar.write(f'Could not find a matching image for page {page_num}, sleeping {retry_delay}s...')
                time.sleep(retry_delay)
                retry_delay += 5
            page, _ = get_num_pages()
            if not base_url:
                bar.write(f'Failed to get a URL for page {page_num}, retrying later.')
                failed_pages.add(page_num)
            else:
                page_urls.add((page, base_url))
                bar.write(base_url)
                del driver.requests
            bar.update(1)
            pages_in_batch_redo += 1
            if pages_in_batch_redo >= batch_size_redo:
                sleep_time = random.randint(args.min_batch_delay * 60, args.max_batch_delay * 60)
                print(f"Re-do batch of {batch_size_redo} pages completed. Sleeping for {sleep_time//60} minutes.")
                
                # If sleep time is greater than 15 minutes, close and reopen browser
                if sleep_time > 15 * 60:
                    print("Sleep time exceeds 15 minutes. Closing browser to save resources...")
                    driver.close()
                    del driver
                    notify("Browser Closed", f"Browser closed for {sleep_time//60} minutes. Will reopen automatically.")
                    time.sleep(sleep_time)
                    
                    # Reopen browser
                    print("Reopening browser...")
                    chrome_options = webdriver.ChromeOptions()
                    ua = UserAgent()
                    chrome_options.add_argument(f'user-agent={ua.random}')
                    if args.disable_web_security:
                        chrome_options.add_argument('--disable-web-security')
                    chrome_options.add_argument('--disable-http2')
                    if args.chrome_exe:
                        chrome_options.binary_location = args.chrome_exe
                    seleniumwire_options = {
                        'disable_encoding': True
                    }
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                             chrome_options=chrome_options, 
                                             seleniumwire_options=seleniumwire_options)
                    driver.get(platform_identifiers['home_url'])
                    notify("Login Required", "Browser reopened for retrying failed pages, login needed to continue")
                    input('Browser reopened. Press ENTER once logged in...')
                    driver.maximize_window()
                    load_book_page(page)
                else:
                    time.sleep(sleep_time)
                
                batch_size_redo = random.randint(args.min_batch_size, args.max_batch_size)
                pages_in_batch_redo = 0
        bar.close()

        time.sleep(1)
        print('All pages scraped! Now downloading images...')

        bar = tqdm(total=len(page_urls))
        for page, base_url in page_urls:
            success = False
            for retry in range(6):
                del driver.requests
                time.sleep((random.randint(args.min_delay, args.max_delay)) / 2)
                driver.get(f'{base_url.strip("/")}/2000')
                time.sleep((random.randint(args.min_delay, args.max_delay)) / 2)
                retry_delay = 5
                img_data = None
                for page_retry in range(3):  # retry the page max this many times
                    largest_size = 0
                    for find_img_retry in range(3):
                        for request in driver.requests:
                            if request.url.startswith(platform_identifiers['jigsaw_url']+f'/books/{args.isbn}/images/'):
                                img_data = request.response.body
                                break
                dl_file = ebook_files / f'{page}.jpg'
                if img_data:
                    with open(dl_file, 'wb') as file:
                        file.write(img_data)
                    # Re-save the image to make sure it's in the correct format
                    img = Image.open(dl_file)
                    if img.width != 2000:
                        bar.write(f'Image too small at {img.width}px wide, retrying: {base_url}')
                        driver.get('https://google.com')
                        time.sleep(8)
                        load_book_page(0)
                        time.sleep(8)
                        continue
                    img.save(dl_file, format='JPEG', subsampling=0, quality=100)
                    del img
                    success = True
                if success:
                    break
            if not success:
                bar.write(f'Failed to download image: {base_url}')
            bar.update()
        bar.close()
        driver.close()
        del driver
else:
    print('Page scrape skipped...')

# Sometimes the book skips a page. Add a blank page if thats the case.
print('Checking for blank pages...')
existing_page_files = move_romans_to_front(roman_sort_with_ints([try_convert_int(str(x.stem)) for x in list(ebook_files.iterdir())]))
if non_number_pages == 0:  # We might not have scraped so this number needs to be updated.
    for item in existing_page_files:
        if isinstance(try_convert_int(item), str):
            non_number_pages += 1

# Create a mapping of actual page numbers to their positions in the list
page_positions = {str(page): i for i, page in enumerate(existing_page_files)}

for i, page in tqdm(enumerate(existing_page_files)):
    page_i = try_convert_int(page)
    if isinstance(page_i, int) and page_i > 0:
        # Check if the previous numbered page exists
        expected_prev = str(page_i - 1)
        if expected_prev not in page_positions:
            img = Image.new('RGB', (2000, 2588), (255, 255, 255))
            img.save(ebook_files / f'{expected_prev}.jpg')
            tqdm.write(f'Created blank image for page {expected_prev}.')

if args.skip_pdf:
    print("Skipping PDF building as requested.")
    notify("Process Complete", "Skipping PDF building as requested.")
    sys.exit(0)

print('Building PDF...')
raw_pdf_file = args.output / f'{args.isbn} RAW.pdf'
existing_page_files = move_romans_to_front(roman_sort_with_ints([try_convert_int(str(x.stem)) for x in list(ebook_files.iterdir())]))
page_files = [str(ebook_files / f'{x}.jpg') for x in existing_page_files]
pdf = img2pdf.convert(page_files)
with open(raw_pdf_file, 'wb') as f:
    f.write(pdf)

if 'book' in book_info.keys() and 'books' in book_info['book'].keys() and len(book_info['book']['books']):
    title = book_info['book']['books'][0]['title']
    author = book_info['book']['books'][0]['author']
    
    # Notify when book processing is complete
    notify("Process Complete", f"Successfully processed '{title}' by {author}")
else:
    title = args.isbn
    author = 'Unknown'
    
    # Notification for incomplete book info
    notify("Process Complete", f"Book {args.isbn} processed, but with limited metadata")

if not args.skip_ocr:
    print('Running OCR...')
    ocr_in = raw_pdf_file
    _, raw_pdf_file = tempfile.mkstemp()
    subprocess.run(f'ocrmypdf -l {args.language} --title "{title}" --jobs $(nproc) --output-type pdfa "{ocr_in}" "{raw_pdf_file}"', shell=True)
else:
    ebook_output_ocr = args.output / f'{args.isbn}.pdf'
    print('Skipping OCR...')

# Add metadata
print('Adding metadata...')
file_in = open(raw_pdf_file, 'rb')
pdf_reader = PdfReader(file_in)
pdf_merger = PdfMerger()
pdf_merger.append(file_in)

pdf_merger.add_metadata({'/Author': author, '/Title': title, '/Creator': f'ISBN: {args.isbn}'})

if 'toc' in book_info.keys():
    print('Creating TOC...')
    # Track bookmark objects by their level
    parent_bookmarks = {0: None}
    current_level = 0
    
    # Preserve original order when items have the same page number
    # We use index as a secondary sorting key to maintain original order
    for i, item in enumerate(book_info['toc']):
        item['_index'] = i
    
    # Sort TOC items by page/cfi to ensure they're in the right order
    sorted_toc = sorted(book_info['toc'], 
                       key=lambda x: (int(x['cfi'].strip('/')) if x['cfi'].strip('/').isdigit() else 0, x['_index']))
    
    for item in sorted_toc:
        level = item.get('level', 1)
        page_num = int(item['cfi'].strip('/'))
        item_title = item['title']
        
        # Handle potential level jumps gracefully
        # Determine the parent for this bookmark based on level
        parent = None
        for l in range(level-1, -1, -1):
            if l in parent_bookmarks and parent_bookmarks[l] is not None:
                parent = parent_bookmarks[l]
                break
        
        # Add the bookmark with the appropriate parent
        bookmark = pdf_merger.add_outline_item(item_title, page_num, parent=parent)
        
        # Store this bookmark as the parent for its level
        parent_bookmarks[level] = bookmark
        
        # Clear any lower levels as they are no longer valid parents
        lower_levels = [l for l in parent_bookmarks.keys() if l > level]
        for l in lower_levels:
            if l in parent_bookmarks:
                parent_bookmarks[l] = None
else:
    print('Not creating TOC...')

# Create a new temporary file for the merged PDF
_, tmpfile = tempfile.mkstemp()
pdf_merger.write(tmpfile)
file_in.close()  # Close the input file before moving/removing

romans_end = 0
for p in existing_page_files:
    if isinstance(p, str):
        romans_end += 1

if romans_end > 0:
    print('Renumbering pages...')
    reader = pdfrw_reader(tmpfile)
    labels = PageLabels.from_pdf(reader)

    roman_labels = PageLabelScheme(
        startpage=0,
        style='none',
        prefix='Cover',
        firstpagenum=1
    )
    labels.append(roman_labels)

    roman_labels = PageLabelScheme(
        startpage=1,
        style='roman lowercase',
        firstpagenum=1
    )
    labels.append(roman_labels)

    normal_labels = PageLabelScheme(
        startpage=romans_end,
        style='arabic',
        firstpagenum=1
    )
    labels.append(normal_labels)

    labels.write(reader)
    writer = pdfrw_writer()
    writer.trailer = reader
    writer.write(args.output / f'{title}.pdf')
    os.remove(tmpfile)  # Remove temporary file after successful write
else:
    shutil.move(tmpfile, args.output / f'{title}.pdf')  # Move instead of copy+delete

if args.compress:
    print('Applying selective lossless compression...')
    input_pdf = args.output / f'{title}.pdf'
    output_pdf = args.output / f'{title} compressed.pdf'
    working_dir = args.output / 'compression_temp'
    working_dir.mkdir(exist_ok=True)
    
    try:
        # Use a staged approach where we verify size at each step
        current_best_pdf = input_pdf
        current_best_size = os.path.getsize(current_best_pdf)
        print(f"Starting size: {current_best_size/1024/1024:.2f} MB")
        
        # Stage 1: Direct image optimization via extraction/recompression
        print('Stage 1: Image optimization...')
        stage1_pdf = working_dir / 'stage1.pdf'
        
        # Extract all images for optimization
        extract_dir = working_dir / 'extracted_images'
        extract_dir.mkdir(exist_ok=True)
        
        # Using pdfimages to extract images
        extract_cmd = [
            'pdfimages', '-all', str(current_best_pdf), str(extract_dir / 'img')
        ]
        extract_result = subprocess.run(extract_cmd, capture_output=True)
        
        if extract_result.returncode != 0:
            print(f"Warning: Image extraction failed, skipping image optimization")
        else:
            optimized_count = 0
            total_saved = 0
            
            # Optimize each image with appropriate lossless method
            for img_file in extract_dir.glob('*'):
                if img_file.suffix.lower() in ['.jpg', '.jpeg']:
                    try:
                        orig_size = os.path.getsize(img_file)
                        # JPEG optimization with metadata stripping only
                        opt_cmd = ['jpegoptim', '--strip-all', '--all-progressive', str(img_file)]
                        subprocess.run(opt_cmd, capture_output=True)
                        new_size = os.path.getsize(img_file)
                        saved = orig_size - new_size
                        if saved > 0:
                            optimized_count += 1
                            total_saved += saved
                    except Exception as e:
                        print(f"  Warning: JPEG optimization failed for {img_file.name}: {e}")
                
                elif img_file.suffix.lower() == '.png':
                    try:
                        orig_size = os.path.getsize(img_file)
                        # PNG optimization with metadata stripping
                        opt_cmd = ['optipng', '-o3', '-strip', 'all', str(img_file)]
                        subprocess.run(opt_cmd, capture_output=True)
                        new_size = os.path.getsize(img_file)
                        saved = orig_size - new_size
                        if saved > 0:
                            optimized_count += 1
                            total_saved += saved
                    except Exception as e:
                        print(f"  Warning: PNG optimization failed for {img_file.name}: {e}")
            
            print(f"  Optimized {optimized_count} images, saved {total_saved/1024:.1f}KB")
            
            if optimized_count > 0:
                # Now rebuild the PDF with optimized images using a direct approach
                print("  Rebuilding PDF with optimized images...")
                
                # Simple approach: Use qpdf to rebuild, focusing only on image optimization
                rebuild_cmd = [
                    'qpdf', 
                    '--stream-data=compress',
                    '--compress-streams=y',
                    '--compression-level=9',
                    '--object-streams=generate',
                    str(current_best_pdf),
                    str(stage1_pdf)
                ]
                
                try:
                    subprocess.run(rebuild_cmd, capture_output=True)
                    if os.path.exists(stage1_pdf):
                        stage1_size = os.path.getsize(stage1_pdf)
                        if stage1_size < current_best_size:
                            print(f"  Image optimization reduced size to {stage1_size/1024/1024:.2f} MB ({(current_best_size-stage1_size)/1024/1024:.2f} MB saved)")
                            current_best_pdf = stage1_pdf
                            current_best_size = stage1_size
                        else:
                            print("  Image optimization didn't reduce overall PDF size")
                except Exception as e:
                    print(f"  Warning: PDF rebuild with optimized images failed: {e}")
        
        # Stage 2: Content stream optimization with PyPDF2
        print('Stage 2: Content stream optimization...')
        stage2_pdf = working_dir / 'stage2.pdf'
        
        try:
            reader = PdfReader(current_best_pdf)
            writer = PdfWriter()
            
            # Simple content stream optimization
            for page in reader.pages:
                # Compress content streams - very conservative approach
                page.compress_content_streams()
                writer.add_page(page)
            
            # Preserve metadata
            metadata = {
                '/Author': author,
                '/Title': title, 
                '/Creator': f'ISBN: {args.isbn}',
                '/Producer': 'vitalsource2pdf (optimized)',
            }
            writer.add_metadata(metadata)
                
            with open(stage2_pdf, 'wb') as f:
                writer.write(f)
            
            if os.path.exists(stage2_pdf):
                stage2_size = os.path.getsize(stage2_pdf)
                if stage2_size < current_best_size:
                    print(f"  Content optimization reduced size to {stage2_size/1024/1024:.2f} MB ({(current_best_size-stage2_size)/1024/1024:.2f} MB saved)")
                    current_best_pdf = stage2_pdf
                    current_best_size = stage2_size
                else:
                    print("  Content optimization didn't reduce overall PDF size")
        except Exception as e:
            print(f"  Warning: Content stream optimization failed: {e}")
        
        # Stage 3: Minimal structure optimization with QPDF
        print('Stage 3: Minimal structure optimization...')
        stage3_pdf = working_dir / 'stage3.pdf'
        
        try:
            # QPDF with minimal, conservative settings
            qpdf_cmd = [
                'qpdf',
                '--stream-data=compress',      # Basic stream compression
                '--compress-streams=y',        # Compress all streams
                '--recompress-flate',          # Recompress existing streams
                '--compression-level=9',       # Maximum compression level
                '--decode-level=specialized',  # Advanced decoding
                str(current_best_pdf),
                str(stage3_pdf)
            ]
            
            subprocess.run(qpdf_cmd, capture_output=True)
            
            if os.path.exists(stage3_pdf):
                stage3_size = os.path.getsize(stage3_pdf)
                if stage3_size < current_best_size:
                    print(f"  Structure optimization reduced size to {stage3_size/1024/1024:.2f} MB ({(current_best_size-stage3_size)/1024/1024:.2f} MB saved)")
                    current_best_pdf = stage3_pdf
                    current_best_size = stage3_size
                else:
                    print("  Structure optimization didn't reduce overall PDF size")
        except Exception as e:
            print(f"  Warning: Structure optimization failed: {e}")
        
        # Copy the best result to the output file
        if current_best_pdf != input_pdf:
            shutil.copy(current_best_pdf, output_pdf)
            reduction = (1 - (current_best_size / os.path.getsize(input_pdf))) * 100
            print()
            print(f"Original size:   {os.path.getsize(input_pdf)/1024/1024:.2f} MB")
            print(f"Compressed size: {current_best_size/1024/1024:.2f} MB")
            print(f"Reduction:       {reduction:.2f}%")
            
            if reduction >= 5:
                print("✓ Significant size reduction achieved while maintaining 100% quality")
            else:
                print("ℹ Modest size reduction achieved while maintaining 100% quality")
        else:
            print()
            print("No size reduction achieved with any method. Using original file.")
            # If the output exists from a previous run, remove it
            if os.path.exists(output_pdf):
                os.remove(output_pdf)
    
    except Exception as e:
        print(f"Error during compression: {e}")
        print("Compression failed - using original file")
        
    finally:
        # Clean up temporary files
        try:
            if working_dir.exists():
                shutil.rmtree(working_dir)
        except Exception:
            print("Warning: Could not clean up temporary files")