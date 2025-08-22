import os
import re
from pathlib import Path

from PyPDF2 import PdfReader

# --- Input and Output Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
input_folder = SCRIPT_DIR / "text-input"
output_folder = SCRIPT_DIR / "audio-input"
CHARACTER_LIMIT = 4000


def find_source_file(folder_path: Path) -> Path:
    """
    Finds the first .pdf or .txt file in the specified folder.

    Args:
        folder_path: The directory to search in.

    Returns:
        The full path to the first found file.

    Raises:
        FileNotFoundError: If no .pdf or .txt file is found.
    """
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".txt"]:
            return file_path
    raise FileNotFoundError("No source .pdf or .txt file found in the input folder.")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts all text from a given PDF file.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        A single string containing all the text from the PDF.
    """
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def split_text_into_blocks(text: str, limit: int) -> list[str]:
    """
    Splits a large text into smaller blocks, ensuring sentences are not cut off.

    Args:
        text: The full text to be split.
        limit: The maximum character limit for each block.

    Returns:
        A list of text blocks.
    """
    blocks = []
    # Split by sentence-ending punctuation, keeping the punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
    current_block = ""

    for sentence in sentences:
        # Check if adding the next sentence exceeds the limit
        if len(current_block) + len(sentence) + 1 <= limit:
            current_block += sentence + " "
        else:
            # If the current block is not empty, save it
            if current_block:
                blocks.append(current_block.strip())
            # Start a new block with the current sentence
            current_block = sentence + " "

    # Add the last remaining block if it exists
    if current_block:
        blocks.append(current_block.strip())

    return blocks


def save_blocks_to_files(blocks: list[str], destination_folder: Path):
    """
    Saves a list of text blocks into sequentially numbered .txt files.

    Args:
        blocks: The list of text blocks to save.
        destination_folder: The directory where files will be saved.
    """
    destination_folder.mkdir(parents=True, exist_ok=True)
    for i, block in enumerate(blocks, start=1):
        filename = f"block{i}.txt"
        file_path = destination_folder / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(block)


def main():
    """Main execution process to find, process, and save text blocks."""
    try:
        source_file_path = find_source_file(input_folder)
        print(f"Source file found: {source_file_path}")

        # Handle file based on its type
        if source_file_path.suffix.lower() == ".pdf":
            text_content = extract_text_from_pdf(source_file_path)
        else:  # .txt file
            with open(source_file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

        blocks = split_text_into_blocks(text_content, limit=CHARACTER_LIMIT)
        save_blocks_to_files(blocks, output_folder)

        print(f"{len(blocks)} blocks successfully saved to '{output_folder}'")
    except Exception as e:
        print(f"An error occurred: {e}")


# Run the script
if __name__ == "__main__":
    main()