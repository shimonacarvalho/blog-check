import os
import requests
import argparse
import htmlbits
from amazon_paapi import AmazonApi
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv



def find_broken_images(url):
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
    images = soup.find_all('img')
    broken_images = []

    for img in images:
        img_url = img.get('src')
        if not img_url.startswith('http'):
            from urllib.parse import urljoin
            img_url = urljoin(url, img_url)
        try:
            img_res = requests.head(img_url, allow_redirects=True)
            if not (200 <= img_res.status_code < 300):
                broken_images.append(img_url)
        except requests.exceptions.RequestException as e:
            # print(f"Error during requests to {img_url}: {e}")
            broken_images.append(img_url)

    return broken_images

def extract_asin(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    asin = query_params.get('ASIN', [''])[0]  # Default to empty string if ASIN not found
    return asin


# Set your credentials. It's recommended to use environment variables or secure methods to store them.
load_dotenv()  # take environment variables from .env.
ACCESS_KEY = os.getenv('AMAZON_ACCESS_KEY')
SECRET_KEY = os.getenv('AMAZON_SECRET_KEY')
ASSOCIATE_TAG = os.getenv('AMAZON_ASSOCIATE_TAG')
REGION = 'US'

# Initialize the Amazon API client
amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG, REGION)

def output_to_html(items):
    html = ""
    html += htmlbits.html_head
    html += f"<body><div class=\"container\">"
    for item in items:
        # print(item)
        title = item.item_info.title.display_value
        imageUrl = item.images.primary.large.url if item.images.primary.large else "#"
        listings = item.offers.listings
        images = item.images.primary
        
        
        html += f"<h3>{title}</h3>"
        url = f"https://www.amazon.com/dp/{item.asin}/?tag={ASSOCIATE_TAG}"
        html += f"<a href=\"{url}\">{url}</a><br>"

        for listing in listings:            
            html += f"<div class=\"brand\">{listing.merchant_info.name}</div>"
            html += f"<ul>"
            html += f"<li>condition : {listing.condition.value}</li>"
            html += f"<li>availability : {listing.availability.message} {listing.availability.type}</li>"
            html += f"</ul>"

        # Loop through each item and create an img tag
        img_tags = []
        for size, attributes in images.to_dict().items():
            # attributes = images[size]
            img_tag = f'<img src="{attributes["url"]}" width="{attributes["width"]}" height="{attributes["height"]}" alt="{size} image">'
            img_tags.append(img_tag)

        # Join all img tags into a single string with newlines between each for readability
        html += '\n'.join(img_tags)
        html += f"<div class=\"rule\"></div>"

    html += "</div></body></html>"

    # Specify the path for the HTML file
    html_file_path = "output.html"

    # Write the HTML content to the file
    with open(html_file_path, "w") as html_file:
        html_file.write(html)




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
    elif args.url:
        in_mode = URL_MODE
        print(f"URL provided: {args.url}")
    else:
        print("No valid option provided.")

    asins = []
    if in_mode == ASIN_MODE:
        asins = args.asins.split(',')
    else:
        broken_images = find_broken_images(args.url)
        if broken_images:
            print("Broken images found:")
            asins = [extract_asin(url) for url in broken_images]
        else:
            print("No broken images found.")
        

    print(f"ASINs found: {asins}")
    items = amazon.get_items(asins)
    if json_mode:
        print(items)
    else:
        output_to_html(items)


main()