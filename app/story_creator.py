import os
from pathlib import Path
from typing import Dict, Any

from fpdf import FPDF
from app.job_manager import JobManager
from app.api_manager import ApiKeyManager, get_api_keys, is_quota_error
from app.gemini_client import generate_story_with_memory


class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

def clean_markdown(text: str) -> str:
    """Removes common Markdown formatting from text."""
    text = text.replace("### ", "").replace("## ", "").replace("# ", "")
    text = text.replace("**", "").replace("*", "")
    return text.strip()

def create_pdf(title: str, content: str, output_path: Path):
    """Creates a PDF file from the generated story text using a Unicode font."""
    pdf = PDF()
    pdf.set_title(title)

    font_path = Path(__file__).resolve().parent.parent / "assets/fonts/DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", str(font_path), uni=True)

    pdf.add_page()

    pdf.set_font("DejaVu", size=12)

    pdf.multi_cell(0, 10, content)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"PDF saved to {output_path}")


async def run_story_creation_pipeline(job_id: str, base_data_dir: Path, story_params: Dict[str, Any]):
    """
    The main background task for the story creation pipeline.
    """
    final_story_dir = base_data_dir / job_id / "final-story"
    story_name = story_params.get("name")

    try:
        JobManager.update_job_status(job_id, "processing", "Step 1/3: Initializing and preparing prompts...")

        # --- Prepare Prompts ---
        # 1.1 Load prompt templates from files
        prompt_dir = Path(__file__).resolve().parent.parent / "prompts"
        with open(prompt_dir / "story_creator_prompt.txt", "r", encoding="utf-8") as f:
            initial_prompt_template = f.read()
        with open(prompt_dir / "story_creator_prompt2.txt", "r", encoding="utf-8") as f:
            chapter_prompt_template = f.read()

        # 1.2 Format the initial prompt
        initial_prompt = initial_prompt_template.replace("[INSIRA AQUI]", story_name) \
            .replace("[INSIRA UM RESUMO GERAL DO ENREDO, AMBIENTAÇÃO, PERSONAGENS PRINCIPAIS ETC.]",
                     story_params.get("summary")) \
            .replace("[INSIRA O NÚMERO TOTAL DE CAPÍTULOS]", str(story_params.get("chapters"))) \
            .replace("[INSIRA UM NÚMERO APROXIMADO, EX: 3.000 CARACTERES]", str(story_params.get("chars_per_chapter")))

        # 1.3 Create batched chapter prompts
        num_chapters = story_params.get("chapters")
        chapter_prompts = []
        for i in range(1, num_chapters + 1, 2):
            if i + 1 <= num_chapters:
                prompt_text = f"Perfeito!\nAgora, escreva os capítulos {i} e {i + 1} da história."
            else:
                prompt_text = f"Perfeito!\nAgora, escreva o capítulo final, o de número {i}."

            # Add the crucial instruction from prompt2 to every request
            prompt_text += ("\nImportante: sua resposta deve ser apenas o nome e texto do capítulo, você não deve fazer "
                            "nenhum tipo de interação comigo na resposta ou falar algo que não seja o capítulo em si.")
            prompt_text += "\nNão use formatação Markdown como '#', '*' ou '_'. Escreva apenas o texto puro."

            chapter_prompts.append(prompt_text)

        JobManager.update_job_status(job_id, "processing", "Step 2/3: Generating story with AI... (This can take time)")

        # --- Initialize API Manager and get a key ---
        api_keys = get_api_keys()
        key_manager = ApiKeyManager(api_keys)
        api_key, key_idx = await key_manager.get_key_for_processing()
        if not api_key:
            raise RuntimeError("All API keys are exhausted.")

        # --- Generate Story ---
        full_story_text = await generate_story_with_memory(api_key, initial_prompt, chapter_prompts)

        cleaned_story_text = clean_markdown(full_story_text)

        JobManager.update_job_status(job_id, "processing", "Step 3/3: Creating final PDF document...")

        # --- Create PDF ---
        pdf_output_path = final_story_dir / f"{story_name.replace(' ', '_')}.pdf"
        create_pdf(title=story_name, content=cleaned_story_text, output_path=pdf_output_path)

        JobManager.update_job_status(job_id, "complete", "Your story is ready for download!")
        print(f"[{job_id}] Story creation job completed successfully.")

    except Exception as e:
        if is_quota_error(e):
            # In a future version, you could implement re-queueing logic here.
            # For now, we will mark it as a clear error.
            error_msg = "API quota exhausted. Please try again later or add a new API key."
            print(f"[{job_id}] A quota error occurred: {error_msg}")
            JobManager.update_job_status(job_id, "error", error_msg)
        else:
            print(f"[{job_id}] An error occurred in the story pipeline: {e}")
            JobManager.update_job_status(job_id, "error", f"An error occurred: {e}")