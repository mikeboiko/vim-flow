import os
import threading

import vim

import flow
import runners

lock_cache = {}

_running_lock = threading.Lock()
_running = False


def _run_flow_sync(filepath, locked=False):
    # NOTE: this function may run on a background thread.
    # Do not call any Neovim APIs (vim.*) here.
    if locked:
        dirpath = os.path.dirname(filepath)
        dirpath = os.path.expanduser(dirpath)
        os.chdir(dirpath)

    flow_defs = flow.get_defs(filepath)
    if flow_defs is None:
        return

    cmd_def = flow.get_cmd_def(filepath, flow_defs)
    if cmd_def is None:
        return

    runner = {
        'debug': runners.debug_runner,
        'vim': runners.vim_runner,
        'tmux': runners.tmux_runner,
        'sync-remote': runners.sync_remote_runner,
        'async-remote': runners.async_remote_runner,
    }[cmd_def['runner']]

    # Anything that touches Neovim (vim.command, etc) must run on the main thread.
    vim.async_call(runner, cmd_def)


def run_flow(_=None):
    """flow: run a flow for the current filepath (async)

    This avoids freezing Neovim when flow resolution (git/yaml/fs/subprocess) blocks.
    """
    global _running

    # Capture Neovim state on the main thread (worker thread must not call vim.*)
    if 'filepath' in lock_cache:
        filepath = lock_cache['filepath']
        locked = True
    else:
        filepath = vim.current.buffer.name
        locked = False

    with _running_lock:
        if _running:
            vim.command('echom "vim-flow: already running"')
            return
        _running = True

    def worker():
        global _running
        try:
            _run_flow_sync(filepath, locked=locked)
        finally:
            with _running_lock:
                _running = False

    threading.Thread(target=worker, daemon=True).start()


def debug_flow(_=None, cache=lock_cache):
    if 'filepath' in cache:
        filepath = cache['filepath']

        dirpath = os.path.dirname(filepath)
        dirpath = os.path.expanduser(dirpath)
        os.chdir(dirpath)
    else:
        filepath = vim.current.buffer.name
    flow_defs = flow.get_defs(filepath)
    if flow_defs is None:
        return

    cmd_def = flow.get_cmd_def(filepath, flow_defs)
    if cmd_def is None:
        return

    runners.debug_runner(cmd_def)


def toggle_lock(filepath, cache=lock_cache):
    if filepath:
        cache['filepath'] = filepath
        return

    if 'filepath' in cache:
        del cache['filepath']
        print('file lock released...')
    else:
        cache['filepath'] = _get_filepath()
        print('file lock set...')


def _get_filepath():
    return vim.current.buffer.name
