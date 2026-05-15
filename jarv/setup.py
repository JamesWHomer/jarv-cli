import os

from rich.prompt import Prompt, Confirm
from rich.text import Text

from .display import console, jarv_panel, section_rule


MODELS = [
    ("gpt-5.4-mini", "Fast & cheap — great default"),
    ("gpt-4.1-nano", "Fastest, lowest cost"),
    ("gpt-4.1-mini", "Balanced speed and quality"),
    ("gpt-4.1", "High quality, slower"),
    ("o4-mini", "Reasoning model, best for complex tasks"),
]


def run_setup_wizard() -> dict:
    from .config import DEFAULT_CONFIG

    console.print()
    console.print(jarv_panel(
        Text.from_markup(
            "[bold]Welcome to jarv![/bold]\n\n"
            "Let's get you set up. This will only take a moment."
        ),
        title="setup",
    ))
    console.print()

    # --- API key ---
    console.print(section_rule("API Key"))
    console.print()

    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key:
        masked = env_key[:7] + "..." + env_key[-4:]
        console.print(f"  [green]Found[/green] OPENAI_API_KEY in your environment [dim]({masked})[/dim]")
        use_env = Confirm.ask("  Use this key?", default=True, console=console)
        if use_env:
            api_key = ""
        else:
            api_key = _prompt_api_key()
    else:
        console.print("  [dim]You'll need an OpenAI API key. Get one at[/dim] [cyan]https://platform.openai.com/api-keys[/cyan]")
        console.print()
        api_key = _prompt_api_key()

    # --- Model ---
    console.print()
    console.print(section_rule("Model"))
    console.print()
    for i, (name, desc) in enumerate(MODELS, 1):
        default_tag = " [bold green](default)[/bold green]" if name == DEFAULT_CONFIG["model"] else ""
        console.print(f"  [bold cyan]{i}.[/bold cyan] [bold]{name}[/bold] — [dim]{desc}[/dim]{default_tag}")
    console.print()

    choice = Prompt.ask(
        "  Pick a model [dim](number or name, Enter for default)[/dim]",
        default="1",
        console=console,
    ).strip()

    model = _resolve_model(choice)

    # --- Build config ---
    config = dict(DEFAULT_CONFIG)
    config["api_key"] = api_key
    config["model"] = model

    # --- Done ---
    console.print()
    display_key = "[dim](from environment)[/dim]" if not api_key and env_key else "[dim]***[/dim]"
    console.print(jarv_panel(
        Text.from_markup(
            f"[bold green]You're all set![/bold green]\n\n"
            f"  API key   {display_key}\n"
            f"  Model     [bold]{model}[/bold]\n\n"
            f"[dim]Run [bold]jarv /config[/bold] to view settings or [bold]jarv /set <key> <value>[/bold] to change them.[/dim]"
        ),
        title="ready",
    ))
    console.print()

    return config


def _prompt_api_key() -> str:
    while True:
        key = Prompt.ask("  Enter your OpenAI API key", console=console).strip()
        if key.startswith("sk-") and len(key) > 10:
            return key
        console.print("  [red]That doesn't look like a valid key[/red] [dim](should start with sk-)[/dim]")


def _resolve_model(choice: str) -> str:
    from .config import DEFAULT_CONFIG

    try:
        idx = int(choice)
        if 1 <= idx <= len(MODELS):
            return MODELS[idx - 1][0]
    except ValueError:
        pass

    for name, _ in MODELS:
        if choice.lower() == name.lower():
            return name

    return DEFAULT_CONFIG["model"]
