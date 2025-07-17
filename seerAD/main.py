#!/usr/bin/env python3

# Standard library imports
import os
import shlex
import subprocess
import sys
import termios
from pathlib import Path
from typing import List
import json

# Third-party imports
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory as BaseFileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from datetime import datetime, timedelta

# Local application imports
from seerAD.cli.main import app as typer_app
from seerAD.config import DATA_DIR, LOOT_DIR

TIMEWRAP_FILE = LOOT_DIR / "timewrap.json"
FAKETIME_LIB = "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1"

if TIMEWRAP_FILE.exists() and "FAKETIME" not in os.environ:
    timewrap_data = json.loads(TIMEWRAP_FILE.read_text())
    offset = timewrap_data["offset"]
    env = os.environ.copy()
    env["LD_PRELOAD"] = FAKETIME_LIB
    env["FAKETIME"] = offset
    os.execve(sys.executable, [sys.executable, *sys.argv], env)

class LimitedFileHistory(BaseFileHistory):
    """File history that limits the number of entries to prevent the history file from growing too large."""
    def __init__(self, filename: str, max_size: int = 1000):
        super().__init__(filename)
        self.max_size = max_size
        self._trim_history()

    def _trim_history(self):
        """Trim the history file to the maximum size."""
        try:
            # Read all lines from the file
            with open(self.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # If we're under the limit, do nothing
            if len(lines) <= self.max_size:
                return

            # Keep only the most recent entries
            lines = lines[-self.max_size:]

            # Write them back to the file
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        except Exception as e:
            console.print(f"[yellow][!] Warning: Could not trim history file: {e}[/]")

    def append(self, string: str) -> None:
        super().append(string)
        self._trim_history()


# Rich console theme for consistent styling
class SeerTheme:
    SUCCESS = "green"
    INFO = "blue"
    WARNING = "yellow"
    ERROR = "red"
    DEBUG = "magenta"
    PROMPT = "cyan"
    SEPARATOR = "#555555"
    HIGHLIGHT = "#ffffff"
    MUTED = "#888888"
    COMMAND = "cyan"
    ARGUMENT = "yellow"
    OPTION = "blue"
    TARGET = "cyan"
    CREDENTIAL = "green"
    PATH = "yellow"

    @classmethod
    def get_style(cls) -> Style:
        return Style.from_dict({
            "clock": f"{cls.WARNING} bold",
            "prompt": f"{cls.PROMPT} bold",
            "brackets": f"{cls.SEPARATOR}",
            "userinfo": f"{cls.CREDENTIAL} bold",
            "path": f"{cls.PATH}",
            "separator": f"{cls.SEPARATOR}",
            "completion-menu.completion": "bg:#008888 #ffffff",
            "completion-menu.completion.current": "bg:#00aaaa #000000",
            "scrollbar.background": "bg:#88aaaa",
            "scrollbar.button": "bg:#222222",
        })

THEME = SeerTheme()
PROMPT_STYLE = THEME.get_style()
INTERACTIVE_COMMANDS = {'nano', 'vim', 'vi', 'less', 'more', 'top', 'htop'}
console = Console()

class SeerCompleter(Completer):
    """Command completer for Seer shell with support for command hierarchy and file completion."""
    
    def __init__(self, get_cwd_func: callable) -> None:
        """Initialize the command completer.
        
        Args:
            get_cwd_func: Function that returns the current working directory
        """
        self.get_cwd = get_cwd_func
        self.shell_builtins = ["cd", "ls", "pwd"]
        self.commands = {
            "version": {},
            "reset": {},
            "target": {
                "add": {},
                "info": {},
                "list": {},
                "switch": self.get_target_labels,
                "set": {
                    "ip": {},
                    "domain": {},
                    "fqdn": {},
                    "os": {},
                },
                "del": self.get_target_labels,
            },
            "creds": {
                "add": {},
                "list": {},
                "use": self.get_cred_users,
                "del": self.get_cred_users,
                "info": self.get_cred_users,
                "set": {
                    "password": {},
                    "ntlm": {},
                    "aes128": {},
                    "aes256": {},
                    "ticket": {},
                    "cert": {},
                    "notes": {},
                    "domain": {},
                },
                "fetch": {},
            },
            "enum": {
                "run": {
                    "smb": {},
                    "ldap": {},
                    "winrm": {},
                    "ssh": {},
                    "rdp": {},
                    "nfs": {},
                    "vnc": {},
                    "wmi": {},
                    "GetNPUsers": {},
                    "GetUserSPNs": {},
                },
                "list": {},
            },
            "abuse": {},
            "tasks": {},
            "timewrap": {
                "set": {},
                "reset": {},
                "status": {},
            },
            "help": {
                "reset": {},
                "target": {},
                "creds": {},
                "enum": {},
                "abuse": {},
                "tasks": {},
                "timewrap": {},
                "exit": {},
                "quit": {}
            },
            "exit": {}
        }

    def get_cred_users(self) -> List[str]:
        """Get list of usernames from current target's credentials.
        
        Returns:
            List of usernames for the current target
        """
        try:
            from seerAD.core.session import session
            if not session.current_target:
                return []
            creds = session.get_credentials(session.current_target_label)
            return [cred['username'] for cred in creds]
        except Exception as e:
            console.print(f"[yellow][!] Error getting credential users: {e}[/]")
            return []

    def get_enum_modules(self) -> List[str]:
        """Get list of available enum modules.
        Returns:
            List of enum module names
        """
        try:
            return list(get_enum_module.__globals__['ENUM_MODULES'].keys())
        except Exception as e:
            console.print(f"[yellow][!] Error getting enum modules: {e}[/]")
            return []
    
    def get_target_labels(self) -> List[str]:
        """Get list of all target labels from the session.
        Returns:
            List of target labels
        """
        try:
            from seerAD.core.session import session
            return list(session.targets.keys())
        except Exception as e:
            console.print(f"[yellow][!] Error getting target labels: {e}[/]")
            return []

    def _get_file_suggestions(self, text):
        from pathlib import Path

        if not text.startswith('@'):
            return []

        partial = text[1:]  # remove '@'

        # Expand ~ to home
        partial = os.path.expanduser(partial)
        path = Path(partial)

        cwd = Path.cwd()

        try:
            if path.is_dir():
                return [
                    f"@{str(f)}" for f in path.iterdir()
                    if not f.name.startswith('.')
                ]
            elif path.exists():
                return [f"@{str(path)}"]

            # If it's not an existing file or dir, suggest matching entries in its parent
            parent = path.parent if path.parent.exists() else cwd
            prefix = path.name
            return [
                f"@{str(f)}"
                for f in parent.iterdir()
                if f.name.startswith(prefix) and not f.name.startswith('.')
            ]
        except Exception:
            return []

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text = document.text_before_cursor.lstrip()
        words = [w for w in text.split() if w]
        
        current_word = ""
        is_completing_word = False
        if document.cursor_position > 0 and not document.text_before_cursor[-1].isspace():
            is_completing_word = True
            current_word = words[-1] if words else ""

        if not words:
            for cmd in self.commands:
                yield Completion(cmd)
            return

        first_word = words[0].lower()

        # Special case: file suggestion
        for word in words:
            if word.startswith('@'):
                for path in self._get_file_suggestions(word):
                    yield Completion(path, start_position=-len(word))
                return

        # Shell builtins (cd, ls)
        if first_word in self.shell_builtins and len(words) > 1:
            path_prefix = words[1]
            cwd = self.get_cwd()
            try:
                for entry in os.listdir(cwd):
                    if entry.startswith(path_prefix) and not entry.startswith('.'):
                        full_path = os.path.join(cwd, entry)
                        display = entry + ('/' if os.path.isdir(full_path) else '')
                        yield Completion(entry, start_position=-len(path_prefix), display=display)
            except Exception:
                pass
            return

        # Begin recursive command traversal
        current = self.commands
        idx = 0
        while idx < len(words):
            word = words[idx]
            if isinstance(current, dict):
                if word in current:
                    current = current[word]
                    idx += 1
                else:
                    break
            else:
                break

        # At this point, `current` might be:
        # 1. a callable -> dynamic completion (like usernames)
        # 2. a dict -> more subcommands to show
        # 3. a list/tuple -> valid argument values

        # If we're at a leaf that provides a completion callback
        if callable(current):
            try:
                options = current() or []
                if not isinstance(options, (list, tuple)):
                    options = []
            except Exception as e:
                if os.getenv("SEER_DEBUG"):
                    console.print(f"[yellow][!] Error in dynamic completion: {e}[/]")
                options = []

            last = current_word if is_completing_word else ""
            for opt in options:
                if isinstance(opt, str) and opt.startswith(last):
                    yield Completion(opt, start_position=-len(last))
            return

        # If we're at a dict: suggest next subcommand
        if isinstance(current, dict):
            last = current_word if is_completing_word else ""
            for subcmd in current:
                if subcmd.startswith(last):
                    yield Completion(subcmd, start_position=-len(last))
            return

        # If list/tuple of static options
        if isinstance(current, (list, tuple)):
            last = current_word if is_completing_word else ""
            for item in current:
                if isinstance(item, str) and item.startswith(last):
                    yield Completion(item, start_position=-len(last))
            return


def run_seer_command(args: List[str]) -> None:
    """Execute a Seer command using the Typer CLI app.
    
    Args:
        args: List of command line arguments
    """      
    try:
        # Always use typer_app with the modified environment
        typer_app(prog_name="seerAD", args=args)
            
    except SystemExit as e:
        if e.code != 0 and args:  # Only show error if args is not empty
            console.print(f"[red][!] Error: Unknown or invalid command '{args[0]}'[/]")
            console.print("[yellow]Type 'help' for available commands[/]")
    except Exception as e:
        console.print(f"[red][!] Error executing command: {e}[/]")


def run_shell_command(cmd: str) -> None:
    """Execute a shell command with proper terminal handling.
    
    Args:
        cmd: The shell command to execute
    """
    if not cmd.strip():
        return
        
    try:
        cmd_name = cmd.split()[0]
        
        # Get current environment
        current_env = os.environ.copy()
        
        # Handle interactive commands that need terminal control
        if cmd_name in INTERACTIVE_COMMANDS:
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                subprocess.run(cmd, shell=True, env=current_env)
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        # Handle regular commands with output capture
        else:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=os.getcwd(),  # Use current working directory
                env=current_env    # Pass current environment
            )
            if result.stdout:
                console.print(result.stdout, end="")
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/]", end="")
    except FileNotFoundError:
        console.print(f"[red]Command not found: {cmd.split()[0]}[/]")
    except PermissionError:
        console.print("[red]Permission denied. Check your permissions.[/]")
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/]")


def run_interactive() -> None:
    """Run the interactive Seer shell.
    
    Handles command input, command routing, and maintains shell state.
    """
    # Print welcome banner
    console.rule(
        "[bold]Seer CTF Assistant[/]",
        style=THEME.PROMPT,
        align="center"
    )
    console.print(
        f"[dim]{'─' * 20} [bold {THEME.INFO}]Interactive Shell[/] {'─' * 20}[/]\n"
        f"[dim]• Type [bold {THEME.COMMAND}]help[/] for available commands\n"
        f"• Use [bold {THEME.COMMAND}]exit[/] or [bold {THEME.COMMAND}]quit[/] to exit\n"
        f"• Press [bold {THEME.COMMAND}]Tab[/] for command completion\n"
        f"• Shell commands work as normal (e.g., [bold {THEME.COMMAND}]ls[/], [bold {THEME.COMMAND}]cd[/], etc.)[/]"
    )
    console.print(f"[dim]{'─' * 60}[/]\n")

    current_dir = os.getcwd()
    seer_commands = SeerCompleter(get_cwd_func=lambda: current_dir)
    
    # Use configured data directory for history file
    history_file = DATA_DIR / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        prompt = PromptSession(
            history=LimitedFileHistory(str(history_file), max_size=1000),
            style=PROMPT_STYLE,
            completer=seer_commands,
            complete_while_typing=True,
        )
    except Exception as e:
        console.print(f"[bold {THEME.WARNING}][!] Warning: Could not load command history: {e}[/]")
        prompt = PromptSession(style=PROMPT_STYLE, completer=seer_commands)

    # Main interactive loop
    while True:
        try:
            from seerAD.core.session import session
            
            # Get current target info
            target_display = session.current_target_label or 'no-target'
            
            # Get current credential info
            current_cred = session.current_credential() if callable(session.current_credential) else session.current_credential
            cred_username = current_cred.get('username') if current_cred else None
            cred_display = f"{cred_username}@" if cred_username else ""
            
            # Format current directory for display
            try:
                # Resolve any . or .. in the path
                resolved_path = Path(current_dir).resolve()
                # Try to make it relative to home directory
                try:
                    display_path = str(resolved_path.relative_to(Path.home()))
                    if not display_path.startswith('.'):
                        display_path = os.path.join("~", display_path)
                except ValueError:
                    # If not under home, use absolute path
                    display_path = str(resolved_path)
            except Exception:
                # Fallback to current_dir if any error occurs
                display_path = current_dir
                
            # Build the prompt
            clock_symbol = "◷" if TIMEWRAP_FILE.exists() else ""

            prompt_text = [
                ("class:clock", clock_symbol),
                ("class:prompt", "seer"),
                ("class:brackets", "["),
                ("class:userinfo", f"{cred_display}{target_display} "),
                ("class:path", display_path),
                ("class:brackets", "]> ")
            ]
            
            # Get user input with completion
            try:
                cmdline = prompt.prompt(prompt_text)
            except KeyboardInterrupt:
                console.print(f"\n[{THEME.INFO}][*] Command cancelled")
                continue
            except EOFError:
                console.print(f"\n[{THEME.SUCCESS}][*] Goodbye")
                break

            # Handle empty input
            if not cmdline.strip():
                continue
                
            # Handle exit commands
            if cmdline.strip().lower() in ("exit", "quit"):
                console.print(f"\n[{THEME.SUCCESS}][*] Goodbye")
                break
                
            try:
                # Handle built-in shell commands
                if cmdline.startswith("cd "):
                    try:
                        target = cmdline[3:].strip()
                        target_path = Path(target).expanduser().absolute()
                        
                        # Handle 'cd -' to go back to previous directory
                        if target == "-":
                            if hasattr(run_interactive, '_last_dir') and run_interactive._last_dir:
                                target_path = run_interactive._last_dir
                            else:
                                console.print(f"[{THEME.WARNING}][*] No previous directory in history")
                                continue
                        
                        # Update current directory
                        if target_path.is_dir():
                            run_interactive._last_dir = current_dir
                            current_dir = str(target_path)
                            os.chdir(current_dir)
                        else:
                            console.print(f"[{THEME.ERROR}][*] No such directory: {target}")
                    except Exception as e:
                        console.print(f"[{THEME.ERROR}][!] cd: {e}[/]")
                    continue
                    
                elif cmdline.strip() == "pwd":
                    console.print(current_dir)
                    continue
                    
                # Handle ls command
                elif cmdline.strip() == "ls" or cmdline.strip().startswith("ls "):
                    try:
                        # Always disable colors for ls to avoid ANSI codes
                        cmd = f"ls --color=never {cmdline[2:].strip()}"
                        result = subprocess.run(
                            cmd, 
                            cwd=current_dir, 
                            shell=True, 
                            capture_output=True, 
                            text=True
                        )
                        if result.stdout:
                            console.print(result.stdout, end="")
                        if result.stderr:
                            console.print(f"[{THEME.ERROR}]{result.stderr}[/]", end="")
                    except Exception as e:
                        console.print(f"[{THEME.ERROR}][*] ls: {e}")
                    continue
                
                # Handle help command
                args = shlex.split(cmdline)
                if not args:  # Shouldn't happen due to strip() check above
                    continue
                    
                cmd_name = args[0].lower()
                
                if cmd_name == "help":
                    help_args = args[1:] + ["--help"] if len(args) > 1 else ["--help"]
                    typer_app(prog_name="seerAD", args=help_args)
                    continue
                    
                # Handle Seer commands
                if cmd_name in seer_commands.commands:
                    run_seer_command(args)
                    continue
                    
                # Fall back to shell command
                run_shell_command(cmdline)
                
            except Exception as e:
                console.print(f"[{THEME.ERROR}][!] Error: {e}[/]")
                if os.getenv("SEER_DEBUG"):
                    console.print_exception()

        except SystemExit as e:
            if e.code != 0:
                console.print(f"[{THEME.WARNING}][!] Process exited with code {e.code}[/]")
                if os.getenv("SEER_DEBUG"):
                    console.print_exception()
        except Exception as e:
            console.print(f"\n[bold {THEME.ERROR}][!] Error: {e}")
            if os.getenv("SEER_DEBUG"):
                console.print_exception()
            console.print(f"[{THEME.INFO}]Type 'exit' or press Ctrl+D to quit.[/]")
            continue

# Entry point function
def main() -> None:
    try:
        if len(sys.argv) > 1:
            typer_app(prog_name="seerAD")
        else:
            run_interactive()
    except KeyboardInterrupt:
        console.print(f"\n[{THEME.INFO}][*] Interrupted. Exiting...")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold {THEME.ERROR}][!] Fatal error: {e}")
        if os.getenv("SEER_DEBUG"):
            console.print_exception()
        sys.exit(1)

if __name__ == "__main__":
    main()