import argparse
import asyncio
import os
from pathlib import Path
from pydantic import BaseModel
from google import genai
from google.genai import types
from pypdf import PdfReader
from playwright.async_api import async_playwright

# --- 1. Schema ---

class StatItem(BaseModel):
    value: str
    label: str

class InfographicData(BaseModel):
    title: str
    subtitle: str
    stats: list[StatItem]       # 3 key numbers or metrics
    takeaways: list[str]        # 4 concise bullet points
    bottom_line: str


# --- 2. Extract Text ---

def read_source(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


# --- 3. Extract Infographic Data with Gemini ---

def generate_infographic_data(
    client: genai.Client, source_text: str, model: str
) -> InfographicData:
    prompt = f"""
    Extract data for a clean executive visual briefing from the source text below:
    - A punchy title and concise subtitle
    - 3 standout stats, metrics, or concrete facts (short value + brief label)
    - 4 sharp, concrete key takeaways
    - A 1-sentence bottom line

    SOURCE TEXT:
    {source_text[:50000]}
    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InfographicData,
        ),
    )
    return InfographicData.model_validate_json(response.text)


# --- 4. Render HTML to PNG ---

async def render_infographic(data: InfographicData, output_path: str):
    stats_html = "".join(
        f"""
        <div class="bg-slate-800/80 border border-slate-700 rounded-xl p-5 text-center">
            <div class="text-3xl font-extrabold text-sky-400">{s.value}</div>
            <div class="text-sm text-slate-300 mt-1">{s.label}</div>
        </div>
        """
        for s in data.stats[:3]
    )

    takeaways_html = "".join(
        f"""
        <li class="flex items-start gap-3 bg-slate-800/50 p-4 rounded-lg border border-slate-700/60">
            <span class="text-sky-400 font-bold text-lg">•</span>
            <span class="text-slate-200 leading-relaxed">{t}</span>
        </li>
        """
        for t in data.takeaways
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8" />
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-white font-sans p-10 w-[900px]">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-10 shadow-2xl">
            <div class="uppercase tracking-widest text-xs font-semibold text-sky-400 mb-2">
                Visual Briefing
            </div>
            <h1 class="text-4xl font-extrabold tracking-tight text-white">{data.title}</h1>
            <p class="text-slate-400 text-lg mt-2 mb-8">{data.subtitle}</p>

            <div class="grid grid-cols-3 gap-4 mb-8">
                {stats_html}
            </div>

            <h2 class="text-sm uppercase tracking-wider text-slate-400 font-semibold mb-4">
                Key Takeaways
            </h2>
            <ul class="space-y-3 mb-8">
                {takeaways_html}
            </ul>

            <div class="bg-sky-950/60 border border-sky-800/60 rounded-xl p-5">
                <span class="text-sky-400 font-bold uppercase text-xs tracking-wider">Bottom Line: </span>
                <span class="text-slate-100">{data.bottom_line}</span>
            </div>
        </div>
    </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 900, "height": 1200})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
    print(f"Saved infographic to {output_path}")


# --- 5. CLI Entrypoint ---

async def main(args: argparse.Namespace):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(
        api_key=api_key,
        http_options={"api_version": "v1beta"},
    )

    print(f"Reading {args.source_file}...")
    text = read_source(args.source_file)

    print(f"Extracting infographic data ({args.model})...")
    data = generate_infographic_data(client, text, args.model)

    print("Rendering infographic...")
    await render_infographic(data, args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a PNG infographic from a PDF or TXT file.")
    parser.add_argument("source_file", help="Path to the .pdf or .txt file")
    parser.add_argument(
        "--model",
        default="gemini-3.5-flash",
        help="Gemini model for data extraction",
    )
    parser.add_argument(
        "-o", "--output",
        default="infographic.png",
        help="Output PNG filename (default: infographic.png)",
    )
    asyncio.run(main(parser.parse_args()))