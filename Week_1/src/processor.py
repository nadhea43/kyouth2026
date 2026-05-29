import json
from pathlib import Path
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError


class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str


# Method untuk extract source id by finding og:url in the html
def extract_source_id(soup):
    og_url_tag = soup.find("meta", property="og:url")

    if not og_url_tag:
        return None

    # untuk baca content url tu .get()
    url = og_url_tag.get("content", "")

    # remove "/" at the end of url kemudian split by "/" dan [-1] untuk ambik part plaing last
    source_id = url.rstrip("/").split("/")[-1]

    return source_id if source_id else None


# Method untuk extract other field yang data:
def extract_by_automation(soup, automation_val, tag=True):
    element = soup.find(tag, {"data-automation": automation_val})

    if not element:
        return None

    text = element.get_text(separator=" ", strip=True)

    return text if text else None


# Main function
def process_all_html(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    # create output directory if not exist yet
    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(input_dir.glob("*.html"))

    if not html_files:
        print("No .html files found")
        return

    # counter for summary
    total = len(html_files)
    processed = 0
    skipped = 0

    print("Silver: Processing HTML files... ")

    # loop for every html file dalam html_files list
    for html_path in html_files:
        # baca content dalam html file
        html_content = html_path.read_text(encoding="utf-8", errors="ignore")

        # tukar raw HTML stings into structured data supaya senang nak navigate n cari
        soup = BeautifulSoup(html_content, "html.parser")

        # extract source_id using method above
        source_id = extract_source_id(soup)

        # extract nama job
        job_title = extract_by_automation(soup, "job-detail-title")

        # extract nama company
        company_raw = extract_by_automation(soup, "advertiser-name")
        if company_raw:
            company = company_raw.split("view")[0].strip()
        else:
            company = None

        # extract job description
        description = extract_by_automation(soup, "jobAdDetails")

        # check fr any missing value
        missing = False

        if not source_id:
            print(f"Missing source_id: {html_path.name}")
            missing = True
        if not job_title:
            print(f"Missing job_title: {html_path.name}")
            missing = True
        if not company:
            print(f"Missing company: {html_path.name}")
            missing = True
        if not description:
            print(f"Missing job description: {html_path.name}")
            missing = True

        if missing:
            skipped += 1
            continue

        try:
            # check guna Pydantic
            job = JobListing(
                source_id=source_id,
                job_title=job_title,
                company=company,
                description=description,
            )
        except ValidationError as e:
            print(f"validation error in {html_path.name}: {e}")
            skipped += 1
            continue

        # convert to JSON and save fx model_dump() tukar Pydantic object to python disctionary
        job_data = job.model_dump()

        # create output path
        output_filename = html_path.stem + ".json"
        output_path = output_dir / output_filename

        # tulis the JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)

        print(f"Processed: {html_path.name}")
        processed += 1

    print(
        f"Silver summary: Total: {total} | Proccessed: {processed} | Skipped: {skipped}"
    )
