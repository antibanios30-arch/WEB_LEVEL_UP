import asyncio
import threading

ff_status = {
    'bot_online': False,
    'bot_uid': None,
    'auto_running': False,
    'current_team_code': None,
    'region': 'IND',
}

_pending_command = {'cmd': None, 'data': None}
_cmd_lock = threading.Lock()
_ff_loop = None
_ff_loop_lock = threading.Lock()

def set_ff_loop(loop):
    global _ff_loop
    with _ff_loop_lock:
        _ff_loop = loop

def get_ff_loop():
    with _ff_loop_lock:
        return _ff_loop

def set_command(cmd, data=None):
    with _cmd_lock:
        _pending_command['cmd'] = cmd
        _pending_command['data'] = data

def pop_command():
    with _cmd_lock:
        cmd = _pending_command['cmd']
        data = _pending_command['data']
        _pending_command['cmd'] = None
        _pending_command['data'] = None
        return cmd, data
