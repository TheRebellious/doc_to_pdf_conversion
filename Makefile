PDF_BUILDER_DIR := $(CURDIR)/md_to_pdf
PDF_MARGIN ?= 0.5in
PDF_ENGINE ?= xelatex
PDF_MONOFONT ?= DejaVu Sans Mono
MD_FILE ?= $(firstword $(wildcard *.md))
PDF_FILE ?= $(basename $(MD_FILE)).pdf

.PHONY: pdf
pdf:
	@test -f "$(PDF_BUILDER_DIR)/Makefile" || { echo "Markdown-to-PDF subsystem is missing; run: git submodule update --init" >&2; exit 1; }
	@test -n "$(MD_FILE)" || { echo "No Markdown input found; set MD_FILE=path/to/file.md" >&2; exit 1; }
	@test -f "$(MD_FILE)" || { echo "Markdown file not found: $(MD_FILE)" >&2; exit 1; }
	$(MAKE) -C "$(PDF_BUILDER_DIR)" pdf \
		MD_FILE="$(abspath $(MD_FILE))" \
		PDF_FILE="$(abspath $(PDF_FILE))" \
		PDF_MARGIN="$(PDF_MARGIN)" \
		PDF_ENGINE="$(PDF_ENGINE)" \
		PDF_MONOFONT="$(PDF_MONOFONT)"
