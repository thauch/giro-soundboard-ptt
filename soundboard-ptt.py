"""Windows PTT helper. Requires Python 3 with Tkinter; no third-party packages."""
import ctypes
from ctypes import wintypes
import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.request import Request, urlopen
from urllib.parse import urlparse

__version__ = '0.2.4-beta.1'

if os.name != 'nt':
    raise SystemExit('Run this helper on the Windows gaming PC.')

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wintypes.DWORD), ('wParamL', wintypes.WORD), ('wParamH', wintypes.WORD)]
class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]
class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', INPUTUNION)]
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

def virtual_key(key):
    key = key.strip().upper()
    named = {'SPACE':0x20,'ENTER':0x0D,'TAB':0x09,'SHIFT':0x10,'CTRL':0x11,'ALT':0x12,'CAPSLOCK':0x14,'BACKSPACE':0x08,'UP':0x26,'DOWN':0x28,'LEFT':0x25,'RIGHT':0x27,'HOME':0x24,'END':0x23,'INSERT':0x2D,'DELETE':0x2E}
    if key in named: return named[key]
    if len(key) == 1 and key.isascii() and key.isalnum(): return ord(key)
    if key.startswith('F') and key[1:].isdigit() and 1 <= int(key[1:]) <= 24: return 0x70 + int(key[1:]) - 1
    raise ValueError('Use a letter, digit, F1–F24, or a named key such as Space, Ctrl, or Shift.')

def key_event(key, up=False):
    vk = virtual_key(key)
    scan = user32.MapVirtualKeyW(vk, 0)
    event = INPUT(type=1, u=INPUTUNION(ki=KEYBDINPUT(0, scan, 0x0008 | (0x0002 if up else 0) | (0x0001 if vk in [0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x2D,0x2E] else 0), 0, 0)))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError('Windows rejected the keypress. Check game/helper privileges.')

class Helper:
    def __init__(self):
        self.root = tk.Tk(); self.root.title(f"Giro's Soundboard v{__version__} — Push To Talk Helper")
        self.root.geometry('580x590'); self.root.minsize(520,590); self.root.configure(bg='#0c1118')
        self.stop = threading.Event(); self.held = None; self.mode = 'Off'; self.thread = None
        self.keys = {'Squad':'J','Local':'K'}
        self.status = tk.StringVar(value='Disconnected — Pair with your soundboard to connect.')
        style = ttk.Style(self.root); style.theme_use('clam')
        style.configure('.', font=('Segoe UI',10), background='#141c27', foreground='#e8eef5')
        style.configure('TFrame', background='#141c27')
        style.configure('TLabel', background='#141c27', foreground='#bccbdd')
        style.configure('Title.TLabel', font=('Segoe UI',19,'bold'), foreground='#69e2c2')
        style.configure('TEntry', fieldbackground='#0c131d', foreground='#e8eef5', padding=8)
        style.configure('TCombobox', fieldbackground='#0c131d', foreground='#e8eef5', padding=8)
        style.map('TCombobox', fieldbackground=[('readonly','#0c131d')], foreground=[('readonly','#e8eef5')])
        style.configure('TButton', background='#294437', foreground='#c6f4e5', padding=(14,10), borderwidth=0)
        style.map('TButton', background=[('active','#365c49')])
        self.status_label = tk.Label(self.root, textvariable=self.status, bg='#0c1118', fg='#e8c684', font=('Segoe UI',10), anchor='w', justify='left', wraplength=520, padx=20, pady=14)
        self.status_label.pack(side='bottom', fill='x')
        frame = ttk.Frame(self.root, padding=24); frame.pack(fill='both', expand=True,padx=16,pady=16)
        ttk.Label(frame,text='Push To Talk Helper',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text=f"Giro's Soundboard · v{__version__}").pack(anchor='w',pady=(4,16))
        ttk.Label(frame, text='Soundboard HTTPS Address').pack(anchor='w')
        self.url = ttk.Entry(frame); self.url.insert(0, 'https://dirtydeedsgaming.com:8443'); self.url.pack(fill='x', pady=(5,12))
        ttk.Label(frame, text='Pairing Code').pack(anchor='w')
        self.code = ttk.Entry(frame); self.code.pack(fill='x',pady=(5,12))
        keyframe=ttk.Frame(frame);keyframe.pack(fill='x',pady=6)
        keyframe.columnconfigure(0,weight=1);keyframe.columnconfigure(1,weight=1)
        ttk.Label(keyframe,text='Squad Key').grid(row=0,column=0,sticky='w')
        ttk.Label(keyframe,text='Local Key').grid(row=0,column=1,sticky='w',padx=(12,0))
        self.squad_key=ttk.Entry(keyframe);self.squad_key.insert(0,'J');self.squad_key.grid(row=1,column=0,sticky='ew',pady=5)
        self.local_key=ttk.Entry(keyframe);self.local_key.insert(0,'K');self.local_key.grid(row=1,column=1,sticky='ew',padx=(12,0),pady=5)
        for entry in [self.squad_key,self.local_key]: entry.bind('<FocusOut>',lambda _:self.change_mode());entry.bind('<Return>',lambda _:self.change_mode())
        ttk.Label(frame,text='Letters, Numbers, F1–F24, Space, Ctrl, Shift, Alt').pack(anchor='w',pady=(0,8))
        self.choice = ttk.Combobox(frame, values=['Off', 'Squad', 'Local'], state='readonly'); self.choice.set('Off'); self.choice.pack(fill='x', pady=8)
        self.choice.bind('<<ComboboxSelected>>', lambda _: self.change_mode())
        buttons = ttk.Frame(frame); buttons.pack(fill='x',pady=(8,0))
        self.connect_button = ttk.Button(buttons, text='Pair And Connect', command=self.connect); self.connect_button.pack(side='left')
        ttk.Button(buttons, text='Disconnect / Release Key', command=self.disconnect).pack(side='right')
        self.messages = []; self.lock = threading.Lock()
        self.root.after(100, self.tick); self.root.protocol('WM_DELETE_WINDOW', self.close)
    def change_mode(self):
        try:
            keys={'Squad':self.squad_key.get().strip().upper(),'Local':self.local_key.get().strip().upper()}
            for key in keys.values(): virtual_key(key)
            with self.lock:
                self.release(); self.keys=keys; self.mode=self.choice.get()
        except (ValueError,RuntimeError) as error:
            with self.lock: self.mode='Off'
            self.choice.set('Off'); self.status.set(str(error))
    def release(self):
        if self.held:
            key = self.held
            key_event(key, True)
            self.held = None
    def request(self, base, path, token=None, body=None):
        headers = {'Content-Type':'application/json'}
        if token: headers['X-Remote-Token'] = token
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(req, timeout=2) as response: return json.load(response)
    def connect(self):
        if self.thread and self.thread.is_alive(): return
        self.change_mode()
        base = self.url.get().strip().rstrip('/')
        parsed = urlparse(base)
        if parsed.scheme != 'https' or not parsed.hostname:
            self.status.set('Enter a valid HTTPS address.'); return
        code = self.code.get().strip()
        self.stop.clear(); self.connect_button.state(['disabled'])
        self.thread = threading.Thread(target=self.worker, args=(base, code), daemon=True); self.thread.start()
    def worker(self, base, code):
        try:
            token = self.request(base, '/api/remote/pair', body={'code':code})['token']
            while not self.stop.is_set():
                settings = self.request(base, '/api/remote/status', token)
                state = self.request(base, '/api/live/state')
                session = settings.get('sessionId')
                playing = any(row.get('sessionId') == session and row.get('status') == 'playing' and time.time()*1000-row.get('lastSeen',0) < 15000 for row in state.get('localPlayback', [])) if session else False
                with self.lock:
                    key = self.keys.get(self.mode) if playing else None
                    if self.held != key:
                        self.release()
                        if key: key_event(key); self.held = key
                self.messages.append('Connected — Holding ' + key if key else 'Connected — ' + ('PTT off' if self.mode == 'Off' else 'waiting for Local audio'))
                self.stop.wait(.1)
        except Exception as error:
            self.messages.append('Disconnected: ' + str(error))
        finally:
            with self.lock:
                try: self.release()
                except Exception as error: self.messages.append(str(error))
            self.messages.append('__finished__')
    def disconnect(self):
        self.stop.set()
        self.status.set('Disconnected — Key Released')
        self.status_label.configure(fg='#e8c684')
        with self.lock:
            try: self.release()
            except Exception as error: self.status.set(str(error))
    def tick(self):
        while self.messages:
            message = self.messages.pop(0)
            if message == '__finished__': self.connect_button.state(['!disabled'])
            else:
                self.status.set(message)
                self.status_label.configure(fg='#69e2c2' if message.startswith('Connected') else '#e8c684')
        self.root.after(100, self.tick)
    def close(self):
        self.disconnect(); self.root.destroy()
    def run(self): self.root.mainloop()

if __name__ == '__main__': Helper().run()
