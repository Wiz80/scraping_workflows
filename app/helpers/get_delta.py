import os
import difflib
import hashlib

class GetDelta:

    def sanitize_filename(self, url: str) -> str:
        """Sanitizes the URL to be used as a valid filename."""
        return hashlib.md5(url.encode()).hexdigest() + ".txt"

    def save_pdf_text_to_file(self, text: str, filename: str):
        """Saves the extracted PDF text to a file."""
        with open(filename, "w") as file:
            file.write(text)

    def calculate_text_delta(self, old_text: str, new_text: str) -> float:
        """Calculates the delta between two texts in the range of 0 to 1."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        diff = difflib.SequenceMatcher(None, old_lines, new_lines)
        return 1 - diff.ratio()  # 0 indicates no change, 1 indicates complete change

    def get_existing_text(self, filename: str) -> str:
        """Retrieves the existing text from a file if it exists."""
        if os.path.exists(filename):
            with open(filename, "r") as file:
                return file.read()
        return ""
