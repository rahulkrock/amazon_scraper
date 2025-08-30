from flask import Flask, render_template, request, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time, csv, re, os

app = Flask(__name__)
OUTPUT_FILE = "books.csv"


def get_driver():
    options = Options()
    options.add_argument("--headless")        # Run Chrome in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrape_books(category_url):
    driver = get_driver()
    driver.get(category_url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    books = []

    for idx, item in enumerate(soup.select(".zg-grid-general-faceout"), start=1):
        if idx > 50:
            break
        link_tag = item.find("a", href=True)
        if not link_tag:
            continue

        book_url = "https://www.amazon.in" + link_tag["href"].split("?")[0]
        driver.get(book_url)
        time.sleep(2)

        prod_soup = BeautifulSoup(driver.page_source, "html.parser")

        def extract(regex):
            m = re.search(regex, prod_soup.get_text(" ", strip=True), re.I)
            return m.group(1).strip() if m else None

        title = prod_soup.select_one("#productTitle")
        author = prod_soup.select_one(".author a")
        price = prod_soup.select_one(".a-price .a-offscreen")

        pages = extract(r"(\d+)\s+pages")
        if pages and int(pages) >= 500:
            continue

        books.append({
            "Rank": idx,
            "Title": title.get_text(strip=True) if title else None,
            "Author": author.get_text(strip=True) if author else None,
            "Edition": extract(r"Edition\s*:\s*([\w\s\d\.\-]+)"),
            "Publisher": extract(r"Publisher\s*:\s*([^;]+)"),
            "Pages": pages,
            "Dimensions": extract(r"Dimensions\s*:\s*([^;]+)"),
            "Weight": extract(r"Item Weight\s*:\s*([^;]+)"),
            "Price": price.get_text(strip=True) if price else None,
            "URL": book_url
        })

    driver.quit()
    return books


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        books = scrape_books(url)

        if books:
            # save to CSV
            with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=books[0].keys())
                writer.writeheader()
                writer.writerows(books)

        return render_template("results.html", books=books)

    return render_template("index.html")


@app.route("/download")
def download():
    if os.path.exists(OUTPUT_FILE):
        return send_file(OUTPUT_FILE, as_attachment=True)
    return "No file found!"


if __name__ == "__main__":
    app.run(debug=True)
