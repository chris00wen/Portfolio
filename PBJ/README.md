# PBJ --- Prompt Builder Jam

*A modular, structured, multi-LLM prompt-engineering toolkit*

PBJ (Prompt Builder Jam) is a flexible framework for building
**reliable, reusable, and well-structured prompts** across multiple LLM
platforms. It simplifies complex prompt workflows by organizing your
prompts into consistent templates, reusable steps, best-practice
frameworks, and versioned JSON definitions.

PBJ is designed for **AI developers, data scientists, and enterprise
teams** who need clarity, repeatability, and governance in their LLM
prompting workflows.

## 🎯 Core Features

### Structured Prompt Frameworks

Create prompts using reusable building blocks: 
- FrameworkSpec definitions
- Stepwise prompt construction
- Modular building patterns (CRAFT, TAP, custom workflows)

### Multi-Model Dispatching

PBJ can transparently send prompts to: 
- OpenAI models
- Llama-cpp / local GGUF models
- Gemma
- Claude
- Any REST-based LLM endpoint

### Template Storage & Versioning

PBJ stores prompts as JSON templates with: 
- Version control
- Optional RBAC-ready metadata
- Template types and categories
- Reusable components (StepSpecs, FieldSpecs)

### Elegant Streamlit UI

-   Sidebar-based navigation
-   Context-aware controls
-   Template browsing and editing

### Planned Future Features

-   Adding more templates and LLM model support
-   Prompt patterns suggestions
-   User logins to persist Prompt catalogs, API keys
-   Response analysis to reduce hallucinations

## 🚀 Getting Started

### Installation

``` bash
pip install -r requirements.txt
```

### Run the Streamlit App

``` bash
streamlit run src/pbj.py
```

### Basic Usage

1.  Choose a prompt framework (CRAFT, TAP, custom).\
2.  Fill in required prompt fields.\
3.  Render the final prompt.\
4.  Send to your selected LLM.\
5.  Save templates for reuse or team sharing.

## 📂 Repository Structure

    PBJ/
    ├── src/                    # Core package modules
    │   ├── llm_client.py       # LLM definitions
    │   ├── pbj.py              # Core logic & UI
    │   └── templates.py        # template definitions
    ├── models/
    ├── tests/
    ├── prompt_templates.json
    ├── README.md
    └── requirements.txt    

## 🧠 Why PBJ?

Modern LLM workflows demand: 
- Structure
- Consistency
- Versioning
- Clarity
- Multi-model flexibility

PBJ gives you a unified system for all of that --- ideal for engineering
teams, analytics groups, or personal AI projects.

## 📬 Contact

Questions or suggestions?
Reach me on LinkedIn: https://www.linkedin.com/in/chris0wen
