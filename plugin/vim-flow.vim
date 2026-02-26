" NOTE: we cannot do hot reloading without dynamically reloading python3 modules
if exists("g:vim_flow_loaded") || &cp
  finish
endif
let g:vim_flow_loaded = 1

let g:vim_flow_remote_address = "http://localhost:7000"

" make sure that vim is compiled with correct python2.7 suppor
if !has("python3")
  echo "vim-flow requires python3 support"
  finish
endif

let s:plugin_path = expand('<sfile>:p:h')

python3 <<EOF
import sys
from os import path as p
import vim

def _init_vim_flow():
    global cli
    if "cli" in globals():
        return
    plugin_path = vim.eval("s:plugin_path")
    lib_path = p.abspath(p.join(plugin_path, "../lib"))
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    import cli
EOF

" run flow for the current window
command! FlowRun :python3 _init_vim_flow(); cli.run_flow("")

" run flow for the current window
command! FlowDebug :python3 _init_vim_flow(); cli.debug_flow("")

" toggle lock on / off for current file
command! FlowToggleLock :python3 _init_vim_flow(); cli.toggle_lock("")

command! -nargs=1 FlowSet :python3 _init_vim_flow(); cli.toggle_lock(<f-args>)

function! FlowSetFile(filename)
  :python3 _init_vim_flow(); cli.toggle_lock(vim.eval("a:filename"))
endfunction
