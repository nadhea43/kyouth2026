## Project Overview
The goal of this project is to build and containerize a full-stack, intelligent chat application integrated with an AI pipeline. The system processes PDF resumes, manages real-time interactions using LLMs (Gemini & Ollama), and includes specialized logic to detect professional skill gaps against an active database. The entire pipeline is orchestrated using a decoupled multi-container layout to ensure isolation, reproducibility, and modern deployment standards.

## Setup Instructions

### Prerequisites
Make sure you have the following tools installed on your local computer
* **Docker** (Desktop or Engine)
* **Docker Compose**
* **uv** (Optional, only needed if you plan to execute manual python environments without containerization)

### Configuration of Environment Variables
The application reads parameters directly from an environment configuration file to protect sensitive information. Create a `.env` file in the `Week_3` root folder based on the provided `.env.example` template:

```env
# server endpoints
BACKEND_URL=http://localhost:8001

# AI model configs
OLLAMA_MODEL = phi3
OLLAMA_HOST = http://localhost:11434
GEMINI_MODEL=gemini-2.5-flash-lite

# Secret Keys
GEMINI_API_KEY=your_actual_google_gemini_api_key
```

### Step by step execution
1. Open your terminal and navigate to your main Week_3 folder:
    ```bash
    cd Week_3

2. Build the environments and run both containers using a single orchestration command:
    ```bash
    docker compose up --build

3. Docker will automatically assemble the separate backend and frontend images, construct a unified bridge network, and host your services simultaneously.

## Usage
Once the containers report a healthy status, you can interact with the system:  
 - Access the Frontend App: Open your web browser and navigate to http://localhost:8000  
 - Access the Backend Service directly: Check the raw server status or docs at http://localhost:8001

### Expected inputs & outputs
1. Normal Conversational Thread:
- Input: Type a normal prompt (e.g., "Hi, tell me about yourself" or "What is Python?") into the chat bar and click Send.  
- Output: The UI transfers the text payload to the backend, which proxies the request to Gemini or Ollama, returning a formatted text markdown reply.

2. Skill Gap Analysis Thread:
- Input: Upload a resume file using the file picker UI elements, type an explicit analytical keyword trigger (e.g., "find skills gap"), and submit.  
- Output: The pipeline reads the embedded text extraction data, matches it against the SQLite jobs data tracking layer, and provides an itemized breakdown of missing skills. 

## API & Function Reference
1. Backend Service (POST /chat)
- Handles core system logic, user chat messaging, and text parsing routing.
- Expected Request JSON Payload:
    ```bash
    {
    "message": "string",
    "pdf_text": "string (optional field containing extracted text layer)"
    }
    ```
- Response Format
    ```bash
    {
    "reply": "string containing text response markdown from the processing models"
    }
    ```

2. Frontend Core JavaScript Functions
Responsible for standardizing client-side interaction mechanics and dynamic view injections.
- **sendMessage()**: Captures input text strings along with any state-managed file extraction buffers, structures a standard JSON payload object, and sends a fetch request to the backend service.
- **appendMessage(sender, text)**: Handles DOM manipulation to dynamically build, format, and render speech bubbles into the view container

3. Service Interaction over Docker Network
The frontend and backend run inside distinct containers isolated from your host system. They communicate over a custom defined virtual Docker network ai_pipeline_network using a bridge driver. This allows the frontend to stream data queries to the backend using automatic Docker internal DNS name resolution (http://backend:8000) instead of hardcoding volatile, temporary IP coordinates.

## Data Flows & System Assumptions

### Data Architecture
Data is modeled as single asynchronous requests containing structural string attributes. During a session request, the transaction flows as follows:
- The user inputs text or attaches a document in the browser window.  
- The frontend processes actions, aggregates payload states, and dispatches an asynchronous HTTP request over the internal network.  
- The FastAPI backend captures the payload, verifies matching operational conditions, invokes the model logic via script processing, and serializes a clean JSON output response back to the client UI. 

### Core Project Assumptions
- Input Document State: It is assumed that text data sent inside pdf_text is fully compiled, clean, and uncorrupted text data layers.  
- Context/Size Limits: Processing models assume text constraints conform to standard prompt context windows. Massive datasets or overly large documents may degrade inference performance or hit API request size caps.  
- AI Model Pipeline Integration: Models from Week 2 are structured into isolated stateless functions (prompt_model and find_skill_gaps) that accept static file parameters or textual requests directly without native session persistence layers.  

## Testing

### Frontend Test Suites
- Execute user input simulation: Verify message transmission by typing distinct strings into the chatbot and confirming speech layer placement.  
- Validation of attachment fields: Upload test resume data and verify that text contexts append cleanly without interface crashing.  

### Backend Validation Testing
- Reproduction with curl: You can test raw API functionality directly using your terminal:
    ```bash
    curl -X POST "http://localhost:8001/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "hi", "pdf_text": ""}'
     ```
- Verification of Container Communication: Internal system communication check is performed by running docker compose ps to ensure both layers run correctly in step, followed by checking server streams using docker compose logs -f to observe structural traffic crossing the custom network bridge.

## Limitations
- Lack of Session Persistence: Chat histories do not persist; refreshing your browser resets your active chatbot session layout state.  
- Lack of Authentication Layers: The API services are entirely open and omit user access rules or authentication guards.  
- Inference Speeds & Rate Bounds: Processing depends heavily on underlying third-party host rates or local computing iron capabilities when calling local Ollama setups, which can sometimes produce latency spikes.  
- Model Factuality: Like all LLM architectures, responses can experience contextual inaccuracies based on prompt styling limitations.  

## Architecture & Design Reflection

### Design Choices
Choosing a modern Microservices Architecture allows complete isolation of duties. The frontend layer is dedicated solely to interface state rendering, while the backend focuses completely on data processing, file work, and AI pipeline routing.  

Containerizing the individual environments via Docker completely eliminates environmental inconsistencies across different operational systems (such as path formatting differences between Windows and Linux systems)

### Trade-offs & Priorities
We chose to explicitly prioritize Simplicity of Configuration and Deployment Speed through unified Docker Compose management over extreme horizontal scale configurations. Keeping the network topology centralized around a lightweight, isolated bridge network allowed for fast local development cycle iterations, prioritizing a clean, minimalist chat interface layout instead of over-complicating state mechanics at an early development stage.  

### Improvements
- Migrate the data state layer to a production-grade external persistent storage system (e.g., PostgreSQL) to track user accounts and save chat session history logs.  
- Transition the frontend implementation to a robust Single Page Application framework (such as React + Vite) to build out richer UI states. 