"""Shell integration utilities for environment variable exports."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class Shell(Enum):
    """Supported shells."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"


class ShellExporter:
    """Generate shell-specific export commands for environment variables.

    Used to help users set up shell integration for automatic context switching.
    """

    @staticmethod
    def detect_shell() -> Shell:
        """Detect the current shell from environment.

        Returns:
            Detected Shell enum value, defaults to BASH.
        """
        import os

        shell_path = os.environ.get("SHELL", "/bin/bash")
        shell_name = Path(shell_path).name.lower()

        shell_map = {
            "zsh": Shell.ZSH,
            "fish": Shell.FISH,
            "pwsh": Shell.POWERSHELL,
            "powershell": Shell.POWERSHELL,
        }

        return shell_map.get(shell_name, Shell.BASH)

    @classmethod
    def export_var(cls, name: str, value: str, shell: Shell | None = None) -> str:
        """Generate export command for a variable.

        Args:
            name: Variable name.
            value: Variable value.
            shell: Target shell. If None, auto-detect.

        Returns:
            Shell-specific export command.
        """
        if shell is None:
            shell = cls.detect_shell()

        if shell == Shell.FISH:
            return f'set -gx {name} "{value}"'
        elif shell == Shell.POWERSHELL:
            return f'$env:{name} = "{value}"'
        else:  # bash/zsh
            return f'export {name}="{value}"'

    @classmethod
    def generate_hook(cls, shell: Shell | None = None) -> str:
        """Generate shell hook for automatic ADC context display.

        Args:
            shell: Target shell. If None, auto-detect.

        Returns:
            Shell hook code to add to rc file.
        """
        if shell is None:
            shell = cls.detect_shell()

        if shell == Shell.FISH:
            return """
# Gloom ADC Context Hook
function __gloom_prompt_hook --on-variable PWD
    set -gx GLOOM_CONTEXT (gloom current --quiet 2>/dev/null)
end
__gloom_prompt_hook
"""
        elif shell == Shell.ZSH:
            return """
# Gloom ADC Context Hook
__gloom_prompt_hook() {
    export GLOOM_CONTEXT="$(gloom current --quiet 2>/dev/null)"
}
precmd_functions+=(__gloom_prompt_hook)
"""
        elif shell == Shell.POWERSHELL:
            return """
# Gloom ADC Context Hook
function prompt {
    $env:GLOOM_CONTEXT = (gloom current --quiet 2>$null)
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
"""
        else:  # bash
            return """
# Gloom ADC Context Hook
__gloom_prompt_hook() {
    export GLOOM_CONTEXT="$(gloom current --quiet 2>/dev/null)"
}
PROMPT_COMMAND="__gloom_prompt_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
"""

    @classmethod
    def get_rc_file(cls, shell: Shell | None = None) -> Path:
        """Get the RC file path for a shell.

        Args:
            shell: Target shell. If None, auto-detect.

        Returns:
            Path to the shell's RC file.
        """
        if shell is None:
            shell = cls.detect_shell()

        home = Path.home()

        rc_files = {
            Shell.BASH: home / ".bashrc",
            Shell.ZSH: home / ".zshrc",
            Shell.FISH: home / ".config" / "fish" / "config.fish",
            Shell.POWERSHELL: home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1",
        }

        return rc_files.get(shell, home / ".bashrc")
