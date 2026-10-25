"""Temporary local diagnosis: modifier/button states and window classes only."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import time

u=ctypes.WinDLL('user32',use_last_error=True)
u.GetForegroundWindow.restype=wintypes.HWND
u.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
u.GetAsyncKeyState.argtypes=[ctypes.c_int]
u.GetAsyncKeyState.restype=ctypes.c_short
u.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)]
u.WindowFromPoint.argtypes=[wintypes.POINT]
u.WindowFromPoint.restype=wintypes.HWND
u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
u.GetAncestor.restype=wintypes.HWND

def cls(handle):
    text=ctypes.create_unicode_buffer(256)
    u.GetClassNameW(handle,text,256)
    return text.value

events=[]; last=None; start=time.monotonic(); count=0
while time.monotonic()-start<45:
    point=wintypes.POINT();u.GetCursorPos(ctypes.byref(point))
    state={
        'left':bool(u.GetAsyncKeyState(1)&0x8000),
        'right':bool(u.GetAsyncKeyState(2)&0x8000),
        'ctrl':bool(u.GetAsyncKeyState(0x11)&0x8000),
        'left_ctrl':bool(u.GetAsyncKeyState(0xA2)&0x8000),
        'right_ctrl':bool(u.GetAsyncKeyState(0xA3)&0x8000),
        'altgr':bool(u.GetAsyncKeyState(0xA5)&0x8000),
        'foreground':cls(u.GetForegroundWindow()),
        'under_pointer':cls(u.GetAncestor(u.WindowFromPoint(point),2)),
    }
    if state!=last:
        events.append({'seconds':round(time.monotonic()-start,2),**state})
        last=state
    count+=1;time.sleep(.016)
result={'samples':count,'events':events[-200:]}
Path(__file__).with_name('artifacts').joinpath('drag-input-probe.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
