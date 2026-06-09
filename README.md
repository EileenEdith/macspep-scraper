# MACSpep Single Peptides Scraper

A web scraper for collecting and organizing MACSpep Single Peptides data from the Miltenyi Biotec website.

This project was built to create a structured reference table of antigen–peptide–MHC allele combinations listed in MACSpep product datasheets. The final dataset makes it easier to browse peptide sequences by antigen and MHC allele without manually opening each product page and datasheet.

## Purpose

MACSpep Single Peptides are listed across multiple product pages and datasheets. Each datasheet contains key information such as antigen name, peptide sequence, main MHC allele, and further compatible MHC alleles.

This scraper automates the collection of those fields and saves them into a clean CSV file.

The resulting dataset can be used to quickly check:

- Which peptide sequences are listed for a given antigen
- Which MHC allele is the main allele for each peptide
- Which additional MHC alleles are listed in the datasheet
- Where the original datasheet information came from

> Note: This scraper organizes information reported in Miltenyi Biotec datasheets. It should not be interpreted as an independent experimental validation that every peptide binds under all conditions.

## Features

- Scrapes MACSpep Single Peptides from the Miltenyi Biotec website
- Expands product groups and collects individual peptide product pages
- Processes all available MHC allele options for each product page
- Collects all visible datasheet links for each selected allele
- Downloads and parses datasheet PDFs
- Extracts the following fields:
  - Antigen
  - Peptide sequence
  - Main MHC allele
  - Further MHC alleles
- Deduplicates product and datasheet URLs
- Saves the extracted data into a clean CSV file
- Tracks failed products, allele cases, and PDF parsing errors

## Results

The current run collected:

- 310 records
- 74 unique antigens
- 43 unique MHC alleles
- Complete values for the target fields in the final dataset

## Installation

### Requirements

- Python 3.7+
- Google Chrome browser

### Setup

```bash
git clone https://github.com/EileenEdith/macspep-scraper.git
cd macspep-scraper
pip install -r requirements.txt
```

## Usage

Run the scraper with the default MACSpep Single Peptides page:

```bash
python3 macspep_scraper.py
```

Run with a custom URL and output file:

```bash
python3 macspep_scraper.py --url "https://..." --output "output.csv"
```

Show available options:

```bash
python3 macspep_scraper.py --help
```

## Output Format

The output CSV contains only the following columns:

```csv
antigen,peptide_sequence,main_mhc_allele,further_mhc_alleles,datasheet_url
```

Example:

```csv
CEACAM1,NPVEDKDAVAF,HLA-B*35,"B*35:01, B*35:03",https://...
CEACAM1,LPVSPRLQL,HLA-B*07,B*07:02,https://...
```

## Workflow

### Phase 1: Load Product Listing

The scraper opens the MACSpep Single Peptides listing page and loads the available product groups.

### Phase 2: Collect Product Links

The scraper expands product group sections and collects individual MACSpep product links.

### Phase 3: Process Allele Options

For each product page, the scraper checks all available MHC allele options.

For every selected allele, it collects all visible datasheet links.

### Phase 4: Parse Datasheets

Each datasheet PDF is downloaded and parsed to extract:

- Antigen
- Peptide sequence
- Main MHC allele
- Further MHC alleles

### Phase 5: Save CSV

The extracted records are deduplicated and saved as a CSV file.

## Logging

The scraper reports key metrics during execution, including:

- Number of product groups processed
- Number of product URLs collected
- Number of allele options processed
- Number of datasheet URLs collected
- Number of PDFs successfully parsed
- Final CSV shape

The scraper also saves failure logs when applicable:

- `failed_product_urls.txt`
- `failed_allele_cases.txt`
- `failed_pdf_urls.txt`

## Notes

- The Miltenyi Biotec website is dynamically rendered, so Selenium is used to interact with product pages.
- WebDriverWait is used to wait for dynamically loaded content.
- Website structure changes may require updates to the scraper.
- Please use the scraper responsibly and avoid excessive requests.

## License

MIT License

## Author

sbpark@target.re.kr

## Contributions

Bug reports, suggestions, and improvements are welcome through GitHub Issues or Pull Requests.
