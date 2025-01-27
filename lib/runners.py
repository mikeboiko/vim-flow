import contextlib
import glob
import os
import subprocess
import stat
import time
import urllib.parse
import vim

import requests

def _build_script(cmd_def):
    '''_build_script: in order to simplify things such as escaping and
    multiline commands, we template out all `cmds` into a script that is
    written to a tempfile and executed
    '''
    filepath = '/tmp/flow--{}'.format(int(time.time()))
    # print(filepath)

    # if the script doesn't start with a hashbang, then we default to the local $SHELL var
    with open(filepath, 'w') as fh:
        if not cmd_def['cmd'].startswith('#!'):
            hashbang = '#!{}\n'.format(os.environ.get('SHELL', '/usr/bin/env bash'))
            fh.write(hashbang)

        fh.write(cmd_def['cmd'])
        fh.write('\n')

    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)
    return filepath

def cleanup():
    '''cleanup: due to the tmux send keys command being asynchronous, we can not guarantee when a command is finished
    and therefore can not clean up after ourselves consistently.
    '''
    for filepath in glob.glob("/tmp/flow--*"):
        os.remove(filepath)

@contextlib.contextmanager
def _script(cmd_def):
    '''_script: a context manager for creating a command script and cleaning it up

    usage:
        with _script(cmd_def) as script_filepath:
            print script_filepath
    '''
    filepath = _build_script(cmd_def)
    yield filepath

def vim_runner(cmd_def):
    '''vim_runner: run a command in the vim tty
    '''
    cleanup()
    with _script(cmd_def) as script_path:
        term_close = vim.eval('g:term_close')
        if 'nvim' in vim.eval('$VIMRUNTIME'):
            vim.command(f'15split term://{script_path}')
        else:
            vim.command(f'terminal {term_close} ++rows=15 {script_path}')

def tmux_runner(cmd_def):
    '''tmux_runner: accept a command definition and then run it as a shell script in the tmux session.pane.
    '''
    cleanup()
    with _script(cmd_def) as script:
        args = [
            'tmux', 'send', '-t',
            '%s.%s' % (cmd_def['tmux_session'], cmd_def['tmux_pane']),
            'sh -c \'%s\'' % script, 'ENTER'
        ]

        env = os.environ.copy()
        process = subprocess.Popen(args, env=env)
        process.wait()

def async_remote_runner(cmd_def):
    '''async_remote_runner: run the command against a vim-flow remote
    '''
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
    '''sync_remote_runner: run the command against a vim-flow remote
    '''
    vim.command('echom "vim-flow: {}"'.format('res'))
