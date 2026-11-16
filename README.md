
# DOC to PDF Conversion

Convert supported Word `.doc` exports into Markdown and then PDF. The converter extracts the HTML body and embedded images from a MIME-based document, uses Pandoc to produce Markdown, and uses XeLaTeX to render the final PDF.

> **Compatibility note:** This project is intended for `.doc` files that contain a MIME/HTML document (for example, certain exported or emailed Word documents). It does **not** convert arbitrary legacy binary Microsoft Word `.doc` files. A binary `.doc` file from an older version of Word will need to be exported to a supported format first.

## How it works

1. `convert_doc.py` reads the MIME message, extracts its HTML content and embedded images, and writes a Markdown file alongside an images directory.
2. Pandoc converts the HTML content to GitHub-flavoured Markdown.
3. The Makefile invokes Pandoc with XeLaTeX to generate a styled PDF.
4. `convert_doc_to_pdf.sh` runs the complete pipeline in a temporary working directory and copies the resulting PDF to the current directory.

## Requirements

The project uses Python's standard library only; there are no third-party Python packages to install.

Required system tools:

- Python 3
- Pandoc
- XeLaTeX (provided by a TeX Live installation)
- GNU Make
- Bash

The LaTeX header (`header.tex`) uses packages including `booktabs`, `longtable`, `array`, `tabularx`, `colortbl`, `xcolor`, `etoolbox`, and `enumitem`. Install a TeX distribution that provides these packages.

### Install on:

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y \
  python3 \
  make \
  pandoc \
  texlive-xetex \
  texlive-latex-extra \
  texlive-fonts-recommended
```

### Fedora

```bash
sudo dnf upgrade --refresh -y
sudo dnf install -y \
  python3 \
  make \
  pandoc \
  texlive-xetex \
  texlive-collection-fontsrecommended \
  texlive-collection-latexextra
```

The Makefile requests the **Arial** main font. Ensure Arial is installed and discoverable by XeLaTeX on your system. If it is not available, either install a licensed Arial font or change `mainfont:Arial` in the Makefile to an installed substitute (for example, `Liberation Sans`).

### Check the installed tools

```bash
python3 --version
pandoc --version
xelatex --version
make --version
```

## Usage

Clone the repository:

```bash
git clone https://github.com/TheRebellious/doc_to_pdf_conversion.git
cd doc_to_pdf_conversion
```

Make the wrapper executable if necessary:

```bash
chmod +x convert_doc_to_pdf.sh
```

### Convert one document

```bash
./convert_doc_to_pdf.sh /path/to/document.doc
```

The resulting file is written to the directory from which you ran the command:

```text
document.pdf
```

The input file is copied to a temporary working directory during conversion. The temporary directory is removed when the script exits.

### Convert multiple documents

Run the wrapper once for each input file:

```bash
./convert_doc_to_pdf.sh /path/to/first.doc
./convert_doc_to_pdf.sh /path/to/second.doc
```

### Run the conversion stages separately

To convert a supported `.doc` file to Markdown in the current directory:

```bash
python3 convert_doc.py /path/to/document.doc
```

This creates `document.md` and, when images are present, a `document_images/` directory.

To convert an existing Markdown file to PDF using the repository's styling:

```bash
make pdf MD_FILE=/path/to/document.md
```

You can override the output name, PDF engine, or page margin:

```bash
make pdf MD_FILE=document.md PDF_FILE=output.pdf PDF_ENGINE=xelatex PDF_MARGIN=0.5in
```

The Makefile defaults to the first `.md` file in the repository directory and writes a PDF with the same base name.

## Output and formatting

- Embedded images are extracted and referenced from the generated Markdown.
- Tables are converted to Markdown tables, with special handling for availability-highlight tables.
- The PDF uses XeLaTeX, 11pt text, 1.15 line spacing, and a default page margin of 0.5 inches.
- Table and list styling is defined in `header.tex`.

## Troubleshooting

### No `.doc` files found in the current directory

When running `convert_doc.py` without an argument, it searches the current directory for `*.doc` files. Pass a file path explicitly or run the command from the directory containing the documents.

### Document not found

Check that the input path is correct and that the file exists and is readable.

### Pandoc or XeLaTeX is not found

Install Pandoc and a TeX Live distribution that includes XeLaTeX, then ensure `pandoc` and `xelatex` are available on your `PATH`.

### Font not found (Arial)

Install Arial or change the Makefile's `mainfont` variable to a font installed on your system. For example:

```make
--variable=mainfont:"Liberation Sans"
```

### The input document cannot be parsed or produces empty output

The converter expects a MIME message containing an HTML part. It is not a general-purpose reader for binary Word documents. Open the document in a compatible office application and export it to a supported HTML/MIME-based format before trying again.

### LaTeX reports a missing package

Install the TeX Live package that provides the missing LaTeX package. On Ubuntu/Debian, `texlive-latex-extra` and `texlive-fonts-recommended` cover many of the packages used by this project.

## Repository files

| File                    | Purpose                                                      |
|-------------------------|--------------------------------------------------------------|
| `convert_doc.py`        | Extracts MIME/HTML content and images and generates Markdown |
| `convert_doc_to_pdf.sh` | Runs the full DOC-to-PDF pipeline                            |
| `Makefile`              | Configures and runs Markdown-to-PDF generation               |
| `header.tex`            | LaTeX packages and document styling                          |

## Limitations

- Only MIME/HTML-based `.doc` inputs are supported by the current parser; ordinary binary `.doc` files are not guaranteed to work.
- The converter expects an HTML part encoded in UTF-8 (with replacement for invalid byte sequences).
- PDF generation requires a working XeLaTeX installation and an available font matching the Makefile's configured main font.
- The project does not currently provide a Windows-native wrapper, automated test suite, or dependency lockfile.

## Tested on:
| OS        | Shell       | Result          |
|-----------|-------------|-----------------|
| Debian 13 | bash        | Works perfectly |
| Fedora 45 | fish & bash | Works perfectly |