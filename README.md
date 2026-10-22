![PHP Luminova VCI](https://github.com/luminovang/phpvci-admin/blob/main/logo.svg?v=2)

# PHP Luminova Version Control Interface (VCI)

A lightweight tool for managing shared Luminova PHP framework installations across one or more projects on a single server.

This file covers the command line tool, `phpvci.sh`. The browser based admin panel, is documented in [ADMIN.README.md](ADMIN.README.md).

---

## What problem does this solve?

Normally, each PHP project carries its own copy of the Luminova framework. That means:

- The same files duplicated across every project
- Framework updates applied one project at a time
- No easy way to roll back if an update breaks something

VCI installs the framework once into a shared directory, and each project points to that copy through a `.phpvci.php` file. Projects that target `current` follow the active release, so switching versions needs no change in the project. Projects pinned to a specific release stay on it until their target changes.

Think of it like a PHP version manager (for example `phpenv`), but for the Luminova framework itself.

---

## How it works

```
/opt/phpvci.packages/
    repo/            temporary clone of the framework source
    releases/
        3.8.0/       a built release
        3.9.0/
    current          symlink to the active release
```

Each release contains `system/` (built from `src/` in the framework repository), `bootstrap/` (built from `install/Boot/`) and a `.metadata/` directory. `.metadata/` holds the files that belong in the project rather than the shared tree, and the hash of the build.

Projects reference either `current` or a specific release. Running `phpvci package --switch=3.9.0` only moves the `current` symlink. No files are copied.

The tool stores the packages directory and its own location in `config.conf` (see [Configuration file](#configuration-file)). The admin panel reads that file to find the packages directory.

---

## Requirements

| Tool | Purpose |
|------|---------|
| `bash` | Runs the script |
| `git` | Clones the framework source |
| `rsync` | Builds release directories |
| `find`, `mktemp`, `awk`, `sed`, `basename`, `dirname` | Checked at startup, the script exits if one is missing |
| `sha256sum` or `shasum` | Fingerprints a local source directory (falls back to `md5sum`, `md5`, then `cksum`) |
| root access | Required for every `package` and `self` command |

Without root, the script prints `requires root privileges` and exits with status 1. The `--help`, `--version`, `--paths` and `--where` options work without root.

Check that the main tools are available:

```bash
bash --version && git --version && rsync --version
```

---

## Installation

There are three ways to install VCI: a Git clone (shell only), pip (adds a Python wrapper), or a manual upload.

### Option A: Git clone (recommended for servers)

```bash
# Create the installation directory
sudo mkdir -p /opt/phpvci

# Clone VCI into it
sudo git clone https://github.com/phpvci/phpvci.git /opt/phpvci

# Make the script executable
sudo chmod +x /opt/phpvci/phpvci.sh

# Register it as a global command
sudo /opt/phpvci/phpvci.sh self --install
```

`self --install` proposes a target and asks for confirmation. The target is the first writable directory from `/usr/local/bin`, `/usr/bin` and `~/.local/bin` that is already in `PATH`, or `/usr/local/bin/phpvci` when none qualifies. You can enter a different directory or a full path at the prompt, but the directory must be in `PATH`.

The script creates a symlink to `phpvci.sh` at the target, or copies the script when the filesystem does not support symlinks. If `phpvci` already exists at the target, the install stops.

### Option B: pip (Python CLI wrapper)

```bash
pip install git+https://github.com/phpvci/phpvci.git
```

Pin to a specific version:

```bash
pip install git+https://github.com/phpvci/phpvci.git@v2.1.0
```

The `phpvci` command installed by pip accepts the same flags as the shell script. See [Python API](#python-api) for programmatic access.

### Option C: manual upload

If you cannot clone directly on the server, upload the files from your local machine first:

```bash
scp -r /path/to/phpvci/. user@your-server:/opt/phpvci/
```

Then continue with Option A, starting at `chmod +x`.

---

## Directory structure

After installation, the layout looks like this:

```
/opt/phpvci/
    phpvci.sh            main script
    lib/                 internal modules, do not edit

/opt/phpvci.packages/    default packages directory
    repo/
    releases/
        3.8.0/
            system/
            bootstrap/
            .metadata/
        3.9.0/
    current              symlink to the active release
```

By default the packages directory is created as `phpvci.packages` beside the directory that contains `phpvci.sh`. Use [`--path`](#change-the-packages-directory) to choose another location.

### Configuration file

`config.conf` is created by the first `package` or `self` command and holds three keys:

| Key | Description |
|-----|-------------|
| `PHPVCI_CONF` | Path of the config file |
| `PHPVCI_PACKAGE_DIR` | Packages directory |
| `PHPVCI_BIN` | Path of the `phpvci` binary |

The file is saved in the first of these directories that exists and is readable and writable:

```
/etc/phpvci/
/var/lib/phpvci/
~/.config/.phpvci/
~/.local/share/.phpvci/
~/.phpvci/
```

---

## Installing a framework release

Install without a version, which uses the version found in the framework source:

```bash
sudo phpvci package --install
```

Install a specific version:

```bash
sudo phpvci package --install=3.8.0
```

When no version is given, it is detected from the cloned source in this order: the `VERSION` constant in `src/Luminova.php`, the latest git tag, then the `version` field in `composer.json`. If none is found, the script stops and asks for `--install=<version>`.

What happens during an install:

1. `config.conf` is written with the binary path and the packages directory.
2. The framework source is cloned from [GitHub](https://github.com/luminovang/framework) into `repo/`. The clone is shallow and uses the version as the branch or tag, or `main` when no version is given.
3. The release is built into `releases/<version>/`.
4. A fingerprint of the source (the commit SHA for a remote source) is saved in `releases/<version>/.metadata/.hash`.
5. `current` is pointed at the new release, but only when no release is active yet or the new version is higher than the active one.
6. The script directory is set to owner root and mode `755` unless it already is.

If the build fails, the incomplete release directory is removed when the script exits.

A clone into a `repo/` directory that already has files fails. To reinstall or rebuild a version, use `--update`, or add `--force` to delete `repo/` first.

---

## Configuring your PHP project

Add a `.phpvci.php` file to the root of each project. It tells the framework where the shared installation is.

```php
<?php
// .phpvci.php (project root)
return [

    // Enable shared framework resolution
    'enabled' => true,

    // Autoloader strategy:
    //   'auto'      detect Composer, fall back to the framework autoloader if needed
    //   'composer'  Composer only (update the Composer PSR-4 mapping to match)
    //   'framework' framework autoloader only
    'autoloader' => 'auto',

    // Framework version constraint, checked at startup
    'version' => '>=3.8',

    // 'root' is the packages directory, 'target' is the release in use.
    // A target ending in 'current' follows the active symlink.
    'paths' => [
        'root'   => '/opt/phpvci.packages',
        'target' => '/opt/phpvci.packages/current',
    ],
];
```

Notes:

- When `enabled` is false or the file is missing, the project loads its own framework files.
- `paths.target` and `version` are required. Startup stops with an error if either is missing.
- `version` accepts an exact version (`3.9.0`), a comparison (`>=3.8`, `<4.0`) or a range (`^3.8`, `~3.8`). Startup stops if the target release does not satisfy it.
- Only `system/` and `bootstrap/` are shared. Application code, routes and storage stay in the project.

To pin a project to a specific version instead of following `current`:

```php
'target' => '/opt/phpvci.packages/releases/3.8.0',
```

The admin panel creates and updates this file when you apply a version, and keeps the Composer mapping in step.

---

## Common commands

### List all installed releases

```bash
sudo phpvci package --list
```

Example output:

```
Installed releases:
  3.7.8
  3.8.0  ← active
  3.9.0
```

### Check the active version

```bash
sudo phpvci package --current
```

### Switch to a different release (instant, no rebuild)

```bash
sudo phpvci package --switch=3.9.0
```

The release must already be installed, otherwise the script prints `Release not found`. Only the `current` symlink changes. Projects that target a specific release are not affected. If the filesystem does not support symlinks, `current` becomes a copy of the release directory.

### Update a release

```bash
sudo phpvci package --update
sudo phpvci package --update=3.9.0
```

`--update` needs at least one installed release. It wipes `repo/`, clones again, rebuilds the release and always bypasses the hash check. As with an install, `current` only moves when the version is higher than the active one.

`--update` already starts from a fresh clone, so do not combine it with `--force`.

### Roll back to a previous version

```bash
sudo phpvci package --list
sudo phpvci package --switch=3.8.0
```

No rebuild is needed.

---

## Advanced options

### Install from a specific git branch

```bash
sudo phpvci package --install --branch=develop
```

`--branch` sets the same value as the version argument, so `--branch=develop` is the same as `--install=develop`. The value is used as the git ref to clone and as the release directory name, so this builds `releases/develop`. If both are given, the last one on the command line wins.

### Change the packages directory

The packages directory is resolved in this order: `--path`, `PHPVCI_PACKAGE_DIR` from `config.conf`, then the default `phpvci.packages` beside the script directory.

```bash
sudo phpvci package --install=3.8.0 --path=/srv/phpvci/shared
```

Run `--path` without an action to only change the stored location:

```bash
sudo phpvci package --path=/srv/phpvci/shared
```

When `config.conf` already points to a different directory, the script asks for confirmation. If the old directory is not empty it also offers to move its contents. Declining stops the command. Without a terminal, the default answer (No) is used.

### Print paths

```bash
phpvci --paths
phpvci --where=packages
phpvci --where=release
phpvci --where=current
phpvci --where=repo
```

`--paths` prints the script directory and the contents of `config.conf`. `--where` prints the path for one directory, taken from `PHPVCI_PACKAGE_DIR` when it is set.

### Force a fresh clone

```bash
sudo phpvci package --install=3.8.0 --force
```

This deletes `repo/`, clones again and skips the hash check for that run. Use it when the clone is corrupted or you want a clean start.

### Remove the repo after building

```bash
sudo phpvci package --install=3.8.0 --delete
```

After the build, everything in `repo/` except the `.git` directory is removed. A local source (see below) is always cleaned this way.

### Change the framework source

The source is the `PACKAGE_REPO_URL` constant at the top of `phpvci.sh`. A value that starts with `http` or `git@` is cloned with git. Any other value is treated as a local directory and synced with `rsync` on every run, excluding `.git`, `vendor/` and `libraries/`.

### Lock file permissions

```bash
# Default mode (755)
sudo phpvci package --install=3.8.0 --lock

# Stricter mode (555)
sudo phpvci package --install=3.8.0 --lock --mode=555

# Equivalent long form with an explicit mode
sudo phpvci package --install=3.8.0 --lock-mode=555
```

After the build, the mode is applied to every file and directory under the packages directory, and ownership is set to `root:root` (or the current user and group with `--runtime=user`). Passing `--mode` or `--lock-mode` on its own also enables locking. The step is skipped when the directory is already owned by root with the requested mode.

Locking only runs after an install or update that rebuilds a release.

---

## Removing releases

### Remove a specific version

```bash
sudo phpvci package --remove=3.7.8
```

If the removed version was active, the latest remaining release becomes active. If no release is left, the `current` symlink is removed.

### Free up disk space (remove the repo clone only)

```bash
sudo phpvci package --remove=repo
```

This removes `repo/` but does not touch `releases/` or `current`.

### Full reset

```bash
sudo phpvci package --remove
```

> **Warning:** This removes `repo/`, `releases/` and `current` from the packages directory. The script asks for confirmation first.

### Skip the confirmation prompt

```bash
sudo phpvci package --remove --force
sudo phpvci package --remove=3.7.8 --force
```

Without a terminal, the confirmation defaults to No, so scripted removals need `--force`. The script refuses to delete a path that contains the script itself.

---

## Self management

These commands manage the `phpvci` script itself, not the framework packages.

### Install as a global command

```bash
sudo ./phpvci.sh self --install
```

See [Installation](#option-a-git-clone-recommended-for-servers) for how the target is chosen. A version value such as `--install=3.8.0` is ignored with a message.

### Update the VCI script from GitHub

```bash
# Update from the main branch
sudo phpvci self --update

# Update from a specific branch or tag
sudo phpvci self --update --branch=v2.1.0
```

The update clones `https://github.com/phpvci/phpvci.git` into a temporary directory and reads the new `VERSION` from `phpvci.sh`. If it matches the installed version, the script reports `Already up to date` and stops. Otherwise the new script is checked with `bash -n`, and the clone is mirrored into the script directory with `rsync --delete`, excluding `.git`.

Because the sync deletes files that are not in the repository, do not keep the packages directory inside the script directory.

### Uninstall

```bash
# Remove the binary only
sudo phpvci self --uninstall

# Also clear the config file
sudo phpvci self --uninstall --purge
```

The target is the `PHPVCI_BIN` value from `config.conf`. When it is a global command, only that link is removed. When `PHPVCI_BIN` points inside the script directory, which is the case until you run `self --install`, the whole installation directory is removed after a confirmation (default No), together with the config directory. The packages directory is not touched.

With `--purge` on a global command, `config.conf` is cleared and then written again with `PHPVCI_BIN` set to the script path.

---

## Python API

The `phpvci` Python package provides a thin programmatic interface for build pipelines and deployment scripts.

```python
from phpvci import runner

# Returns the shell exit code
exit_code = runner.run(["package", "--install=3.8.0", "--runtime=root"])

# Install from a branch
runner.run(["package", "--install", "--branch=develop"])

# Exit automatically if the command fails
runner.run_or_exit(["package", "--list"])

# Enable bash xtrace for debugging
runner.run(["package", "--install"], env={"DEBUG": "1"})
```

### Python CLI examples

```bash
# Self management
phpvci self --install
phpvci self --update
phpvci self --update --branch=v2.1.0
phpvci self --uninstall --purge

# Installing and updating
phpvci package --install
phpvci package --install=3.8.0
phpvci package --install=3.8.0 --runtime=root --lock-mode=755
phpvci package --install --branch=develop
phpvci package --update=3.9.0

# Switching and inspecting
phpvci package --switch=3.8.0
phpvci package --list
phpvci package --current

# Cleanup
phpvci package --remove
phpvci package --remove=3.7.8
phpvci package --remove=repo --force
```

---

## All options reference

Short options that take a value use the same `=` form, for example `-i=3.8.0` or `-s=3.8.0`.

### Global options

| Flag | Short | Description |
|------|-------|-------------|
| `--help` | `-h` | Show usage. Add `package` or `self` for command specific help |
| `--version` | `-v` | Show the VCI tool version |
| `--paths` | | Print the script directory and the contents of `config.conf` |
| `--where=<target>` | `-w` | Print the path for `packages`, `release`, `current` or `repo` |

### `package` subcommand

| Flag | Short | Description |
|------|-------|-------------|
| `--install[=<version>]` | `-i` | Install a release (omit the version to detect it from the source) |
| `--update[=<version>]` | `-u` | Rebuild a release from a fresh clone, always bypasses the hash check |
| `--switch=<version>` | `-s` | Point `current` at an installed release without rebuilding |
| `--list` | `-l` | List all installed releases |
| `--current` | `-c` | Show the active release |
| `--remove[=<target>]` | `-r` | Remove a release, the repo clone (`repo`), or everything (no value or `all`) |
| `--branch=<ref>` | `-b` | Git branch or tag to clone, same as the version argument |
| `--path=<dir>` | | Set the packages directory |
| `--runtime=<mode>` | `-ru` | `root`, `user` or `auto` (default `auto`) |
| `--force` | `-f` | Delete `repo/` and clone again, skip the hash check. With `--remove`, skip the confirmation |
| `--delete` | `-d` | Remove the repo source files after building, keeping `.git` |
| `--lock` | | Lock the packages directory after a build (default mode `755`) |
| `--mode=<mode>` | `-m` | Permission mode for the lock, enables locking (for example `755`, `555`) |
| `--lock-mode=<mode>` | `-lm` | Same as `--lock` with an explicit mode |

### `self` subcommand

| Flag | Short | Description |
|------|-------|-------------|
| `--install` | `-i` | Install this script as `phpvci` in `PATH` |
| `--update[=<ref>]` | `-u` | Update the script directory from GitHub |
| `--uninstall` | `-ui` | Remove the installed `phpvci` binary or the main installation |
| `--branch=<ref>` | `-b` | Git branch or tag to use with `--update` |
| `--runtime=<mode>` | `-ru` | `root`, `user` or `auto` (default `auto`) |
| `--purge` | `-p` | Also clear `config.conf` when uninstalling |

### Runtime mode

`--runtime` controls how ownership and permissions are applied. `root` applies `root:root`. `user` applies the current user and group, ignores permission errors on `chmod`, and skips `git clean` on the repo. `auto` selects `root` when running as root, when `sudo` works without a password, or when `/opt`, `/usr/local` or `/etc` is writable, and `user` otherwise. Since the script requires root, `auto` resolves to `root`.

### Environment variables

| Variable | Description |
|----------|-------------|
| `DEBUG` | Set to `1`, `yes` or `true` to enable bash xtrace |
| `NO_COLOR` | Set to `1` to disable colored output. Color is also off when output is not a terminal |

---

## Troubleshooting

**`requires root privileges`**

Every `package` and `self` command must run as root. Add `sudo`:

```bash
sudo phpvci package --install=3.8.0
```

---

**"Release not found" when switching**

The version is not in `releases/`. Run `--list` to see what is installed:

```bash
sudo phpvci package --list
sudo phpvci package --install=3.9.0   # install it if missing
```

---

**"Clone failed" with "already exists and is not empty"**

`repo/` still holds files from an earlier run. Rebuild from a fresh clone:

```bash
sudo phpvci package --update=3.8.0
# or
sudo phpvci package --install=3.8.0 --force
```

---

**Build fails with "Source directory not found"**

The repo clone is missing. Force a clean clone:

```bash
sudo phpvci package --install=3.8.0 --force
```

---

**"No changes detected" but you expect a rebuild**

The stored hash matches the source. Use `--update` to bypass it:

```bash
sudo phpvci package --update=3.8.0
```

---

**Active symlink is broken**

The script removes an incomplete release when it exits with an error. If the process was killed, or `current` is broken for another reason, restore it manually:

```bash
sudo rm /opt/phpvci.packages/current
sudo phpvci package --switch=3.8.0
```

---

**The wrong ref was cloned**

Discard the existing clone and start fresh with the ref you want:

```bash
sudo phpvci package --install=3.8.0 --force
```

---

**`self --update` reports "Already up to date"**

The update compares only the `VERSION` value in `phpvci.sh`. A branch with the same `VERSION` is not applied.
