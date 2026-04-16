#!/usr/bin/env python3
"""Generate EoS Report PDF.html from index.html as the source of truth."""

import csv
import re
from bs4 import BeautifulSoup

# ── 1. LOAD SOURCE ────────────────────────────────────────────────────────────

with open('index.html', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# ── 2. TITLE ──────────────────────────────────────────────────────────────────

soup.find('title').string = 'Hollyhock End of Season Survey 2025 — Print Version'

# ── 3. UPDATE INTRO BLURB ─────────────────────────────────────────────────────

# Replace the intro paragraph text (the long description div near the top)
for div in soup.find_all('div', style=re.compile(r'font-size:15px.*color:#555')):
    if 'interactive' in div.get_text() or 'hover' in div.get_text() or 'summarizes' in div.get_text():
        div.string = (
            'This document is the printable version of the 2025 end of season staff survey report. '
            'It covers five sections: respondent profile, engagement and development, connectedness '
            'and empowerment, open-ended responses, and a cross-question synthesis. All theme and '
            'synthesis content is fully expanded. An appendix of custom and open-ended responses '
            'follows the main report.'
        )
        break

# ── 4. ADD PRINT CSS (append to existing <style>) ────────────────────────────

style = soup.find('style')
style.append("""
  /* ── Print / PDF ── */
  @page { size: letter; margin: 0.65in 0.7in; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }

  /* Expand all interactive elements */
  .hh-collapsible  { display: block !important; }
  .hh-quotes       { display: block !important; }
  .hh-synth-body   { display: block !important; }

  /* Hide interactive controls */
  .hh-card-expand    { display: none !important; }
  .hh-card-chevron   { display: none !important; }
  .hh-synth-chevron  { display: none !important; }
  .hh-quotes-toggle  { display: none !important; }
  .print-hide        { display: none !important; }

  /* Page break rules */
  .hh-section-title  { page-break-before: always; page-break-after: avoid; }
  .hh-chart-wrap     { page-break-inside: avoid; }
  .hh-theme-card     { page-break-inside: avoid; }
  .hh-synth-card     { page-break-inside: avoid; }
  .hh-card           { page-break-inside: avoid; }
  .hh-theme-box      { page-break-inside: avoid; }
  .hh-callout        { page-break-inside: avoid; }
  .hh-singles-card   { page-break-inside: avoid; }
  hr.hh-divider      { page-break-after: avoid; }

  /* Keep section header with its first chart */
  .hh-section-title + .hh-row,
  .hh-section-title + .hh-cards-3,
  .hh-section-title + .hh-chart-wrap { page-break-before: avoid; }
""")

# ── 5. REMOVE DOWNLOAD PDF BUTTON ─────────────────────────────────────────────

for btn in soup.find_all('button', string=re.compile('Download PDF', re.I)):
    parent = btn.parent
    btn.decompose()
    if parent and 'position:absolute' in parent.get('style', ''):
        parent.decompose()

# ── 6. REMOVE INTERACTIVE ONCLICK HANDLERS AND CHEVRONS ───────────────────────

for el in soup.find_all(class_='hh-card-toggle'):
    if el.get('onclick'):
        del el['onclick']
    for exp in el.find_all(class_='hh-card-expand'):
        exp.decompose()

for el in soup.find_all(class_='hh-synth-header'):
    if el.get('onclick'):
        del el['onclick']

for el in soup.find_all(class_='hh-synth-chevron'):
    el.decompose()

for el in soup.find_all(class_='hh-quotes-toggle'):
    el.decompose()

# ── 7. REMOVE OLD HIDDEN APPENDIX DIV ────────────────────────────────────────

for div in soup.find_all('div', style=re.compile(r'display\s*:\s*none')):
    div.decompose()

# ── 8. UPDATE DONUT CHART LEGEND TEXT TO INCLUDE PERCENTAGES ─────────────────

# The legends already exist in index.html after each canvas; update the label text
donut_legend_labels = {
    'tenureChart': [
        '1 year or less (32.1%)',
        '2–4 seasons (42.9%)',
        '5–7 seasons (10.7%)',
        '8+ seasons (14.3%)',
    ],
    'newChart': [
        'Returning staff (67.9%)',
        'New staff (32.1%)',
    ],
}

for canvas_id, labels in donut_legend_labels.items():
    canvas = soup.find('canvas', id=canvas_id)
    if not canvas:
        continue
    chart_wrap = canvas.find_parent(class_='hh-chart-wrap')
    if not chart_wrap:
        continue
    legend = chart_wrap.find(class_='hh-legend')
    if not legend:
        continue
    spans = legend.find_all('span', recursive=False)
    for span, label in zip(spans, labels):
        dot = span.find(class_='hh-dot')
        # Clear span and rebuild with dot + new label text
        span.clear()
        span.append(dot)
        span.append(label)

# ── 9. REMOVE APPENDIX PLACEHOLDER COMMENT ───────────────────────────────────

for node in soup.find_all(string=re.compile('APPENDIX: moved')):
    node.extract()

# ── 10. BUILD APPENDIX FROM CSV ───────────────────────────────────────────────

# Strings to strip from multi-select responses (standard checkbox options)
STANDARD_STRINGS = sorted([
    "I will not be coming back next season, but Mental Health First Aid to those who need it would have been my first choic.",
    "Being part of Hollyhocks leadership education mission",
    "Extra activities available for staff Ex: Yoga, presenter evening etc.",
    "Perks (comp program, yoga classes, extracurriculars, spa)",
    "Perks (comp program, yoga classes, extracurriculars)",
    "Professional Growth and Development",
    "Conflict Engagement/Resolution",
    "Compensation and/or benefits",
    "Community with other staff",
    "Natural/remote setting",
    "Coworkers and colleagues",
    "Mental Health First Aid",
    "Gratitude from guests",
    "Seasonal opportunity",
    "Need an income to live",
    "Leadership Skills",
    "Competitive pay",
    "Values alignment",
    "Insufficient training",
    "Outdoor activities",
    "Gender Diversity",
    "Remote setting",
    "De-escalation",
    "Movie nights",
    "Communication",
    "Antiracism",
    "I.T. Skills",
    "Location",
    "Workload",
    "Meetings",
    "Parties",
    "Games",
], key=len, reverse=True)


def strip_standard(text):
    """Remove standard checkbox options (as comma-delimited items) from response text.
    Only removes a string when it appears as a standalone CSV item, not mid-sentence."""
    result = text
    for s in STANDARD_STRINGS:
        escaped = re.escape(s)
        # Remove when at the very start, followed by comma or end-of-string
        result = re.sub(r'^' + escaped + r'\s*(?:,\s*|$)', '', result, flags=re.IGNORECASE)
        # Remove when preceded by a comma (mid-list or at end)
        result = re.sub(r',\s*' + escaped + r'\s*(?=,|$)', '', result, flags=re.IGNORECASE)
    # Clean up leftover commas and whitespace
    result = result.strip().strip(',').strip()
    result = ' '.join(result.split())
    return result


with open('End of Season Survey 2025 (Responses) - Form Responses 1.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

COL = {}
for h in rows[0].keys():
    if 'Why did you join' in h:              COL['join_new']      = h
    if 'returned to' in h:                   COL['join_ret']      = h
    if 'training' in h and '(new)' in h:     COL['train_new']     = h
    if 'training' in h and '(new)' not in h and 'Why' not in h:
                                             COL['train_ret']     = h
    if 'rewarding' in h and '(new)' in h:    COL['reward_new']    = h
    if 'rewarding' in h and '(new)' not in h: COL['reward_ret']   = h
    if 'challenging' in h and '(new)' in h:  COL['challenge_new'] = h
    if 'challenging' in h and '(new)' not in h: COL['challenge_ret'] = h
    if 'doing well' in h and '(new)' in h:   COL['well_new']      = h
    if 'doing well' in h and '(new)' not in h: COL['well_ret']    = h
    if 'improve on' in h and '(new)' in h:   COL['improve_new']   = h
    if 'improve on' in h and '(new)' not in h: COL['improve_ret'] = h
    if 'transparency' in h.lower() and 'mean' in h and '(new)' in h:
                                             COL['transp_new']    = h
    if 'transparency' in h.lower() and 'mean' in h and '(new)' not in h:
                                             COL['transp_ret']    = h
    if 'favourite perk' in h:               COL['perk']          = h
    if 'team-building' in h:                COL['team']          = h


def collect_custom(col_new, col_ret=''):
    """Collect cleaned custom write-in text from multi-select questions."""
    seen = set()
    results = []
    for r in rows:
        for col in [col_new, col_ret]:
            if not col:
                continue
            val = r.get(col, '').strip()
            if not val:
                continue
            cleaned = strip_standard(val)
            if len(cleaned) > 3 and cleaned not in seen:
                seen.add(cleaned)
                results.append(cleaned)
    return results


def collect_open(col_new, col_ret=''):
    """Collect all non-empty open-ended responses."""
    out = []
    for r in rows:
        v = r.get(col_new, '').strip() or r.get(col_ret, '').strip()
        if v:
            out.append(v)
    return out


join_custom      = collect_custom(COL.get('join_new', ''), COL.get('join_ret', ''))
train_custom     = collect_custom(COL.get('train_new', ''), COL.get('train_ret', ''))
reward_custom    = collect_custom(COL.get('reward_new', ''), COL.get('reward_ret', ''))
challenge_custom = collect_custom(COL.get('challenge_new', ''), COL.get('challenge_ret', ''))
perk_custom      = collect_custom(COL.get('perk', ''))
team_custom      = collect_custom(COL.get('team', ''))

well_all    = collect_open(COL.get('well_new', ''), COL.get('well_ret', ''))
improve_all = collect_open(COL.get('improve_new', ''), COL.get('improve_ret', ''))
transp_all  = collect_open(COL.get('transp_new', ''), COL.get('transp_ret', ''))


def li_list(items):
    return ''.join(f'<li>{item}</li>' for item in items if item)


def appendix_section(title, items):
    if not items:
        return ''
    return f'''
    <div class="hh-app-q">
      <div class="hh-app-q-title">{title}</div>
      <ul class="hh-app-list">{li_list(items)}</ul>
    </div>'''


appendix_html = f'''
<hr class="hh-divider">
<div style="page-break-before:always;">
  <div style="font-size:20px; font-weight:600; color:#233C4D; margin-bottom:1.5rem;">Appendix — Survey Responses</div>

  <div style="font-size:13px; font-weight:600; color:#427C7D; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:1rem; margin-top:1.5rem; border-bottom:1px solid #d0cfc8; padding-bottom:0.4rem;">Custom responses — multi-select questions</div>

  {appendix_section("Why did you join, return to, or stay at Hollyhock? — write-in responses", join_custom)}
  {appendix_section("What types of training opportunities would you like to see next year? — write-in responses", train_custom)}
  {appendix_section("What's a particularly rewarding and/or motivating part of working at Hollyhock? — write-in responses", reward_custom)}
  {appendix_section("What is a particularly challenging part of working at Hollyhock? — write-in responses", challenge_custom)}
  {appendix_section("What is your favourite perk at Hollyhock? — write-in responses", perk_custom)}
  {appendix_section("Which team-building activities would you be interested in? — write-in responses", team_custom)}

  <div style="font-size:13px; font-weight:600; color:#427C7D; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:1rem; margin-top:2rem; border-bottom:1px solid #d0cfc8; padding-bottom:0.4rem;">Open-ended question responses — all respondents</div>

  {appendix_section("What is something Hollyhock, as an organisation, is doing well?", well_all)}
  {appendix_section("What is something Hollyhock as an organisation could improve on?", improve_all)}
  {appendix_section('What does "organizational transparency" in a workplace mean for you?', transp_all)}
</div>
'''

appendix_tag = BeautifulSoup(appendix_html, 'html.parser')
wrap = soup.find('div', class_='hh-wrap')
wrap.append(appendix_tag)

# ── 11. WRITE OUTPUT ──────────────────────────────────────────────────────────

output = str(soup)
with open('EoS Report PDF.html', 'w', encoding='utf-8') as f:
    f.write(output)

print("Generated EoS Report PDF.html successfully.")
