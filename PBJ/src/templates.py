# pbj_core.py — PBJ core types, registry, and framework specs
from dataclasses import dataclass
from typing import Callable, List, Dict, Any

@dataclass
class FieldSpec:
    key: str
    label: str
    widget: str = "text"        # "text", "textarea", "examples"
    placeholder: str = ""
    help: str = ""
    required: bool = False

@dataclass
class FrameworkSpec:
    name: str
    fields: List[FieldSpec]
    assemble: Callable[[Dict[str, Any]], str]

FRAMEWORKS: Dict[str, FrameworkSpec] = {}

def register_framework(spec: FrameworkSpec) -> None:
    FRAMEWORKS[spec.name] = spec

# ---------- Assemblers ----------
def assemble_craft(values: Dict[str, Any]) -> str:
    examples = values.get("examples", [])
    prompt = f"""
Context: {values.get('context','')}
Role: {values.get('role','')}
Action: {values.get('action','')}
Format: {values.get('format','')}
Tone: {values.get('tone','')}

Constraints: {values.get('constraints','')}
""".rstrip()
    if isinstance(examples, list):  # Ensure examples is a list
        if examples:
            prompt += "\n\nExamples:\n"
            for ex in examples:
                if isinstance(ex, dict):  # Ensure each example is a dictionary
                    prompt += f"\nInput:\n{ex.get('input','')}\nOutput:\n{ex.get('output','')}\n"
    return prompt.strip()

def assemble_prompt(values: Dict[str, Any]) -> str:
    examples = values.get("examples", [])
    prompt = f"""
You are {values.get('persona','')}.

Request: {values.get('request','')}
Output: {values.get('output','')}
Mechanics: {values.get('mechanics','')}
Parameters: {values.get('parameters','')}
Time: {values.get('time','')}
""".rstrip()
    if isinstance(examples, list):  # Ensure examples is a list
        if examples:
            prompt += "\n\nExamples:\n"
            for ex in examples:
                if isinstance(ex, dict):  # Ensure each example is a dictionary
                    prompt += f"\nInput:\n{ex.get('input','')}\nOutput:\n{ex.get('output','')}\n"
    return prompt.strip()

def assemble_tap(values: Dict[str, Any]) -> str:
    examples = values.get("examples", [])
    prompt = f"""
Task: {values.get('task','')}
Audience: {values.get('audience','')}
Purpose: {values.get('purpose','')}
""".rstrip()
    if isinstance(examples, list):  # Ensure examples is a list
        if examples:
            prompt += "\n\nExamples:\n"
            for ex in examples:
                if isinstance(ex, dict):  # Ensure each example is a dictionary
                    prompt += f"\nInput:\n{ex.get('input','')}\nOutput:\n{ex.get('output','')}\n"
    return prompt.strip()

# ---------- Register Frameworks ----------
register_framework(FrameworkSpec(
    name="CRAFT",
    fields=[
        FieldSpec("context", "Context", "textarea", help="Background, domain, data, constraints", required=True),
        FieldSpec("role", "Role", "text", placeholder="e.g., Senior Data Analyst", required=True),
        FieldSpec("action", "Action", "textarea", placeholder="What should the AI do?", required=True),
        FieldSpec("format", "Format", "text", placeholder="markdown table, JSON, bullets"),
        FieldSpec("tone", "Tone", "text", placeholder="professional, friendly, concise"),
        FieldSpec("constraints", "Constraints", "text", placeholder="word limits, exclusions"),
        FieldSpec("examples", "Examples", "examples", help="Few-shot input/output pairs - Enter a list of dictionaries"),
    ],
    assemble=assemble_craft
))

register_framework(FrameworkSpec(
    name="PROMPT",
    fields=[
        FieldSpec("persona", "Persona", "text", placeholder="Who should the model be?"),
        FieldSpec("request", "Request", "textarea", required=True),
        FieldSpec("output", "Output Format", "text", placeholder="markdown, JSON, code, bullets"),
        FieldSpec("mechanics", "Mechanics", "text", placeholder="step-by-step, rubric, reasoning hints"),
        FieldSpec("parameters", "Parameters", "text", placeholder="length, audience, tone"),
        FieldSpec("time", "Time", "text", placeholder="timeframe / recency"),
        FieldSpec("examples", "Examples", "examples", help="Few-shot input/output pairs - Enter a list of dictionaries"),
    ],
    assemble=assemble_prompt
))

register_framework(FrameworkSpec(
    name="TAP",
    fields=[
        FieldSpec("task", "Task", "textarea", required=True),
        FieldSpec("audience", "Audience", "text", placeholder="Who will read/use this?"),
        FieldSpec("purpose", "Purpose", "text", placeholder="Why are we doing this?"),
        FieldSpec("examples", "Examples", "examples", help="Few-shot input/output pairs - Enter a list of dictionaries"),
    ],
    assemble=assemble_tap
))
