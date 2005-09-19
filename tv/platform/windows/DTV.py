#import app
#app.main()

# NEEDS: do not commit
print "Your DTV session has been hijacked for Mozilla testing."

import win32gui, win32api
from win32con import *
from ctypes import *
from ctypes.wintypes import *
user32 = windll.user32

# CREATE TOP-LEVEL
def onClose(hwnd, msg, wparam, lparam):
    win32gui.PostQuitMessage(0)
theControl = None
def onSize(hwnd, msg, wparam, lparam):
    theControl and theControl.recomputeSize()
def onActivate(hwnd, msg, wparam, lparam):
    if theControl:
        wparam == WA_ACTIVE and theControl.activate()
        wparam == WA_INACTIVE and theControl.deactivate()
messageMap = { WM_CLOSE: onClose,
               WM_SIZE: onSize,
               WM_ERASEBKGND: lambda *args: 1, # flicker reduction
               WM_ACTIVATE: onActivate,
}

hInstance = win32api.GetModuleHandle(None)
wc = win32gui.WNDCLASS()
wc.style = CS_HREDRAW | CS_VREDRAW
wc.lpfnWndProc = messageMap
wc.cbWndExtra = 0
wc.hInstance = hInstance
wc.hIcon = win32gui.LoadIcon(0, IDI_APPLICATION)
wc.hCursor = win32gui.LoadCursor(0, IDC_ARROW)
wc.hbrBackground = win32gui.GetStockObject(WHITE_BRUSH)
#wc.lpszMenuName = None
wc.lpszClassName = "Test frame"
mainWindowClassAtom = win32gui.RegisterClass(wc)

hwndTop = win32gui.CreateWindowEx(0, mainWindowClassAtom,
            "Test DTV", WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
            CW_USEDEFAULT, CW_USEDEFAULT, 0, 0, hInstance, None)
user32.ShowWindow(hwndTop, SW_SHOWDEFAULT)
user32.UpdateWindow(hwndTop)

# CREATE CHILD
wc = win32gui.WNDCLASS()
wc.style = 0 
wc.lpfnWndProc = { }
wc.cbWndExtra = 0
wc.hInstance = win32api.GetModuleHandle(None)
wc.hIcon = win32gui.LoadIcon(0, IDI_APPLICATION)
wc.hCursor = win32gui.LoadCursor(0, IDC_ARROW)
wc.hbrBackground = win32gui.GetStockObject(WHITE_BRUSH)
#wc.lpszMenuName = None
wc.lpszClassName = "DTV Blank Window"
blankWindowClassAtom = win32gui.RegisterClass(wc)

hwndChild = win32gui.CreateWindowEx(0, blankWindowClassAtom,
            "", WS_CHILDWINDOW, 0, 0, 200,
            200, hwndTop, 0,
            win32api.GetModuleHandle(None), None)
#win32gui.ShowWindow(hwndChild, SW_SHOW)
win32gui.UpdateWindow(hwndChild)

print "hwnd: top = %s child = %s" % (hwndTop, hwndChild)
import MozillaBrowser
#m = MozillaBrowser.MozillaBrowser(hwndChild)
m = MozillaBrowser.MozillaBrowser(hwndTop)
theControl = m

print "Got m = %s" % m


print "Entering message loop"
msg = MSG()
returnCode = 0
while True:
    returnCode = user32.GetMessageA(byref(msg), None, 0, 0)
    if not returnCode:
        break
    user32.TranslateMessage(byref(msg))
    user32.DispatchMessageA(byref(msg))
    win32gui.UpdateWindow(hwndChild)
print "Leaving message loop"

import sys
sys.exit(returnCode)