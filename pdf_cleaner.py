import os
import re
from PyPDF2 import PdfReader  # Or from pypdf import PdfReader for newer installations
from pathlib import Path

def find_first_pdf(folder_path):
    """Finds the first PDF file in the given folder."""
    for filename in sorted(os.listdir(folder_path)):  # sorted ensures some predictability
        if filename.lower().endswith(".pdf"):
            return os.path.join(folder_path, filename)
    return None


def clean_pdf_text(pdf_path, output_path, header_text, footer_page_number_pattern_str, skip_first_page_cleaning=True):
    """
    Extracts text from a PDF, removes specified headers and footers, and saves it.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_path (str): Path to save the cleaned text file.
        header_text (str): The exact text of the header to remove.
        footer_page_number_pattern_str (str): Regex pattern string for the page number.
                                            Example: r"^\d+ of \d+$" for "X of Y"
        skip_first_page_cleaning (bool): If True, the first page will not have headers/footers removed.
    """
    all_pages_cleaned_text = []
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        print(f"Processing PDF: {pdf_path} with {num_pages} pages.")

        # Regex for matching a line that IS ENTIRELY the page number
        # footer_page_number_pattern_str should include ^ and $ for this
        standalone_page_num_regex = re.compile(footer_page_number_pattern_str)

        # Regex for matching a line that STARTS WITH the page number
        # We need the core pattern without ^ and $ for prefix matching.
        core_page_num_pattern = footer_page_number_pattern_str.lstrip('^').rstrip('$')
        # This will capture the page number part (group 1) and the rest of the line (group 2)
        prefix_page_num_re = re.compile(r"(" + core_page_num_pattern + r")\s*(.*)")

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if not page_text:
                all_pages_cleaned_text.append(f"[Page {i + 1} - No text extracted or blank page]")
                continue

            lines_original = page_text.splitlines()

            if i == 0 and skip_first_page_cleaning:
                print(f"Page {i + 1}: Keeping as is (first page).")
                all_pages_cleaned_text.append("\n".join(lines_original))
                continue

            current_page_final_lines = []
            line_cursor = 0  # Points to the current line in lines_original to be processed

            # 1. Attempt to remove Header
            if line_cursor < len(lines_original) and lines_original[line_cursor].strip() == header_text:
                print(f"Page {i + 1}: Removed header: '{lines_original[line_cursor].strip()}'")
                line_cursor += 1

            # 2. Process the line that might contain the page number (either standalone or as a prefix)
            if line_cursor < len(lines_original):
                line_to_check_for_page_num = lines_original[line_cursor]
                stripped_line_to_check = line_to_check_for_page_num.strip()

                # Scenario A: The line IS the page number (e.g., "2 of 130")
                if standalone_page_num_regex.fullmatch(stripped_line_to_check):
                    print(f"Page {i + 1}: Removed standalone page number line: '{stripped_line_to_check}'")
                    line_cursor += 1  # This line is consumed
                else:
                    # Scenario B: The line STARTS WITH the page number (e.g., "2 of 130 CHAPTER...")
                    # We match against the stripped line to robustly find the pattern,
                    # then extract the remainder from the original line if needed.
                    match_obj = prefix_page_num_re.match(stripped_line_to_check)
                    if match_obj:
                        page_num_part = match_obj.group(1)  # The part that matched core_page_num_pattern
                        rest_of_line = match_obj.group(2)  # The part after the pattern and spaces

                        print(f"Page {i + 1}: Removed page number prefix '{page_num_part}' from line.")

                        if rest_of_line.strip():  # If there's actual content after the page number
                            current_page_final_lines.append(rest_of_line)
                        line_cursor += 1  # This line is consumed/processed
                    else:
                        # This line was not a standalone page number, nor did it start with one.
                        # So, it's the first line of actual content for this page.
                        current_page_final_lines.append(line_to_check_for_page_num)
                        line_cursor += 1

            # 3. Add all subsequent lines from the original list
            if line_cursor < len(lines_original):
                current_page_final_lines.extend(lines_original[line_cursor:])

            all_pages_cleaned_text.append("\n".join(current_page_final_lines))

        # Join cleaned page texts. Add a newline between pages.
        # If a page becomes empty after cleaning, it will just contribute an empty string,
        # leading to potentially multiple newlines if `\n\n` is used.
        # Let's filter out empty page strings before joining if we want cleaner separation.

        final_output_text = []
        for page_content in all_pages_cleaned_text:
            if page_content.strip() or "[Page" in page_content:  # Keep content or error messages
                final_output_text.append(page_content)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(final_output_text))  # Use \n\n to separate page content visibly
        print(f"Cleaned text saved to: {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()


def main():
    input_folder = Path(__file__).resolve().parent / "text-input"

    # Parameters for "Alice's Adventures in Wonderland"
    header_to_remove = "Alice’s Adventures in Wonderland"  # Exact header text

    # Regex for "X of Y" (e.g., "1 of 130", "12 of 130")
    # This pattern is used for both standalone line matching and prefix matching.
    # It must have ^ and $ for standalone_page_num_regex.fullmatch()
    page_number_pattern = r"^\d+ of \d+$"

    pdf_file_path = find_first_pdf(input_folder)

    if pdf_file_path:
        base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]
        output_file_path = os.path.join(input_folder, f"{base_name}_cleaned.txt")

        clean_pdf_text(
            pdf_path=pdf_file_path,
            output_path=output_file_path,
            header_text=header_to_remove,
            footer_page_number_pattern_str=page_number_pattern,
            skip_first_page_cleaning=True
        )
    else:
        print(f"No PDF files found in {input_folder}")


if __name__ == "__main__":
    main()