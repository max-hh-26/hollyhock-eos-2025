#!/usr/bin/env python3
"""Generate EoS Report PDF.html from index.html as the source of truth."""

import csv
import re
from bs4 import BeautifulSoup, NavigableString, Tag

# ── 1. LOAD SOURCE ────────────────────────────────────────────────────────────

with open('index.html', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# ── 2. TITLE ──────────────────────────────────────────────────────────────────

soup.find('title').string = 'Hollyhock End of Season Survey 2025 — Print Version'

# ── 3. ADD DATALABELS PLUGIN ──────────────────────────────────────────────────

chart_script = soup.find('script', src=re.compile('chart', re.I))
dl_tag = soup.new_tag('script', src='https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2')
chart_script.insert_after(dl_tag)

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

  /* Donut data table */
  .pdf-donut-table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 12px; font-family: 'Montserrat', sans-serif; }
  .pdf-donut-table td { padding: 3px 6px; color: #444; }
  .pdf-donut-table td:last-child { text-align: right; font-weight: 600; color: #233C4D; }
  .pdf-donut-swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
""")

# ── 5. REMOVE DOWNLOAD PDF BUTTON ─────────────────────────────────────────────

for btn in soup.find_all('button', string=re.compile('Download PDF', re.I)):
    # Remove the button and its parent positioning div if it only contains the button
    parent = btn.parent
    btn.decompose()
    if parent and parent.get('style', '').find('position:absolute') != -1:
        parent.decompose()

# ── 6. REMOVE CARD-TOGGLE ONCLICK (make headings non-interactive) ─────────────

for el in soup.find_all(class_='hh-card-toggle'):
    del el['onclick']
    # Remove the expand indicator span
    for exp in el.find_all(class_='hh-card-expand'):
        exp.decompose()

# Remove synth header onclick
for el in soup.find_all(class_='hh-synth-header'):
    del el['onclick']
for el in soup.find_all(class_='hh-synth-chevron'):
    el.decompose()

# Remove quotes toggle buttons
for el in soup.find_all(class_='hh-quotes-toggle'):
    el.decompose()

# ── 7. ADD DONUT DATA TABLES ──────────────────────────────────────────────────

donut_data = {
    'tenureChart': {
        'rows': [
            ('#233C4D', '1 year or less',  '32.1%', '(n=9)'),
            ('#427C7D', '2–4 seasons',     '42.9%', '(n=12)'),
            ('#D6AD60', '5–7 seasons',     '10.7%', '(n=3)'),
            ('#CA5757', '8+ seasons',      '14.3%', '(n=4)'),
        ]
    },
    'newChart': {
        'rows': [
            ('#233C4D', 'Returning staff', '67.9%', '(n=19)'),
            ('#D6AD60', 'New staff',       '32.1%', '(n=9)'),
        ]
    },
}

for canvas_id, info in donut_data.items():
    canvas = soup.find('canvas', id=canvas_id)
    if not canvas:
        continue
    # Build table HTML
    rows_html = ''
    for color, label, pct, count in info['rows']:
        rows_html += (
            f'<tr><td><span class="pdf-donut-swatch" style="background:{color}"></span>{label} {count}</td>'
            f'<td>{pct}</td></tr>'
        )
    table_html = f'<table class="pdf-donut-table">{rows_html}</table>'
    table_tag = BeautifulSoup(table_html, 'html.parser')
    # Insert after the canvas wrapper div
    wrapper = canvas.parent
    wrapper.insert_after(table_tag)

# ── 8. INJECT JS: REGISTER DATALABELS + CONFIGURE CHARTS ─────────────────────

datalabel_js = """
// ── PDF: register datalabels and configure all charts ──
Chart.register(ChartDataLabels);
Chart.defaults.set('plugins.datalabels', { display: false });  // off by default

// After page loads, patch each chart to show values
window.addEventListener('load', () => {
  Chart.instances && Object.values(Chart.instances).forEach(chart => {
    const type = chart.config.type;
    const isHorizontalBar = chart.options.indexAxis === 'y';
    const isVerticalBar   = type === 'bar' && !isHorizontalBar;
    const isDoughnut      = type === 'doughnut';

    if (isHorizontalBar) {
      chart.options.plugins.datalabels = {
        display: true,
        anchor: 'end',
        align: 'right',
        formatter: (v) => v > 0 ? v.toFixed(1) + '%' : '',
        font: { size: 9, weight: '600', family: 'Montserrat' },
        color: '#444',
        clamp: true,
        offset: 2,
      };
      chart.update('none');
    } else if (isVerticalBar) {
      chart.options.plugins.datalabels = {
        display: true,
        anchor: 'end',
        align: 'top',
        formatter: (v) => v > 0 ? v.toFixed(1) + '%' : '',
        font: { size: 9, weight: '600', family: 'Montserrat' },
        color: '#444',
        clamp: true,
        offset: 2,
      };
      chart.update('none');
    }
  });
});
"""

# Find the closing </script> of the main script block and append before it
main_script = soup.find_all('script')[-1]  # last script block is the chart JS
main_script.append(datalabel_js)

# ── 9. REMOVE APPENDIX COMMENT AND OLD HIDDEN APPENDIX ───────────────────────

# Remove the placeholder comment
for node in soup.find_all(string=re.compile('APPENDIX: moved')):
    node.extract()

# Remove the old hidden appendix div (display:none containing old appendix content)
for div in soup.find_all('div', style=re.compile(r'display\s*:\s*none')):
    div.decompose()

# ── 10. BUILD APPENDIX FROM CSV ───────────────────────────────────────────────

STANDARD_OPTIONS = {
    'join_return': {
        'Competitive pay', 'Seasonal opportunity',
        'Perks (comp program, yoga classes, extracurriculars)',
        'Perks (comp program, yoga classes, extracurriculars, spa)',
        'Need an income to live', 'Need income',
        'Community with other staff', 'Staff community',
        'Values alignment', 'Location',
    },
    'training': {
        'Gender Diversity', 'Antiracism', 'I.T. Skills', 'De-escalation',
        'Leadership Skills', 'Communication', 'Conflict Engagement/Resolution',
        'Mental Health First Aid',
    },
    'rewarding': {
        'Coworkers and colleagues', 'Natural/remote setting',
        'Professional Growth and Development',
        'Being part of Hollyhocks leadership education mission',
        'Gratitude from guests',
    },
    'challenging': {
        'Workload', 'Compensation and/or benefits', 'Insufficient training',
        'Coworkers and colleagues', 'Remote setting',
    },
    'perk': {
        'Spa', 'Complimentary program', 'Breakfast', 'Magic meals fridge',
        'Activities',
    },
    'team': {
        'Outdoor activities', 'Parties', 'Meetings', 'Movie nights', 'Games',
    },
}

def parse_custom(cell_value, standard_set):
    """Return write-in responses that are not in the standard option set."""
    if not cell_value or not cell_value.strip():
        return []
    parts = [p.strip() for p in cell_value.split(',')]
    custom = []
    buf = ''
    for part in parts:
        candidate = (buf + ', ' + part).strip(', ') if buf else part
        # Check if candidate or any standard option starts with it
        matched = any(
            s.lower() == candidate.lower() or
            s.lower().startswith(candidate.lower() + ',')
            for s in standard_set
        )
        in_standard = any(s.lower() == candidate.lower() for s in standard_set)
        partial_match = any(
            s.lower().startswith(candidate.lower())
            for s in standard_set
        )
        if in_standard:
            buf = ''
        elif partial_match:
            buf = candidate
        else:
            # Not a standard option — it's custom
            if buf:
                custom.append(buf)
            buf = ''
            # Check if this part alone is standard
            if any(s.lower() == part.lower() for s in standard_set):
                pass
            else:
                buf = part
    if buf:
        custom.append(buf)
    return [c for c in custom if len(c) > 2]

def has_custom(cell_value, standard_set):
    """Return True if cell contains text beyond the standard option set."""
    if not cell_value or not cell_value.strip():
        return False
    remaining = cell_value
    for opt in sorted(standard_set, key=len, reverse=True):
        remaining = re.sub(re.escape(opt), '', remaining, flags=re.IGNORECASE)
    # If meaningful text remains after removing all standard options, it has custom content
    cleaned = re.sub(r'[,\s]+', '', remaining)
    return len(cleaned) > 3

with open('End of Season Survey 2025 (Responses) - Form Responses 1.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Column name fragments (partial match)
COL = {}
headers_list = list(rows[0].keys())
for h in headers_list:
    if 'Why did you join' in h:         COL['join_new']      = h
    if 'returned to' in h:              COL['join_ret']      = h
    if 'training' in h and '(new)' in h: COL['train_new']   = h
    if 'training' in h and '(new)' not in h and 'Why' not in h: COL['train_ret'] = h
    if 'rewarding' in h and '(new)' in h: COL['reward_new'] = h
    if 'rewarding' in h and '(new)' not in h: COL['reward_ret'] = h
    if 'challenging' in h and '(new)' in h: COL['challenge_new'] = h
    if 'challenging' in h and '(new)' not in h: COL['challenge_ret'] = h
    if 'doing well' in h and '(new)' in h: COL['well_new']  = h
    if 'doing well' in h and '(new)' not in h: COL['well_ret'] = h
    if 'improve on' in h and '(new)' in h: COL['improve_new'] = h
    if 'improve on' in h and '(new)' not in h: COL['improve_ret'] = h
    if 'transparency' in h.lower() and 'mean' in h and '(new)' in h: COL['transp_new'] = h
    if 'transparency' in h.lower() and 'mean' in h and '(new)' not in h: COL['transp_ret'] = h
    if 'favourite perk' in h:           COL['perk']          = h
    if 'team-building' in h:            COL['team']          = h

# Collect all responses for open-ended questions
def collect_open(col_new, col_ret):
    out = []
    for r in rows:
        v = r.get(col_new, '').strip() or r.get(col_ret, '').strip()
        if v:
            out.append(v)
    return out

def collect_single(col):
    return [r.get(col, '').strip() for r in rows if r.get(col, '').strip()]

# Collect full raw responses that contain at least one custom (write-in) value
def collect_custom(col_new, col_ret, std_key):
    std = STANDARD_OPTIONS[std_key]
    seen = set()
    results = []
    for r in rows:
        for col in [col_new, col_ret]:
            val = r.get(col, '').strip()
            if val and has_custom(val, std) and val not in seen:
                seen.add(val)
                results.append(val)
    return results

join_custom      = collect_custom(COL.get('join_new',''), COL.get('join_ret',''), 'join_return')
train_custom     = collect_custom(COL.get('train_new',''), COL.get('train_ret',''), 'training')
reward_custom    = collect_custom(COL.get('reward_new',''), COL.get('reward_ret',''), 'rewarding')
challenge_custom = collect_custom(COL.get('challenge_new',''), COL.get('challenge_ret',''), 'challenging')
perk_custom      = collect_custom(COL.get('perk',''), '', 'perk')
team_custom      = collect_custom(COL.get('team',''), '', 'team')

well_all    = collect_open(COL.get('well_new',''), COL.get('well_ret',''))
improve_all = collect_open(COL.get('improve_new',''), COL.get('improve_ret',''))
transp_all  = collect_open(COL.get('transp_new',''), COL.get('transp_ret',''))

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

# Find the hh-wrap div and append the appendix before its closing tag
wrap = soup.find('div', class_='hh-wrap')
wrap.append(appendix_tag)

# ── 11. WRITE OUTPUT ──────────────────────────────────────────────────────────

output = str(soup)
with open('EoS Report PDF.html', 'w', encoding='utf-8') as f:
    f.write(output)

print("Generated EoS Report PDF.html successfully.")
