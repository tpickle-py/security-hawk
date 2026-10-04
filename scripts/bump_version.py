#!/usr/bin/env python3
"""
Semantic version bumper for Security Hawk.
Uses `uv version` to bump pyproject.toml and uv.lock, then propagates the new
version across:
  - config.yaml (root)
  - security_hawk/config.yaml (app add-on manifest)
  - frontend/package.json
  - Dockerfile (io.hass.version label)
  - CHANGELOG.md
  - ../ha-addons/security_hawk/config.yaml (HA catalog repo, if present)
"""

import argparse
import datetime
import re
import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def update_file(path: Path, pattern: str, replacement: str, dry_run: bool = False) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        print(f"  [WARN] Pattern not found in {path}")
        return False
    if text != new_text:
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        print(f"  [UPDATED] {path} ({count} match{'es' if count > 1 else ''})")
        return True
    return False


def update_changelog(repo_root: Path, new_ver: str, changelog_entry: str | None, dry_run: bool = False):
    changelog_path = repo_root / "CHANGELOG.md"
    if not changelog_path.is_file():
        return

    content = changelog_path.read_text(encoding="utf-8")
    header_check = f"## [{new_ver}]"
    if header_check in content:
        print(f"  [SKIPPED] {changelog_path} already contains {header_check}")
        return

    today = datetime.date.today().isoformat()
    entry_body = changelog_entry.strip() if changelog_entry else f"- Release version {new_ver}"

    new_section = (
        f"## [{new_ver}] - {today}\n\n"
        f"### Changed\n"
        f"{entry_body}\n\n"
    )

    m = re.search(r"^(##\s+\[\d+\.\d+\.\d+\])", content, re.MULTILINE)
    if m:
        idx = m.start()
        updated_content = content[:idx] + new_section + content[idx:]
        if not dry_run:
            changelog_path.write_text(updated_content, encoding="utf-8")
        print(f"  [UPDATED] {changelog_path} with new section for {new_ver}")
    else:
        print(f"  [WARN] Could not find insertion point in {changelog_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Increment semver across Security Hawk codebase using uv version"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="patch",
        help="Semver bump ('patch', 'minor', 'major') or explicit version (e.g., '0.3.5'). Default: patch",
    )
    parser.add_argument(
        "-m", "--message",
        dest="message",
        help="Changelog notes for CHANGELOG.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying files",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    ha_addons_root = repo_root.parent / "ha-addons"

    # Current version
    current_ver = run_cmd(["uv", "version", "--short"], cwd=repo_root)

    # Determine command to uv
    if args.target in ("major", "minor", "patch", "stable", "alpha", "beta", "rc"):
        bump_cmd = ["uv", "version", "--bump", args.target]
    else:
        bump_cmd = ["uv", "version", args.target]

    if args.dry_run:
        bump_cmd.append("--dry-run")
        uv_out = run_cmd(bump_cmd, cwd=repo_root)
        print(f"==> uv version: {uv_out}")
        new_ver = uv_out.split("=>")[-1].strip() if "=>" in uv_out else args.target
    else:
        uv_out = run_cmd(bump_cmd, cwd=repo_root)
        print(f"==> uv version: {uv_out}")
        new_ver = run_cmd(["uv", "version", "--short"], cwd=repo_root)

    print(f"==> Bumping {current_ver} -> {new_ver}")
    print(f"==> Propagating version {new_ver} across project files" + (" (DRY RUN)" if args.dry_run else "") + ":")

    # 1. config.yaml (root)
    update_file(
        repo_root / "config.yaml",
        r'^(version:\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        args.dry_run,
    )

    # 2. security_hawk/config.yaml (app subdir)
    update_file(
        repo_root / "security_hawk" / "config.yaml",
        r'^(version:\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        args.dry_run,
    )

    # 3. frontend/package.json
    pkg_json = repo_root / "frontend" / "package.json"
    if pkg_json.is_file():
        update_file(
            pkg_json,
            r'("version":\s*)"[^"]+"',
            rf'\g<1>"{new_ver}"',
            args.dry_run,
        )

    # 4. Dockerfile
    update_file(
        repo_root / "Dockerfile",
        r'(io\.hass\.version=")[^"]+(")',
        rf'\g<1>{new_ver}\g<2>',
        args.dry_run,
    )

    # 5. CHANGELOG.md
    update_changelog(repo_root, new_ver, args.message, args.dry_run)

    # 6. ha-addons/security_hawk/config.yaml (if present)
    ha_addon_config = ha_addons_root / "security_hawk" / "config.yaml"
    if ha_addon_config.is_file():
        update_file(
            ha_addon_config,
            r'^(version:\s*)"[^"]+"',
            rf'\g<1>"{new_ver}"',
            args.dry_run,
        )

    print(f"\nSuccessfully synchronized version to {new_ver}!")
    print("\nNext steps:")
    print("  1. Review changes: git diff")
    print(f"  2. Commit: git commit -am \"chore(release): v{new_ver}\"")
    print(f"  3. Tag:    git tag v{new_ver}")
    print(f"  4. Push:   git push origin master && git push origin v{new_ver}")


if __name__ == "__main__":
    main()
