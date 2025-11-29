# Complexity Daemon (cogload)

A local developer tool that monitors file changes, tracks cumulative complexity delta across all edits, and auto-commits when a threshold is reached.

## Installation

1.  Install the required dependencies:

    ```bash
    pip install -r tools/complexity_daemon/requirements.txt
    ```

2.  Install the `cogload` CLI:

    The `cogload` CLI is a single file and can be run directly. For convenience, you can create a symbolic link to a location in your `PATH`.

    ```bash
    ln -s $(pwd)/tools/complexity_daemon/cli.py ~/.local/bin/cogload
    ```

## Usage

1.  Initialize the config file:

    ```bash
    cogload init
    ```

2.  Add a repository to the watch list:

    ```bash
    cogload add ~/path/to/your/repo
    ```

3.  Run the daemon:

    ```bash
    cogload daemon
    ```

## Commands

-   `init`: Create the default config file.
-   `add <path>`: Add a repository to the watch list.
-   `remove <path>`: Remove a repository from the watch list.
-   `list`: Show watched repositories and their status.
-   `status`: Show the current cumulative delta per repo.
-   `watch <path>`: Watch a single repository in the foreground.
-   `daemon`: Run the daemon for all configured repositories.
-   `commit`: Force a commit now.
-   `reset`: Reset the cumulative counter.
-   `history`: Show the auto-commit history.
