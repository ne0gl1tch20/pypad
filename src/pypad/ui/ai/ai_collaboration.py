from ._plugin_bridge import export_runtime_symbols

try:
    export_runtime_symbols(globals(), "ai_collaboration")
except ImportError:
    def build_ai_conflict_merge_prompt(local_text: str, shared_text: str) -> str:
        return (
            "AI collaboration is unavailable because 'pypad_ai_assistant' is disabled.\n\n"
            f"Local:\n{local_text}\n\nShared:\n{shared_text}"
        )

    def build_conflict_markers(local_text: str, shared_text: str, title: str = "Conflict") -> str:
        return (
            f"<<<<<<< {title}:local\n{local_text}\n=======\n{shared_text}\n>>>>>>> {title}:shared\n"
        )

    def build_project_qa_prompt(question: str, snippets: str, project_name: str = "") -> str:
        name = str(project_name or "Project")
        return f"[AI unavailable] {name}\nQuestion: {question}\n\n{snippets}"

    def build_workspace_citation_snippets(*_args, **_kwargs):
        return []

    def build_collab_presence_text(*_args, **_kwargs) -> str:
        return "AI collaboration unavailable."

    def paragraph_bounds(text: str, index: int) -> tuple[int, int]:
        i = max(0, min(len(text), int(index)))
        return i, i

    def strip_model_fences(text: str) -> str:
        return str(text or "").strip()

    __all__ = [
        "build_ai_conflict_merge_prompt",
        "build_conflict_markers",
        "build_project_qa_prompt",
        "build_workspace_citation_snippets",
        "build_collab_presence_text",
        "paragraph_bounds",
        "strip_model_fences",
    ]
