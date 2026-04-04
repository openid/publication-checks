import sys
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import csv
import io
import os
import time

# Define exit status codes
EXIT_SUCCESS = 0
EXIT_INVALID_USAGE = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_FILE_PROCESSING_ERROR = 3
EXIT_CSV_WRITING_ERROR = 4
EXIT_NETWORK_ERROR = 5
EXIT_PERMISSION_ERROR = 6
EXIT_FILENAME_STATE_ERROR = 10
EXIT_CONTENT_STATE_ERROR = 20
EXIT_CONTENT_DATE_ERROR = 30
EXIT_CONTENT_REF_ERROR = 40
EXIT_CONTENT_NOTICES_ERROR = 50
EXIT_CONTENT_STRUCT_ERROR = 60
EXIT_CONTENT_AUTHORS_ERROR = 70
EXIT_CONTENT_HISTORY_ERROR = 80
EXIT_CONTENT_FILENAME_MISMATCH = 90
EXIT_CONTENT_TITLE_MISMATCH = 95
EXIT_GET_SPEC_LIST_ERROR = 100
EXIT_GET_SPECS_ERROR = 110
EXIT_INVALID_DRAFT_FILENAME = 120
EXIT_STATE_UNKNOWN = 130
EXIT_DRAFT_FOUND_IN_CSV = 140  

PATTERNS = {
    'CURRENT': r'^((?:[a-z0-9-]+)(?:-[a-z0-9-]+)*-\d+_\d+)\.html$',     
    'DRAFT': r'^[\w-]+-\d+_\d+-\d{2}\.html$',
    'IMPLEMENTERS': r'^((?:[a-z0-9-]+)(?:-[a-z0-9-]+)*-\d+_\d+)-ID(\d)\.html$',
    'ERRATA': r'^((?:[a-z0-9-]+)(?:-[a-z0-9-]+)*-\d+_\d+)-errata(\d+)\.html$',
    'FINAL': r'^((?:[a-z0-9-]+)(?:-[a-z0-9-]+)*-\d+_\d+)-final\.html$',
    'TITLE_TAG': r'<title>(.*?)</title>',
    'H1_TITLE': r'<h1(?:\s+id="title")?>(.*?)</h1>',
    'DRAFT_CONTENT': r'.*?\b(?:\d+\.\d+\s*[-–—]\s*)?[Dd]raft\s+(\d+).*',
    'ERRATA_CONTENT': r'(?i).*?(?:errata\s*set\s*(\d+)|\berrata.*?(\d+)).*',
    'FINAL_CONTENT': r'(?i)(?:<dd\s+class="(?:intended-)?status">\s*Final\s*</dd>|<td\s+class="header">\s*Final\s*</td>)',
    'IMPLEMENTERS_CONTENT': r'.*?\b\d+\.\d+\s*[-–—]\s*[Ii]mplementers?\s+[Dd]raft\s+(\d+).*',
    'ABSTRACT': r'(?:<h2[^>]*id="abstract"[^>]*>\s*<a[^>]*>Abstract</a>\s*</h2>|<h3>\s*Abstract\s*</h3>)',
    'INTRODUCTION': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?introduction")?[^>]*>(?:\d+\.?&nbsp;)?.*?Introduction(?:</a>)?\s*</(?:h[123])>)',
    'NORMATIVE_REFERENCES': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?normative-references(?:-\d+)?")?[^>]*>.*?Normative [Rr]eferences(?:</a>)?\s*</(?:h[123])>)',
    'INFORMATIVE_REFERENCES': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?informative-references")?[^>]*>.*?Informative [Rr]eferences(?:</a>)?\s*</(?:h[123])>)',
    'SECURITY': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?security-considerations")?[^>]*>(?:\d+\.?&nbsp;)?.*?Security [Cc]onsiderations(?:</a>)?\s*</(?:h[123])>)',
    'REFERENCES': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?references")?[^>]*>(?:\d+\.?&nbsp;)?.*?References(?:</a>)?\s*</(?:h[123])>)',
    'ACKNOWLEDGEMENTS': r'(?:<(?:h[123])[^>]*(?:id="(?:name-)?acknowledg[^"]*")?[^>]*>(?:(?:Annex|Appendix)\s+[A-Z]\s*(?:\([^)]*\))?\s*)?(?:\d+\.?&nbsp;)?.*?Acknowledge?ments?(?:</a>)?\s*</(?:h[123])>)',
    'REF': r'(?:<dt\s+id="([^"]+)">[^<]*</dt>\s*<dd>.*?<a\s+href="([^"]+)")|(?:<tr><td[^>]*><a\s+name="([^"]+)">\[([^]]+)\]</a></td>\s*<td[^>]*>.*?<a\s+href="([^"]+)")',
    'NOTICES': r'(?:<h3>Appendix C\.&nbsp;\s*Notices</h3>|<a href="#name-notices" class="section-name selfRef">Notices</a>|<h2[^>]*id="name-notices"[^>]*>\s*Notices\s*</h2>)',
    'COPYRIGHT': r'Copyright \(c\) (\d{4}) The OpenID Foundation',
    'AUTHORS_DIV': r'<dd class="authors?">(.*?)</dd>',
    'AUTHOR_DIV': r'<div class="author">\s*<div class="author-name">(.*?)</div>\s*<div class="org">(.*?)</div>\s*</div>',
    'AUTHORS_TABLE': r'<table width="99%" border="0" cellpadding="0" cellspacing="0">\s*<tbody>(.*?)</tbody>\s*</table>',
    'AUTHOR_TABLE_ROW': r'<tr><td class="author-text">&nbsp;</td>\s*<td class="author-text">(.*?)</td></tr>\s*<tr><td class="author-text">&nbsp;</td>\s*<td class="author-text">(.*?)</td></tr>',
    'PUBLISHED_DATE': r'<dd class="published">\s*<time datetime="(\d{4}-\d{2}-\d{2})"',
    'DOCUMENT_HISTORY': r'(?:<section id="appendix-[A-Z]">\s*<h2 id="name-document-history">\s*<a href="#appendix-[A-Z]" class="section-number selfRef">Appendix [A-Z]\. </a><a href="#name-document-history" class="section-name selfRef">Document [Hh]istory</a>\s*</h2>|<h1 id="rfc\.appendix\.[A-Z]">\s*<a href="#rfc\.appendix\.[A-Z]">Appendix [A-Z]\.</a>\s*<a href="#document-history" id="document-history">Document History</a>\s*</h1>|<h3>Appendix [A-Z]\.&nbsp;\s*Document History</h3>|<div id="document-history">\s*<h2 id="name-document-history">|<h1[^>]*id="[^"]*document-history"[^>]*>(?:(?:Appendix|Annex)\s+[A-Z]\s*(?:\([^)]*\))?\s*)?Document\s+History\s*</h1>)(.*?)(?:</section>|<h1|<h3|<div\s+id=)',
    'HEADER_DATE': r'<tr><td class="header">&nbsp;</td><td class="header">(\w+ \d{1,2}, \d{4})</td></tr>'
}


def filename_state(filename, debug=False):
    result = {"state": "UNKNOWN", "debug": {}}
    for state, pattern in PATTERNS.items():
        if state in ['CURRENT', 'DRAFT', 'IMPLEMENTERS', 'ERRATA', 'FINAL']:
            match = re.match(pattern, filename)
            if match:
                result["state"] = state
                if debug:
                    result["debug"][state] = {
                        "pattern": pattern,
                        "match": match.group()
                    }
                break
            elif debug:
                result["debug"][state] = {
                    "pattern": pattern,
                    "match": None
                }
    return result

def content_state(content, debug=False):
    result = {"state": "UNKNOWN", "debug": {}}
    
    title_tag_match = re.search(PATTERNS['TITLE_TAG'], content, re.DOTALL | re.IGNORECASE)
    h1_title_match = re.search(PATTERNS['H1_TITLE'], content, re.DOTALL | re.IGNORECASE)
    
    if debug:
        result["debug"]["TITLE_TAG"] = {
            "pattern": PATTERNS['TITLE_TAG'],
            "match": title_tag_match.group() if title_tag_match else None
        }
        result["debug"]["H1_TITLE"] = {
            "pattern": PATTERNS['H1_TITLE'],
            "match": h1_title_match.group() if h1_title_match else None
        }
    
    if title_tag_match and h1_title_match:
        title_content = title_tag_match.group(1)
        state_order = ['ERRATA', 'IMPLEMENTERS', 'DRAFT', 'FINAL']
        for state in state_order:
            pattern = PATTERNS[f'{state}_CONTENT']
            match = re.search(pattern, title_content if state != 'FINAL' else content, re.IGNORECASE | re.DOTALL)
            if match:
                result["state"] = state
                if debug:
                    result["debug"][f'{state}_CONTENT'] = {
                        "pattern": pattern,
                        "match": match.group()
                    }
                break

        # Detect DRAFT_ERRATA: title contains both errata and draft keywords
        if result["state"] == "ERRATA":
            draft_match = re.search(PATTERNS['DRAFT_CONTENT'], title_content, re.IGNORECASE | re.DOTALL)
            if draft_match:
                result["state"] = "DRAFT_ERRATA"
        
        if result["state"] == "UNKNOWN":
            result["state"] = "RELEASED"
        
        if debug:
            for state in state_order:
                pattern = PATTERNS[f'{state}_CONTENT']
                match = re.search(pattern, title_content if state != 'FINAL' else content, re.IGNORECASE | re.DOTALL)
                result["debug"][f'{state}_CONTENT'] = {
                    "pattern": pattern,
                    "match": match.group() if match else None
                }
    
    return result

def normalize_text(text):
    """Normalize text by removing extra whitespace, newlines and standardizing quotes"""
    text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
    return ' '.join(text.split())

def content_notices(content, debug=False):
    result = {
        "notices": False, 
        "copyright_year": None,
        "published_year": None,
        "years_match": False,
        "license_text_present": False,
        "debug": {}
    }
    
    # Key phrases to look for in the license text
    key_phrases = [
        "The OpenID Foundation (OIDF) grants to any Contributor, developer, implementer",
        "non-exclusive, royalty free, worldwide copyright license",
        "reproduce, prepare derivative works from, distribute, perform and display",
        "Implementers Draft, Final Specification, or Final Specification Incorporating Errata",
        "Corrections solely for the purposes of",
        "(i) developing specifications, and (ii)",
        "implementing Implementers Drafts, Final Specifications",
        "based on such documents",
        "attribution be made to the OIDF as the source of the material",
        "but that such attribution does not indicate an endorsement by the OIDF",
        "technology described in this specification was made available from contributions",
        "from various sources",
        "members of the OpenID Foundation and others",
        "OpenID Foundation has taken steps to help ensure that the technology",
        "available for distribution",
        "takes no position regarding the validity or scope of any intellectual property",
        "the extent to which any license under such rights might or might not be available",
        "made any independent effort to identify any such rights",
        "The OpenID Foundation and the contributors to this specification make no",
        "and hereby expressly disclaim any",
        "warranties (express, implied, or otherwise)",
        "including implied warranties of",
        "warranties of merchantability, non-infringement, fitness for a particular purpose",
        "or title",
        "related to this specification",
        "entire risk as to implementing this specification is assumed by the implementer",
        "The OpenID Intellectual Property Rights policy",
        "found at openid.net",
        "requires contributors to offer a patent promise",
        "not to assert certain patent claims against other contributors",
        "against other contributors and against implementers",
        "OpenID invites any interested party to bring to its attention",
        "copyrights, patents, patent applications, or other proprietary rights",
        "may cover technology that may be required to practice this specification"
    ]
    
    # Check for notices, copyright, and published date
    for notice_type in ['NOTICES', 'COPYRIGHT', 'PUBLISHED_DATE']:
        pattern = PATTERNS[notice_type]
        match = re.search(pattern, content)
        
        if notice_type == 'NOTICES':
            result["notices"] = bool(match)
        elif notice_type == 'COPYRIGHT' and match:
            result["copyright_year"] = int(match.group(1))
        elif notice_type == 'PUBLISHED_DATE' and match:
            published_date = match.group(1)  # Format: YYYY-MM-DD
            result["published_year"] = int(published_date.split('-')[0])
        
        if debug:
            result["debug"][notice_type] = {
                "pattern": pattern,
                "match": match.group() if match else None
            }
    
    # Check for the license text
    soup = BeautifulSoup(content, 'html.parser')
    document_text = normalize_text(' '.join(p.get_text() for p in soup.find_all('p')))
    
    missing_phrases = []
    for phrase in key_phrases:
        normalized_phrase = normalize_text(phrase)
        if normalized_phrase not in document_text:
            missing_phrases.append(phrase)
    
    result["license_text_present"] = len(missing_phrases) == 0
    
    if debug:
        result["debug"]["LICENSE_TEXT"] = {
            "missing_phrases": missing_phrases,
            "document_text_excerpt": document_text[:500] + "..." if len(document_text) > 500 else document_text
        }
    
    # Check if both years are present and match
    if result["copyright_year"] and result["published_year"]:
        result["years_match"] = result["copyright_year"] == result["published_year"]
        
        if debug:
            result["debug"]["YEARS_MATCH"] = {
                "copyright_year": result["copyright_year"],
                "published_year": result["published_year"],
                "match": result["years_match"]
            }
    
    return result 

def content_date(content, compare_date=None, debug=False):
    result = {
        "date": "Date not found",
        "copyright_date": "Copyright date not found",
        "years_match": False,
        "error": None,
        "debug": {}
    }
    content_date = None
    copyright_date = None
    
    # Check for published date
    for date_type in ['PUBLISHED_DATE', 'HEADER_DATE']:
        pattern = PATTERNS[date_type]
        match = re.search(pattern, content)
        if match:
            if date_type == 'PUBLISHED_DATE':
                content_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            else:
                content_date = datetime.strptime(match.group(1), "%B %d, %Y").date()
            result["date"] = content_date.isoformat()
            if debug:
                result["debug"][date_type] = {
                    "pattern": pattern,
                    "match": match.group()
                }
            break
        elif debug:
            result["debug"][date_type] = {
                "pattern": pattern,
                "match": None
            }
    
    # Check for copyright date
    copyright_pattern = PATTERNS['COPYRIGHT']
    copyright_match = re.search(copyright_pattern, content)
    if copyright_match:
        copyright_date = copyright_match.group(1)
        result["copyright_date"] = copyright_date
        if debug:
            result["debug"]["COPYRIGHT"] = {
                "pattern": copyright_pattern,
                "match": copyright_match.group()
            }
    elif debug:
        result["debug"]["COPYRIGHT"] = {
            "pattern": copyright_pattern,
            "match": None
        }
    
    # Validate that the years match
    if content_date and copyright_date:
        published_year = str(content_date.year)
        result["years_match"] = published_year == copyright_date
        if not result["years_match"]:
            result["error"] = f"Copyright year ({copyright_date}) must match published year ({published_year})"
    
    if compare_date and content_date:
        compare_date = datetime.strptime(compare_date, "%Y-%m-%d").date()
        days_difference = abs((compare_date - content_date).days)
        result["comparison"] = {
            "compare_date": compare_date.isoformat(),
            "days_difference": days_difference,
            "status": "ahead" if compare_date > content_date else "behind" if compare_date < content_date else "same"
        }
    
    return result, EXIT_CONTENT_DATE_ERROR if not result["years_match"] else EXIT_SUCCESS


def content_title(content, debug=False):
    """
    Compare the title tag content with the h1 title content.
    Returns a dictionary with match result and optional debug info.
    """
    result = {
        "match": False,
        "title_tag": None,
        "h1_title": None,
        "debug": {} if debug else None
    }
    
    # Find title tag content
    title_tag_match = re.search(PATTERNS['TITLE_TAG'], content, re.DOTALL | re.IGNORECASE)
    h1_title_match = re.search(PATTERNS['H1_TITLE'], content, re.DOTALL | re.IGNORECASE)
    
    if title_tag_match and h1_title_match:
        # Extract and clean the titles
        title_tag_content = title_tag_match.group(1).strip()
        h1_title_content = h1_title_match.group(1).strip()
        
        # Store the found titles
        result["title_tag"] = title_tag_content
        result["h1_title"] = h1_title_content
        
        # Compare titles (case-insensitive)
        result["match"] = title_tag_content.lower() == h1_title_content.lower()
        
        if debug:
            result["debug"] = {
                "TITLE_TAG": {
                    "pattern": PATTERNS['TITLE_TAG'],
                    "match": title_tag_match.group()
                },
                "H1_TITLE": {
                    "pattern": PATTERNS['H1_TITLE'],
                    "match": h1_title_match.group()
                }
            }
    
    return result

def content_struct(content, debug=False):
    # Define which sections are required vs optional
    required_sections = ['ABSTRACT', 'INTRODUCTION', 'REFERENCES', 'NORMATIVE_REFERENCES', 
                        'ACKNOWLEDGEMENTS', 'SECURITY']
    optional_sections = ['INFORMATIVE_REFERENCES']
    
    result = {
        "structure": {},
        "warnings": [],
        "missing_required": [],
        "missing_optional": [],
        "debug": {}
    }
    
    # Check all sections (both required and optional)
    all_sections = required_sections + optional_sections
    for section in all_sections:
        pattern = PATTERNS[section]
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        result["structure"][section] = bool(match)
        
        # Track missing sections
        if not match:
            if section in required_sections:
                result["missing_required"].append(section)
            else:
                result["missing_optional"].append(section)
                result["warnings"].append(f"Optional section {section} is missing")
        
        if debug:
            result["debug"][section] = {
                "pattern": pattern,
                "match": match.group() if match else None,
                "required": section in required_sections
            }
    
    return result

def check_url_accessibility(url, debug=False):
    if os.environ.get("MOCK_URL_CHECK"):
        if debug:
            print(f"  Mocked URL check (accessible): {url}")
        return True
    if debug:
        print(f"  Checking URL: {url}")
    try:
        response = requests.head(url, allow_redirects=True, timeout=30)
        if response.status_code == 200:
            if debug:
                print(f"    Status: Accessible (HEAD {response.status_code})")
            return True
        # HEAD failed — retry with GET (some servers reject HEAD)
        print(f"    HEAD returned {response.status_code}, retrying with GET for {url}")
        response = requests.get(url, allow_redirects=True, timeout=30, stream=True)
        response.close()
        is_accessible = response.status_code == 200
        if is_accessible:
            print(f"    GET returned {response.status_code} (OK) for {url}")
        else:
            print(f"    GET returned {response.status_code} (FAIL) for {url}")
        return is_accessible
    except requests.RequestException as e:
        print(f"    Error checking {url} - {str(e)}")
        return False

def content_ref(content, check_url=False, debug=False):
    pattern = PATTERNS['REF']
    matches = re.findall(pattern, content, re.DOTALL)
    references = []
    debug_info = []
    all_accessible = True
    
    for match in matches:
        if match[0]:  # <dt>/<dd> format
            id_value, href = match[0], match[1]
        else:  # table format
            id_value, href = match[2], match[4]
        
        if check_url:
            is_accessible = check_url_accessibility(href, debug)
            all_accessible &= is_accessible
            references.append((id_value, href, is_accessible))
        else:
            references.append((id_value, href))
        
        if debug:
            debug_info.append(match)
    
    return {
        "references": references,
        "all_accessible": all_accessible if check_url else None,
        "debug": {
            "pattern": pattern,
            "matches": debug_info
        } if debug else None
    }


def content_authors(content, debug=False):
    result = {"authors": [], "debug": {}}
    soup = BeautifulSoup(content, 'html.parser')
    
    # Check for authors in div format (class="authors" or class="author")
    authors_div = soup.find('dd', class_='authors') or soup.find('dd', class_='author')
    if authors_div:
        author_divs = authors_div.find_all('div', class_='author')
        for div in author_divs:
            name_div = div.find('div', class_='author-name')
            org_div = div.find('div', class_='org')
            if name_div and org_div:
                name = name_div.text.strip()
                org = org_div.text.strip()
                if name or org:
                    result["authors"].append({"name": name, "organization": org})
    
    # If no authors found in div format, check for table format
    if not result["authors"]:
        author_table = soup.find('table', {'width': '99%', 'border': '0', 'cellpadding': '0', 'cellspacing': '0'})
        if author_table:
            rows = author_table.find_all('tr')
            for i in range(0, len(rows), 5):  # Each author has 5 rows
                if i + 1 < len(rows):
                    name_row = rows[i]
                    org_row = rows[i+1]
                    
                    name_cells = name_row.find_all('td', class_='author-text')
                    org_cells = org_row.find_all('td', class_='author-text')

                    if name_cells and org_cells:
                        name = name_cells[-1].text.strip()
                        org = org_cells[-1].text.strip()
                        if name or org:
                            result["authors"].append({"name": name, "organization": org})
    
    if debug:
        result["debug"]["AUTHORS_DIV"] = re.search(PATTERNS['AUTHORS_DIV'], content)
        result["debug"]["AUTHOR_DIV"] = re.findall(PATTERNS['AUTHOR_DIV'], content)
        result["debug"]["AUTHORS_TABLE"] = re.search(PATTERNS['AUTHORS_TABLE'], content)
        result["debug"]["AUTHOR_TABLE_ROW"] = re.findall(PATTERNS['AUTHOR_TABLE_ROW'], content)
    
    return result

def content_history(content, debug=False):
    result = {"history_present": False, "history": None, "debug": {}}
    
    # Find the Document History section
    history_match = re.search(PATTERNS['DOCUMENT_HISTORY'], content, re.DOTALL | re.IGNORECASE)
    
    if history_match:
        result["history_present"] = True
        history_content = history_match.group(1)
        
        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(history_content, 'html.parser')
        
        # Extract the history entries
        history_entries = []
        version = None
        for entry in soup.find_all(['p', 'li', 'ul']):
            if entry.name == 'ul':
                # For nested lists, get all list items
                items = entry.find_all('li')
                for item in items:
                    text = item.get_text(strip=True)
                    if text and not text.startswith('['):
                        history_entries.append(f"{version}: {text}" if version else text)
            else:
                text = entry.get_text(strip=True)
                if text and not text.startswith('['):
                    if re.match(r'^-?\d+', text):  # This looks like a version number
                        version = text
                        history_entries.append(text)
                    else:
                        history_entries.append(f"{version}: {text}" if version else text)
        
        result["history"] = history_entries
    
    if debug:
        result["debug"]["DOCUMENT_HISTORY"] = {
            "pattern": PATTERNS['DOCUMENT_HISTORY'],
            "match": history_match.group() if history_match else None
        }
    
    return result

# ---------------------------------------------------------------------------
# Additional content checks
# ---------------------------------------------------------------------------

_IETF_IPR_PHRASES = [
    "IETF Trust",
    "BCP 78",
    "BCP 79",
    "subject to the rights, licenses and restrictions contained in BCP",
]

_DRAFT_DISCLAIMER = "This document is not an OIDF International Standard"


def history_references_draft(history_result, draft_num):
    """Check if the history section references the given draft number."""
    if not history_result.get("history"):
        return True  # No history entries to check
    draft_int = int(draft_num)
    history_text = " ".join(str(e) for e in history_result["history"])
    return f"-{draft_int:02d}" in history_text or f"-{draft_int}" in history_text


def check_ietf_ipr(content):
    """Check if content contains IETF Trust IPR boilerplate. Returns list of found phrases."""
    return [phrase for phrase in _IETF_IPR_PHRASES if phrase in content]


def check_draft_disclaimer(content):
    """Check if content contains the draft disclaimer text. Returns True if found."""
    return _DRAFT_DISCLAIMER in content


def check_noncanonical_refs(content):
    """Find references using openid.github.io or openid.bitbucket.io instead of openid.net/specs/."""
    urls = re.findall(r'href="(https?://openid\.(?:github|bitbucket)\.io/[^"]*)"', content)
    return urls


def check_md_includes(md_content):
    """Check if markdown content references external files via include directives."""
    return bool(
        re.search(r'<\{\{[^}]+\}\}', md_content)
        or re.search(r'!include\b', md_content, re.IGNORECASE)
        or re.search(r'\{%\s*include', md_content)
        or re.search(r'^#include\b', md_content, re.MULTILINE)
    )


def get_spec_list_csv():
    url = 'https://openid.net/specs/'
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.find_all('tr')
    
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    csv_writer.writerow(['Filename', 'Date', 'Size'])
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            filename = cols[1].text.strip()
            date = cols[3].text.strip()
            size = cols[2].text.strip()
            csv_writer.writerow([filename, date, size])
    
    return csv_output.getvalue()

def get_specs(directory):
    url = "https://openid.net/specs/"
    
    os.makedirs(directory, exist_ok=True)
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    base_url = "https://openid.net/specs/"
    
    downloaded_files = []
    for link in soup.find_all('a', href=True):
        file_url = link['href']
        
        if file_url.endswith('.html'):
            file_name = file_url.split('/')[-1]
            file_path = os.path.join(directory, file_name)
            download_link = base_url + file_url
            print(f"Downloading {file_name}...")
            file_response = requests.get(download_link)
            
            last_modified_str = file_response.headers.get('Last-Modified')
            if last_modified_str:
                last_modified_time = datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S GMT")
                modified_timestamp = time.mktime(last_modified_time.timetuple())
            else:
                modified_timestamp = time.time()
            
            with open(file_path, 'wb') as f:
                f.write(file_response.content)
            os.utime(file_path, (modified_timestamp, modified_timestamp))
            downloaded_files.append(f"{file_name} (Last modified: {last_modified_str if last_modified_str else 'Unknown'})")
    
    return downloaded_files

def analyze_file(options, filename=None):
    results = {}
    debug = '-debug' in options
    check_url = '-check-url' in options
    compare_date = None
    list_history = '-list' in options

    if '-date' in options:
        date_index = options.index('-date')
        if date_index + 1 < len(options):
            compare_date = options[date_index + 1]

    # Handle -get-spec-list-csv option
    if '-get-spec-list-csv' in options:
        output_file = "spec-list.csv"
        if '-output' in options:
            output_index = options.index('-output')
            if output_index + 1 >= len(options) or options[output_index + 1].startswith('-'):
                print("Error: -output option requires a filename.")
                return results, EXIT_INVALID_USAGE
            output_file = options[output_index + 1]

        try:
            csv_data = get_spec_list_csv()
            if csv_data:
                with open(output_file, 'w', newline='') as f:
                    f.write(csv_data)
                results['Spec List CSV'] = f"CSV data written to {output_file}"
                return results, EXIT_SUCCESS
            else:
                print("Error: Failed to retrieve spec list CSV data.")
                return results, EXIT_GET_SPEC_LIST_ERROR
        except IOError as e:
            print(f"Error writing to file {output_file}: {e}")
            return results, EXIT_CSV_WRITING_ERROR
        except Exception as e:
            print(f"Unexpected error in get_spec_list_csv: {e}")
            return results, EXIT_GET_SPEC_LIST_ERROR

    # Handle -get-specs option
    if '-get-specs' in options:
        if '-directory' not in options:
            print("Error: -get-specs requires -directory option to specify the download directory.")
            return results, EXIT_INVALID_USAGE

        directory_index = options.index('-directory')
        if directory_index + 1 >= len(options) or options[directory_index + 1].startswith('-'):
            print("Error: -directory option requires a valid directory path.")
            return results, EXIT_INVALID_USAGE

        directory = options[directory_index + 1]
        try:
            downloaded_files = get_specs(directory)
            if downloaded_files:
                results['Downloaded Specs'] = {
                    "directory": directory,
                    "files": downloaded_files
                }
                return results, EXIT_SUCCESS
            else:
                print("Error: Failed to download specification files.")
                return results, EXIT_GET_SPECS_ERROR
        except Exception as e:
            print(f"Error downloading specs: {e}")
            return results, EXIT_GET_SPECS_ERROR

    # Handle filename state analysis
    if filename and '-filename-state' in options:
        filename_state_result = filename_state(os.path.basename(filename), debug)
        results['Filename State'] = filename_state_result
        if filename_state_result['state'] == "UNKNOWN":
            return results, EXIT_FILENAME_STATE_ERROR

    # Handle file content analysis options
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            if '-content-state' in options:
                content_state_result = content_state(content, debug)
                results['Content State'] = content_state_result
                if content_state_result['state'] == "UNKNOWN":
                    return results, EXIT_CONTENT_STATE_ERROR

            if '-content-date' in options:
                date_result, date_exit_code = content_date(content, compare_date, debug)
                results['Content Date'] = date_result
                if not date_result['years_match']:
                    print(f"Error: {date_result['error']}")
                    return results, date_exit_code

            if '-content-ref' in options:
                content_ref_result = content_ref(content, check_url, debug)
                results['References'] = content_ref_result
                if check_url and not content_ref_result.get('all_accessible', True):
                    return results, EXIT_CONTENT_REF_ERROR

            if '-content-notices' in options:
                content_notices_result = content_notices(content, debug)
                results['Notices'] = content_notices_result
                if not content_notices_result['notices'] or not content_notices_result['license_text_present']:
                    if not content_notices_result['notices']:
                        print("Error: Required notices section is missing.")
                    if not content_notices_result['license_text_present']:
                        print("Error: Required license text is missing or incomplete.")
                        if debug and 'LICENSE_TEXT' in content_notices_result['debug']:
                            print("Missing phrases:")
                            for phrase in content_notices_result['debug']['LICENSE_TEXT']['missing_phrases']:
                                print(f"  - {phrase}")
                    return results, EXIT_CONTENT_NOTICES_ERROR

            
            if '-content-struct' in options:
                content_struct_result = content_struct(content, debug)
                results['Document Structure'] = content_struct_result
                # Only check required sections for errors
                required_sections = ['ABSTRACT', 'INTRODUCTION', 'REFERENCES', 'NORMATIVE_REFERENCES', 
                                  'ACKNOWLEDGEMENTS', 'SECURITY']
                required_sections_present = all(content_struct_result['structure'][section] 
                                             for section in required_sections)
                if not required_sections_present:
                    return results, EXIT_CONTENT_STRUCT_ERROR


            if '-content-authors' in options:
                content_authors_result = content_authors(content, debug)
                results['Authors'] = content_authors_result
                if not content_authors_result['authors']:
                    return results, EXIT_CONTENT_AUTHORS_ERROR

            if '-content-history' in options:
                history_result = content_history(content, debug)
                results['Document History'] = history_result
                if not history_result['history_present']:
                    return results, EXIT_CONTENT_HISTORY_ERROR

            if '-content-title' in options:
                content_title_result = content_title(content, debug)
                results['Content Title'] = content_title_result
                if not content_title_result['match']:
                    return results, EXIT_CONTENT_TITLE_MISMATCH

            if '-content-filename-match' in options:
                match_result = content_filename_match(content, os.path.basename(filename), debug)
                results['Filename Match'] = match_result
                if not match_result['match']:
                    return results, EXIT_CONTENT_FILENAME_MISMATCH

        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return results, EXIT_FILE_NOT_FOUND
        except PermissionError:
            print(f"Error: Permission denied when accessing file '{filename}'.")
            return results, EXIT_PERMISSION_ERROR
        except Exception as e:
            print(f"Error reading or processing file '{filename}': {str(e)}")
            return results, EXIT_FILE_PROCESSING_ERROR

    return results, EXIT_SUCCESS
    
def content_filename_match(content, filename, debug=False):
    result = {"match": False}
    filename_type = None
    content_type = None
    filename_number = None
    content_number = None
    
    # Check filename
    for file_type, pattern in PATTERNS.items():
        if file_type in ['CURRENT', 'DRAFT', 'IMPLEMENTERS', 'ERRATA', 'FINAL']:
            match = re.match(pattern, filename)
            if match:
                filename_type = file_type
                if file_type == 'CURRENT':
                    filename_number = match.group(1).split('-')[-1].replace('_', '.')
                elif file_type == 'DRAFT':
                    # DRAFT pattern has no capture groups; extract trailing number before .html
                    draft_num_match = re.search(r'-(\d{1,2})\.html$', filename)
                    if draft_num_match:
                        filename_number = draft_num_match.group(1)
                elif file_type != 'FINAL':
                    filename_number = match.group(2)
                break

    # Check content
    title_match = re.search(PATTERNS['TITLE_TAG'], content, re.DOTALL | re.IGNORECASE)
    if title_match:
        title_content = title_match.group(1)
        for content_type_check in ['ERRATA', 'IMPLEMENTERS', 'DRAFT']:
            pattern = PATTERNS[f'{content_type_check}_CONTENT']
            match = re.search(pattern, title_content, re.IGNORECASE)
            if match:
                content_type = content_type_check
                content_number = match.group(1) or match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)
                break
        
        if not content_type:
            final_pattern = PATTERNS['FINAL_CONTENT']
            if re.search(final_pattern, content, re.IGNORECASE | re.DOTALL):
                content_type = 'FINAL'
        
        if not content_type:
            current_pattern = r'(?i).*?(\d+\.\d+).*'
            match = re.search(current_pattern, title_content)
            if match:
                content_type = 'CURRENT'
                content_number = match.group(1)
    
    # Check for match
    # IMPLEMENTERS filenames (-ID2.html) keep the original draft title,
    # so accept IMPLEMENTERS filename with DRAFT content (numbers will differ
    # since ID number and draft number are independent).
    if filename_type == 'IMPLEMENTERS' and content_type == 'DRAFT':
        result["match"] = True
    elif filename_type == content_type:
        if filename_type == 'FINAL':
            result["match"] = True
        elif filename_type == 'CURRENT':
            result["match"] = filename_number == content_number
        elif filename_number and content_number:
            result["match"] = filename_number == content_number
    
    if debug:
        result["debug"] = {
            "Filename Type": filename_type,
            "Content Type": content_type,
            "Filename Number": filename_number,
            "Content Number": content_number
        }
    
    return result

def process_draft_file(filename, debug=False):
    if debug:
        print(f"Debug: Processing file {filename}")
    
    # Extract just the filename without the directory path
    base_filename = os.path.basename(filename)
    
    if debug:
        print(f"Debug: Base filename is {base_filename}")
    
    if not re.match(PATTERNS['DRAFT'], base_filename):
        print(f"Error: '{base_filename}' does not match the required file naming pattern for drafts.")
        return None, EXIT_INVALID_DRAFT_FILENAME

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()

        content_state_result = content_state(content)
        state = content_state_result['state']
        if debug:
            print(f"Debug: Content state is {state}")

        base_name = re.sub(r'-\d+\.html$', '', base_filename)
        if debug:
            print(f"Debug: Base name is {base_name}")
        published_name = f"{base_name}.html"
        if debug:
            print(f"Debug: Published name is {published_name}")
        
        if state == "DRAFT":
            return f"Existing: {base_filename}\nPublished: {published_name}", EXIT_SUCCESS
        elif state == "FINAL":
            final_name = f"{base_name}-final.html"
            if debug:
                print(f"Debug: Final name is {final_name}")
            return f"Published: {published_name}\nFinal: {final_name}", EXIT_SUCCESS
        elif state == "ERRATA":
            m = re.search(PATTERNS['ERRATA_CONTENT'], content)
            errata_number = m.group(1) or m.group(2)
            errata_name = f"{base_name}-errata{errata_number}.html"
            if debug:
                print(f"Debug: Errata name is {errata_name}")
            return f"Published: {published_name}\nErrata: {errata_name}", EXIT_SUCCESS
        elif state == "UNKNOWN":
            return "State: Unknown", EXIT_STATE_UNKNOWN
        else:
            return f"Unexpected state: {state}", EXIT_CONTENT_STATE_ERROR

    except FileNotFoundError:
        return f"Error: File '{filename}' not found.", EXIT_FILE_NOT_FOUND
    except PermissionError:
        return f"Error: Permission denied when accessing file '{filename}'.", EXIT_PERMISSION_ERROR
    except Exception as e:
        return f"Error processing file '{filename}': {str(e)}", EXIT_FILE_PROCESSING_ERROR

def check_draft_in_csv(draft_filename, csv_file='spec-list.csv'):
    # Extract just the filename without the directory path
    base_filename = os.path.basename(draft_filename)
    
    valid_patterns = ['DRAFT', 'FINAL', 'IMPLEMENTERS', 'ERRATA']
    if not any(re.match(PATTERNS[p], base_filename) for p in valid_patterns):
        print(f"Error: '{base_filename}' does not match any recognised filename pattern.")
        return EXIT_INVALID_DRAFT_FILENAME

    try:
        with open(csv_file, 'r', newline='') as f:
            csv_reader = csv.reader(f)
            next(csv_reader)  # Skip header row
            for row in csv_reader:
                if row[0] == base_filename:
                    print(f"Error: Draft '{base_filename}' found in CSV file '{csv_file}'.")
                    return EXIT_DRAFT_FOUND_IN_CSV
        print(f"Draft '{base_filename}' not found in CSV file '{csv_file}'.")
        return EXIT_SUCCESS
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found.")
        return EXIT_FILE_NOT_FOUND
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        return EXIT_FILE_PROCESSING_ERROR

def main():
    # Define valid options
    VALID_OPTIONS = {
        '-filename-state',
        '-content-state',
        '-content-date',
        '-date',
        '-content-ref',
        '-check-url',
        '-content-notices',
        '-content-struct',
        '-content-authors',
        '-content-history',
        '-content-title',
        '-content-filename-match',
        '-process-draft',
        '-check-draft',
        '-list',
        '-get-spec-list-csv',
        '-output',
        '-get-specs',
        '-directory',
        '-debug',
        '-csv'
    }

    def show_usage():
        print("Usage: python cli-tool.py [OPTIONS] [FILENAME]")
        print("Options:")
        print("  -filename-state   Analyze filename state")
        print("  -content-state    Analyze content state")
        print("  -content-date     Extract content date")
        print("  -date YYYY-MM-DD  Compare with a specific date (use with -content-date)")
        print("  -content-ref      Extract references")
        print("  -check-url        Check accessibility of URLs in references")
        print("  -content-notices  Check notices and copyright")
        print("  -content-struct   Check document structure")
        print("  -content-authors  Extract author information")
        print("  -content-history  Check for document history")
        print("  -content-title    Compare title in documents")
        print("  -content-filename-match  Check if content type and number match filename")
        print("  -process-draft FILE  Process a draft file and output file names")
        print("  -check-draft FILE Check if file already exists in spec-list.csv")
        print("  -list             List full document history (use with -content-history)")
        print("  -get-spec-list-csv Retrieve the spec list as CSV (default output: spec-list.csv)")
        print("  -output FILE      Specify custom output file for -get-spec-list-csv")
        print("  -get-specs        Download all specification files")
        print("  -directory DIR    Specify directory for downloaded specs (use with -get-specs)")
        print("  -debug            Show debug information (matched patterns)")
        print("  -csv FILE         Specify CSV file for -check-draft")
        sys.exit(EXIT_INVALID_USAGE)

    if len(sys.argv) < 2:
        show_usage()

    # Check for unknown options
    options = [arg for arg in sys.argv[1:] if arg.startswith('-')]
    for opt in options:
        if opt not in VALID_OPTIONS:
            print(f"Error: Unknown option '{opt}'")
            show_usage()

    options = sys.argv[1:]
    filename = next((arg for arg in reversed(sys.argv) if not arg.startswith('-')), None)

    debug = '-debug' in options
    
    if '-process-draft' in options:
        draft_index = options.index('-process-draft')
        if draft_index + 1 >= len(options):
            print("Error: -process-draft option requires a filename.")
            sys.exit(EXIT_INVALID_USAGE)
        draft_filename = options[draft_index + 1]
        result, exit_code = process_draft_file(draft_filename, debug)
        print(result)
        sys.exit(exit_code)

    if '-check-draft' in options:
        draft_index = options.index('-check-draft')
        if draft_index + 1 >= len(options):
            print("Error: -check-draft option requires a filename.")
            sys.exit(EXIT_INVALID_USAGE)
        draft_filename = options[draft_index + 1]
        
        csv_file = 'spec-list.csv'
        if '-csv' in options:
            csv_index = options.index('-csv')
            if csv_index + 1 >= len(options):
                print("Error: -csv option requires a filename.")
                sys.exit(EXIT_INVALID_USAGE)
            csv_file = options[csv_index + 1]
        
        exit_code = check_draft_in_csv(draft_filename, csv_file)
        sys.exit(exit_code)


    try:
        results, exit_code = analyze_file(options, filename)
 
        if results:
            for key, value in results.items():
                print(f"{key}:")
                if isinstance(value, str):
                    print(f"  {value}")
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k != "debug":
                            print(f"  {k}: {v}")
                        elif debug:
                            print("  Debug Information:")
                            for debug_key, debug_value in v.items():
                                print(f"    {debug_key}:")
                                if isinstance(debug_value, dict):
                                    # Print each key-value pair in the debug dictionary
                                    for detail_key, detail_value in debug_value.items():
                                        print(f"      {detail_key}: {detail_value}")
                                elif isinstance(debug_value, list):
                                    for i, match in enumerate(debug_value, 1):
                                        print(f"      Match {i}: {match}")
                                else:
                                    print(f"      {debug_value}")
                elif isinstance(value, list):
                    for item in value:
                        print(f"  {item}")

        if exit_code != EXIT_SUCCESS:
            error_messages = {
                EXIT_INVALID_USAGE: "Invalid usage of the script.",
                EXIT_FILE_NOT_FOUND: "File not found.",
                EXIT_FILE_PROCESSING_ERROR: "Error processing the file.",
                EXIT_CSV_WRITING_ERROR: "Error writing CSV file.",
                EXIT_NETWORK_ERROR: "Network error occurred.",
                EXIT_PERMISSION_ERROR: "Permission error.",
                EXIT_FILENAME_STATE_ERROR: "Error in filename state analysis.",
                EXIT_CONTENT_STATE_ERROR: "Error in content state analysis.",
                EXIT_CONTENT_DATE_ERROR: "Error in content date analysis.",
                EXIT_CONTENT_REF_ERROR: "Error in content reference analysis.",
                EXIT_CONTENT_NOTICES_ERROR: "Error in content notices analysis.",
                EXIT_CONTENT_STRUCT_ERROR: "Error in document structure analysis.",
                EXIT_CONTENT_AUTHORS_ERROR: "Error in content authors analysis.",
                EXIT_CONTENT_HISTORY_ERROR: "Error in document history analysis.",
                EXIT_CONTENT_FILENAME_MISMATCH: "Content does not match filename.",
                EXIT_GET_SPEC_LIST_ERROR: "Error retrieving spec list CSV.",
                EXIT_GET_SPECS_ERROR: "Error downloading specification files.",
                EXIT_INVALID_DRAFT_FILENAME: "Invalid draft filename.",
                EXIT_STATE_UNKNOWN: "Unknown state in draft processing.",
                EXIT_CONTENT_TITLE_MISMATCH: "Title tags don't match"
            }
            error_message = error_messages.get(exit_code, "An unknown error occurred.")
            print(f"Error: {error_message}")
            print(f"Exiting with status code: {exit_code}")
            sys.exit(exit_code)

    except requests.RequestException as e:
        print(f"Network error occurred: {str(e)}")
        sys.exit(EXIT_NETWORK_ERROR)
    except IOError as e:
        print(f"I/O error occurred: {str(e)}")
        sys.exit(EXIT_PERMISSION_ERROR)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(EXIT_FILE_PROCESSING_ERROR)

    print("Analysis completed successfully.")
    sys.exit(EXIT_SUCCESS)

if __name__ == "__main__":
    main()