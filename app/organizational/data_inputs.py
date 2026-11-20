"""CSV upload decoding and template presentation; analysis stays in analyzer.py."""
import csv
import io

from .analyzer import analyze_csv


def analyze_uploaded_csv(upload, *, minimum_responses=5):
    """Decode a fresh UTF-8 stream and use the normal strict diagnostic pipeline."""
    try:
        content = upload.getvalue().decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('CSV must use UTF-8 encoding. Save the file as UTF-8 CSV and upload it again.') from error
    return analyze_csv(io.StringIO(content, newline=''), minimum_responses=minimum_responses)


def csv_template(sample_path):
    """Use the existing synthetic sample headers and a few synthetic rows."""
    with open(sample_path, encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source)
        rows = [next(reader) for _ in range(4)]
    output = io.StringIO(newline='')
    csv.writer(output).writerows(rows)
    return output.getvalue()
