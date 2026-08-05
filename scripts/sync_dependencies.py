"""Parse `uv tree` output and update pyproject.toml dependency versions."""

import re
import sys
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / 'pyproject.toml'

BOLD_GREEN = '\033[1;32m'
BOLD_RED = '\033[1;31m'
BOLD_YELLOW = '\033[1;33m'
RESET = '\033[0m'


def parse_tree(text: str) -> dict[str, str]:
    """Extract package==version pairs from uv tree output."""
    deps: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(('├──', '└──')):
            continue
        _, package, version = stripped.split(' ')[:3]
        # Strip extras: "uvicorn[standard]" → "uvicorn"
        name = package.split('[')[0]
        deps[name.lower()] = version.removeprefix('v')
    return deps


def update_dependencies(section: str, tree_input: str) -> None:
    """Update the named section in pyproject.toml with versions from tree input."""
    new_versions = parse_tree(tree_input)
    if not new_versions:
        return

    content = PYPROJECT.read_text()
    # Determine which TOML array to edit
    if section == 'prod':
        array_pattern = re.compile(r'(\[project\][\s\S]*?dependencies\s*=\s*\[)([\s\S]*?)(\n\s*\])')
    else:
        array_pattern = re.compile(r'(\[dependency-groups\][\s\S]*?dev\s*=\s*\[)([\s\S]*?)(\n\s*\])')

    m = array_pattern.search(content)
    if not m:
        return

    header, array_body, footer = m.group(1), m.group(2), m.group(3)
    updated_lines = []
    changes: list[tuple[str, str, str]] = []  # (name, old, new)
    for line in array_body.splitlines():
        dep_m = re.match(r'(\s*")([a-zA-Z0-9_][\w.-]*)(\[[^\]]*\])?(>=?)([\d.][\w.]*)(",?)', line)
        if dep_m:
            quote, name, extras, old_ver, trail = (
                dep_m.group(1),
                dep_m.group(2),
                dep_m.group(3) or '',
                dep_m.group(5),
                dep_m.group(6),
            )
            key = name.lower()
            if key in new_versions:
                new_ver = new_versions[key]
                if new_ver != old_ver:
                    changes.append((name, old_ver, new_ver))
                updated_lines.append(f'{quote}{name}{extras}>={new_ver}{trail}')
                continue
        updated_lines.append(line)

    new_array_body = '\n'.join(updated_lines)
    new_content = content[: m.start()] + header + new_array_body + footer + content[m.end() :]
    PYPROJECT.write_text(new_content)
    if changes:
        print(f'{BOLD_GREEN}{section} dependencies updated{RESET}')
        for name, old_ver, new_ver in changes:
            print(f'{BOLD_YELLOW}{name}{RESET}: {BOLD_RED}{old_ver}{RESET} -> {BOLD_GREEN}{new_ver}{RESET}')
    else:
        print(f'{BOLD_GREEN}{section} dependencies up to date{RESET}')


if __name__ == '__main__':
    if len(sys.argv) != 2:  # noqa: PLR2004
        sys.exit(1)

    section = sys.argv[1]
    tree_text = sys.stdin.read()
    update_dependencies(section, tree_text)
