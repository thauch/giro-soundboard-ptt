"""Windows PTT helper. Requires Python 3 with Tkinter; no third-party packages."""
import ctypes
from ctypes import wintypes
import json
import os
import re
import webbrowser
from queue import Queue, Empty
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse, quote

__version__ = '0.3.1-beta.1'

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
        self.root.geometry('580x740'); self.root.minsize(520,740); self.root.configure(bg='#0c1118')
        self.stop = threading.Event(); self.held = None; self.mode = 'Off'; self.thread = None
        self.keys = {'Squad':'J','Local':'K'}
        self.token = None; self.base = None; self.devices = []; self.busy = False
        self.status = tk.StringVar(value='Sign in with Discord, then choose a remote-enabled host.')
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
        self.update_banner = ttk.Button(frame, text='', command=lambda:webbrowser.open(self.release_url))
        ttk.Label(frame,text='Push To Talk Helper',style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame,text=f"Giro's Soundboard · v{__version__}").pack(anchor='w',pady=(4,16))
        ttk.Label(frame, text='Soundboard HTTPS Address').pack(anchor='w')
        self.url = ttk.Entry(frame); self.url.insert(0, 'https://dirtydeedsgaming.com:8443'); self.url.pack(fill='x', pady=(5,12))
        login_buttons = ttk.Frame(frame); login_buttons.pack(fill='x', pady=(0,12))
        self.discord_icon = tk.BitmapImage(data='#define discord_width 24\n#define discord_height 18\nstatic unsigned char discord_bits[] = { 0x00, 0x00, 0x00, 0xc0, 0x80, 0x03, 0xe0, 0xc3, 0x07, 0xf0, 0xff, 0x0f, 0xf8, 0xff, 0x1f, 0xf8, 0xff, 0x1f, 0xf8, 0xff, 0x1f, 0xfc, 0xfe, 0x3e, 0x7c, 0x7c, 0x3c, 0x7c, 0x7c, 0x3c, 0x7c, 0x7c, 0x3c, 0xfe, 0xfe, 0x7e, 0xfe, 0xff, 0x7f, 0xfe, 0xff, 0x7f, 0x7c, 0x00, 0x3e, 0xf8, 0x00, 0x1f, 0x30, 0x00, 0x0e, 0x00, 0x00, 0x00 };', foreground='#e8eef5')
        self.login_button = ttk.Button(login_buttons, text='  Sign In With Discord', image=self.discord_icon, compound='left', command=self.login); self.login_button.pack(side='left')
        ttk.Button(login_buttons, text='Refresh Hosts', command=self.refresh_hosts).pack(side='right')
        ttk.Label(frame, text='Host Computer (Remote Control Enabled)').pack(anchor='w')
        self.host = ttk.Combobox(frame, state='readonly'); self.host.pack(fill='x', pady=(5,12))
        ttk.Label(frame, text='Sign in on the host soundboard and enable Remote control.', wraplength=480).pack(anchor='w')
        keyframe=ttk.Frame(frame);keyframe.pack(fill='x',pady=6)
        keyframe.columnconfigure(0,weight=1);keyframe.columnconfigure(1,weight=1)
        ttk.Label(keyframe,text='Squad Key').grid(row=0,column=0,sticky='w')
        ttk.Label(keyframe,text='Local Key').grid(row=0,column=1,sticky='w',padx=(12,0))
        self.squad_key=ttk.Entry(keyframe);self.squad_key.insert(0,'J');self.squad_key.grid(row=1,column=0,sticky='ew',pady=5)
        self.local_key=ttk.Entry(keyframe);self.local_key.insert(0,'K');self.local_key.grid(row=1,column=1,sticky='ew',padx=(12,0),pady=5)
        for entry in [self.squad_key,self.local_key]: entry.bind('<FocusOut>',lambda _:self.change_mode());entry.bind('<Return>',lambda _:self.change_mode())
        ttk.Label(frame,text='Letters, Numbers, F1–F24, Space, Ctrl, Shift, Alt').pack(anchor='w',pady=(0,8))
        ttk.Label(frame, text='Choose where you want it to play').pack(anchor='w', pady=(20,0))
        self.choice = ttk.Combobox(frame, values=['Off', 'Squad', 'Local'], state='readonly'); self.choice.set('Off'); self.choice.pack(fill='x', pady=8)
        self.choice.bind('<<ComboboxSelected>>', lambda _: self.change_mode())
        buttons = ttk.Frame(frame); buttons.pack(fill='x',pady=(8,0))
        self.connect_button = ttk.Button(buttons, text='Connect To Host', command=self.connect); self.connect_button.pack(side='left')
        ttk.Button(buttons, text='Disconnect / Release Key', command=self.disconnect).pack(side='right')
        self.messages = Queue(); self.lock = threading.Lock()
        threading.Thread(target=self.check_updates, daemon=True).start()
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
        if token: headers['X-Helper-Token'] = token
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urlopen(req, timeout=2) as response: return json.load(response)
        except HTTPError as error:
            try: message = json.load(error).get('error', str(error))
            except Exception: message = str(error)
            raise RuntimeError(message) from error
    def validated_base(self):
        base = self.url.get().strip().rstrip('/')
        parsed = urlparse(base)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Enter a valid HTTPS address.')
        return base
    def login(self):
        if self.busy: return
        self.disconnect(); self.token = None; self.devices = []; self.host.set(''); self.host['values'] = []
        try: self.base = self.validated_base()
        except ValueError as error: self.status.set(str(error)); return
        self.busy = True; self.login_button.state(['disabled'])
        self.status.set('Finish Discord sign-in in your browser.')
        threading.Thread(target=self.login_worker, args=(self.base,), daemon=True).start()
    def login_worker(self, base):
        try:
            flow = self.request(base, '/api/helper/login/start', body={})
            path = flow['verificationPath']
            if not path.startswith('/auth/discord?'): raise ValueError('Invalid login address.')
            webbrowser.open(base + path)
            for _ in range(300):
                result = self.request(base, '/api/helper/login/poll', body={'request':flow['request'], 'secret':flow['secret']})
                if result.get('token'):
                    devices = self.request(base, '/api/helper/devices', result['token'])['devices']
                    self.messages.put(('login', result['token'], devices)); return
                time.sleep(2)
            raise ValueError('Discord sign-in timed out. Try again.')
        except Exception as error: self.messages.put(str(error))
        finally: self.messages.put(('login_finished',))
    def refresh_hosts(self):
        if not self.token: self.status.set('Sign in with Discord first.'); return
        def refresh():
            try: self.messages.put(('devices', self.request(self.base, '/api/helper/devices', self.token)['devices']))
            except Exception as error: self.messages.put(str(error))
        threading.Thread(target=refresh, daemon=True).start()
    def set_devices(self, devices):
        selected = self.host.current()
        previous = self.devices[selected]['id'] if 0 <= selected < len(self.devices) else None
        self.devices = devices
        self.host['values'] = [d['name'] + (' — online' if d['online'] else ' — offline') for d in devices]
        self.host.set('')
        selected = next((index for index, device in enumerate(devices) if device['id'] == previous and device['online']), None)
        if selected is None:
            selected = next((index for index, device in enumerate(devices) if device['online']), 0 if devices else None)
        if selected is not None: self.host.current(selected)
        self.status.set(('Host selected — click Connect To Host.' if devices[selected]['online'] else 'Hosts offline. Enable Remote control on the host and refresh.') if devices else 'No hosts found. Sign in on the host and enable Remote control.')
    def check_updates(self):
        try:
            req = Request('https://api.github.com/repos/thauch/giro-soundboard-ptt/releases?per_page=100', headers={'User-Agent':'Giro-Soundboard-PTT', 'Accept':'application/vnd.github+json'})
            with urlopen(req, timeout=10) as response: releases = json.load(response)
            def version(tag):
                match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?', tag)
                if not match: return None
                major, minor, patch, stage, number = match.groups()
                return (int(major), int(minor), int(patch), {'alpha':0,'beta':1,'rc':2,None:3}[stage], int(number or 0))
            newer = [r for r in releases if not r.get('draft') and version(r.get('tag_name','')) and version(r['tag_name']) > version(__version__) and r.get('html_url','').startswith('https://github.com/thauch/giro-soundboard-ptt/releases/tag/')]
            if newer:
                release = max(newer, key=lambda r:version(r['tag_name']))
                self.messages.put(('update', release['tag_name'], release['html_url']))
        except Exception: pass
        finally: self.root_update_due = time.monotonic() + 3600
    def connect(self):
        if self.thread and self.thread.is_alive(): return
        if not self.token: self.status.set('Sign in with Discord first.'); return
        if self.url.get().strip().rstrip('/') != self.base: self.status.set('Address changed. Sign in with Discord again.'); return
        index = self.host.current()
        if not 0 <= index < len(self.devices): self.status.set('Choose a host computer.'); return
        if not self.devices[index]['online']: self.status.set('Host offline. Enable Remote control and refresh hosts.'); return
        self.change_mode()
        self.stop.clear(); self.connect_button.state(['disabled'])
        self.thread = threading.Thread(target=self.worker, args=(self.base, self.token, self.devices[index]['id']), daemon=True); self.thread.start()
    def worker(self, base, token, device):
        try:
            while not self.stop.is_set():
                settings = self.request(base, '/api/helper/status?device=' + quote(device, safe=''), token)
                state = self.request(base, '/api/live/state')
                session = settings.get('sessionId')
                playing = any(row.get('sessionId') == session and row.get('status') == 'playing' and time.time()*1000-row.get('lastSeen',0) < 15000 for row in state.get('localPlayback', [])) if session else False
                with self.lock:
                    key = self.keys.get(self.mode) if playing else None
                    if self.held != key:
                        self.release()
                        if key: key_event(key); self.held = key
                self.messages.put('Connected — Holding ' + key if key else 'Connected — ' + ('PTT off' if self.mode == 'Off' else 'waiting for Local audio'))
                self.stop.wait(.1)
        except Exception as error:
            self.messages.put('Disconnected: ' + str(error))
        finally:
            with self.lock:
                try: self.release()
                except Exception as error: self.messages.put(str(error))
            self.messages.put('__finished__')
    def disconnect(self):
        self.stop.set()
        self.status.set('Disconnected — Key Released')
        self.status_label.configure(fg='#e8c684')
        with self.lock:
            try: self.release()
            except Exception as error: self.status.set(str(error))
    def tick(self):
        while True:
            try: message = self.messages.get_nowait()
            except Empty: break
            if isinstance(message, tuple):
                if message[0] == 'login': self.token = message[1]; self.set_devices(message[2])
                elif message[0] == 'devices': self.set_devices(message[1])
                elif message[0] == 'login_finished': self.busy = False; self.login_button.state(['!disabled'])
                elif message[0] == 'update':
                    self.release_url = message[2]; self.update_banner.configure(text='Update available: ' + message[1] + ' — View release'); self.update_banner.pack(before=self.update_banner.master.winfo_children()[1], fill='x', pady=(0,12))
                continue
            if message == '__finished__': self.connect_button.state(['!disabled'])
            else:
                self.status.set(message)
                self.status_label.configure(fg='#69e2c2' if message.startswith('Connected') else '#e8c684')
        if getattr(self, 'root_update_due', float('inf')) <= time.monotonic():
            self.root_update_due = float('inf'); threading.Thread(target=self.check_updates, daemon=True).start()
        self.root.after(100, self.tick)
    def close(self):
        self.disconnect(); self.root.destroy()
    def run(self): self.root.mainloop()

if __name__ == '__main__': Helper().run()
