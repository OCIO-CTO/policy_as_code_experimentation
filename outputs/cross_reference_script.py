import xmltodict
import json
import re

# Load source XML
with open('title-7.xml', 'r', encoding='utf-8', errors='replace') as f:
    xml_content = f.read()
policy_dict = xmltodict.parse(xml_content)

# Load extracted rules
with open('outputs/9-2-output.json', 'r', encoding='utf-8') as f:
    extracted_rules = json.load(f)

# Helper: Get all paragraphs from a section
def get_section_paragraphs(section):
    paragraphs = []
    if 'P' in section:
        ps = section['P']
        if isinstance(ps, str):
            paragraphs.append(ps.strip())
        elif isinstance(ps, list):
            for p in ps:
                if isinstance(p, str):
                    paragraphs.append(p.strip())
                elif isinstance(p, dict):
                    text = p.get('#text', '')
                    if text:
                        paragraphs.append(text.strip())
    return paragraphs

# Get all sections
part = policy_dict.get('DIV5', {})
div8_raw = part.get('DIV8', None)
if isinstance(div8_raw, list):
    sections = div8_raw
elif isinstance(div8_raw, dict):
    sections = [div8_raw]
else:
    sections = []

# Build section lookup by citation or number
section_lookup = {}
for section in sections:
    meta = section.get('hierarchy_metadata', None)
    citation = None
    if isinstance(meta, str):
        try:
            meta_dict = json.loads(meta)
            citation = meta_dict.get('citation', None)
        except Exception:
            citation = None
    elif isinstance(meta, dict):
        citation = meta.get('citation', None)
    if not citation:
        citation = section.get('@N', section.get('HEAD', 'Unknown'))
    section_lookup[citation] = section

# Cross-reference each rule
cross_ref_results = []
for rule in extracted_rules:
    citation = rule.get('metadata', {}).get('citation') if 'metadata' in rule else None
    explanation = rule.get('explanation', '')
    # Try to extract section number from explanation if citation missing
    if not citation:
        m = re.search(r'section ([^\.]+)', explanation)
        if m:
            citation = m.group(1)
    section = section_lookup.get(citation)
    para_match = None
    if section:
        paragraphs = get_section_paragraphs(section)
        # Try to match rule text to a paragraph
        rule_text = rule.get('text', '').strip() if 'text' in rule else ''
        for para in paragraphs:
            if rule_text and rule_text in para:
                para_match = para
                break
    cross_ref_results.append({
        'rule_id': rule.get('id', None),
        'citation': citation,
        'rule_text': rule.get('text', None),
        'matched_paragraph': para_match,
        'match': bool(para_match)
    })

# Output summary
num_total = len(extracted_rules)
num_matched = sum(1 for r in cross_ref_results if r['match'])
num_missing_text = sum(1 for r in cross_ref_results if not r['rule_text'])
num_unmatched = num_total - num_matched

with open('outputs/cross_reference_report.md', 'a', encoding='utf-8') as f:
    f.write(f"\n## Summary\n")
    f.write(f"Total rules extracted: {num_total}\n")
    f.write(f"Rules with regulatory text: {num_total - num_missing_text}\n")
    f.write(f"Rules matched to XML paragraphs: {num_matched}\n")
    f.write(f"Rules missing regulatory text: {num_missing_text}\n")
    f.write(f"Rules not matched to XML paragraphs: {num_unmatched}\n\n")
    f.write("| Rule ID | Citation | Has Text | Matched Paragraph |\n")
    f.write("|---------|----------|----------|-------------------|\n")
    for r in cross_ref_results:
        f.write(f"| {r['rule_id']} | {r['citation']} | {'Yes' if r['rule_text'] else 'No'} | {'Yes' if r['match'] else 'No'} |\n")
    f.write("\nRecommendations:\n")
    if num_missing_text > 0:
        f.write("- Some rules are missing regulatory text. Review extraction logic to ensure all rules include the full regulatory text.\n")
    if num_unmatched > 0:
        f.write("- Some rules could not be matched to XML paragraphs. Check for citation or text mismatches.\n")
    if num_missing_text == 0 and num_unmatched == 0:
        f.write("- All rules are complete and accurately matched to the source XML.\n")
