import re

from rich.console import Group
from rich.markup import escape
from rich.text import Text

from .display import console, jarv_panel

SAFETY_LEVELS = ("all", "risky", "none")
DEFAULT_SAFETY_LEVEL = "risky"

# Each pattern is (compiled_regex, description) for user-facing confirmation.
# Patterns are designed to work across Windows (PowerShell/cmd) and Unix shells.
_RISKY_PATTERNS: list[tuple[re.Pattern, str]] = []


def _p(pattern: str, description: str) -> None:
    _RISKY_PATTERNS.append((re.compile(pattern, re.IGNORECASE), description))


# ── Destructive filesystem operations ─────────────────────────────────────
_p(r"\brm\s+(-[^\s]*[rf]|--recursive|--force)", "recursive/forced file deletion (rm)")
_p(r"\brmdir\s+/s\b", "recursive directory deletion (rmdir /s)")
_p(r"\bdel\s+.*/[sqf]", "forced file deletion (del)")
_p(r"\bRemove-Item\b.*-(Recurse|Force)", "recursive/forced file deletion (Remove-Item)")
_p(r"\bshred\b", "secure file destruction (shred)")
_p(r"\bwipe\b", "disk/file wiping")

# ── Disk / partition operations ───────────────────────────────────────────
_p(r"\bformat\s+[a-zA-Z]:", "drive formatting (format)")
_p(r"\bFormat-Volume\b", "volume formatting (Format-Volume)")
_p(r"\bmkfs\b", "filesystem creation (mkfs)")
_p(r"\bfdisk\b", "partition editing (fdisk)")
_p(r"\bparted\b", "partition editing (parted)")
_p(r"\bdiskpart\b", "disk partitioning (diskpart)")
_p(r"\bdd\s+if=", "raw disk copy (dd)")

# ── Privilege escalation ──────────────────────────────────────────────────
_p(r"\bsudo\b", "elevated privileges (sudo)")
_p(r"\bdoas\b", "elevated privileges (doas)")
_p(r"\brunas\b", "elevated privileges (runas)")
_p(r"\bchmod\s+[0-7]*[67][0-7]{2}\b", "broad permission grant (chmod)")
_p(r"\bchmod\s+.*[ugoa]*\+[rwxsStX]*[sS]", "setuid/setgid (chmod +s)")
_p(r"\bchown\b", "ownership change (chown)")
_p(r"\bicacls\b.*(/grant|/remove|/deny)", "permission change (icacls)")

# ── Network exfiltration / remote code execution ─────────────────────────
_p(r"\bcurl\b.*\|\s*(sudo\s+)?(bash|sh|zsh|dash|powershell|pwsh)\b", "remote code execution (curl | shell)")
_p(r"\bwget\b.*\|\s*(sudo\s+)?(bash|sh|zsh|dash|powershell|pwsh)\b", "remote code execution (wget | shell)")
_p(r"\bwget\b.*-O\s*-.*\|", "remote code execution (wget -O - | ...)")
_p(r"\b(Invoke-WebRequest|Invoke-RestMethod|irm|iwr)\b.*\|\s*(Invoke-Expression|iex)\b", "remote code execution (IWR | IEX)")
_p(r"\b(iex|Invoke-Expression)\s*\(.*\b(Invoke-WebRequest|irm|iwr|Invoke-RestMethod)\b", "remote code execution (iex + IWR)")
_p(r"\bInvoke-Expression\b", "dynamic code execution (Invoke-Expression)")
_p(r"\biex\s+[^|]", "dynamic code execution (iex)")
_p(r"\bnc\b\s+.*-[el]", "netcat listener/exec")
_p(r"\bncat\b", "ncat network connection")
_p(r"\bscp\b", "secure copy to remote (scp)")
_p(r"\brsync\b.*[^/]\w+@\w+:", "remote sync (rsync to remote host)")

# ── System modification ──────────────────────────────────────────────────
_p(r"\breg\s+(delete|add)\b", "registry modification (reg)")
_p(r"\bNew-ItemProperty\b.*Registry", "registry modification (PowerShell)")
_p(r"\bRemove-ItemProperty\b.*Registry", "registry modification (PowerShell)")
_p(r"\bsystemctl\s+(disable|stop|mask)\b", "service control (systemctl)")
_p(r"\blaunchctl\s+(unload|remove)\b", "service control (launchctl)")
_p(r"\bschtasks\s+/(create|delete)\b", "scheduled task modification (schtasks)")
_p(r"\bcrontab\s+-[re]", "cron job modification (crontab)")

# ── Process / service killing ────────────────────────────────────────────
_p(r"\btaskkill\b", "process termination (taskkill)")
_p(r"\bkill\s+-9\b", "forced process kill (kill -9)")
_p(r"\bkillall\b", "mass process termination (killall)")
_p(r"\bpkill\b", "pattern-based process kill (pkill)")
_p(r"\bStop-Process\b", "process termination (Stop-Process)")
_p(r"\bStop-Service\b", "service stop (Stop-Service)")

# ── Package manager (global / system-wide) ───────────────────────────────
_p(r"\b(pip|pip3)\s+install\b(?!.*--user)(?!.*-e\s+\.)(?!.*--target)", "global pip install")
_p(r"\b(python|python3)\s+-m\s+pip\s+install\b(?!.*--user)(?!.*-e\s+\.)(?!.*--target)", "global pip install")
_p(r"\bnpm\s+(install|i)\s+.*-g\b|\bnpm\s+.*-g\s+(install|i)\b", "global npm install")
_p(r"\bchoco\s+(install|uninstall)\b", "Chocolatey package management")
_p(r"\bwinget\s+(install|uninstall)\b", "winget package management")
_p(r"\bbrew\s+(install|uninstall|remove)\b", "Homebrew package management")
_p(r"\bapt(-get)?\s+(install|remove|purge)\b", "apt package management")
_p(r"\byum\s+(install|remove|erase)\b", "yum package management")
_p(r"\bdnf\s+(install|remove|erase)\b", "dnf package management")
_p(r"\bpacman\s+-[SRU]", "pacman package management")

# ── Credential / secret access ───────────────────────────────────────────
_p(r"\b(cat|less|more|head|tail)\s+.*\.(env|pem|key|p12|pfx|jks)\b", "reading secrets file")
_p(r"\btype\s+.*\.(env|pem|key|p12|pfx)\b", "reading secrets file")
_p(r"\bGet-Content\b.*\.(env|pem|key|p12|pfx)\b", "reading secrets file")
_p(r"\b(cat|type|less|more|Get-Content)\b.*[/\\]\.ssh[/\\]", "reading SSH keys")
_p(r"\bssh-keygen\b", "SSH key generation")
_p(r"\b(cat|type|Get-Content)\b.*[/\\]\.gnupg[/\\]", "reading GPG keys")

# ── Git destructive operations ───────────────────────────────────────────
_p(r"\bgit\s+push\s+.*(-f\b|--force\b)(?!.*--force-with-lease)", "force push (git push --force)")
_p(r"\bgit\s+reset\s+--hard\b", "hard reset (git reset --hard)")
_p(r"\bgit\s+clean\s+-[^\s]*f", "forced clean (git clean -f)")
_p(r"\bgit\s+checkout\s+--\s+\.", "discard all changes (git checkout -- .)")
_p(r"\bgit\s+branch\s+-D\b", "force delete branch (git branch -D)")

# ── Environment / shell manipulation ─────────────────────────────────────
_p(r"\bexport\s+(PATH|LD_PRELOAD|LD_LIBRARY_PATH)=", "environment variable modification")
_p(r"\bsetx\s+(PATH|PATHEXT)\b", "permanent environment modification (setx)")
_p(r"\$env:(PATH|PATHEXT)\s*=", "environment modification (PowerShell)")
_p(r"\bSet-ExecutionPolicy\b", "PowerShell execution policy change")
_p(r"\beval\s+\$\(", "dynamic shell evaluation (eval)")
_p(r"\bsource\s+/dev/stdin\b", "sourcing from stdin")


def classify_command(command: str) -> tuple[bool, str]:
    """Check whether a command matches any risky pattern.

    Returns (is_risky, description).  description is empty when not risky.
    """
    for pattern, description in _RISKY_PATTERNS:
        if pattern.search(command):
            return True, description
    return False, ""


def prompt_confirmation(command: str, reason: str) -> bool:
    """Ask the user to approve a risky command.  Returns True if approved."""
    reason_line = Text.from_markup(
        f"[bold yellow]\u26a0  Risky command[/bold yellow]  [dim]\u2014[/dim]  [yellow]{escape(reason)}[/yellow]"
    )
    command_line = Text.assemble(
        ("$ ", "bold bright_black"),
        (command, "bold bright_white"),
    )
    body = Group(reason_line, Text(""), command_line)

    console.print()
    console.print(jarv_panel(body, title="safety", subtitle="confirm to run", padding=(1, 2)))

    prompt = "[bold]Allow this command?[/bold] [dim]\\[y/N][/dim] [bold cyan]\u203a[/bold cyan] "
    try:
        choice = console.input(prompt).strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("[dim]  denied.[/dim]")
        return False

    approved = choice in ("y", "yes")
    if approved:
        console.print("[green]  \u2713 approved[/green]\n")
    else:
        console.print("[red]  \u2717 denied[/red]\n")
    return approved


def check_command(command: str, safety_level: str) -> tuple[bool, str]:
    """Gate a command according to the configured safety level.

    Returns (allowed, denial_message).
    - allowed=True  → caller should execute the command.
    - allowed=False → caller should return denial_message to the model.
    """
    if safety_level == "none":
        return True, ""

    if safety_level == "all":
        if not prompt_confirmation(command, "all commands require approval"):
            return False, "[command denied by user — safety level is set to 'all']"
        return True, ""

    # "risky" (default)
    is_risky, reason = classify_command(command)
    if is_risky:
        if not prompt_confirmation(command, reason):
            return False, f"[command denied by user — detected as risky: {reason}]"
    return True, ""
