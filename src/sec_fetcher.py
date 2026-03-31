import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "SECInsight akshat@example.com"}

COMPANIES = {
    "Apple": "0000320193",
    "Microsoft": "0000789019",
    "Google (Alphabet)": "0001652044",
    "Meta": "0001326801",
    "Amazon": "0001018724",
    "Snowflake": "0001640147",
    "Salesforce": "0001108524",
    "Nvidia": "0001045810",
}


def get_latest_10k_url(cik: str):
    """Find the URL of the most recent 10-K primary document."""
    cik_clean = cik.lstrip("0")
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K":
            accession_nodash = accession_numbers[i].replace("-", "")
            doc = primary_docs[i]
            return f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession_nodash}/{doc}"

    return None


def fetch_filing_text(url: str) -> str:
    """Download an iXBRL 10-K and extract clean readable text."""
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    blocks = []
    for tag in soup.find_all(["p", "div", "span", "td", "h1", "h2", "h3", "li"]):
        text = tag.get_text(" ", strip=True)
        # Skip short blocks and XBRL metadata noise
        if len(text) < 60:
            continue
        if any(marker in text for marker in [
            "http://fasb.org", "http://xbrl", "us-gaap:", "P1Y", "P2Y",
            "xbrli:", "iso4217:", "dei:", "aapl-"
        ]):
            continue
        blocks.append(text)

    # Deduplicate while preserving order (parent tags include child text)
    seen = set()
    unique = []
    for b in blocks:
        if b not in seen:
            seen.add(b)
            unique.append(b)

    return "\n\n".join(unique)


def get_filing_url(company_name: str) -> str:
    """Return the SEC EDGAR URL for a company's latest 10-K."""
    cik = COMPANIES[company_name]
    return get_latest_10k_url(cik)


def get_company_text(company_name: str) -> str:
    """End-to-end: company name → clean 10-K text."""
    cik = COMPANIES[company_name]
    url = get_latest_10k_url(cik)
    if not url:
        raise ValueError(f"No 10-K found for {company_name}")
    return fetch_filing_text(url)
