import os, json, threading
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, font
from PIL import Image, ImageOps, ImageTk
from tooltip import Tooltip
from core.fonts import FontRegistry
from core.models import WatermarkConfig, ImageListManager
from core.metadata import get_exif_date
from core.watermark import draw_watermark

APP_VERSION = "0.26.3.1"
CONFIG_FILE = "settings.json"
ICON_FILE = "icon_image_128.png"
ICON_FILE_16 = "icon_image_16.png"
GITHUB_URL = "https://github.com/1st-world/photoEdit"


class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"촬영일 워터마크 삽입기 (v{APP_VERSION})")
        self.root.iconphoto(True, tk.PhotoImage(file=ICON_FILE), tk.PhotoImage(file=ICON_FILE_16))
        self.settings_file = CONFIG_FILE
        self.style = ttk.Style(self.root)

        self.font_registry = FontRegistry()
        self.list_manager = ImageListManager()

        # 변수 초기화
        self.selected_iid = None
        self.preview_update_job_id = None
        self.is_processing = False
        self.processing_thread = None

        # 탭 관련 변수 초기화
        self.tab_buttons = {}
        self.current_frame = None
        self.watermark_frame = None
        self.coming_soon_frame = None

        # Tk 변수 초기화
        available_fonts = self.font_registry.get_available_font_names()
        default_font = available_fonts[0] if available_fonts else ""
        self.font_name = tk.StringVar(value=default_font)
        self.font_size = tk.DoubleVar(value=3)
        self.font_color = tk.StringVar(value="#000000")
        self.bg_color = tk.StringVar(value="#FFFFFF")
        self.bg_opacity = tk.IntVar(value=50)
        self.bg_padding = tk.DoubleVar(value=1)
        self.position = tk.StringVar(value="우측 하단")
        self.margin = tk.DoubleVar(value=3)
        self.size_mode = tk.StringVar(value="백분율(%)")
        self.date_format = tk.StringVar(value="YYYY-MM-DD")
        self.save_mode = tk.StringVar(value="separate")

        self.load_settings()
        self.configure_styles()
        self.create_widgets()
        self.switch_tab("watermark")
        self.root.bind_all("<Button-1>", self._on_global_mouse_press)


    def get_current_config(self) -> WatermarkConfig:
        """UI의 Tk 변수들을 모아 WatermarkConfig 데이터 모델 객체로 반환합니다."""
        return WatermarkConfig(
            font_name=self.font_name.get() or None,
            font_size=self.font_size.get(),
            font_color=self.font_color.get(),
            bg_color=self.bg_color.get(),
            bg_opacity=self.bg_opacity.get(),
            bg_padding=self.bg_padding.get(),
            position=self.position.get(),
            margin=self.margin.get(),
            size_mode=self.size_mode.get(),
            date_format=self.date_format.get(),
            save_mode=self.save_mode.get()
        )


    def _on_global_mouse_press(self, event):
        """앱 전역에서 마우스 클릭을 감지하여, 포커스가 필요 없는 위젯에서 포커스를 제거합니다."""
        try:
            widget = event.widget
            widget_class = widget.winfo_class()

            # 마우스 클릭 시 포커스를 받지 않을 위젯 목록 (키보드 조작은 해당 없음)
            widgets_to_defocus = {
                "TButton",
                "TRadiobutton",
                "TScale"
            }
            if widget_class in widgets_to_defocus:
                # 위젯의 command가 정상적으로 실행되도록 아주 잠깐(1ms) 후에 포커스를 중립 프레임으로 이동
                self.root.after(1, lambda: self.main_content_frame.focus_set())
        except (tk.TclError, AttributeError):
            # TclError: 위젯이 파괴된 후 클릭하는 경우 등.
            # AttributeError: TCombobox 팝업 등에서 event.widget이 객체가 아닌 문자열(str)을 반환하는 경우 등.
            pass


    def configure_styles(self):
        # 색상 정의
        self.TAB_BAR_COLOR = "#3E3E3E"
        self.INACTIVE_TAB_FG = "#A0A0A0"
        self.ACTIVE_TAB_FG = "#000000"
        try:
            self.ACTIVE_TAB_BG = self.style.lookup('TFrame', 'background')
        except tk.TclError:
            self.ACTIVE_TAB_BG = "#F0F0F0"

        # 기본 폰트 정보 조회
        default_font_obj = font.nametofont("TkDefaultFont")
        self.default_font_family = default_font_obj.actual("family")

        # 탭 바 프레임 스타일
        self.style.configure("TabBar.TFrame", 
                             background=self.TAB_BAR_COLOR)

        # 탭 버튼 스타일
        self.style.configure("Tab.TButton",
                             background=self.TAB_BAR_COLOR,
                             foreground=self.INACTIVE_TAB_FG,
                             bordercolor=self.TAB_BAR_COLOR,
                             relief='flat',
                             padding=(12, 6))
        self.style.map("Tab.TButton",
            foreground=[
                ('disabled', self.ACTIVE_TAB_FG),
                ('pressed', self.ACTIVE_TAB_FG),
                ('active', self.ACTIVE_TAB_FG)
            ]
        )

        # 설정 버튼 스타일
        self.style.configure("Settings.TButton",
                             background=self.TAB_BAR_COLOR,
                             bordercolor=self.TAB_BAR_COLOR,
                             relief='flat',
                             padding=(12, 6))
        self.style.map("Settings.TButton",
            relief=[
                ('active', 'flat'),
                ('pressed', 'flat')
            ]
        )

        # 메인 콘텐츠 프레임 스타일
        self.style.configure("Main.TFrame", background=self.ACTIVE_TAB_BG, focuscolor=self.ACTIVE_TAB_BG)


    def create_widgets(self):
        self.frame_tab_bar = ttk.Frame(self.root, style="TabBar.TFrame")
        self.frame_tab_bar.pack(side='top', fill='x')

        frame_tabs = ttk.Frame(self.frame_tab_bar, style="TabBar.TFrame")
        frame_tabs.pack(side='left', padx=10, pady=5)

        # 탭 버튼 생성 및 저장
        self.tab_buttons["watermark"] = ttk.Button(frame_tabs, text="워터마크", style="Tab.TButton",
                                                   command=lambda: self.switch_tab("watermark"))
        self.tab_buttons["watermark"].pack(side='left')

        self.tab_buttons["feature2"] = ttk.Button(frame_tabs, text="자르기 (예정)", style="Tab.TButton",
                                                  command=lambda: self.switch_tab("feature2"))
        self.tab_buttons["feature2"].pack(side='left')

        self.tab_buttons["feature3"] = ttk.Button(frame_tabs, text="필터 (예정)", style="Tab.TButton",
                                                  command=lambda: self.switch_tab("feature3"))
        self.tab_buttons["feature3"].pack(side='left')

        self.tab_buttons["feature4"] = ttk.Button(frame_tabs, text="배경 제거 (예정)", style="Tab.TButton",
                                                  command=lambda: self.switch_tab("feature4"))
        self.tab_buttons["feature4"].pack(side='left')

        # 설정 버튼
        self.settings_btn = ttk.Button(self.frame_tab_bar, text="⚙️ 설정", style="Settings.TButton", command=self.open_settings)
        self.settings_btn.pack(side='right', padx=10, pady=5)

        # 메인 콘텐츠 프레임
        self.main_content_frame = ttk.Frame(self.root, style="Main.TFrame", takefocus=True)
        self.main_content_frame.pack(side='top', fill='both', expand=True)

        # 1) 워터마크 프레임 로드
        self.watermark_frame = ttk.Frame(self.main_content_frame)   # pack()은 switch_tab()에서 호출
        self.create_watermark_ui()

        # 2) "추후 예정" 프레임 로드
        self.coming_soon_frame = ttk.Frame(self.main_content_frame) # pack()은 switch_tab()에서 호출
        self.coming_soon_label = ttk.Label(self.coming_soon_frame,
                                           text=f"🚧 해당 기능은 추후 업데이트 예정입니다. 🚧\n\n최신 정보는 GitHub 페이지를 참고해 주세요.\n\n{GITHUB_URL}",
                                           font=font.Font(family=self.default_font_family, weight='bold'), anchor='center', justify='center')
        self.coming_soon_label.pack(fill='both', expand=True, padx=50, pady=50)

        # 모든 콘텐츠 프레임 목록
        all_content_frames = [self.watermark_frame, self.coming_soon_frame]

        self.root.update_idletasks()

        # 탭 바 높이 계산 (패딩 포함)
        pady_config = self.frame_tab_bar.pack_info().get('pady', 0)
        pady_top, pady_bottom = 0, 0
        if isinstance(pady_config, (tuple, list)) and len(pady_config) == 2:
            pady_top = int(pady_config[0])
            pady_bottom = int(pady_config[1])
        elif pady_config:
            pady_top = int(pady_config)
            pady_bottom = int(pady_config)
        tab_bar_height = self.frame_tab_bar.winfo_reqheight() + pady_top + pady_bottom

        # 모든 콘텐츠 프레임 중 최대 너비, 높이 계산
        max_w, max_h = 0, 0
        for frame in all_content_frames:
            max_w = max(max_w, frame.winfo_reqwidth())
            max_h = max(max_h, frame.winfo_reqheight())

        # 루트 창 최소 크기 설정
        self.root.minsize(max_w, max_h + tab_bar_height)


    def switch_tab(self, tab_name):
        if self.current_frame:
            self.current_frame.pack_forget()

        for name, btn in self.tab_buttons.items():
            btn.config(state='disabled' if name == tab_name else 'normal')

        if tab_name == "watermark":
            self.watermark_frame.pack(fill='both', expand=True)
            self.current_frame = self.watermark_frame
        else:   # "추후 예정" 탭 처리
            self.coming_soon_frame.pack(fill='both', expand=True)
            self.current_frame = self.coming_soon_frame


    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("환경 설정")
        settings_win.transient(self.root)
        settings_win.grab_set()
        settings_win.focus_set()

        # 창 크기 및 위치(중앙 배치) 설정
        win_w, win_h = 400, 300
        new_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win_w // 2)
        new_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win_h // 2)
        settings_win.geometry(f"{win_w}x{win_h}+{new_x}+{new_y}")

        ttk.Label(settings_win, text=f"환경 설정은 추후 업데이트 예정입니다.\n\n현재 앱 버전: {APP_VERSION}",
                  font=font.Font(family=self.default_font_family, weight='bold'), anchor='center', justify='center').pack(fill='both', expand=True, padx=20, pady=20)

        def on_settings_close():
            settings_win.grab_release()
            settings_win.destroy()

        settings_win.protocol("WM_DELETE_WINDOW", on_settings_close)


    def create_watermark_ui(self):
        # 좌측 프레임
        frame_left = ttk.Frame(self.watermark_frame)
        frame_left.pack(side='left', fill='y', padx=15, pady=15)

        frame_tree_btns = ttk.Frame(frame_left)
        frame_tree_btns.pack(pady=(5, 10))
        self.add_btn = ttk.Button(frame_tree_btns, text="➕ 사진 추가", command=self.add_files)
        self.add_btn.pack(side='left', ipadx=5, ipady=5, padx=5)
        self.remove_btn = ttk.Button(frame_tree_btns, text="➖ 선택 삭제", command=self.remove_file)
        self.remove_btn.pack(side='right', ipadx=5, ipady=5, padx=5)

        self.tree_scrollbar = ttk.Scrollbar(frame_left)
        self.tree_scrollbar.pack(side='right', fill='y')
        self.tree = ttk.Treeview(frame_left, columns=("filename", "date"), show='headings', height=25, yscrollcommand=self.tree_scrollbar.set)
        self.tree.heading("filename", text="파일명")
        self.tree.heading("date", text="촬영일")
        self.tree.column("filename", anchor='w')
        self.tree.column("date", anchor='center')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.tree_scrollbar.config(command=self.tree.yview)

        # 우측 프레임
        frame_right = ttk.Frame(self.watermark_frame)
        frame_right.pack(side='right', fill='both', expand=True, padx=(5, 15), pady=15)

        # 미리보기 프레임
        frame_preview = ttk.Frame(frame_right)
        frame_preview.pack(fill='both', expand=True)
        frame_preview.pack_propagate(False) # 레이아웃 전파 차단 -> 자식 위젯 크기와 무관하게 프레임 크기 유지
        frame_preview.bind("<Configure>", self.schedule_preview_update)
        self.preview_label = ttk.Label(frame_preview, text="선택한 파일 없음", font=font.Font(weight='bold'), anchor='center')
        self.preview_label.pack(fill='both', expand=True)

        # 미리보기 하단 프레임 (날짜 수정 및 사진 회전 기능)
        frame_preview_tools = ttk.Frame(frame_right)
        frame_preview_tools.pack(pady=(15, 0))
        ttk.Label(frame_preview_tools, text="촬영일 (YYYY-MM-DD): ").pack(side='left')
        self.date_entry = ttk.Entry(frame_preview_tools)
        self.date_entry.pack(side='left', fill='x', expand=True)
        self.date_entry.bind("<KeyRelease>", self.commit_date)
        Tooltip(self.date_entry, "파일에 기록된 날짜 데이터입니다. 직접 수정할 수 있습니다.\n날짜 수정 시 YYYY-MM-DD 형식으로 맞춰 주세요. (예: 2025-12-31)")
        self.rotate_btn = ttk.Button(frame_preview_tools, text="↺  사진 회전", command=self.rotate_image)
        self.rotate_btn.pack(side='right', ipadx=10, ipady=5, padx=(30, 0))

        # 워터마크 옵션 패널
        frame_options = ttk.LabelFrame(frame_right, text=" 워터마크 옵션 (일괄 적용) ", padding=5)
        frame_options.pack(fill='x', pady=(15, 0))
        for col in range(4):
            frame_options.columnconfigure(col, weight=1, minsize=120)

        # 1행: 글꼴, 크기, 글자 색, 배경 색
        ttk.Label(frame_options, text="글꼴").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        font_list = self.font_registry.get_available_font_names()
        self.font_name_combo = ttk.Combobox(frame_options, textvariable=self.font_name, values=font_list, state='readonly')
        self.font_name_combo.grid(row=1, column=0, sticky='we', padx=5)

        ttk.Label(frame_options, text="크기").grid(row=0, column=1, sticky='w', padx=5, pady=2)
        self.font_size_spin = ttk.Spinbox(frame_options, from_=1, to=999, increment=0.1, textvariable=self.font_size, width=7)
        self.font_size_spin.grid(row=1, column=1, sticky='we', padx=5)

        ttk.Label(frame_options, text="글자 색").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.font_color_btn = ttk.Button(frame_options, text="편집", command=self.choose_font_color)
        self.font_color_btn.grid(row=1, column=2, sticky='we', padx=5)
        
        ttk.Label(frame_options, text="배경 색").grid(row=0, column=3, sticky='w', padx=5, pady=2)
        self.bg_color_btn = ttk.Button(frame_options, text="편집", command=self.choose_bg_color)
        self.bg_color_btn.grid(row=1, column=3, sticky='we', padx=5)

        # 2행: 위치, 여백, _, 배경 불투명도
        ttk.Label(frame_options, text="위치").grid(row=2, column=0, sticky='w', padx=5, pady=(8, 2))
        self.position_combo = ttk.Combobox(frame_options, textvariable=self.position, values=["좌측 상단", "우측 상단", "좌측 하단", "우측 하단", "중앙"], state='readonly')
        self.position_combo.grid(row=3, column=0, sticky='we', padx=5)

        ttk.Label(frame_options, text="여백").grid(row=2, column=1, sticky='w', padx=5, pady=(8, 2))
        self.margin_spin = ttk.Spinbox(frame_options, from_=0, to=999, increment=0.1, textvariable=self.margin, width=7)
        self.margin_spin.grid(row=3, column=1, sticky='we', padx=5)

        ttk.Label(frame_options, text="배경 불투명도").grid(row=2, column=3, sticky='w', padx=5, pady=(8, 2))
        self.bg_opacity_scale = ttk.Scale(frame_options, from_=0, to=100, variable=self.bg_opacity, orient='horizontal', command=self.update_opacity_tooltip)
        self.bg_opacity_scale.grid(row=3, column=3, sticky='we', padx=5)
        self.bg_opacity_tooltip = Tooltip(self.bg_opacity_scale, f"{self.bg_opacity.get()}%", autohide=3000)

        # 3행: 날짜 형식, 단위, _, 배경 여백
        ttk.Label(frame_options, text="날짜 형식").grid(row=4, column=0, sticky='w', padx=5, pady=(8, 2))
        self.date_format_combo = ttk.Combobox(frame_options, textvariable=self.date_format,
                                 values=["YYYY년 MM월 DD일", "YYYY년 M월 D일", "YYYY-MM-DD", "YYYY. MM. DD.", "YYYY. M. D.", "'YY. MM. DD.", "'YY. M. D.", "M/D/YYYY"])
        self.date_format_combo.grid(row=5, column=0, sticky='we', padx=5, pady=(0, 10))

        ttk.Label(frame_options, text="단위").grid(row=4, column=1, sticky='w', padx=5, pady=(8, 2))
        self.size_mode_combo = ttk.Combobox(frame_options, textvariable=self.size_mode, values=["픽셀(px)", "백분율(%)"], state='readonly', width=10)
        self.size_mode_combo.grid(row=5, column=1, sticky='we', padx=5, pady=(0, 10))

        ttk.Label(frame_options, text="배경 여백").grid(row=4, column=3, sticky='w', padx=5, pady=(8, 2))
        self.bg_padding_spin = ttk.Spinbox(frame_options, from_=0, to=999, increment=0.1, textvariable=self.bg_padding, width=7)
        self.bg_padding_spin.grid(row=5, column=3, sticky='we', padx=5, pady=(0, 10))

        # 워터마크 옵션 변경 시 미리보기 갱신
        vars_to_trace = (
            self.font_name,
            self.font_size,
            self.font_color,
            self.bg_color,
            self.bg_opacity,
            self.bg_padding,
            self.position,
            self.margin,
            self.size_mode,
            self.date_format,
        )
        for v in vars_to_trace:
            v.trace_add("write", lambda *args: self.schedule_preview_update())

        # 결과 저장 옵션 및 작업 진행률 표시
        frame_save = ttk.Frame(frame_right)
        frame_save.pack(side='bottom', fill='x', pady=(15, 0))
        for col in range(3):
            frame_save.columnconfigure(col, weight=1)

        frame_save_radios = ttk.Frame(frame_save)
        frame_save_radios.grid(row=0, column=0, columnspan=2, sticky='w')
        ttk.Label(frame_save_radios, text="파일 저장 방식: ").pack(side='left')
        self.save_mode_radio_ow = ttk.Radiobutton(frame_save_radios, text="덮어쓰기", variable=self.save_mode, value="overwrite")
        self.save_mode_radio_ow.pack(side='left', padx=5)
        self.save_mode_radio_sep = ttk.Radiobutton(frame_save_radios, text="별도 폴더", variable=self.save_mode, value="separate")
        self.save_mode_radio_sep.pack(side='left', padx=5)

        self.progress_bar = ttk.Progressbar(frame_save, mode='determinate', orient='horizontal')
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(5, 0))

        self.apply_button = ttk.Button(frame_save, text="✨ 워터마크 적용", command=self.start_stop_processing)
        self.apply_button.grid(row=0, column=2, rowspan=2, sticky='nsew', padx=(10, 0))


    def add_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("이미지 파일", "*.jpg;*.jpeg;*.png")])
        for path in file_paths:
            date_str = get_exif_date(path)
            item = self.list_manager.add_image(path, date_str if date_str else "")
            if not self.tree.exists(item.id):
                self.tree.insert('', 'end', iid=item.id, values=(os.path.basename(path), date_str if date_str else "❌"))

    def remove_file(self):
        selected_iids = self.tree.selection()
        for iid in selected_iids:
            self.tree.delete(iid)
            self.list_manager.remove_image(iid)
            if self.selected_iid == iid:
                self.selected_iid = None
                self.preview_label.config(image="", foreground="", text="선택한 파일 없음")
                self.date_entry.delete(0, 'end')

    def on_file_select(self, event):
        selected_iids = self.tree.selection()
        if not selected_iids: return
        self.selected_iid = selected_iids[-1] # Treeview 중복 선택 시 마지막 선택 항목만 처리
        
        item = self.list_manager.get_item(self.selected_iid)
        if item:
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, item.date_str)
            self.render_preview()

    def commit_date(self, *args):
        if self.selected_iid is not None:
            new_date = self.date_entry.get().strip()
            if self.list_manager.update_date(self.selected_iid, new_date):
                self.tree.set(self.selected_iid, "date", new_date if new_date else "❌")
                self.render_preview()

    def rotate_image(self):
        if self.selected_iid is not None:
            if self.list_manager.update_rotation(self.selected_iid, 90):
                self.render_preview()

    def choose_font_color(self):
        color = colorchooser.askcolor(title="글자 색 선택")  # color[0]: RGB 값 / color[1]: 16진수 str
        if color[1]: self.font_color.set(color[1])

    def choose_bg_color(self):
        color = colorchooser.askcolor(title="배경 색 선택")
        if color[1]: self.bg_color.set(color[1])

    def update_opacity_tooltip(self, value):
        if hasattr(self, 'bg_opacity_tooltip') and self.bg_opacity_tooltip:
            # value는 콜백에서 자동으로 전달되는 float 값이므로 int로 변환
            self.bg_opacity_tooltip.update_text(f"{int(float(value))}%")


    def render_preview(self):
        if self.selected_iid is None: return
        item = self.list_manager.get_item(self.selected_iid)
        if not item: return
        config = self.get_current_config()
        font_path = self.font_registry.get_font_path(config.font_name)
        try:
            with Image.open(item.path) as img:
                img = ImageOps.exif_transpose(img)
                if item.rotation != 0:
                    img = img.rotate(item.rotation, expand=True)

                watermarked_img = draw_watermark(img, item.date_str, font_path, config)
                preview_img = watermarked_img.convert("RGB")
                width, height = self.preview_label.winfo_width(), self.preview_label.winfo_height()
                preview_img.thumbnail((width, height))

                self.preview_img = ImageTk.PhotoImage(preview_img)
                self.preview_label.config(image=self.preview_img, text="")
        except Exception as e:
            print(f"Preview Error Occured: {e}")
            self.preview_label.config(image="", foreground="#FF6600", text="⚠️ 미리보기 오류:\n\n설정한 값들이 유효하지 않을 수 있습니다.")

    def schedule_preview_update(self, *args, delay=100):
        if self.preview_update_job_id:
            self.root.after_cancel(self.preview_update_job_id)
        self.preview_update_job_id = self.root.after(delay, self._run_scheduled_preview)

    def _run_scheduled_preview(self):
        self.preview_update_job_id = None
        self.render_preview()

    def toggle_ui_state(self, is_disabled):
        state = 'disabled' if is_disabled else 'normal'
        readonly_state = 'disabled' if is_disabled else 'readonly'
        widgets_to_control = [
            self.add_btn, self.remove_btn, self.tree, self.date_entry, self.rotate_btn,
            self.font_name_combo, self.font_size_spin, self.font_color_btn, self.bg_color_btn,
            self.position_combo, self.margin_spin, self.bg_opacity_scale,
            self.date_format_combo, self.size_mode_combo, self.bg_padding_spin,
            self.save_mode_radio_ow, self.save_mode_radio_sep
        ]
        for widget in widgets_to_control:
            try:
                if isinstance(widget, (ttk.Combobox)) and (widget != self.date_format_combo):
                    widget.config(state=readonly_state)
                else:
                    widget.config(state=state)
            except tk.TclError:
                pass    # state 속성이 없는 위젯은 통과

    def start_stop_processing(self):
        if self.is_processing:
            self.is_processing = False
            self.apply_button.config(text="중단 중...", state='disabled')
        else:
            if len(self.list_manager) == 0:
                messagebox.showwarning("경고", "처리할 파일이 없습니다.")
                return

            if self.save_mode.get() == "overwrite":
                output_dir = ""
                if not messagebox.askyesno("확인", "원본 파일을 덮어쓰면 복구할 수 없습니다.\n정말 이대로 진행할까요?"):
                    return
            else:
                output_dir = filedialog.askdirectory(title="저장할 폴더 선택")
                if not output_dir:
                    messagebox.showinfo("알림", "저장할 경로를 지정하지 않아 작업을 취소했습니다.")
                    return

            self.is_processing = True
            self.toggle_ui_state(is_disabled=True)
            self.apply_button.config(text="⏹️ 작업 중단")

            # 스레드로 넘길 데이터(스냅샷) 캡처
            items_snapshot = self.list_manager.get_all_items()
            config_snapshot = self.get_current_config()
            font_path_snapshot = self.font_registry.get_font_path(config_snapshot.font_name)
            save_mode_snapshot = self.save_mode.get()

            self.progress_bar['maximum'] = len(items_snapshot)
            self.progress_bar['value'] = 0

            self.processing_thread = threading.Thread(target=self._apply_watermarks_thread, args=(output_dir, items_snapshot, config_snapshot, font_path_snapshot, save_mode_snapshot), daemon=True)
            self.processing_thread.start()

    def _apply_watermarks_thread(self, output_dir, items, config, font_path, save_mode):
        success, skipped, failed = 0, 0, 0

        for i, item in enumerate(items):
            if not self.is_processing: break
            try:
                if not item.date_str:
                    skipped += 1
                    continue
                with Image.open(item.path) as img:
                    img = ImageOps.exif_transpose(img)
                    exif_bytes = img.info.get("exif")   # Orientation 값을 제외한 EXIF 데이터 보존

                    if item.rotation != 0:
                        img = img.rotate(item.rotation, expand=True)

                    watermarked_img = draw_watermark(img, item.date_str, font_path, config)
                    out_img = watermarked_img.convert("RGB")

                    if save_mode == "overwrite":
                        out_img.save(item.path, **({"exif": exif_bytes} if exif_bytes else {}))
                    else:
                        base = os.path.basename(item.path)
                        out_img.save(os.path.join(output_dir, base), **({"exif": exif_bytes} if exif_bytes else {}))
                success += 1
            except Exception as e:
                failed += 1
                self.root.after(0, lambda path=item.path, err=e:
                    messagebox.showerror("오류 발생", f"{path}\n\n{err}")
                )
            self.root.after(0, self.progress_bar.config, {'value': i + 1})
        self.root.after(0, self.on_process_finished, success, skipped, failed)

    def on_process_finished(self, success, skipped, failed):
        self.is_processing = False
        self.toggle_ui_state(is_disabled=False)
        self.apply_button.config(text="✨ 워터마크 적용", state='normal')
        self.progress_bar['value'] = 0
        messagebox.showinfo("작업 결과", f"요청하신 작업을 다음과 같이 처리했습니다.\n\n완료한 파일: {success}개\n건너뛴 파일: {skipped}개\n실패한 파일: {failed}개")


    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = WatermarkConfig.from_dict(data)
                available_fonts = self.font_registry.get_available_font_names()
                valid_font = config.font_name if config.font_name in available_fonts else (available_fonts[0] if available_fonts else "")
                self.font_name.set(valid_font)
                self.font_size.set(config.font_size)
                self.font_color.set(config.font_color)
                self.bg_color.set(config.bg_color)
                self.bg_opacity.set(config.bg_opacity)
                self.bg_padding.set(config.bg_padding)
                self.position.set(config.position)
                self.margin.set(config.margin)
                self.size_mode.set(config.size_mode)
                self.date_format.set(config.date_format)
                self.save_mode.set(config.save_mode)
            except Exception:
                pass

    def save_settings(self):
        config = self.get_current_config()
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)

    def on_close(self):
        if self.is_processing:
            if messagebox.askyesno("확인", "작업이 진행 중입니다. 정말로 종료할까요?"):
                if self.is_processing:
                    self.is_processing = False
                    self.processing_thread.join(timeout=2)
                self.save_settings()
                self.root.destroy()
        else:
            self.save_settings()
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
