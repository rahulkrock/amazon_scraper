from flask import Flask, render_template, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time, csv, re, os, json

app = Flask(__name__)
OUTPUT_FILE = "books.csv"

progress = {"current": 0, "total": 0}  # shared progress state


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def scrape_books(category_url):
    global progress
    driver = get_driver()
    driver.get(category_url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    books = []

    book_links = []
    for idx, item in enumerate(soup.select(".zg-grid-general-faceout"), start=1):
        if idx > 50:
            break
        link_tag = item.find("a", href=True)
        if link_tag:
            book_links.append(("https://www.amazon.in" + link_tag["href"].split("?")[0], idx))

    progress["total"] = len(book_links)
    progress["current"] = 0

    for book_url, idx in book_links:
        driver.get(book_url)
        time.sleep(2)
        prod_soup = BeautifulSoup(driver.page_source, "html.parser")

        # -------- Collect product details ----------
        details = {}
        for table in prod_soup.select(
            "#productDetailsTable, #productDetails_detailBullets_sections1, #detailBullets_feature_div"
        ):
            for row in table.select("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    details[key] = val
            for li in table.select("li"):
                parts = li.get_text(" ", strip=True).split(":")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    details[key] = val

        # -------- JSON-LD Fallback ----------
        if not details.get("Publisher") or not details.get("Author"):
            for script in prod_soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if "author" in data and not details.get("Author"):
                            details["Author"] = (
                                data["author"][0]["name"]
                                if isinstance(data["author"], list)
                                else data["author"]["name"]
                            )
                        if "publisher" in data and not details.get("Publisher"):
                            details["Publisher"] = (
                                data["publisher"]["name"]
                                if isinstance(data["publisher"], dict)
                                else data["publisher"]
                            )
                except Exception:
                    continue

        # -------- Extract fields ----------
        title = prod_soup.select_one("#productTitle")
        author = prod_soup.select_one(".author a") or details.get("Author")
        price = prod_soup.select_one(".a-price .a-offscreen")

        # ---- Page count (hybrid method) ----
        pages = None
        for k, v in details.items():
            if "page" in k.lower() or "print length" in k.lower():
                m = re.search(r"(\d+)", v)
                if m:
                    pages = int(m.group(1))
                break
        if not pages:
            text = prod_soup.get_text(" ", strip=True)
            m = re.search(r"(\d+)\s+pages", text, re.I)
            if m:
                pages = int(m.group(1))

        if pages and pages >= 500:
            progress["current"] += 1
            continue

        books.append(
            {
                "Rank": idx,
                "Title": title.get_text(strip=True) if title else None,
                "Author": author.get_text(strip=True) if hasattr(author, "get_text") else author,
                "Edition": details.get("Edition"),
                "Publisher": details.get("Publisher"),
                "Pages": pages,
                "Dimensions": details.get("Dimensions") or details.get("Product Dimensions"),
                "Weight": details.get("Item Weight"),
                "Price": price.get_text(strip=True) if price else None,
                "URL": book_url,
            }
        )

        progress["current"] += 1

    driver.quit()
    return books


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        books = scrape_books(url)

        if books:
            with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=books[0].keys())
                writer.writeheader()
                writer.writerows(books)

        return render_template("results.html", books=books)

    return render_template("index.html")


@app.route("/progress")
def get_progress():
    return jsonify(progress)


@app.route("/download")
def download():
    if os.path.exists(OUTPUT_FILE):
        return send_file(OUTPUT_FILE, as_attachment=True)
    return "No file found!"


if __name__ == "__main__":
    app.run(debug=True)
