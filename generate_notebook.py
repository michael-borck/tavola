import argparse
import asyncio
import os
import random
import tempfile
from pathlib import Path
from pydantic import BaseModel
from google import genai
from google.genai import types
from pypdf import PdfReader
import edge_tts
from pydub import AudioSegment
from playwright.async_api import async_playwright

# --- 1. Define Structured Output Schemas ---

class DialogueLine(BaseModel):
    speaker: str  # "Alex" or "Sam"
    text: str

class StatItem(BaseModel):
    value: str
    label: str

class InfographicData(BaseModel):
    title: str
    subtitle: str
    stats: list[StatItem]       # 3 key numbers or metrics
    takeaways: list[str]        # 4 concise bullet points
    bottom_line: str

class NotebookOutput(BaseModel):
    podcast_script: list[DialogueLine]
    infographic: InfographicData


# --- 2. Podcast Style Prompts ---

STYLE_PROMPTS = {
    "deep-dive": (
        "Write an 18-24 line lively two-host Deep Dive between Alex (storyteller who sees the big picture) "
        "and Sam (curious skeptic who asks sharp follow-ups and translates jargon). "
        "Mix longer explanations with short 3-6 word reactions. Connect non-obvious dots in the source."
    ),
    "brief": (
        "Write a tight, single-host Brief delivered ONLY by Alex (6-8 short lines, under 90 seconds spoken). "
        "Every single line MUST have speaker set to 'Alex'. "
        "Lead with the core headline, hit the 3 sharpest facts, and close with one clear takeaway."
    ),
    "critique": (
        "Write a 16-20 line constructive Critique between Alex and Sam acting as candid domain reviewers. "
        "Highlight what is genuinely strong, then directly dissect gaps, risks, missing evidence, "
        "or areas that could be tightened."
    ),
    "debate": (
        "Write an 18-22 line structured Debate. Alex argues the optimistic/pro case from the source; "
        "Sam plays the tough skeptic highlighting trade-offs, blind spots, and counterarguments. "
        "Do not let them agree prematurely."
    ),
}


# --- 3. Extract Text from PDF or TXT ---

def read_source(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


# --- 4. Generate Script & Infographic Data with Gemini ---

def generate_content(
    client: genai.Client, source_text: str, model: str, style: str
) -> NotebookOutput:
    style_instruction = STYLE_PROMPTS[style]
    prompt = f"""
    You are creating a Gemini Notebook-style audio overview and visual infographic from the source text below.

    1. Podcast Script ({style} style):
       {style_instruction}
       Rules:
       - Start with a cold open (NO "Welcome back to the show" or generic greetings).
       - Cite concrete facts, numbers, or names from the source text.
       - Avoid AI clichés ("delve into", "game-changer", "tapestry", "at the end of the day").
       - Keep lines conversational with no stage directions or sound effects.

    2. Infographic:
       Extract a punchy title, subtitle, 3 standout stats/facts, 4 key takeaways, and a 1-sentence bottom line.

    SOURCE TEXT:
    {source_text[:50000]}
    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NotebookOutput,
        ),
    )
    return NotebookOutput.model_validate_json(response.text)


# --- 5A. Podcast Synthesis: Edge TTS (Default) ---

EDGE_VOICES = {
    "Alex": "en-US-AndrewNeural",  # Male
    "Sam": "en-US-AvaNeural",      # Female
}

async def build_podcast_edge(script: list[DialogueLine], output_path: str):
    valid_lines = [
        line for line in script
        if line.text.strip() and any(c.isalnum() for c in line.text)
    ]
    unique_speakers = {line.speaker for line in valid_lines}

    single_voice = None
    if len(unique_speakers) == 1:
        gender, single_voice = random.choice([
            ("male", "en-US-AndrewNeural"),
            ("female", "en-US-AvaNeural"),
        ])
        print(f"Single speaker detected -> coin flip picked {gender} voice ({single_voice})")

    combined = AudioSegment.empty()

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, line in enumerate(valid_lines):
            text = line.text.strip()
            voice = single_voice or EDGE_VOICES.get(line.speaker, "en-US-AndrewNeural")
            clip_path = os.path.join(tmpdir, f"line_{i}.mp3")

            for attempt in range(3):
                try:
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(clip_path)
                    break
                except edge_tts.exceptions.NoAudioReceived:
                    if attempt == 2:
                        print(f"Failed on line {i} ({voice}): {text!r}")
                        raise
                    await asyncio.sleep(1.5)

            pause_ms = random.randint(180, 420)
            combined += AudioSegment.from_mp3(clip_path) + AudioSegment.silent(duration=pause_ms)

    combined.export(output_path, format="mp3")
    print(f"Saved Edge TTS podcast to {output_path}")


# --- 5B. Podcast Synthesis: Gemini Native TTS ---

def build_podcast_gemini(
    client: genai.Client,
    script: list[DialogueLine],
    output_path: str,
    tts_model: str = "gemini-3.8-flash-tts",
):
    valid_lines = [
        line for line in script
        if line.text.strip() and any(c.isalnum() for c in line.text)
    ]
    unique_speakers = {line.speaker for line in valid_lines}

    if len(unique_speakers) == 1:
        # Single-speaker mode (e.g., "brief"): flip a coin for male or female voice
        gender, chosen_voice = random.choice([
            ("male", "Fenrir"),
            ("female", "Leda"),
        ])
        print(f"Single speaker detected -> coin flip picked {gender} voice ({chosen_voice})")

        contents = "\n\n".join(line.text.strip() for line in valid_lines)
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=chosen_voice
                )
            )
        )
    else:
        # Multi-speaker dialogue mode
        parts = [
            {
                "text": line.text.strip(),
                "speech_metadata": {"speaker": line.speaker},
            }
            for line in valid_lines
        ]
        contents = [{"role": "user", "parts": parts}]
        speech_config = types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="Alex",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Fenrir"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Sam",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Leda"
                            )
                        ),
                    ),
                ]
            )
        )

    response = client.models.generate_content(
        model=tts_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=speech_config,
        ),
    )

    audio_bytes = response.candidates[0].content.parts[0].inline_data.data
    # Gemini TTS returns 24kHz, 16-bit, mono PCM audio
    audio = AudioSegment(data=audio_bytes, sample_width=2, frame_rate=24000, channels=1)
    audio.export(output_path, format="mp3")
    print(f"Saved Gemini TTS podcast to {output_path}")


# --- 6. Render the Infographic HTML to PNG ---

async def build_infographic(data: InfographicData, output_path: str = "infographic.png"):
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


# --- 7. Run the Pipeline ---

async def main(source_file: str, tts_engine: str, style: str, model: str, tts_model: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    client = genai.Client(
        api_key=api_key,
        http_options={"api_version": "v1beta"},
    )

    print(f"Reading {source_file}...")
    text = read_source(source_file)

    print(f"Generating '{style}' podcast script and infographic data ({model})...")
    result = generate_content(client, text, model, style)

    audio_output = f"podcast_{style}_{tts_engine}.mp3"
    if tts_engine == "gemini":
        print(f"Synthesizing audio with Gemini ({tts_model})...")
        podcast_task = asyncio.to_thread(
            build_podcast_gemini, client, result.podcast_script, audio_output, tts_model
        )
    else:
        print("Synthesizing audio with Edge TTS...")
        podcast_task = build_podcast_edge(result.podcast_script, audio_output)

    await asyncio.gather(
        podcast_task,
        build_infographic(result.infographic, "infographic.png"),
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a podcast and infographic from a PDF or TXT file.")
    parser.add_argument("source_file", help="Path to the .pdf or .txt file")
    parser.add_argument(
        "--style",
        choices=list(STYLE_PROMPTS.keys()),
        default="deep-dive",
        help="Podcast format style (default: deep-dive)",
    )
    parser.add_argument(
        "--tts",
        choices=["edge", "gemini"],
        default="edge",
        help="TTS engine to use (default: edge)",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.5-flash",
        help="Gemini model for script & infographic generation",
    )
    parser.add_argument(
        "--tts-model",
        default="gemini-3.8-flash-tts",
        help="Gemini model for TTS when --tts gemini is selected",
    )
    args = parser.parse_args()
    asyncio.run(main(args.source_file, args.tts, args.style, args.model, args.tts_model))
