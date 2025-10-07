import tkinter as tk
from tkinter import ttk

class Tooltip:
    """Tkinter 위젯에 간단한 툴팁을 추가할 수 있는 클래스."""
    def __init__(self, widget, text, delay=500, autohide=None, bg_color="#FFFFFF", fg_color="#000000", padding=(5, 3)):
        """
        Args:
            widget: 툴팁을 연결할 위젯.
            text: 툴팁에 표시할 초기 텍스트.
            delay (int): 마우스를 올린 후 툴팁이 나타나기까지의 시간(ms).
            autohide (int, optional): 툴팁이 자동으로 사라지기까지의 시간(ms). 값이 None이면 마우스가 위젯을 벗어날 때까지 사라지지 않음.
            bg_color (str): 툴팁의 배경 색.
            fg_color (str): 툴팁의 글자 색.
            padding (tuple): 툴팁의 내부 여백(x, y).
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.autohide = autohide
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.padding = padding

        self.tip_window = None
        self.tip_label = None
        self.schedule_id = None
        self.autohide_id = None
        self.is_mouse_pressed = False

        self.widget.bind("<Enter>", self.schedule_tip)
        self.widget.bind("<Leave>", self.hide_tip)
        self.widget.bind("<Motion>", self.position_tip)
        self.widget.bind("<ButtonPress-1>", self.on_mouse_press)
        self.widget.bind("<ButtonRelease-1>", self.on_mouse_release)

    def schedule_tip(self, event=None):
        if self.tip_window or self.schedule_id: return
        self.schedule_id = self.widget.after(self.delay, self.show_tip)

    def show_tip(self):
        if self.tip_window: return
        self.schedule_id = None
        
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)

        self.tip_label = ttk.Label(self.tip_window, text=self.text, justify='left', background=self.bg_color, foreground=self.fg_color, padding=self.padding)
        self.tip_label.pack(ipadx=1)

        self.position_tip()

        if not self.is_mouse_pressed:
            self.reschedule_autohide()

    def position_tip(self, event=None):
        if not self.tip_window: return
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10
        self.tip_window.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None

        if self.autohide_id:
            self.widget.after_cancel(self.autohide_id)
            self.autohide_id = None

        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
            self.tip_label = None

    def update_text(self, new_text):
        self.text = new_text
        if self.tip_window and self.tip_label:
            self.tip_label.config(text=self.text)

    def on_mouse_press(self, event=None):
        self.is_mouse_pressed = True
        self.cancel_autohide()

    def on_mouse_release(self, event=None):
        self.is_mouse_pressed = False
        self.reschedule_autohide()

    def cancel_autohide(self):
        if self.autohide_id:
            self.widget.after_cancel(self.autohide_id)
            self.autohide_id = None

    def reschedule_autohide(self):
        self.cancel_autohide()
        if self.autohide and self.tip_window:
            self.autohide_id = self.widget.after(self.autohide, self.hide_tip)
