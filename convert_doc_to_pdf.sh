#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 1 ]]; then
    printf 'Usage: %s path/to/document.doc\n' "${0##*/}" >&2
    exit 2
fi

INPUT_PATH="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
if [[ ! -f "$INPUT_PATH" ]]; then
    printf 'Document not found: %s\n' "$INPUT_PATH" >&2
    exit 1
fi

DOC_NAME="$(basename -- "$INPUT_PATH")"
DOC_STEM="${DOC_NAME%.*}"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/doc-to-pdf.XXXXXXXX")"
trap 'rm -rf -- "$WORK_DIR"' EXIT

cp -- "$INPUT_PATH" "$WORK_DIR/$DOC_NAME"
(
    cd -- "$WORK_DIR"
    python3 "$SCRIPT_DIR/convert_doc.py" "$DOC_NAME"
)

make -C "$SCRIPT_DIR" pdf \
    MD_FILE="$WORK_DIR/$DOC_STEM.md" \
    PDF_FILE="$WORK_DIR/$DOC_STEM.pdf"

cp -- "$WORK_DIR/$DOC_STEM.pdf" "$(pwd)/$DOC_STEM.pdf"
printf 'Created %s\n' "$(pwd)/$DOC_STEM.pdf"
