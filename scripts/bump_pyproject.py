import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

LOCK_FILE = PROJECT_ROOT / 'uv.lock'
PYPROJECT_FILE = PROJECT_ROOT / 'pyproject.toml'


class VersionFormatter:
    def __init__(self, versions: dict[str, str]) -> None:
        self.versions = versions
        self.updated_count = 0
        self.intact_count = 0

    def __call__(self, matchobj: re.Match[str]) -> str:
        package_name_to_update = matchobj.group('name')

        if package_name_to_update not in self.versions:
            return matchobj.group(0)

        existing_version = matchobj.group('version')
        new_version = self.versions[package_name_to_update]

        if existing_version == new_version:
            self.intact_count += 1
        else:
            self.updated_count += 1

        return f'{matchobj.group("padding")}"{package_name_to_update}>={new_version}",'


def update_packages() -> None:
    lock_contents = LOCK_FILE.read_text(encoding='utf-8')

    packages_regex = re.compile(
        r'\[\[package]]\n'
        r'name = "(?P<name>[^"]+)"\n'
        r'version = "(?P<version>[^"]+)"'
    )
    pyproject_regex = re.compile('^(?P<padding> *)"(?P<name>[^>]+)>=(?P<version>[^"]+)",$', flags=re.MULTILINE)

    packages_data = {}

    for match in packages_regex.finditer(lock_contents):
        package_name = match.group('name')
        package_version = match.group('version')

        if package_name in packages_data:
            msg = f'Duplicate package name: {package_name}'
            raise ValueError(msg)
        packages_data[package_name] = package_version

    formatter = VersionFormatter(packages_data)

    pyproject_contents = PYPROJECT_FILE.read_text(encoding='utf-8')
    patched_pyproject_contents = pyproject_regex.sub(formatter, pyproject_contents)

    PYPROJECT_FILE.write_text(patched_pyproject_contents, encoding='utf-8')

    print(f'Updated {formatter.updated_count} packages, kept {formatter.intact_count} unchanged')


if __name__ == '__main__':
    update_packages()
