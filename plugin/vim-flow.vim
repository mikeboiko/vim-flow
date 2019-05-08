if exists("g:vim_flow_loaded") || &cp
  finish
endif
let g:vim_flow_loaded = 1

" make sure that vim is compiled with correct python2.7 suppor
if !has("python3")
  echo "vim-flow requires python3 support"
  finish
endif

python3 <<EOF
from os import path as p
import sys
import vim

lib_path = p.abspath(p.join(vim.eval("expand('<sfile>:p:h')"), "../lib"))
sys.path.insert(0, lib_path)

import cli
EOF

" run flow for the current window
command! FlowRun :python3 cli.run_flow()

" toggle lock on / off for current file
command! FlowToggleLock :python3 cli.toggle_lock()
