import os

from rich.prompt import Prompt
from rich.text import Text

from .display import console, jarv_panel, section_rule


MODELS = [
    ("gpt-5.5", "Largest, slowest, smartest"),
    ("gpt-5.4-mini", "Smaller, faster, cheaper"),
    ("gpt-5.4-nano", "Smallest, fastest, cheapest"),
]


def run_setup_wizard() -> dict | None:
    """Run the interactive setup wizard. Returns updated config or None if the
    user needs to set their env var first."""
    from .config import load_config, save_config

    console.print()
    console.print(jarv_panel(
        Text.from_markup(
            "[bold]Welcome to jarv![/bold]\n\n"
            "Let's get you set up. This will only take a moment."
        ),
        title="setup",
    ))

    config = load_config()

    # --- API key ---
    console.print()
    console.print(section_rule("API Key"))

    env_key = os.environ.get("OPENAI_API_KEY", "")
    config_key = config.get("api_key", "")
    if env_key:
        masked = env_key[:7] + "..." + env_key[-4:]
        console.print(f"\n  [green]Found[/green] OPENAI_API_KEY in your environment [dim]({masked})[/dim]")
    elif config_key:
        masked = config_key[:7] + "..." + config_key[-4:]
        console.print(f"\n  [green]Found[/green] API key in config [dim]({masked})[/dim]")
    else:
        console.print(f"\n  [dim]You'll need an OpenAI API key. Get one at[/dim] [cyan]https://platform.openai.com/api-keys[/cyan]")
        console.print()
        api_key = _prompt_api_key()
        config["api_key"] = api_key

    # --- Model ---
    console.print()
    console.print(section_rule("Model"))
    console.print()

    for i, (name, desc) in enumerate(MODELS, 1):
        default_tag = " [bold green](default)[/bold green]" if i == 1 else ""
        console.print(f"  [bold cyan]{i}.[/bold cyan] [bold]{name}[/bold] — [dim]{desc}[/dim]{default_tag}")
    console.print()

    choice = Prompt.ask(
        "  Pick a model [dim](number or name, Enter for default)[/dim]",
        default="1",
        console=console,
    ).strip()

    model = _resolve_model(choice)
    config["model"] = model
    save_config(config)

    # --- Done ---
    console.print()
    if env_key:
        key_display = "[dim](from OPENAI_API_KEY env var)[/dim]"
    else:
        key_display = "[dim](saved to config)[/dim]"
    console.print(jarv_panel(
        Text.from_markup(
            f"[bold green]You're all set![/bold green]\n\n"
            f"  API key   {key_display}\n"
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
    try:
        idx = int(choice)
        if 1 <= idx <= len(MODELS):
            return MODELS[idx - 1][0]
    except ValueError:
        pass

    for name, _ in MODELS:
        if choice.lower() == name.lower():
            return name

    return MODELS[0][0]
