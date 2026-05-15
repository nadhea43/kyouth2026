import email
import quopri
from pathlib import Path

def ingest_all_mhtml(input_dir,output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print("Source directory does not exist.")
        return
    
    mhtml_files = list(input_dir.glob("*.mhtml"))

    if not mhtml_files:
        print("no .mthml files found")
        return
    
    total = len(mhtml_files)
    extracted = 0
    failed = 0

    print("Starting extraction....")

    for mthml_path in mhtml_files:
        # baca raw bytes of mthml files sbb email tu expects bytes 
        raw_bytes = mthml_path.read_bytes()
        # parse mthml files tu sebagai email yg ada byk bahagian
        msg = email.message_from_bytes(raw_bytes)

        html_content = None

        # cari HTML part by using walk()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                # bagi raw encoded content so that it translates any special chars to normal HTML
                payload = part.get_payload(decode=True)
                if payload:
                    # decode bytes to stringg yg boleh dibaca
                    try:
                        html_content = payload.decode("utf-8")
                    except UnicodeDecodeError:
                        html_content = payload.decode("latin-1")
                    break

        output_filename = mthml_path.stem + ".html"
        output_path = output_dir/output_filename

        if html_content:
            # tulis HTML string dekat output file
            output_path.write_text(html_content, encoding="utf-8")
            print(f"Extracted: {mthml_path.name}")
            extracted += 1
        else:
            print(f"No html content found in {mthml_path.name}")
            failed += 1

    print(f" Bronze Summary: Total: {total} | Extracted: {extracted} | Failed: {failed}")


