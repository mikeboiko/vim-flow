import contextlib
import glob
import os
import stat
import subprocess
import time
import urllib.parse
import warnings

import vim


def _build_script(cmd_def):
    """_build_script: in order to simplify things such as escaping and
    multiline commands, we template out all `cmds` into a script that is
    written to a tempfile and executed
    """
    filepath = '/tmp/flow--{}'.format(int(time.time()))

    cmd = cmd_def['cmd']
    lines = cmd.splitlines()

    # Identify hashbang
    if lines and lines[0].startswith('#!'):
        hashbang = lines[0]
        start_idx = 1
    else:
        hashbang = '#!{}'.format(os.environ.get('SHELL', '/usr/bin/env bash'))
        start_idx = 0

    # Strip 'clear' from the execution part to avoid wiping the 'cat' output
    cleaned_lines = []
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if line.strip() == 'clear':
            continue
        cleaned_lines.append(line)

    with open(filepath, 'w') as fh:
        fh.write(hashbang + '\n')
        # Display the original command content
        fh.write("cat << 'VIMFLOW_CONTENT_EOF'\n")
        fh.write(cmd + '\n')
        fh.write('VIMFLOW_CONTENT_EOF\n')
        fh.write('echo "--------------------------------------------------------------------------------"\n')

        # Execute the cleaned command
        fh.write('\n'.join(cleaned_lines))
        fh.write('\n')

    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)
    return filepath


def cleanup():
    """cleanup: due to the tmux send keys command being asynchronous, we can not guarantee when a command is finished
    and therefore can not clean up after ourselves consistently.
    """
    for filepath in glob.glob('/tmp/flow--*'):
        os.remove(filepath)


@contextlib.contextmanager
def _script(cmd_def):
    """_script: a context manager for creating a command script and cleaning it up

    usage:
        with _script(cmd_def) as script_filepath:
            print script_filepath
    """
    filepath = _build_script(cmd_def)
    yield filepath


def debug_runner(cmd_def):
    """debug_runner: run a command using nvim-dap"""

    # # Serialize cmd_def to JSON file in /tmp
    # with open('/tmp/cmd_def', 'w') as f:
    #     json.dump(cmd_def, f, indent=2)

    cmd = f'lua require("config.dap.functions").flow_debug({repr(cmd_def["cmd"])})'
    vim.command(cmd)


def vim_runner(cmd_def):
    """vim_runner: run a command in the vim tty"""
    cleanup()
    with _script(cmd_def) as script_path:
        term_close = vim.eval('g:term_close')
        if 'nvim' in vim.eval('$VIMRUNTIME'):
            prev_win = vim.eval('win_getid()')
            vim.command(f'15split term://{script_path}')
            vim.command('normal! G')
            vim.command(f'call win_gotoid({prev_win})')
        else:
            vim.command(f'terminal {term_close} ++rows=15 {script_path}')


def tmux_runner(cmd_def):
    """tmux_runner: accept a command definition and then run it as a shell script in the tmux session.pane."""
    cleanup()
    with _script(cmd_def) as script:
        args = [
            'tmux',
            'send',
            '-t',
            '%s.%s' % (cmd_def['tmux_session'], cmd_def['tmux_pane']),
            "sh -c '%s'" % script,
            'ENTER',
        ]

        env = os.environ.copy()
        process = subprocess.Popen(args, env=env)
        process.wait()


def async_remote_runner(cmd_def):
    """async_remote_runner: run the command against a vim-flow remote"""
    try:
        from requests.exceptions import RequestsDependencyWarning
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
            import requests
    except ImportError:
        import requests

    base_url = vim.eval('g:vim_flow_remote_address')
    if not base_url.startswith('http'):
        base_url = 'http://' + 'url'
    url = urllib.parse.urljoin(base_url, 'async')

    try:
        resp = requests.post(url, data=cmd_def['cmd'])
    except Exception:
        vim.command('echom "vim-flow: unable to submit job: {}"'.format(url))
        return

    vim.command('echom "vim-flow: async job submitted {}"'.format(resp.status_code))


def sync_remote_runner(cmd_def):
    """sync_remote_runner: run the command against a vim-flow remote"""
    vim.command('echom "vim-flow: {}"'.format('res'))
