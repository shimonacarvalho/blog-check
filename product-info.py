import os
import requests
import argparse
import htmlbits
import json
from amazon_paapi import AmazonApi
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from urllib.parse import urlparse
import re

def slugify(source):

    parsed_url = urlparse(source)
    if bool(parsed_url.scheme):
        print('is an url')
        source = parsed_url.path
    slug = re.sub('[/.,]|(%..)', '-', source)
    slug = re.sub('^-+', '', slug)
    slug = re.sub('-+$', '', slug)
    slug = re.sub('-+', '-', slug)
    return slug



def check_images(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the status is 4xx, 5xx
    except requests.exceptions.HTTPError as e:
        print(f"Failed to retrieve {url}: {e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {url}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    found_images = soup.find_all('img')
    images = []

    for img in found_images:
        img_url = img.get('src')
        img_status = ""
        if not img_url.startswith('http'):
            from urllib.parse import urljoin
            img_url = urljoin(url, img_url)
        img_asin = extract_asin(img_url)
        print(img_asin, img_url)
        if img_asin:                    
            try:
                img_res = requests.head(img_url, allow_redirects=True)
                img_status = "success"
                if not (200 <= img_res.status_code < 300):
                    img_status = f"error_${img_res.status_code}"
            except requests.exceptions.RequestException as e:
                # print(f"Error during requests to {img_url}: {e}")
                img_status = "failure"
            images.append({"url": img_url, "status": img_status, "asin": img_asin})

    return images

def find_amazon_links(url):
    # Send a GET request to the URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP request errors
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        return []
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
        return []

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags in the HTML
    links = soup.find_all('a')

    # Filter links containing 'amazon.com'
    amazon_links = [link['href'] for link in links if 'amazon.com' in link.get('href', '')]

    return amazon_links


def extract_asin(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    asin = query_params.get('ASIN', [''])[0]  # Default to empty string if ASIN not found
    if asin == '':
        path_parts = urlparse(url).path.split('/')
        # The ASIN typically follows '/dp/' in the URL path
        try:
            asin_index = path_parts.index('dp') + 1
            return path_parts[asin_index]
        except (ValueError, IndexError):
            return None  
    return asin


# Set your credentials. It's recommended to use environment variables or secure methods to store them.
load_dotenv()  # take environment variables from .env.
ACCESS_KEY = os.getenv('AMAZON_ACCESS_KEY')
SECRET_KEY = os.getenv('AMAZON_SECRET_KEY')
ASSOCIATE_TAG = os.getenv('AMAZON_ASSOCIATE_TAG')
REGION = 'US'

# Initialize the Amazon API client
amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG, REGION)

def txt_to_copy(txt):
    return f"<button class='copyButton' data-text-to-copy='{txt}'><img src='copy-icon.svg' width='24' height='24'></button>"


def item_to_html(item):
    html = ""
    title = item.item_info.title.display_value
    imageUrl = item.images.primary.large.url if item.images.primary.large else "#"
    status = "BORKED"
    try:
        listings = item.offers.listings if item.offers.listings else []
    except AttributeError:
        listings = []
    try:
        images = item.images.primary
    except AttributeError:
        images = []
    
    html += f"<h3>{title}{txt_to_copy(title)}</h3>"
    html += f"{item.asin}{txt_to_copy(item.asin)}<br>"
    url = f"https://www.amazon.com/dp/{item.asin}/?tag={ASSOCIATE_TAG}"
    html += f"<a href=\"{url}\">{url}</a>"
    html += f"{txt_to_copy(url)}<br>";

    for listing in listings:            
        html += f"<div class=\"brand\">{listing.merchant_info.name}</div>"
        html += f"<ul>"
        cond = listing.condition.value
        html += f"<li>condition : {cond}</li>"
        avl = f"{listing.availability.message} {listing.availability.type}"
        html += f"<li>availability : {avl}</li>"
        html += f"</ul>"
        if avl == "In Stock Now" and cond == "New":
            status = "AVAILABLE"

    html += f"<div class=\"status {status.lower()}\"> {status} </div><p>"
    # Loop through each item and create an img tag
    img_tags = []
    for size, attributes in images.to_dict().items():
        # attributes = images[size]
        img_tag = f'<img src="{attributes["url"]}" width="{attributes["width"]}" height="{attributes["height"]}" alt="{size} image">'
        img_tags.append(img_tag)

    # Join all img tags into a single string with newlines between each for readability
    html += '\n'.join(img_tags)
    return html


def output_to_html(items, replacement_items, source):
    html = ""
    html += htmlbits.html_head
    html += f"<body>"


    for item in items:
        html += "<div class=\"container\">"
        html += item_to_html(item)
        if item.asin in replacement_items:
            rep = replacement_items[item.asin]
            html += f"<div class=\"status replace\">{item.asin} will be replaced by {rep.asin}</div><p>"

            html += item_to_html(rep)
        html +="</div>"
    html += "</body></html>"

    # Specify the path for the HTML file
    html_file_path = f"{slugify(source)}.html"
    print(f"Printing to {html_file_path}")

    # Write the HTML content to the file
    with open(html_file_path, "w") as html_file:
        html_file.write(html)


# Todo - eventually only request info when you want to replace
def load_replacement_asins(filepath):
    # hese are the replacement asin dict
    asin_to_rsins = load_json(filepath)
    # make a list of all the replacement products
    rsins = list(asin_to_rsins.values())
    # get product info
    rprods = amazon.get_items(rsins)
    print("\n\n")
    # print(products)
    # make a dictionary with entries asin -> product
    rsins_to_rprods = {product.asin: product for product in rprods}
    # make a another dictionary of the original asin -> replacement product
    asins_to_rprods = {asin: rsins_to_rprods[asin_to_rsins[asin]] for asin in asin_to_rsins}
    print(asins_to_rprods)
    return asins_to_rprods



def load_json(filepath):
    # Check if the file exists
    if os.path.exists(filepath):
        # File exists, attempt to load the dictionary from the file
        try:
            with open(filepath, 'r') as json_file:
                return json.load(json_file)

        except json.JSONDecodeError:
            # Handle case where the file could not be decoded as JSON
            print(f"Error: {filepath} could not be decoded as JSON.")
            return {}
    else:
        # File does not exist, skip loading and return None or an empty dict
        print(f"Notice: {filepath} does not exist. Skipping.")
        return {}

def main():



    # Create the parser
    parser = argparse.ArgumentParser(description='Process -asins or -url options.')

    # Add the arguments
    parser.add_argument('-a', '--asins', type=str, help='The ASINs')
    parser.add_argument('-u', '--url', type=str, help='The URL')
    parser.add_argument('--json', action='store_true', help='Enable json output')

    # Execute the parse_args() method
    args = parser.parse_args()
    in_mode = None
    ASIN_MODE = 1
    URL_MODE = 2
    json_mode = args.json

    if args.asins:
        in_mode = ASIN_MODE
        source = args.asins
    elif args.url:
        in_mode = URL_MODE
        source = args.url
        print(f"URL provided: {args.url}")
    else:
        print("No valid option provided.")
        exit(1)

    asins = {}
    if in_mode == ASIN_MODE:
        asins = args.asins.split(',')
    else:
        amz_links = find_amazon_links(args.url)
        print(amz_links)
        if amz_links:
            for url in amz_links:
                asin = extract_asin(url)
                if asin and not asin in asins:
                    asins[asin] = url
        else:
            print("No broken images found.")
        asins = list(asins.keys())
        
    print(asins)
    items = amazon.get_items(asins)
    replacement_items = load_replacement_asins("replacements.json")

    print(f"ASINs found: {asins}")
    if json_mode:
        print(items)
    else:
        output_to_html(items, replacement_items, source)


main()