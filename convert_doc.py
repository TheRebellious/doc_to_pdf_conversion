import argparse
import email
import html as html_lib
import re
import subprocess
from email import policy
from pathlib import Path
from urllib.parse import urljoin

def convert_doc(doc_path):
    doc_path = Path(doc_path)
    md_path = doc_path.with_suffix(".md")
    img_dir = doc_path.with_name(f"{doc_path.stem}_images")
    img_dir.mkdir(exist_ok=True)
    image_refs = {}
    named_images = {
        "474c2d803ce2e6418705a8a0c3fa9a4e67c5c5fef5fe42dd5c8d1606827b1d2e": "figuur-1-fasen-en-disciplines.png",
        "d3bc8bd9b2f64edb49e3e33cfe7f0a536ed0dc284eeeab943dde6b0a26e41b3e": "planningsgraaf.png",
        "e8289e2c77014dd8deaa126800540b3cdff783ca2e7c74940948d56e91d44049": "bob-model.png",
    }
    DOC_FILE = str(doc_path)
    MD_FILE = str(md_path)
    image_ref_dir = img_dir.name

    # 1. Parse MIME
    with open(DOC_FILE, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    html_content = ""
    html_location = ""
    for part in msg.walk():
        loc = part.get("Content-Location", "")
        fn = Path(loc.split("?", 1)[0]).name
        if part.get_content_maintype() == "image" and fn:
            filename = named_images.get(fn, fn)
            # Keep attachment names safe and portable on disk.
            filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
            image_path = img_dir / filename
            image_path.write_bytes(part.get_payload(decode=True) or b"")
            image_refs[fn] = f"{image_ref_dir}/{filename}"
        elif part.get_content_type() == "text/html":
            html_content = part.get_payload(decode=True).decode("utf-8", errors="replace")
            html_location = loc

    # Resolve embedded image URLs to the files extracted beside this Markdown file.
    def localize_image_source(match):
        src = match.group(3)
        filename = Path(src.split("?", 1)[0]).name
        ref = image_refs.get(filename)
        return f'{match.group(1)}{match.group(2)}{ref}{match.group(4)}' if ref else match.group(0)

    html_content = re.sub(
        r'(\bsrc=)(["\'])([^"\']*)(["\'])',
        localize_image_source,
        html_content,
        flags=re.IGNORECASE,
    )

    base_url = msg.get("Content-Base") or html_location

    # Resolve root-relative links when the MIME document supplies a base URL.
    def fix_url(match):
        url = match.group(1)
        if url.startswith("/") and base_url:
            url = urljoin(base_url, url)
        return f'href="{url}"'

    html_content = re.sub(r'href=[\"\'](/[^\"\']+)[\"\']', fix_url, html_content)

    # Remove HTML head, styles, XML, conditionals
    html_content = re.sub(r'<head.*?</head>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<!--\[if.*?<!\[endif\]-->', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<map[^>]*>.*?</map>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # This export can wrap a Gliffy image in nested tables. Replace that wrapper
    # only when its known attachment was actually extracted.
    if "planningsgraaf.png" in {Path(ref).name for ref in image_refs.values()}:
        html_content = re.sub(
            r'<table[^>]*class=[\"\'][^\"\']*gliffy-macro-table[^\"\']*[\"\'][^>]*>.*?</table>\s*</td>\s*</tr>\s*</tbody>\s*</table>',
            f'\n\n![Planningsgraaf]({image_ref_dir}/planningsgraaf.png)\n\n',
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Convert syntax-highlighted code blocks
    def fix_code_blocks(m):
        code_text = m.group(1)
        code_text = html_lib.unescape(code_text)
        code_text = re.sub(r'<[^>]+>', '', code_text)
        return f'<pre><code>\n{code_text}\n</code></pre>'

    html_content = re.sub(
        r'<pre class=[\"\']syntaxhighlighter-pre[\"\'][^>]*>(.*?)</pre>',
        fix_code_blocks,
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove empty pre tags
    html_content = re.sub(r'<pre><br\s*/?></pre>', '', html_content, flags=re.IGNORECASE)

    # Table conversion function to GFM Pipe Tables
    def convert_table(table_html):
        is_availability_table = 'data-highlight-colour=' in table_html
    
        rows = []
        tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
    
        for tr in tr_matches:
            cells = []
            cell_matches = re.finditer(r'<(td|th)([^>]*)>(.*?)</\1>', tr, re.DOTALL | re.IGNORECASE)
            for cm in cell_matches:
                tag = cm.group(1).lower()
                attrs = cm.group(2)
                c_raw = cm.group(3)
            
                colspan_match = re.search(r'colspan=[\"\']?(\d+)', attrs, re.IGNORECASE)
                colspan = int(colspan_match.group(1)) if colspan_match else 1
            
                if is_availability_table:
                    color_match = re.search(r'data-highlight-colour=[\"\']([^\"\']+)[\"\']', attrs)
                    color = color_match.group(1) if color_match else ''
                    clean_text = re.sub(r'<[^>]+>', '', c_raw).strip()
                    clean_text = html_lib.unescape(clean_text).strip()
                    if color == '#79f2c0':
                        cell_text = r'\textcolor[HTML]{00A86B}{\textbullet} Beschikbaar'
                    elif color == '#ffab00':
                        if clean_text:
                            cell_text = rf'\textcolor[HTML]{{E69500}}{{\textbullet}} {clean_text}'
                        else:
                            cell_text = r'\textcolor[HTML]{E69500}{\textbullet} Beperkt'
                    elif color == '#ff8f73':
                        cell_text = r'\textcolor[HTML]{D94343}{\textbullet} Niet beschikbaar'
                    else:
                        cell_text = clean_text
                else:
                    c = c_raw
                    # Lists inside cell
                    def replace_list(lm):
                        lis = re.findall(
                            r'<li[^>]*>(.*?)</li>',
                            lm.group(0),
                            re.DOTALL | re.IGNORECASE
                        )

                        clean_lis = [
                            re.sub(r'</?[a-zA-Z][^>]*>', ' ', li).strip()
                            for li in lis
                        ]

                        clean_lis = [
                            re.sub(r'\s+', ' ', li)
                            for li in clean_lis if li
                        ]

                        # Use LaTeX line breaks instead of HTML <br>
                        return r'\newline{} '.join(['• ' + li for li in clean_lis])
                
                    c = re.sub(r'<[ou]l[^>]*>.*?</[ou]l>', replace_list, c, flags=re.DOTALL | re.IGNORECASE)
                    # Links
                    c = re.sub(r'<a\s+[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', r'[\2](\1)', c, flags=re.DOTALL | re.IGNORECASE)
                    # Bold, Italic, Code
                    c = re.sub(r'<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>', r'**\1**', c, flags=re.DOTALL | re.IGNORECASE)
                    c = re.sub(r'<(?:em|i)[^>]*>(.*?)</(?:em|i)>', r'*\1*', c, flags=re.DOTALL | re.IGNORECASE)
                    c = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', c, flags=re.DOTALL | re.IGNORECASE)
                    # Paragraphs to <br>
                    c = re.sub(r'</p>\s*<p[^>]*>', r'\newline{} ', c, flags=re.IGNORECASE)
                    c = re.sub(r'</?p[^>]*>', '', c, flags=re.IGNORECASE)
                    # Strip remaining tags except br
                    c = re.sub(r'<(?!br\b)[^>]+>', '', c)
                    c = html_lib.unescape(c)
                    c = c.replace('\n', ' ').replace('\r', ' ')
                    c = re.sub(r'\s*<br\s*/?>\s*', '<br>', c, flags=re.IGNORECASE)
                    c = c.replace('|', r'\|')
                    c = re.sub(r'\s+', ' ', c)
                    c = re.sub(r'^(?:<br>)+|(?:<br>)+$', '', c).strip()
                    cell_text = c
            
                for _ in range(colspan):
                    cells.append((tag, cell_text))
                
            # Check if entire row is empty or spacer row
            if cells and any(t.strip() for _, t in cells):
                rows.append(cells)
            
        if not rows:
            return ''
        
        num_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < num_cols:
                r.append(('td', ''))
            
        lines = []
        if is_availability_table and not rows[0][0][1].strip():
            rows[0][0] = ('th', 'Persoon')
    
        h_row = [t if t.strip() else ' ' for _, t in rows[0]]
        lines.append('| ' + ' | '.join(h_row) + ' |')
        lines.append('| ' + ' | '.join(['---'] * num_cols) + ' |')
        for r in rows[1:]:
            row_str = [t if t.strip() else ' ' for _, t in r]
            lines.append('| ' + ' | '.join(row_str) + ' |')
        
        return '\n\n' + '\n'.join(lines) + '\n\n'

    # Find all tables and replace with alphanumeric placeholders
    tables = re.findall(r'<table[^>]*>.*?</table>', html_content, re.DOTALL | re.IGNORECASE)
    table_placeholders = {}
    for i, t in enumerate(tables):
        placeholder = f"CUSTOMTABLEPLACEHOLDER{i}CUSTOM"
        table_placeholders[placeholder] = convert_table(t)
        html_content = html_content.replace(t, f"<p>{placeholder}</p>", 1)

    # Unwrap comment markers and numbers
    html_content = re.sub(r'<span class=[\"\']inline-comment-marker[\"\'][^>]*>(.*?)</span>', r'\1', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<span class=[\"\']nh-number[\"\']>(\d+(?:\.\d+)*\.?\s*)</span>', r'\1', html_content, flags=re.IGNORECASE)

    # Preserve heading IDs for backward-compatible anchor links
    def preserve_heading_id(m):
        level = m.group(1)
        h_id = m.group(2)
        content = m.group(3)
        return f'<a id="{h_id}"></a>\n<h{level}>{content}</h{level}>'

    html_content = re.sub(r'<h([1-6])[^>]*id=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</h\1>', preserve_heading_id, html_content, flags=re.DOTALL | re.IGNORECASE)

    # Unwrap div and span tags
    html_content = re.sub(r'</?(?:div|span)[^>]*>', ' ', html_content, flags=re.IGNORECASE)

    # Convert remaining raw HTML links <a ... href="url" ...>text</a> to markdown friendly
    def clean_a_tag(m):
        attrs = m.group(1)
        text = m.group(2)
        href_m = re.search(r'href=[\"\']([^\"\']+)[\"\']', attrs)
        if href_m:
            return f'<a href="{href_m.group(1)}">{text}</a>'
        return text

    html_content = re.sub(r'<a\s+([^>]+)>(.*?)</a>', clean_a_tag, html_content, flags=re.DOTALL | re.IGNORECASE)

    # Run Pandoc to convert HTML to GFM
    pandoc_cmd = ["pandoc", "-f", "html", "-t", "gfm", "--wrap=none"]
    res = subprocess.run(pandoc_cmd, input=html_content.encode("utf-8"), capture_output=True, check=True)
    md_output = res.stdout.decode("utf-8")

    # Replace table placeholders with clean markdown tables
    for placeholder, md_table in table_placeholders.items():
        md_output = md_output.replace(placeholder, md_table)

    # Post-processing:
    # 1. Convert any remaining raw <a href="url">text</a> to [text](url)
    md_output = re.sub(r'<a\s+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', r'[\2](\1)', md_output, flags=re.DOTALL | re.IGNORECASE)

    # 2. Unescape images \![ -> ![
    md_output = re.sub(r'\\!\[', '![', md_output)

    # The exported TOC keeps Confluence IDs, while Markdown/Pandoc headings use
    # slugs derived from the visible heading text. Rewrite the first contiguous
    # block of linked list items (the TOC) to use the matching heading slugs.
    def slugify(title):
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'\s+', '-', slug)
        return slug.strip('-')

    lines = md_output.splitlines()
    toc_item = re.compile(r'^(\s*(?:[-*+]|\d+[.)])\s+)\[([^\]]*)\]\(#.*\)\s*$')
    index = 0
    while index < len(lines):
        if not toc_item.match(lines[index]):
            index += 1
            continue

        end = index
        while end < len(lines) and toc_item.match(lines[end]):
            end += 1
        if end - index >= 2:
            rewritten = []
            for line in lines[index:end]:
                match = toc_item.match(line)
                indent, title = match.groups()
                if title.strip():
                    rewritten.append(f'{indent}[{title}](#{slugify(title)})')
            lines[index:end] = rewritten
            break
        index = end
    md_output = '\n'.join(lines)

    # Explicit header IDs make these targets available to Pandoc's LaTeX writer,
    # even when the source document's export did not preserve heading IDs.
    header_line = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
    for line_number, line in enumerate(lines):
        heading = header_line.match(line)
        if heading and not re.search(r'\s+\{#[^}]+\}\s*$', heading.group(2)):
            heading_id = slugify(heading.group(2))
            if heading_id:
                lines[line_number] = f'{heading.group(1)} {heading.group(2)} {{#{heading_id}}}'
    md_output = '\n'.join(lines)

    # 4. Remove standalone backslash lines
    md_output = re.sub(r'^\s*\\\s*$', '', md_output, flags=re.MULTILINE)
    # Remove trailing backslash before empty line
    md_output = re.sub(r'\\\s*\n\s*\n', '\n\n', md_output)

    # 5. Fix escaped brackets or backslashes
    md_output = re.sub(r'\\([_#*\[\]])', r'\1', md_output)

    # 6. Clean non-breaking spaces
    md_output = md_output.replace('\u00a0', ' ')

    # 7. Collapse excessive blank lines
    md_output = re.sub(r'\n{3,}', '\n\n', md_output)

    # 8. Strip trailing whitespaces per line
    md_output = '\n'.join(line.rstrip() for line in md_output.splitlines()) + '\n'

    with open(MD_FILE, "w", encoding="utf-8") as f_out:
        f_out.write(md_output)

    print(f"Successfully generated {MD_FILE} ({len(md_output)} chars, {len(md_output.splitlines())} lines)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Word .doc files to Markdown")
    parser.add_argument(
        "doc_file",
        nargs="?",
        type=Path,
        help="a specific .doc file to convert (defaults to every .doc in this directory)",
    )
    args = parser.parse_args()

    doc_files = [args.doc_file] if args.doc_file else sorted(Path.cwd().glob("*.doc"))
    if not doc_files:
        raise SystemExit("No .doc files found in the current directory")
    for doc_file in doc_files:
        if not doc_file.is_file():
            raise SystemExit(f"Document not found: {doc_file}")
        convert_doc(doc_file)
