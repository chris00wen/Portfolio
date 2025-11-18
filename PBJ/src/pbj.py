# pbj_app.py — Prompt Builder Jam (main Streamlit app)
import json
import os
from uuid import uuid4
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from templates import FRAMEWORKS  # registry + specs + assemblers
from LLMClient import LLMClient

# =============================================================
# LLM provider registry and simple .env loader
# =============================================================
# LLM_PROVIDERS = ["OpenAI", "Anthropic", "Llama", "Gemma"]  # adjust to your actual providers
LLM_PROVIDERS = ["OpenAI", "Llama"]  # adjust to your actual providers
LOCAL_LLMS = ["Llama", "Gemma"]      # those that run locally, no API key needed


def load_env_keys(env_path: str = ".env") -> Dict[str, str]:
    """
    Read simple KEY=VALUE lines from a local .env file and return as dict.
    Lines starting with # are ignored. No interpolation.
    """
    keys: Dict[str, str] = {}
    if not os.path.exists(env_path):
        return keys
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return keys


# =============================================================
# Simple JSON storage for templates (by title)
#TODO: migrate to a real DB for more robust storage
# =============================================================
STORAGE_FILE = "prompt_templates.json"


def load_templates() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(STORAGE_FILE):
        return {}
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_templates(data: Dict[str, Dict[str, Any]]) -> None:
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================
# Session state init
# =============================================================
def ensure_state():
    ss = st.session_state
    ss.setdefault("templates", load_templates())     # { title: {id, title, framework, values} }
    ss.setdefault("selected_type", None)             # framework name
    ss.setdefault("selected_tab", "List")            # tab screen (List, Edit, Responses)
    ss.setdefault("next_tab", "List")                # tab screen (List, Edit, Responses)
    ss.setdefault("selected_title", None)            # template title (key into templates)
    ss.setdefault("values", {})                      # editor values (dict)
    ss.setdefault("dirty", False)                    # editor dirty flag
    ss.setdefault("delete_target_title", None)       # for delete modal
    ss.setdefault("saveas_open", False)              # for Save As modal
    ss.setdefault("saveas_name", "")                 # new name

    # LLM output + keys
    ss.setdefault("llm_response", "")
    ss.setdefault("llm_responses", {})               # { provider_name: response_str }
    ss.setdefault("llm_selected_view", None)         # which provider to view on Response page
    ss.setdefault("llm_sidebar_selected", [])        # list of providers to send to on Send action

    # per-LLM configuration: api_key (optional), enabled flag, and type ('api' | 'local')
    default_configs = {}
    for p in LLM_PROVIDERS:
        default_configs[p] = {
            "api_key": None,
            "enabled": True if p in LOCAL_LLMS else False,
            "type": "local" if p in LOCAL_LLMS else "api",
        }
    ss.setdefault("llm_configs", default_configs)
    ss.setdefault("enter_key_for_provider", None)    # temp holder to drive API key dialog
    ss.setdefault("llm_edit_provider", None)         # which provider is currently being edited

    # load .env keys into session (do not overwrite user-provided keys)
    env_keys = load_env_keys()
    for p in LLM_PROVIDERS:
        lookup = f"{p.upper()}_API_KEY"
        if lookup in env_keys:
            cfg = ss["llm_configs"].get(p, {})
            if not cfg.get("api_key"):
                cfg["api_key"] = env_keys[lookup]
                ss["llm_configs"][p] = cfg

# =============================================================
# Helpers
# =============================================================
def sorted_types() -> List[str]:
    return sorted(FRAMEWORKS.keys())


def current_spec():
    name = st.session_state.get("selected_type")
    return FRAMEWORKS.get(name) if name else None


def assemble_preview() -> str:
    spec = current_spec()
    if not spec:
        return ""
    try:
        values = st.session_state["values"]
        return spec.assemble(st.session_state["values"])
    except Exception as e:
        return f"[Error assembling prompt: {e}]"


def mark_dirty():
    st.session_state["dirty"] = True


def reset_editor_from_template(title: str):
    """Load values from a saved template into the editor and switch to editor mode."""
    selected_tab = st.session_state["selected_tab"]
    tpl = st.session_state["templates"][title]
    st.session_state.update({
        "selected_title": title,
        "values": dict(tpl.get("values", {})),
        "dirty": False,
        "next_tab": "Edit",
    })
    st.rerun()


def new_editor_for_type(framework_name: str):
    """Open a blank editor for a given type."""
    st.session_state.update({
        "selected_title": None,
        "values": {},
        "dirty": False,
    })


def delete_template(title: str):
    tpls = st.session_state["templates"]
    if title in tpls:
        del tpls[title]
        save_templates(tpls)
    if st.session_state.get("selected_title") == title:
        st.session_state["selected_title"] = None


# =============================================================
# UI pieces
# =============================================================
def header_bar():
    st.title("Prompt Builder Jam")
    with st.container():
        cols = st.columns([2, 4, 2])
        with cols[0]:
            st.caption("Template Type")
            initial_type = None
            if st.session_state.get("selected_title"):
                template = st.session_state["templates"][st.session_state["selected_title"]]
                initial_type = template.get("framework")

            types = sorted_types()
            type_index = types.index(initial_type) if initial_type in types else 0

            st.selectbox(
                "Type",
                options=types,
                index=type_index if types else None,
                key="selected_type",
                label_visibility="collapsed",
            )
        with cols[1]:
            pass  # spacer
        with cols[2]:
            if st.button("New Template", use_container_width=True):
                st.session_state.update({
                    "selected_title": None,
                    "values": {},
                    "dirty": False,
                })


@st.dialog("Confirm Delete")
def show_delete_dialog():
    t = st.session_state["delete_target_title"]
    st.warning(f"Delete the template **{t}**? This cannot be undone.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Delete", type="primary"):
            delete_template(t)
            st.session_state["delete_target_title"] = None
            st.success("Deleted.")
            st.rerun()
    with c2:
        if st.button("Cancel"):
            st.session_state["delete_target_title"] = None
            st.rerun()


def list_mode():
    st.subheader("Templates")
    spec = current_spec()
    if not spec:
        st.info("No Template Type selected.")
        return

    templates = st.session_state["templates"]
    filtered_templates = {
        title: tpl for title, tpl in templates.items()
        if tpl.get("framework") == spec.name
    }

    if not filtered_templates:
        st.info("No templates saved for this type yet.")
        return

    header_cols = ["Title", "View", "Delete"]
    col_widths = [8, 1, 1]  # Adjusted widths for Title, View, and Delete
    col_defs = st.columns(col_widths)  # Create columns for headers

    for i, h in enumerate(header_cols):
        with col_defs[i]:
            st.markdown(f"**{h}**")

    for title in sorted(filtered_templates.keys()):
        with st.container():
            cols = st.columns([8, 1, 1])
            with cols[0]:
                st.write(f"**{title}**")
            with cols[1]:
                if st.button("👁️", key=f"view_{title}"):
                    reset_editor_from_template(title)
            with cols[2]:
                if st.button("🗑️", key=f"delete_{title}"):
                    st.session_state["delete_target_title"] = title
                    show_delete_dialog()


def render_field(field, values: Dict[str, Any]):
    st.markdown(
        """
        <style>
        .stTextInput, .stTextArea {
            margin-bottom: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    key = field.key
    label = field.label
    placeholder = field.placeholder or ""
    help_txt = field.help or ""
    req = field.required

    if key not in values:
        values[key] = ""

    if field.widget == "textarea":
        st.text_area(
            label,
            value=values.get(key, ""),
            key=f"inp_{key}",
            placeholder=placeholder,
            help=help_txt,
            on_change=lambda: on_widget_change(key),
            height=120,
        )
    elif field.widget == "examples":
        st.text_area(
            label,
            value=values.get(key, ""),
            key=f"inp_{key}",
            placeholder=placeholder,
            help=help_txt,
            on_change=lambda: on_widget_change(key),
            height=100,
        )
    else:
        st.text_input(
            label,
            value=values.get(key, ""),
            key=f"inp_{key}",
            placeholder=placeholder,
            help=help_txt,
            on_change=lambda: on_widget_change(key),
        )

    if req:
        st.caption(":red[* required]")


def on_widget_change(field_key: str):
    st.session_state["values"][field_key] = st.session_state.get(f"inp_{field_key}", "")
    mark_dirty()


@st.dialog("Save Template As…")
def show_save_as_dialog():
    st.text_input("New template name", key="saveas_name")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save"):
            name = (st.session_state.get("saveas_name") or "").strip()
            if not name:
                st.error("Please enter a name.")
            else:
                spec = current_spec()
                do_save_as(spec, name)
                st.session_state["saveas_open"] = False
                st.rerun()
    with c2:
        if st.button("Cancel"):
            st.session_state["saveas_open"] = False
            st.rerun()


def editor_mode():
    spec = current_spec()
    if not spec:
        st.info("Pick a Template Type to start.")
        return

    title = st.session_state.get("selected_title")
    heading = title if title else f"New {spec.name} Template"
    st.subheader(heading)

    left, right = st.columns([2, 2], vertical_alignment="top")

    with left:
        for f in spec.fields:
            render_field(f, st.session_state["values"])
            st.divider()

        b1, b2, b3 = st.columns([1, 1, 2])
        with b1:
            disabled = not st.session_state["dirty"]
            if st.button("Save", type="primary", disabled=disabled):
                do_save_current(spec)

        with b2:
            if st.button("Save As…"):
                st.session_state["saveas_open"] = True
                st.session_state["saveas_name"] = (title + " (copy)") if title else ""
                show_save_as_dialog()

        with b3:
            if st.button("Back to List"):
                st.session_state["selected_tab"] = "List"
                st.session_state["next_tab"] = "List"
                st.rerun()

    with right:
        st.markdown("#### Final Prompt Preview")
        st.code(assemble_preview(), language="markdown")

        st.markdown("#### Run Prompt")
        st.caption("To run this prompt against selected LLMs, go to the Responses tab.")
        if st.button("Go to Responses"):
            st.session_state["next_tab"] = "Responses"
            st.session_state["selected_tab"] = "Responses"
            st.rerun()


def do_save_current(spec):
    """Save over the current template title; if no title, prompt Save As."""
    title = st.session_state.get("selected_title")
    if not title:
        st.session_state["saveas_open"] = True
        st.session_state["saveas_name"] = ""
        return

    tpls = st.session_state["templates"]
    tpls[title] = {
        "id": tpls.get(title, {}).get("id", str(uuid4())),
        "title": title,
        "framework": spec.name,
        "values": dict(st.session_state["values"]),
    }
    save_templates(tpls)
    st.session_state["dirty"] = False
    st.success("Template saved.")


def do_save_as(spec, new_name: str):
    tpls = st.session_state["templates"]
    if new_name in tpls:
        st.error("A template with that name already exists.")
        return
    tpls[new_name] = {
        "id": str(uuid4()),
        "title": new_name,
        "framework": spec.name,
        "values": dict(st.session_state["values"]),
    }
    save_templates(tpls)
    st.session_state["selected_title"] = new_name
    st.session_state["dirty"] = False
    st.success(f"Saved as “{new_name}”.")


# =============================================================
# LLM configuration & sidebar
# =============================================================
def mask_key(k: str) -> str:
    if not k:
        return "No API Key"
    s = str(k)
    if len(s) <= 4:
        return "API Key: …" + s
    return "API Key: …" + s[-4:]


def request_llm_config(provider: str):
    st.session_state["llm_edit_provider"] = provider
    show_llm_config_dialog()


@st.dialog("Configure LLM")
def show_llm_config_dialog():
    p = st.session_state.get("llm_edit_provider")
    if not p:
        st.info("No provider selected.")
        return
    cfg = st.session_state["llm_configs"].get(p, {"api_key": None, "enabled": False, "type": "api"})
    st.header(f"Configure {p}")
    if cfg["type"] == "local":
        st.markdown("Local model — no API key required.")
        enabled = st.checkbox("Enable for use", value=cfg.get("enabled", False), key=f"dlg_enabled_{p}")
        if st.button("Save", key=f"dlg_save_{p}"):
            cfg["enabled"] = bool(enabled)
            st.session_state["llm_configs"][p] = cfg
            st.session_state["llm_edit_provider"] = None
            st.success("Saved.")
            st.rerun()
        if st.button("Cancel", key=f"dlg_cancel_{p}"):
            st.session_state["llm_edit_provider"] = None
            st.rerun()
        return

    current_key = cfg.get("api_key") or ""
    api_input = st.text_input("API Key", value=current_key, type="password", key=f"dlg_key_{p}")
    enabled = st.checkbox("Enable for use", value=cfg.get("enabled", False), key=f"dlg_enabled_{p}")
    if not api_input:
        st.caption("Enter an API key to enable the provider.")
        st.button("Save", disabled=True, key=f"dlg_save_disabled_{p}")
    else:
        if st.button("Save", key=f"dlg_save_{p}"):
            cfg["api_key"] = api_input
            cfg["enabled"] = bool(enabled)
            st.session_state["llm_configs"][p] = cfg
            st.session_state["llm_edit_provider"] = None
            st.success("Saved.")
            st.rerun()
    if st.button("Cancel", key=f"dlg_cancel_{p}"):
        st.session_state["llm_edit_provider"] = None
        st.rerun()


def render_sidebar():
    tabs = ["List", "Edit", "Responses"]

    with st.sidebar:
        # --- View selector at top of sidebar ---
        st.header("Prompt Builder Jam")

        # Use next_tab (for programmatic navigation) if set, otherwise selected_tab, otherwise "List"
        default_tab = st.session_state.get(
            "next_tab",
            st.session_state.get("selected_tab", "List"),
        )
        if default_tab not in tabs:
            default_tab = "List"

        selected_tab = st.radio(
            "Select View",
            tabs,
            index=tabs.index(default_tab),
            key="selected_tab",
        )

        # Keep next_tab in sync with the user's choice
        st.session_state["next_tab"] = selected_tab

        # --- Separator before LLM Management section ---
        st.markdown("---")

        st.header("LLM Management")
        if selected_tab != "Responses":
            st.caption("Open Responses tab to configure and run LLMs.")
            return

        st.markdown("### Providers")
        for p in LLM_PROVIDERS:
            cfg = st.session_state["llm_configs"].get(
                p, {"api_key": None, "enabled": False, "type": "api"}
            )
            api_present = bool(cfg.get("api_key"))
            typ = cfg.get("type", "api")

            if typ == "local":
                bg = "#d4f8d4" if cfg.get("enabled") else "#ffd6d6"
            else:
                if not api_present:
                    bg = "#999999"  # medium gray
                else:
                    bg = "#d4f8d4" if cfg.get("enabled") else "#ffd6d6"

            if typ == "local":
                key_html = "Local"
            else:
                key_html = mask_key(cfg.get("api_key"))

            box_html = f"""
            <div style="background:{bg};padding:10px;border-radius:6px;margin-bottom:8px;">
              <strong>{p}</strong><br/>
              <span style="font-weight:400;color:#222">{key_html}</span><br/>
            </div>
            """
            st.markdown(box_html, unsafe_allow_html=True)
            if st.button("Config", key=f"cfg_{p}", on_click=lambda prov=p: request_llm_config(prov)):
                pass


# =============================================================
# Multi-LLM send logic
# =============================================================
def build_client_for_provider(provider_name: str) -> tuple[str, LLMClient]:
    """
    Map UI provider name -> (label, LLMClient instance).
    """
    cfg = st.session_state["llm_configs"].get(provider_name, {})
    typ = cfg.get("type", "api")
    api_key = cfg.get("api_key")

    if typ == "api":
        if provider_name == "OpenAI":
            if not api_key:
                raise ValueError("OpenAI API key not configured.")
            client = LLMClient(
                provider="openai",
                api_key=api_key,
                model="gpt-4o-mini",
                temperature=0.7,
                max_output_tokens=1024,
            )
            label = "OpenAI (gpt-4o-mini)"
            return label, client
        # future: other API providers (Claude, etc.)
        raise NotImplementedError(f"API provider mapping not implemented for {provider_name}.")

    # local providers
    if provider_name == "Llama":
        client = LLMClient(
            provider="local_http",
            base_url="http://127.0.0.1:8001/v1/chat/completions",
            model="local-llama3",
            temperature=0.7,
            max_output_tokens=1024,
        )
        label = "Llama (local-llama3)"
        return label, client

    # placeholder for Gemma or others
    raise NotImplementedError(f"Local provider mapping not implemented for {provider_name}.")


def send_prompt_to_selected_llms():
    prompt = assemble_preview()

    llm_configs = st.session_state["llm_configs"]

    # Use all providers that are "enabled" in their Config dialog
    targets = [p for p, cfg in llm_configs.items() if cfg.get("enabled")]

    if not targets:
        st.error("No LLMs are enabled. Open a provider's Config and check 'Enable for use'.")
        return

    results = st.session_state.get("llm_responses", {})
    clients = []
    skipped = {}

    for p in targets:
        cfg = llm_configs.get(p, {})
        try:
            label, client = build_client_for_provider(p)
            clients.append((p, label, client))
        except NotImplementedError as e:
            skipped[p] = f"[Skipped: {e}]"
        except ValueError as e:
            skipped[p] = f"[Skipped: {e}]"
        except Exception as e:
            skipped[p] = f"[Error creating client for {p}: {e}]"

    if not clients and not skipped:
        st.error("No valid LLM clients configured.")
        return

    if clients:
        with st.spinner("Running prompt across selected models..."):
            with ThreadPoolExecutor(max_workers=len(clients)) as pool:
                fut_map = {
                    pool.submit(client.run_prompt, prompt): (provider, label)
                    for (provider, label, client) in clients
                }
                for fut in as_completed(fut_map):
                    provider, label = fut_map[fut]
                    try:
                        resp_text = fut.result()
                    except Exception as e:
                        resp_text = f"[Error calling {label}: {e}]"
                    results[provider] = resp_text

    # Attach skipped messages
    for p, msg in skipped.items():
        results[p] = msg

    st.session_state["llm_responses"] = results
    st.success("Requests complete.")
    st.rerun()


# =============================================================
# Responses page
# =============================================================
def responses_mode():
    st.subheader("Responses")

    llm_configs = st.session_state["llm_configs"]

    # LLMs that are enabled in their Config dialog
    enabled_providers = [p for p, cfg in llm_configs.items() if cfg.get("enabled")]

    # If nothing is enabled, show preview + hint
    if not enabled_providers:
        st.info("No LLMs are enabled. Use the Config buttons in the sidebar and check 'Enable for use'.")
        st.markdown("#### Final Prompt Preview")
        st.code(assemble_preview(), language="markdown")
        if st.button("Send to LLM", key="resp_send_btn_no_targets"):
            send_prompt_to_selected_llms()
        return

    # Optional: warn about any enabled API providers missing keys
    missing_keys = []
    for p in enabled_providers:
        cfg = llm_configs.get(p, {})
        if cfg.get("type") == "api" and not cfg.get("api_key"):
            missing_keys.append(p)

    if missing_keys:
        names = ", ".join(missing_keys)
        st.warning(f"API key not configured for: {names}. Configure them in the sidebar before sending.")

    # Prompt preview + global actions
    st.markdown("#### Final Prompt Preview")
    st.code(assemble_preview(), language="markdown")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Send to LLM", key="resp_send_btn_tabs"):
            send_prompt_to_selected_llms()
    with c2:
        if st.button("Clear Responses"):
            st.session_state["llm_responses"] = {}
            st.success("Cleared.")

    # Tabs for enabled providers only
    providers = enabled_providers
    tabs = st.tabs(providers)

    llm_responses = st.session_state.get("llm_responses", {})

    for provider, tab in zip(providers, tabs):
        with tab:
            resp = llm_responses.get(provider, "")
            if not resp:
                st.caption("No response yet for this model. Click 'Send to LLM' above to run the prompt.")
            st.text_area(
                f"{provider} Response",
                value=resp,
                height=400,
                label_visibility="collapsed",
            )


# =============================================================
# App
# =============================================================
def main():
    ensure_state()
    header_bar()

    # Sidebar now owns the Select View control
    render_sidebar()

    selected_tab = st.session_state.get("selected_tab", "List")

    if selected_tab == "List":
        list_mode()
    elif selected_tab == "Edit":
        editor_mode()
    elif selected_tab == "Responses":
        responses_mode()


if __name__ == "__main__":
    main()
