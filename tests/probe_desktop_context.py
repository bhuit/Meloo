"""Read-only diagnostic of desktop/job context; makes no permission changes."""
import ctypes
from ctypes import wintypes as w
import json

k=ctypes.WinDLL('kernel32',use_last_error=True)
u=ctypes.WinDLL('user32',use_last_error=True)
k.GetCurrentProcess.restype=w.HANDLE
u.GetProcessWindowStation.restype=w.HANDLE
u.GetThreadDesktop.argtypes=[w.DWORD];u.GetThreadDesktop.restype=w.HANDLE
u.OpenInputDesktop.argtypes=[w.DWORD,w.BOOL,w.DWORD];u.OpenInputDesktop.restype=w.HANDLE
u.GetUserObjectInformationW.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
u.CloseDesktop.argtypes=[w.HANDLE]
k.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,ctypes.POINTER(w.BOOL)]
k.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]

def name(handle):
    if not handle:return {'error':ctypes.get_last_error()}
    buf=ctypes.create_unicode_buffer(256);needed=w.DWORD()
    ok=u.GetUserObjectInformationW(handle,2,buf,ctypes.sizeof(buf),ctypes.byref(needed))
    return buf.value if ok else {'error':ctypes.get_last_error()}

desktop=u.OpenInputDesktop(0,False,1)
result={'window_station':name(u.GetProcessWindowStation()),'thread_desktop':name(u.GetThreadDesktop(k.GetCurrentThreadId())),'input_desktop':name(desktop)}
if desktop:u.CloseDesktop(desktop)
in_job=w.BOOL();k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(in_job))
flags=w.DWORD();ok=k.QueryInformationJobObject(None,4,ctypes.byref(flags),4,None)
result.update(in_job=bool(in_job.value),ui_restrictions=flags.value if ok else None,query_error=0 if ok else ctypes.get_last_error())
a=ctypes.WinDLL('advapi32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
a.IsTokenRestricted.argtypes=[w.HANDLE];a.IsTokenRestricted.restype=w.BOOL
a.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
a.GetSidSubAuthorityCount.argtypes=[ctypes.c_void_p];a.GetSidSubAuthorityCount.restype=ctypes.POINTER(w.BYTE)
a.GetSidSubAuthority.argtypes=[ctypes.c_void_p,w.DWORD];a.GetSidSubAuthority.restype=ctypes.POINTER(w.DWORD)

def token_context(process):
    token=w.HANDLE()
    if not a.OpenProcessToken(process,8,ctypes.byref(token)):return {'error':ctypes.get_last_error()}
    try:
        info={'restricted_token':bool(a.IsTokenRestricted(token))}
        needed=w.DWORD();buf=ctypes.create_string_buffer(256)
        if a.GetTokenInformation(token,25,buf,len(buf),ctypes.byref(needed)):
            sid=ctypes.c_void_p.from_buffer(buf).value
            count=a.GetSidSubAuthorityCount(sid)[0]
            info['integrity_level']=hex(a.GetSidSubAuthority(sid,count-1)[0])
        value=w.DWORD()
        if a.GetTokenInformation(token,29,ctypes.byref(value),4,ctypes.byref(needed)):info['app_container']=bool(value.value)
        return info
    finally:k.CloseHandle(token)
result['tool_process']=token_context(k.GetCurrentProcess())
import sys
if len(sys.argv)>1:
    process=k.OpenProcess(0x1000,False,int(sys.argv[1]))
    if process:
        result['explorer_process']=token_context(process)
        k.CloseHandle(process)
print(json.dumps(result))
