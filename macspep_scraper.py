# macspep_scraper.py
# 필요한 패키지: pip install selenium webdriver-manager beautifulsoup4 requests pdfplumber pandas tqdm lxml

import re
import time
import argparse
import requests
import pdfplumber
import pandas as pd
from io import BytesIO
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from webdriver_manager.chrome import ChromeDriverManager
from collections import defaultdict


BASE_URL = "https://www.miltenyibiotec.com"

DEFAULT_START_URL = (
    "https://www.miltenyibiotec.com/KR-en/products/"
    "macs-flow-cytometry/kits-and-support-reagents/mhc-multimers/"
    "macspep-single-peptides.html?query=%3Arelevance%3AallCategoriesOR%3A10000802"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}


class WorkflowLogger:
    """Track workflow metrics and failures."""
    def __init__(self):
        self.load_25_more_clicks = 0
        self.product_groups_expanded = 0
        self.product_urls_collected = 0
        self.unique_product_urls = 0
        self.allele_options_processed = 0
        self.unique_datasheet_urls = 0
        self.pdfs_successfully_parsed = 0
        self.failed_product_urls = []
        self.failed_allele_cases = defaultdict(list)
        self.failed_pdf_urls = []

    def save_failure_logs(self):
        """Save failure logs to files."""
        if self.failed_product_urls:
            with open("failed_product_urls.txt", "w") as f:
                for url in self.failed_product_urls:
                    f.write(url + "\n")

        if self.failed_allele_cases:
            with open("failed_allele_cases.txt", "w") as f:
                for product_url, errors in self.failed_allele_cases.items():
                    f.write(f"Product: {product_url}\n")
                    for error in errors:
                        f.write(f"  - {error}\n")
                    f.write("\n")

        if self.failed_pdf_urls:
            with open("failed_pdf_urls.txt", "w") as f:
                for url in self.failed_pdf_urls:
                    f.write(url + "\n")

    def log_summary(self):
        """Print workflow summary."""
        print("\n" + "="*70)
        print("📊 WORKFLOW SUMMARY")
        print("="*70)
        print(f"Load 25 More clicks:          {self.load_25_more_clicks}")
        print(f"Product groups expanded:      {self.product_groups_expanded}")
        print(f"Product URLs collected:       {self.product_urls_collected}")
        print(f"Unique product URLs:          {self.unique_product_urls}")
        print(f"Allele options processed:     {self.allele_options_processed}")
        print(f"Unique datasheet URLs:        {self.unique_datasheet_urls}")
        print(f"PDFs successfully parsed:     {self.pdfs_successfully_parsed}")
        if self.failed_product_urls:
            print(f"Failed product URLs:          {len(self.failed_product_urls)}")
        if self.failed_allele_cases:
            print(f"Failed allele cases:          {len(self.failed_allele_cases)}")
        if self.failed_pdf_urls:
            print(f"Failed PDF URLs:              {len(self.failed_pdf_urls)}")
        print("="*70 + "\n")


logger = WorkflowLogger()


def full_url(url):
    return urljoin(BASE_URL, url)


def get_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def phase1_load_all_products(listing_url):
    """
    Phase 1: Open listing page and load all products.
    - Scroll down and click "Load 25 More" until no more products.
    """
    print("\n[PHASE 1] Loading all products on listing page...")
    driver = get_driver(headless=True)

    try:
        driver.get(listing_url)
        wait = WebDriverWait(driver, 20)

        # Wait for page to be interactive - Angular needs more time
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(10)  # Allow Angular and dynamic content to fully render
        except:
            time.sleep(10)

        load_count = 0
        max_attempts = 100

        for attempt in range(max_attempts):
            # Scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # Try to find and click "Load 25 More" button
            try:
                load_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Load') or contains(., 'load')]")
                    ),
                    timeout=3
                )
                driver.execute_script("arguments[0].scrollIntoView();", load_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", load_button)
                load_count += 1
                logger.load_25_more_clicks += 1
                print(f"  ✓ Clicked 'Load 25 More' #{load_count}")

                # Wait for new products to load
                time.sleep(2)

            except:
                # No load button found - all products loaded
                print(f"  ✅ All products loaded (total clicks: {load_count})")
                break

        time.sleep(1)
        return driver

    except Exception as e:
        print(f"  ❌ Error in Phase 1: {e}")
        driver.quit()
        raise e


def phase2_expand_accordions_and_collect_product_links(driver):
    """
    Phase 2: Expand all accordion groups and collect individual product links.
    - Click accordion buttons with data-cy="mb-search-family-line-expand-button"
    - Collect product name links from expanded rows (not group titles)
    """
    print("\n[PHASE 2] Expanding accordions and collecting product links...")

    wait = WebDriverWait(driver, 15)

    # Find all accordion buttons
    accordion_buttons = driver.find_elements(
        By.XPATH,
        "//button[@data-cy='mb-search-family-line-expand-button']"
    )
    print(f"  Found {len(accordion_buttons)} accordion groups")

    # Click each accordion to expand
    for i, btn in enumerate(accordion_buttons):
        try:
            driver.execute_script("arguments[0].scrollIntoView();", btn)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", btn)
            logger.product_groups_expanded += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠ Error expanding accordion #{i}: {e}")

    # Wait for all content to render
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    # Collect product links from expanded rows
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    product_links = set()

    # Look for product links - macspep-*.html but not the listing page itself
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if not href:
            continue

        href_lower = href.lower()

        # Product links contain /products/macspep- and end with .html
        if "/products/macspep-" in href_lower and ".html" in href_lower:
            # Exclude the listing page itself
            if "macspep-single-peptides.html" in href_lower and "query=" in href_lower:
                continue

            # Clean URL and convert to full URL
            clean_url = href.split("#")[0]
            full = full_url(clean_url)
            product_links.add(full)

    product_links = sorted(product_links)
    logger.product_urls_collected = len(product_links)
    logger.unique_product_urls = len(product_links)

    print(f"  ✅ Collected {len(product_links)} unique product URLs")

    return product_links


def phase3_collect_datasheets_with_allele_handling(product_url):
    """
    Phase 3: Visit product page, wait for Angular rendering, and iterate through
    all allele options to collect datasheets.

    For each allele:
    1. Click the allele button
    2. Wait for product table to update
    3. Collect ALL visible Data sheet links in the table
    4. Store all of them (deduplicate by datasheet_url only)
    """
    driver = get_driver(headless=True)
    all_datasheets = {}
    allele_count = 0

    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 20)

        # Wait for Angular-rendered content
        try:
            wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(@data-cy, 'mb-product-filter-item')]")),
                    EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Data sheet')]")),
                    EC.presence_of_element_located((By.XPATH, "//*[contains(@data-cy, 'mb-variants-list')]"))
                )
            )
            time.sleep(2)
        except:
            time.sleep(3)

        # Find all allele filter buttons
        allele_buttons = driver.find_elements(By.XPATH, "//button[contains(@data-cy, 'mb-product-filter-item')]")

        if not allele_buttons:
            # No allele buttons found - collect datasheets from current view
            datasheets = _collect_datasheets_from_current_view(driver)
            return datasheets, allele_count

        # Collect allele text from buttons
        allele_info = []
        for btn in allele_buttons:
            try:
                aria_label = btn.get_attribute("aria-label") or ""
                btn_text = btn.text or ""
                allele_info.append({
                    "button": btn,
                    "text": btn_text,
                    "aria_label": aria_label,
                })
            except:
                pass

        print(f"    Found {len(allele_info)} allele options")

        # Process each allele
        for allele_info_item in allele_info:
            allele_text = allele_info_item["text"].strip()

            try:
                # Re-find the button to avoid stale element reference
                allele_button = driver.find_element(
                    By.XPATH,
                    f"//button[contains(@data-cy, 'mb-product-filter-item') and contains(., '{allele_text}')]"
                )

                print(f"      Selecting allele: {allele_text}")

                # Click the allele button
                driver.execute_script("arguments[0].scrollIntoView();", allele_button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", allele_button)
                allele_count += 1
                logger.allele_options_processed += 1

                # Wait for table/content to update
                time.sleep(1)

                # Wait for variants list to update
                try:
                    wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//*[contains(@data-cy, 'mb-variants-list')]")
                        ),
                        timeout=5
                    )
                except:
                    pass

                time.sleep(1)

                # Collect all datasheets visible for this allele
                datasheets_for_allele = _collect_datasheets_from_current_view(driver)

                # Count product rows visible for this allele
                html = driver.page_source
                soup = BeautifulSoup(html, "lxml")
                product_rows = soup.find_all("div", attrs={"data-cy": lambda x: x and "mb-variant" in x})
                row_count = len(product_rows) if product_rows else 0

                print(f"        - {len(datasheets_for_allele)} datasheets collected, "
                      f"{row_count} product rows visible")

                # Add to all datasheets (deduplicate by URL only)
                for ds_url in datasheets_for_allele.values():
                    all_datasheets[ds_url] = ds_url

            except Exception as e:
                error_msg = f"Allele '{allele_text}': {str(e)[:50]}"
                logger.failed_allele_cases[product_url].append(error_msg)
                print(f"      ❌ {error_msg}")

        return all_datasheets, allele_count

    except Exception as e:
        logger.failed_product_urls.append(product_url)
        return {}, allele_count

    finally:
        try:
            driver.quit()
        except:
            pass


def _collect_datasheets_from_current_view(driver):
    """
    Collect all visible datasheet links on current page.

    Looks for:
    - Links with "Data sheet" text
    - That point to static.miltenyibiotec.com PDFs
    - Within the visible variants list/table
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    datasheets = {}

    # Find the variants list container
    variants_list = soup.find(attrs={"data-cy": "mb-variants-list"})
    if variants_list:
        # Search within variants list only
        search_scope = variants_list
    else:
        # Fallback to entire page
        search_scope = soup

    # Find all links in the search scope
    for a in search_scope.find_all("a"):
        text = a.get_text(" ", strip=True).lower()
        href = a.get("href", "").strip()

        if not href:
            continue

        href_lower = href.lower()

        # Look for "Data sheet" links that point to Miltenyi PDFs
        if "data sheet" in text and "static.miltenyibiotec.com" in href_lower:
            if href_lower.startswith("http"):
                datasheets[href] = href
            else:
                datasheets[full_url(href)] = full_url(href)

    return datasheets


def phase4_download_and_parse_pdfs(datasheet_urls):
    """
    Phase 4: Download PDFs and extract fields.
    - Antigen
    - Peptide sequence
    - Main MHC allele
    - Further MHC alleles
    """
    print("\n[PHASE 4] Parsing PDF datasheets...")

    records = []

    for pdf_url in tqdm(datasheet_urls, desc="  Parsing PDFs"):
        try:
            record = _parse_datasheet_pdf(pdf_url)
            if record:
                records.append(record)
                logger.pdfs_successfully_parsed += 1
            else:
                logger.failed_pdf_urls.append(pdf_url)
        except Exception as e:
            logger.failed_pdf_urls.append(pdf_url)

    print(f"  ✅ Parsed {logger.pdfs_successfully_parsed}/{len(datasheet_urls)} PDFs")

    return records


def _download_pdf(pdf_url):
    """Download PDF content."""
    response = requests.get(pdf_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.content


def _extract_pdf_text(pdf_content):
    """Extract text from PDF bytes."""
    text = ""
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += "\n" + page_text
    except Exception as e:
        return ""
    return text


def _extract_field_value(text, field_name):
    """
    Extract field value from PDF text (case-insensitive).
    Tries multiple patterns to find the field.
    """
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_name_lower = field_name.lower()

    # Pattern 1: Field name at start of line
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if line_lower.startswith(field_name_lower):
            value = line[len(field_name):].strip()
            if value and value not in (":", "="):
                return value
            if i + 1 < len(lines):
                next_val = lines[i + 1].strip()
                if next_val:
                    return next_val

    # Pattern 2: Field name with separator
    pattern = rf"(?i){re.escape(field_name)}\s*[:=]?\s*([^\n\r]+)"
    match = re.search(pattern, text)
    if match:
        value = match.group(1).strip()
        if value:
            return value

    return None


def _parse_datasheet_pdf(pdf_url):
    """Extract fields from datasheet PDF."""
    try:
        pdf_content = _download_pdf(pdf_url)
        text = _extract_pdf_text(pdf_content)

        if not text:
            return None

        record = {
            "antigen": _extract_field_value(text, "Antigen"),
            "peptide_sequence": _extract_field_value(text, "Peptide sequence"),
            "main_mhc_allele": _extract_field_value(text, "Main MHC allele"),
            "further_mhc_alleles": _extract_field_value(text, "Further MHC alleles"),
            "datasheet_url": pdf_url,
        }

        # Only return if at least one field was extracted
        if record["antigen"] or record["peptide_sequence"]:
            return record

        return None

    except Exception as e:
        return None


def phase5_save_csv(records, output_csv):
    """
    Phase 5: Save extracted records to CSV.
    Columns: antigen, peptide_sequence, main_mhc_allele, further_mhc_alleles, datasheet_url
    """
    print("\n[PHASE 5] Saving results to CSV...")

    if not records:
        print("  ❌ No records to save!")
        return

    df = pd.DataFrame(records)

    # Ensure correct column order
    column_order = [
        "antigen",
        "peptide_sequence",
        "main_mhc_allele",
        "further_mhc_alleles",
        "datasheet_url"
    ]
    df = df[column_order]

    # Sort by antigen
    df = df.sort_values("antigen").reset_index(drop=True)

    # Save to CSV
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"  ✅ CSV saved: {output_csv}")
    print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")

    return df


def run_workflow(listing_url, output_csv):
    """Complete workflow."""

    try:
        # Phase 1: Load all products
        driver = phase1_load_all_products(listing_url)

        try:
            # Phase 2: Expand accordions and collect product links
            product_links = phase2_expand_accordions_and_collect_product_links(driver)

            if not product_links:
                print("\n❌ No product links found!")
                return

        finally:
            driver.quit()

        # Phase 3: Collect datasheets with allele handling
        print(f"\n[PHASE 3] Collecting datasheets from {len(product_links)} products...")
        print(f"  Processing each product with ALL allele options...\n")

        all_datasheet_urls = set()

        for i, product_url in enumerate(product_links, 1):
            try:
                # Extract product name from URL for better logging
                product_name = product_url.split("/")[-1].replace(".html", "").replace("-", " ").title()

                print(f"  [{i}/{len(product_links)}] {product_name}")

                datasheets, allele_count = phase3_collect_datasheets_with_allele_handling(
                    product_url
                )

                if datasheets:
                    for ds_url in datasheets.values():
                        all_datasheet_urls.add(ds_url)
                    print(f"    ✓ Total: {len(datasheets)} unique datasheets from {allele_count} allele(s)\n")
                else:
                    print(f"    - No datasheets found\n")

            except Exception as e:
                logger.failed_product_urls.append(product_url)
                print(f"    ❌ Error: {str(e)[:60]}\n")

        logger.unique_datasheet_urls = len(all_datasheet_urls)
        all_datasheet_urls = sorted(all_datasheet_urls)

        print(f"  ✅ Collected {len(all_datasheet_urls)} unique datasheet URLs")

        if not all_datasheet_urls:
            print("\n❌ No datasheets to parse!")
            return

        # Phase 4: Parse PDFs
        records = phase4_download_and_parse_pdfs(all_datasheet_urls)

        if not records:
            print("\n❌ No records extracted from PDFs!")
            return

        # Phase 5: Save CSV
        df = phase5_save_csv(records, output_csv)

        if df is not None:
            # Show sample
            print("\n📋 Sample data (first 10 rows):")
            pd.set_option("display.max_columns", None)
            pd.set_option("display.max_colwidth", 40)
            pd.set_option("display.width", 150)
            print(df.head(10).to_string())

        # Save failure logs
        logger.save_failure_logs()

        # Print summary
        logger.log_summary()

    except Exception as e:
        print(f"\n❌ Workflow error: {e}")
        logger.save_failure_logs()
        logger.log_summary()
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="MACSpep Single Peptides Data Scraper"
    )
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Listing page URL")
    parser.add_argument("--output", default="macspep_single_peptides.csv", help="Output CSV file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_workflow(args.url, args.output)
