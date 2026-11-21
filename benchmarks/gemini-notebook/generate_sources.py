from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path('/tmp/tavola-notebooklm-tests')
CSS = """
@page { size: A4; margin: 18mm 18mm 20mm; }
html { font-size: 11pt; }
body { margin: 0; color: #202124; font-family: Georgia, 'Times New Roman', serif; line-height: 1.48; }
h1 { font-family: Helvetica, Arial, sans-serif; font-size: 25pt; line-height: 1.08; margin: 0 0 5mm; color: #14213d; letter-spacing: -0.02em; }
h2 { font-family: Helvetica, Arial, sans-serif; font-size: 14pt; margin: 8mm 0 2.5mm; color: #14213d; }
h3 { font-family: Helvetica, Arial, sans-serif; font-size: 11.5pt; margin: 5mm 0 1.5mm; color: #243b6b; }
p { margin: 0 0 3mm; }
ul, ol { margin: 0 0 4mm 5mm; padding: 0; }
li { margin-bottom: 1.6mm; }
.lede { font-size: 12.5pt; color: #4b5563; margin-bottom: 8mm; }
.meta { font-family: Helvetica, Arial, sans-serif; font-size: 8pt; color: #6b7280; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 4mm; }
.rule { border-top: 2px solid #14213d; margin: 6mm 0; }
table { width: 100%; border-collapse: collapse; margin: 4mm 0 6mm; font-size: 9.5pt; }
th { font-family: Helvetica, Arial, sans-serif; text-align: left; background: #eef2f7; color: #14213d; padding: 2.2mm 2.5mm; border-bottom: 1px solid #b8c2d1; }
td { padding: 2.2mm 2.5mm; border-bottom: 1px solid #d9dee7; vertical-align: top; }
.callout { background: #f4f1e8; border-left: 4px solid #b08d57; padding: 4mm 5mm; margin: 5mm 0; }
.quote { font-size: 15pt; line-height: 1.3; color: #243b6b; margin: 7mm 0; padding-left: 5mm; border-left: 3px solid #b08d57; }
.page-break { break-before: page; }
footer { position: fixed; bottom: 0; left: 0; right: 0; font-family: Helvetica, Arial, sans-serif; font-size: 8pt; color: #8a94a3; border-top: 1px solid #d9dee7; padding-top: 2mm; }
"""

sources = {
"01-urban-heat-data": f"""
<div class="meta">Synthetic research brief · urban climate · 2026</div>
<h1>Cooling the city: the case for street trees</h1>
<p class="lede">A evidence review for a city resilience committee. The source compares heat exposure, tree cover, costs, and implementation time.</p>
<div class="rule"></div>
<h2>Why cities overheat</h2>
<p>Dark roofs, asphalt, and low tree cover combine to raise surface and air temperatures. The effect is uneven: neighbourhoods with less shade can be several degrees hotter than leafy districts nearby. The committee asked for a practical comparison of interventions, not a general essay on climate change.</p>
<h2>What the evidence says</h2>
<ul>
<li>Mature street trees cut peak street temperature by up to 4.2°C.</li>
<li>One mature tree can intercept about 1,400 litres of rainfall a year, reducing pressure on drains.</li>
<li>Tree cover in the surveyed district fell from 29% to 21% over ten years.</li>
<li>Residents in planted streets report fewer heat-illness days after two summers.</li>
<li>Maintenance costs are lower than installing and running new air conditioning.</li>
</ul>
<table>
<tr><th>Intervention</th><th>Peak cooling</th><th>Relative cost</th><th>Time to benefit</th></tr>
<tr><td>Mature street trees</td><td>Up to 4.2°C</td><td>Low</td><td>5–10 years</td></tr>
<tr><td>Reflective roof coating</td><td>1.5–2.5°C indoors</td><td>Medium</td><td>1–2 years</td></tr>
<tr><td>New air conditioning</td><td>2–3°C indoors</td><td>High</td><td>Immediate</td></tr>
<tr><td>Shade structures</td><td>2–3°C at street level</td><td>Medium</td><td>1 year</td></tr>
</table>
<h2>Implementation sequence</h2>
<p>The committee’s preferred programme runs in four stages: survey streets and heat exposure; plant in winter; water and maintain for two years; evaluate shade, rain interception, and resident health. The order matters because planting without maintenance produces little shade and wastes the establishment cost.</p>
<div class="callout"><strong>Recommendation.</strong> Treat shade as infrastructure. Fund a ten-year planting and maintenance programme instead of buying short-lived cooling equipment.</div>
<h2>Limits</h2>
<p>Trees take time to mature. They are not a substitute for emergency cooling during extreme heat, and species selection must account for water use, roots, and local climate. The evidence supports a mixed programme, not a single intervention.</p>
<div class="page-break"></div>
<h2>What to measure</h2>
<p>Track canopy cover, peak street temperature, rainfall interception, maintenance cost per tree, and heat-related health visits. A dashboard should show the trend over time, not only a single year’s result. The strongest story is the relationship between planting, shade, and health—not just the number of trees planted.</p>
<div class="quote">“The cheapest cooling is a tree that was planted ten years ago.”</div>
<p>Prepared as a synthetic benchmark source for infographic design testing. All figures are illustrative.</p>
""",
"02-launch-timeline": f"""
<div class="meta">Synthetic programme brief · product operations · 2026</div>
<h1>Launching the neighbourhood heat pilot</h1>
<p class="lede">A six-month operating plan for a small council pilot. The source is rich in ordered phases, dependencies, and measurable outcomes.</p>
<div class="rule"></div>
<h2>Why this pilot</h2>
<p>The council wants to test a repeatable model for cooling public streets before committing to a city-wide programme. The pilot covers four streets, two schools, and one transport interchange. Success means lower peak temperatures, fewer heat complaints, and a costed plan that can be repeated elsewhere.</p>
<h2>Phases</h2>
<ol>
<li><strong>Map and prioritise.</strong> Survey heat exposure, shade, foot traffic, and existing trees. Select four streets and two school frontages. Publish the selection criteria.</li>
<li><strong>Design and procure.</strong> Choose species with the parks team, confirm irrigation and maintenance contracts, and order trees and shade structures. Community groups review the plan.</li>
<li><strong>Install.</strong> Plant in winter, install temporary shade at the transport interchange, and begin the watering schedule. Record every location and cost.</li>
<li><strong>Measure.</strong> Track surface temperature, canopy cover, rain interception, complaints, and maintenance hours. Compare with two control streets.</li>
<li><strong>Review and scale.</strong> Publish a costed playbook. Recommend either expansion, redesign, or stop.</li>
</ol>
<h2>Timeline and owners</h2>
<table>
<tr><th>Month</th><th>Milestone</th><th>Owner</th><th>Decision</th></tr>
<tr><td>January</td><td>Street selection and baseline</td><td>Climate team</td><td>Approve four sites</td></tr>
<tr><td>February</td><td>Species and procurement</td><td>Parks + finance</td><td>Release budget</td></tr>
<tr><td>March</td><td>Community review</td><td>Engagement</td><td>Resolve objections</td></tr>
<tr><td>April</td><td>Planting week</td><td>Parks contractor</td><td>Confirm completion</td></tr>
<tr><td>May–July</td><td>Watering and monitoring</td><td>Parks + climate</td><td>Monthly review</td></tr>
<tr><td>August</td><td>Evaluation and playbook</td><td>Programme lead</td><td>Scale or stop</td></tr>
</table>
<h2>Risks</h2>
<ul>
<li>Dry spring or irrigation failure. Mitigation: contract a backup watering crew.</li>
<li>Community opposition to tree pits or parking loss. Mitigation: publish trade-offs and co-design two sites.</li>
<li>Measurement gaps. Mitigation: baseline sensors before planting and two control streets.</li>
<li>Cost overrun. Mitigation: fixed-price procurement and a 12% contingency.</li>
</ul>
<div class="page-break"></div>
<h2>Success measures</h2>
<p>The pilot will report canopy cover, peak temperature reduction, rainfall intercepted, maintenance hours per tree, complaints, and cost per site. A traffic-light review at month five decides whether to continue. The final report should fit on one page and include a clear recommendation.</p>
<div class="callout"><strong>Operating principle.</strong> Plant for shade, measure for trust, and publish the cost. A pilot that cannot be repeated is not a pilot.</div>
<p>Prepared as a synthetic benchmark source for infographic design testing. All names and figures are illustrative.</p>
""",
"03-library-argument": f"""
<div class="meta">Synthetic essay · civic infrastructure · 2026</div>
<h1>The library is the last free room in town</h1>
<p class="lede">A short argument about public space, attention, and why libraries are more than book storage. The source is qualitative and quote-led, with one budget comparison.</p>
<div class="rule"></div>
<h2>The argument</h2>
<p>A library is not a warehouse for books. It is heated space, reliable internet, a desk, a toilet, a printer, and a person who will help without asking for a purchase. Those things are infrastructure. When a town closes a library, it does not remove a service; it removes the only indoor place where a person can stay without spending money.</p>
<div class="quote">“A library card is the cheapest membership in civic life.”</div>
<h2>Three things libraries actually provide</h2>
<ul>
<li><strong>Access.</strong> Job applications, benefits forms, schoolwork, and immigration paperwork increasingly assume a computer and a quiet hour.</li>
<li><strong>Attention.</strong> A room where no one is selling anything is rare. Reading is only one use; thinking is another.</li>
<li><strong>Company.</strong> Older residents, new parents, freelancers, and schoolchildren share a table without needing a reason.</li>
</ul>
<h2>What the budget misses</h2>
<p>Library budgets are usually compared with book purchases or digital subscriptions. The better comparison is the cost of isolation: emergency services, missed appointments, school support, and the unpaid labour of people helping neighbours fill in forms. The library is cheap because it is shared.</p>
<h2>Design implication</h2>
<p>If the library is infrastructure, its annual report should not lead with acquisitions. It should lead with visits, form-filling sessions, computer help, warm hours, and the number of people who had nowhere else to go. The visual story is a hierarchy: access, attention, and company, with the building as the root.</p>
<h2>Objection</h2>
<p>“Everyone has a phone.” A phone is not a desk, a printer, a quiet room, or a person who can explain a letter. Access is not only a screen; it is space, time, and help. That distinction is the whole argument.</p>
<div class="callout"><strong>Recommendation.</strong> Fund the room, not just the shelves. Measure the library by the people who stay.</div>
<p>Prepared as a synthetic benchmark source for infographic design testing.</p>
""",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for name, body in sources.items():
        html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
        page.set_content(html, wait_until='load')
        page.pdf(path=str(OUT / f'{name}.pdf'), format='A4', print_background=True, margin={'top': '18mm', 'bottom': '20mm', 'left': '18mm', 'right': '18mm'})
        (OUT / f'{name}.md').write_text(body.replace('<h1>', '# ').replace('</h1>', '\n').replace('<h2>', '## ').replace('</h2>', '\n').replace('<p class="lede">', '').replace('</p>', '\n'), encoding='utf-8')
        print(OUT / f'{name}.pdf')
    browser.close()
