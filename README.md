# 📚 Amazon Bestseller Book Scraper

A Flask + Selenium based web app that scrapes book details from **Amazon India Bestsellers**.  
You can enter a bestseller category URL, and the app will extract details of books that:  
- Rank within the top 50  
- Have **page count less than 500**

It exports the results to a CSV file for easy use in your projects.

---

## ✨ Features

- Scrapes book details from Amazon India:
  - Title  
  - Author  
  - Edition  
  - Publisher  
  - Page count  
  - Dimensions  
  - Weight  
  - Price  
  - Bestsellers rank  
- Works directly with **Amazon Bestseller category URLs**  
- Built-in **fallback parsing** for missing fields  
- Progress bar during scraping  
- Exports data as `books.csv`

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/rahulkrock/amazon_scraper.git
cd amazon_scraper
