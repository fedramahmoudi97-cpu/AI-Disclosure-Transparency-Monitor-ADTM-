import regex as re 
from bs4 import BeautifulSoup
def extract_text_from_html (html_content):
    soup=BeautifulSoup (html_content, "lxml")
    for element in soup(["script", "style", "table"]):
        element.decompose()
    return soup.get_text(separator=' ', strip=True)

def parse_sections(text, section_patterns):
    # Create a robust regex to split the document by section headers
    # This uses a positive lookahead to keep the delimiter (the section title)
    pattern = '|'.join(f'(?=^{p.strip()})' for p in section_patterns)
    parts = re.split(pattern, text, flags=re.IGNORECASE | re.MULTILINE) 

    sections = {}
    if len(parts) > 1:
        # The first part is everything before the first section marker
        sections['header'] = parts[0].strip()
        for part in parts[1:]:
            part = part.strip()
            # Find the section title (the first line)
            title_match = re.match(r'.*(?:\n|$)', part)
            if title_match:
                title = title_match.group(0).strip()
                content = part[len(title):].strip()
                # Normalize title for consistent key
                normalized_title = ' '.join(title.split()).lower()
                sections[normalized_title] = content
    else:
        # If no sections found, treat the whole document as one section
        sections['full_document'] = parts[0].strip()
        
    return sections
    