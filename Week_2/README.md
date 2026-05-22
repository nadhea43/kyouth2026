# Week 2: AI Component - Skill Gap Detection Pipeline

## Project Overview
The goal of this project is to build the foundational AI component of a flexible skill gap detection pipeline[cite: 269]. Instead of relying on rigid, hard-to-manage rule-based matching configurations, this system leverages Large Language Models (LLMs) to identify pattern-based technical insights[cite: 268]. 

The system performs two primary automated workflows:
1. **Automated Data Tagging (`tag_data.py`)**: Batches raw job description rows from a SQLite database and uses Gemini models to extract structured, comma-separated technical stacks[cite: 16, 22, 42].
2. **Deterministic Skill Gap Detection (`find_skill_gaps.py`)**: Sanitizes an incoming applicant resume, extracts its key technical core competencies via an LLM, and benchmarks them directly against unique market skills inside the database to uncover missing skill gaps in a strictly deterministic matching layout[cite: 66, 85].

---

## Setup Instructions

### Prerequisites
* **Python Version**: `3.14.*` 
* **Environment & Package Manager**: `uv` version `0.8.*` 
* **Local LLM Engine**: Ollama (configured with version `0.21.*`) 
* **Operating System**: Platform-independent (fully supports Linux, macOS, and Windows) 
* **Create data folder**: Create a new 'data' folder, and two other files below 'resources' and 'resources_eval' to add folder document downloaded from notion
    ```bash
    -Week_2
        |_data
            |_resources
            |_resources_eval

### Environment Configuration
1. **Install Local Models**: Ensure Ollama is running locally and pull the required target models[cite: 131, 133]:
   ```bash
   ollama pull llama3.1
   ollama pull phi3
   ollama pull deepseek-r1:1.5b
2. API Keys: Secure a free Gemini API Key from Google AI Studio. 
3. Environment File: Create a .env file in the root directory (this file is ignored via .gitignore and must never be committed). Add your keys as follows:  
    ```bash
    GEMINI_API_KEY=your_actual_api_key_here

4. Rate Limits Document: Create a rate_limits.txt file in the root directory mapping target metrics:
    ```bash
    gemini-2.5-flash <RPM> <TPM> <RPD>
    gemini-2.5-flash-lite <RPM> <TPM> <RPD>
    gemini-3-flash-preview <RPM> <TPM> <RPD>

## Usage

Run the operational scripts via the uv environment runner:

1. Test Model Prompter
Test connectivity to either local Ollama instances or Cloud Gemini instances:
    ```Bash
    # General Syntax: uv run prompt_model.py <model_name> "<prompt>"
    uv run prompt_model.py llama3.1 "tell me one country"

    uv run prompt_model.py gemini-2.5-flash "tell me one country"

2. Run Database Tagging
Populate empty tech_stack columns in your jobs database using batched execution:
    ```Bash
    uv run tag_data.py

3. Run Skill Gap Analyzer
Extract candidate attributes and calculate missing competencies against database insights:
    ```Bash
    uv run find_skill_gaps.py

## API / Function Reference

**prompt_model.py**
- prompt_model(model: str, prompt: str) -> str   
Purpose: Routes prompts to either a local Ollama instance or the Google   - Gemini API based on model name definitions, safely returning text strings while trapping internal communication errors gracefully.  
- Inputs: model (e.g., "llama3.1", "gemini-2.5-flash"), prompt (string text).  
- Outputs: Model text response window string (or structured [Error] logs).

**tag_data.py**
- tag_data(db_url: str) -> Tuple[int, int, float]
- Purpose: Chunks untagged job descriptions in safe batch processing sizes, requesting comma-separated tech stack lists from Gemini, and updating records inside the SQLite environment.  
- Inputs: Path to the target SQLite database file.  
- Outputs: Returns a performance tuple indicating (input_tokens, output_tokens, time_elapsed_ms).  

**find_skill_gaps.py**
- find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult  
- Purpose: Coordinates parsing of raw resume text, implements regex filtering for prompt injections, queries unique market constraints, resolves complex string structural differences, and yields sorted missing competencies.  
- Inputs: input_file_path (path to resume text), db_url (path to SQLite database).  
- Outputs: A Pydantic SkillGapResult object carrying lowercase sorted gaps, aggregate token footprints, and processing speeds. 

## Data / Assumptions

- Database Target: Expects a SQLite database table named jobs populated with columns source_id, description, and a nullable tech_stack text block.  
- Token Estimations: If an LLM response pipeline drops metadata attachments, a default fallback calculation ruleset of 4 tokens per word is applied to compute metrics.  
- Skill Omissions: Non-technical skills (e.g., leadership, management) and specialized security/professional certifications are safely bypassed to focus specifically on core frameworks, tools, and languages.  

## Testing

- Tagging Consistency: Variations in output formatting on different executions are accepted across data processing layers for tag_data.py.  
- Deterministic Gap Matching: find_skill_gaps.py enforces absolute determinism (NOT OK to have different results across runs). This is guaranteed by using the LLM exclusively for extracting raw skills from the resume into structural JSON arrays, while utilizing deterministic Python set differences (market_skills - resume_skills) to compute the final gaps.
- Complex Variant Edge Cases: Direct string matching inaccuracies are solved by normalizations. Variants like "c/c++" are split and mapped into distinct set records ("c", "c++") so that single-term appearances in resume profiles successfully clear composite requirements in job logs.  

## Limitations

- Token Falling Estimation: Using a 4-words-per-token model calculation wrapper when telemetry structures lack precision can introduce slight metric deviations compared to native tokenizers.  
- Text Chunk Splitting: Descriptions are truncated at a hard-coded length limit (4000 characters) to avoid exceeding token limits during massive batch transfers.
- Context Over-Sanitization: The script's prompt injection sanitation filtering could flag legitimate security resumes that contain phrases like "vulnerability jailbreak testing" or "cross-site scripting mitigation" as false positives.

## Architecture Reflection

**Design Choices**
- Separation of Concerns: Decoupled network routing pipelines (prompt_model.py) from business execution units (tag_data.py). This allows switching between cloud engines and localized privacy clusters effortlessly without mutating target dataset handlers.  
- Data Serialization: Standardized structured communication pathways by forcing LLM outputs into native, parsable JSON schemas checked cleanly using Pydantic parameters.  

**Trade-offs**
- Cloud Costs vs. Local Controls: Prioritized external API engines (gemini-2.5-flash) during tagging operations over local instances to maintain stable parsing accuracy , accepting token billing liabilities over raw local throughput dependencies.  
- Batch Sizing Over Speed: Chose conservative, low-density chunk boundaries (Batch Size = 5) during processing to operate safely beneath free-tier RPM/TPM thresholds, sacrificing pure latency to guarantee execution safety.

**Future Improvements**
- Advanced Async Architecture: Convert current batch generation loops into fully concurrent, thread-pooled asyncio generators using gemini-3-flash-preview tools.  
- Integration of FastMCP: Abstract direct raw queries out of Python runtimes by integrating an intermediate FastMCP client/server architecture layer.  