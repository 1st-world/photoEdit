# pip install Pillow
# pip install matplotlib
import os, json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, font
from PIL import Image, ImageOps, ImageTk, ImageDraw, ImageFont, ExifTags
from matplotlib import font_manager
from datetime import datetime

APP_VERSION = "v0.25.9.21.1"
CONFIG_FILE = "settings.json"
GITHUB_URL = "https://github.com/1st-world/photoEdit"

def get_exif_date(path: str) -> str:
    '''
    사진 파일의 EXIF 데이터를 통해 촬영일(DateTime) 값을 추출합니다.\n
    "YYYY-MM-DD" 형식으로 반환하며, 해당 데이터가 없거나 예외가 발생하면 빈 문자열을 반환합니다.\n
    가장 일반적인 "YYYY:MM:DD HH:MM:SS" 형식 외에는 현재 지원하지 않습니다.
    '''
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if exif:
                # `ExifTags.TAGS` dict 형태{ID: 이름}를 뒤집은 {이름: ID} 생성해 이름으로 ID 찾기
                exif_tags_reversed = {v: k for k, v in ExifTags.TAGS.items()}
                date_tag_id = exif_tags_reversed.get("DateTime")

                if date_tag_id is not None and date_tag_id in exif:
                    date_time = exif.get(date_tag_id)
                    # "YYYY:MM:DD HH:MM:SS" 형식에서 날짜만 추출
                    date_part = date_time.split(" ")[0]
                    return date_part.replace(":", "-")
    except Exception:
        pass
    return ""

def format_date(date_str: str, fmt: str) -> str:
    """
    날짜 문자열의 형식을 변환합니다.
    Args:
        `date_str` (str): 변환할 날짜 문자열 (예: "1999-01-31").
        `fmt` (str): 목표 형식 문자열 (예: "YYYY년 MM월 DD일").
    Returns:
        str: 변환된 날짜 문자열.
    Raises:
        ValueError: 인자의 날짜 형식이 올바르지 않거나 존재하지 않는 경우.
        TypeError: `date_str` 인자가 문자열 타입이 아닌 경우 등.
        AttributeError: `fmt` 인자가 문자열 타입이 아닌 경우 등.
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # 사용자 지정 입력 코드를 표준 형식 코드로 매핑
    fmt_map = {
        "YYYY": "%Y", "YY": "%y",   # 연도 (예: 1999 또는 99)
        "MM": "%m", "M": "%#m" if os.name == 'nt' else "%-m",   # 월 (예: 01 또는 1)
        "DD": "%d", "D": "%#d" if os.name == 'nt' else "%-d",   # 일 (예: 01 또는 1)
        "AA": "%A", "A": "%a",      # 요일 (예: Thursday 또는 Thu)
    }
    output_fmt = fmt.upper()
    # 매핑 테이블을 사용하여 형식 코드 치환, 더 긴 형식 코드부터 (예: YYYY가 YY보다 먼저)
    for key in sorted(fmt_map.keys(), key=len, reverse=True):
        output_fmt = output_fmt.replace(key, fmt_map[key])

    return date_obj.strftime(output_fmt)


class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"사진 워터마크 삽입기 ({APP_VERSION})")
        self.settings_file = CONFIG_FILE

        # 변수 초기화
        self.files = []
        self.selected_index = None
        self.font_map = self._get_font_map()
        self.font_name = tk.StringVar(value=list(self.font_map.keys())[0])
        self.font_size = tk.DoubleVar(value=48)
        self.font_color = tk.StringVar(value="#000000")
        self.bg_color = tk.StringVar(value="")
        self.position = tk.StringVar(value="우측 하단")
        self.margin = tk.DoubleVar(value=20)
        self.size_mode = tk.StringVar(value="픽셀(px)")
        self.date_format = tk.StringVar(value="YYYY-MM-DD")
        self.save_mode = tk.StringVar(value="separate")

        # 설정 불러오기
        self.load_settings()

        # 좌측 프레임
        frame_left = ttk.Frame(self.root, padding=5)
        frame_left.pack(side='left', fill='y', padx=5, pady=5)

        # 파일 추가/삭제 버튼
        frame_left_btns = ttk.Frame(frame_left)
        frame_left_btns.pack(pady=5)
        ttk.Button(frame_left_btns, text="➕ 사진 추가", command=self.add_files).pack(side='left', ipadx=5, ipady=5, padx=5, pady=5)
        ttk.Button(frame_left_btns, text="➖ 선택 삭제", command=self.remove_file).pack(side='right', ipadx=5, ipady=5, padx=5, pady=5)

        # 파일 목록 (Treeview)
        scrollbar = ttk.Scrollbar(frame_left)
        scrollbar.pack(side='right', fill='y')
        self.tree = ttk.Treeview(frame_left, columns=("filename", "date"), show='headings', height=25, yscrollcommand=scrollbar.set)
        self.tree.heading("filename", text="파일명")
        self.tree.heading("date", text="촬영일")
        self.tree.column("filename", anchor='w')
        self.tree.column("date", anchor='center')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_file_select)
        scrollbar.config(command=self.tree.yview)

        # 우측 프레임
        frame_right = ttk.Frame(self.root, padding=5)
        frame_right.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # 사진 미리보기
        self.preview_label = ttk.Label(frame_right, text="선택한 파일 없음", anchor='center')
        self.preview_label.pack(fill='both', expand=True)

        # 촬영일 (수정 가능)
        ttk.Label(frame_right, text="날짜 (YYYY-MM-DD)").pack()
        self.date_entry = ttk.Entry(frame_right)
        self.date_entry.pack()
        self.date_entry.bind("<KeyRelease>", self.commit_date)

        # 사진 회전
        ttk.Button(frame_right, text="↺ 사진 회전", command=self.rotate_image).pack()

        # 워터마크 옵션 패널
        frame_options = ttk.LabelFrame(frame_right, text="워터마크 옵션 (일괄 적용)")
        frame_options.pack(fill='x', padx=5, pady=5)
        for col in range(6):
            frame_options.columnconfigure(col, weight=1)

        ttk.Label(frame_options, text="글꼴").grid(row=0, column=0)
        self.font_combo = ttk.Combobox(frame_options, textvariable=self.font_name, values=list(self.font_map.keys()), state='readonly')
        self.font_combo.grid(row=0, column=1)

        ttk.Label(frame_options, text="크기").grid(row=0, column=2)
        ttk.Spinbox(frame_options, from_=1, to=999, textvariable=self.font_size).grid(row=0, column=3)

        ttk.Label(frame_options, text="단위").grid(row=0, column=4)
        ttk.Combobox(frame_options, textvariable=self.size_mode, values=["픽셀(px)", "백분율(%)"], state='readonly').grid(row=0, column=5)

        frame_color_btns = ttk.Frame(frame_options)
        frame_color_btns.grid(row=0, column=6, columnspan=2)
        ttk.Button(frame_color_btns, text="글자색 편집", command=self.choose_font_color).pack(side='left')
        ttk.Button(frame_color_btns, text="배경색 편집", command=self.choose_bg_color).pack(side='right')

        ttk.Label(frame_options, text="위치").grid(row=1, column=0)
        ttk.Combobox(frame_options, textvariable=self.position, values=["좌측 상단", "우측 상단", "좌측 하단", "우측 하단", "중앙"], state='readonly').grid(row=1, column=1)

        ttk.Label(frame_options, text="여백").grid(row=1, column=2)
        ttk.Spinbox(frame_options, from_=1, to=999, textvariable=self.margin).grid(row=1, column=3)

        ttk.Label(frame_options, text="단위").grid(row=1, column=4)
        ttk.Combobox(frame_options, textvariable=self.size_mode, values=["픽셀(px)", "백분율(%)"], state='readonly').grid(row=1, column=5)

        ttk.Label(frame_options, text="날짜 형식").grid(row=1, column=6)
        ttk.Combobox(frame_options, textvariable=self.date_format,
                     values=["YYYY년 MM월 DD일", "YYYY년 M월 D일", "YYYY-MM-DD", "YYYY. MM. DD.", "YYYY. M. D.", "'YY. M. D.", "M/D/YYYY"]).grid(row=1, column=7)

        # 워터마크 옵션 변경 시 미리보기 갱신
        vars_to_trace = (
            self.font_name,
            self.font_size,
            self.font_color,
            self.bg_color,
            self.position,
            self.margin,
            self.size_mode,
            self.date_format,
        )
        for v in vars_to_trace:
            v.trace_add("write", lambda *args: self.render_preview())

        # 결과 저장 옵션
        frame_save = ttk.Frame(frame_right)
        frame_save.pack(side='bottom', fill='x', anchor='center')
        frame_save.columnconfigure(1, weight=1)
        ttk.Label(frame_save, text="저장 방식").grid(row=0, column=0, rowspan=2)
        ttk.Radiobutton(frame_save, text="덮어쓰기", variable=self.save_mode, value="overwrite").grid(row=0, column=1)
        ttk.Radiobutton(frame_save, text="별도 폴더", variable=self.save_mode, value="separate").grid(row=1, column=1)
        ttk.Button(frame_save, text="✨ 워터마크 적용", command=self.apply_watermarks).grid(row=0, column=2, rowspan=2, sticky='nsew')



    def add_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("이미지 파일", "*.jpg;*.jpeg;*.png")])
        for path in file_paths:
            date_str = get_exif_date(path)
            self.files.append({"path": path, "date_str": date_str, "rotation": 0})
            self.tree.insert('', 'end', values=(os.path.basename(path), date_str if date_str else "❌"))

    def remove_file(self):
        selected = self.tree.selection()
        for item in selected:
            idx = self.tree.index(item)
            self.tree.delete(item)
            self.files.pop(idx)
            self.selected_index = None
            self.preview_label.config(image="", text="선택한 파일 없음")
            self.date_entry.delete(0, 'end')

    def on_file_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_index = self.tree.index(selected[-1]) # Treeview 중복 선택 시 마지막 선택 항목만 처리
        file_info = self.files[self.selected_index]
        try:
            img = Image.open(file_info["path"])
            img = ImageOps.exif_transpose(img)
            img.thumbnail((500, 500))
            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.preview_img, text="")
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, file_info["date_str"])
            self.render_preview()
        except Exception:
            self.preview_label.config(text="⚠️ 미리보기 불가")
            self.date_entry.delete(0, 'end')

    def commit_date(self, *args):
        if self.selected_index is not None:
            self.files[self.selected_index]["date_str"] = self.date_entry.get().strip()
            self.render_preview()

    def rotate_image(self):
        if self.selected_index is not None:
            self.files[self.selected_index]["rotation"] = (self.files[self.selected_index]["rotation"] + 90) % 360
            self.render_preview()

    def choose_font_color(self):
        color = colorchooser.askcolor(title="글자색 선택")  # color[0]: RGB 색상 값 / color[1]: 16진수 str
        if color[1]:
            self.font_color.set(color[1])

    def choose_bg_color(self):
        color = colorchooser.askcolor(title="배경색 선택")
        if color[1]:
            self.bg_color.set(color[1])
        else:
            self.bg_color.set("none")

    def get_position(self, size, text_w, text_h, margin):
        W, H = size
        pos_map = {
            "좌측 상단": (margin, margin),
            "우측 상단": (W - text_w - margin, margin),
            "좌측 하단": (margin, H - text_h - margin),
            "우측 하단": (W - text_w - margin, H - text_h - margin),
            "중앙": ((W - text_w) // 2, (H - text_h) // 2),
        }
        return pos_map.get(self.position.get(), (margin, margin))


    def _get_font_map(self):
        fonts = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
        font_map = {}
        for font_path in fonts:
            try:
                name, style = ImageFont.truetype(font_path).getname()
                if style.lower() in ["regular", "normal"]:
                    font_display_name = name
                else:
                    # 이름이 스타일로 끝나지 않을 때만 스타일 추가
                    if not name.endswith(style):
                         font_display_name = f"{name} {style}"
                    else:
                         font_display_name = name

                if font_display_name not in font_map:   # 이름 중복 시 첫 번째만 사용
                    font_map[font_display_name] = font_path
            except Exception:
                continue
        return dict(sorted(font_map.items()))

    def _draw_watermark(self, img, date_str):
        # 날짜 포맷 적용
        date_text = format_date(date_str, self.date_format.get())
        if not date_text:
            return img.convert("RGBA") # 날짜 없으면 원본 이미지 반환

        # 텍스트 레이어 생성
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # 텍스트 및 여백 크기 로드
        if self.size_mode.get() == "픽셀(px)":
            font_px = float(self.font_size.get())
            margin_px = float(self.margin.get())
        elif self.size_mode.get() == "백분율(%)":
            font_px = float(max(img.width, img.height) * (self.font_size.get() / 100.0))
            margin_px = float(max(img.width, img.height) * (self.margin.get() / 100.0))

        # 텍스트 스타일 로드
        try:
            font_path = self.font_map.get(self.font_name.get())
            if not font_path: raise Exception
            font = ImageFont.truetype(font_path, font_px)
        except Exception as e:
            print(f"Font loading failed: {e}. Falling back to default font.")
            font = ImageFont.load_default(font_px)

        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), date_text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # 위치 계산
        pos = self.get_position(img.size, text_w, text_h, margin_px)
        
        # 배경 적용
        bg_color = self.bg_color.get()
        if bg_color and bg_color.lower() != "none":
            draw.rectangle([pos, (pos[0] + text_w, pos[1] + text_h)], fill=bg_color)
        
        # 텍스트 적용
        draw.text(pos, date_text, font=font, fill=self.font_color.get())

        # 원본 이미지, 텍스트 레이어 합성
        return Image.alpha_composite(img.convert("RGBA"), txt_layer)

    def render_preview(self):
        if self.selected_index is None:
            return
        file_info = self.files[self.selected_index]
        try:
            img = Image.open(file_info["path"])
            img = ImageOps.exif_transpose(img)

            if file_info.get("rotation", 0) != 0:
                img = img.rotate(file_info["rotation"], expand=True)

            watermarked_img = self._draw_watermark(img, file_info["date_str"])
            preview_img = watermarked_img.convert("RGB")
            preview_img.thumbnail((500, 500))

            self.preview_img = ImageTk.PhotoImage(preview_img)
            self.preview_label.config(image=self.preview_img, text="")
        except Exception as e:
            print(f"Preview Error Occured: {e}")
            self.preview_label.config(text="⚠️ 미리보기 불가")
    
    def apply_watermarks(self):
        save_mode = self.save_mode.get()
        output_dir = "watermarked"
        if save_mode == "separate":
            os.makedirs(output_dir, exist_ok=True)
        
        success, skipped, failed = 0, 0, 0

        for i, file_info in enumerate(self.files):
            try:
                date_str = file_info["date_str"]
                if not date_str:
                    skipped += 1
                    continue

                img = Image.open(file_info["path"])
                img = ImageOps.exif_transpose(img)
                exif_bytes = img.info.get("exif")   # Orientation 값을 제외한 EXIF 데이터 보존

                if file_info.get("rotation", 0) != 0:
                    img = img.rotate(file_info["rotation"], expand=True)

                watermarked_img = self._draw_watermark(img, date_str)
                out_img = watermarked_img.convert("RGB")

                if save_mode == "overwrite":
                    out_img.save(file_info["path"], **({"exif": exif_bytes} if exif_bytes else {}))
                elif save_mode == "separate":
                    base = os.path.basename(file_info["path"])
                    out_img.save(os.path.join(output_dir, base), **({"exif": exif_bytes} if exif_bytes else {}))
                
                success += 1
            except Exception as e:
                failed += 1
                print(f"Apply Error Occured: {e}")
                messagebox.showerror("오류 발생", f"{file_info['path']}\n\n{e}")

        message = f"요청하신 작업을 다음과 같이 처리했습니다.\n\n완료한 파일: {success}개\n건너뛴 파일: {skipped}개\n실패한 파일: {failed}개"
        messagebox.showinfo("작업 결과", message)


    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.font_name.set(data.get("font_name", list(self.font_map.keys())[0]))
                self.font_size.set(data.get("font_size", 48))
                self.font_color.set(data.get("font_color", "#000000"))
                self.bg_color.set(data.get("bg_color", ""))
                self.position.set(data.get("position", "우측 하단"))
                self.margin.set(data.get("margin", 20))
                self.size_mode.set(data.get("size_mode", "픽셀(px)"))
                self.date_format.set(data.get("date_format", "YYYY-MM-DD"))
                self.save_mode.set(data.get("save_mode", "separate"))
            except Exception:
                pass

    def save_settings(self):
        data = {
            "font_name": self.font_name.get(),
            "font_size": self.font_size.get(),
            "font_color": self.font_color.get(),
            "bg_color": self.bg_color.get(),
            "position": self.position.get(),
            "margin": self.margin.get(),
            "size_mode": self.size_mode.get(),
            "date_format": self.date_format.get(),
            "save_mode": self.save_mode.get(),
        }
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def on_close(self):
        self.save_settings()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
