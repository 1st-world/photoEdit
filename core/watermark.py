from typing import Tuple
from PIL import Image, ImageDraw, ImageFont
from .models import WatermarkConfig
from .metadata import format_date


def _hex_to_rgba(hex_color: str, alpha_percent: float) -> Tuple[int, int, int, int]:
    """[내부 함수] Hex 색상 코드와 투명도 값을 RGBA 튜플로 변환합니다.  
    Args:
        hex_color (str): 변환할 색상의 Hex 문자열 (예: "#FFFFFF").
        alpha_percent (float): 불투명도 백분율 (0~100).
    Returns:
        Tuple[int, int, int, int]: (R, G, B, A) 형태의 튜플.
    """
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    alpha = int(255 * (alpha_percent / 100.0))
    return (r, g, b, alpha)


def _get_position(size: Tuple[int, int], margin: float, position: str) -> Tuple[Tuple[float, float], str]:
    """[내부 함수] 이미지 크기와 여백을 기반으로 텍스트를 그릴 위치 좌표와 앵커를 계산합니다.  
    Args:
        size (Tuple[int, int]): 대상 이미지의 너비와 높이 (width, height).
        margin (float): 이미지 테두리로부터의 여백 픽셀 값.
        position (str): 텍스트의 배치 위치 ("좌측 상단", "우측 상단", "좌측 하단", "우측 하단", "중앙").
    Returns:
        Tuple[Tuple[float, float], str]: 텍스트의 (x, y) 좌표와 Pillow 앵커 문자열("lt", "rt", "lb", "rb", "mm").
    """
    W, H = size
    pos_map = {
        "좌측 상단": ((margin, margin), "lt"),
        "우측 상단": ((W - margin, margin), "rt"),
        "좌측 하단": ((margin, H - margin), "lb"),
        "우측 하단": ((W - margin, H - margin), "rb"),
        "중앙": ((W // 2, H // 2), "mm"),
    }
    return pos_map.get(position, ((W - margin, H - margin), "rb"))


def draw_watermark(img: Image.Image, date_str: str, font_path: str, config: WatermarkConfig) -> Image.Image:
    """이미지 객체에 주어진 설정(WatermarkConfig)에 따라 날짜 워터마크를 합성합니다.  
    원본 이미지를 훼손하지 않고 투명한 텍스트 레이어를 생성한 뒤 원본과 Alpha Composite을 수행합니다.  
    Args:
        img (Image.Image): 워터마크를 적용할 원본 Pillow 이미지 객체.
        date_str (str): 워터마크로 출력할 기준 날짜 문자열 ("YYYY-MM-DD").
        font_path (str): 적용할 텍스트 폰트(.ttf) 파일의 시스템 또는 로컬 절대 경로.
        config (WatermarkConfig): 워터마크의 위치, 색상, 크기 등을 담은 데이터 모델 객체.
    Returns:
        Image.Image: 워터마크를 합성한 새로운 RGBA 형식의 Pillow 이미지 객체.  
                    날짜 형식이 잘못되었거나 오류 발생 시 원본 이미지를 RGBA로 변환한 객체.
    """
    try:
        date_text = format_date(date_str, config.date_format)
    except Exception:
        return img.convert("RGBA")

    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    base_size = max(img.width, img.height)

    if config.size_mode == "픽셀(px)":
        font_px = config.font_size
        margin_px = config.margin
        padding_px = config.bg_padding
    else:
        font_px = base_size * (config.font_size / 100.0)
        margin_px = base_size * (config.margin / 100.0)
        padding_px = base_size * (config.bg_padding / 100.0)

    try:
        font = ImageFont.truetype(font_path, int(font_px))
    except Exception:
        try:
            font = ImageFont.load_default(int(font_px))
        except TypeError:
            font = ImageFont.load_default()

    pos, anchor = _get_position(img.size, margin_px, config.position)
    bbox = draw.textbbox(pos, date_text, font=font, anchor=anchor)

    if config.bg_color:
        bg_box = (bbox[0] - padding_px, bbox[1] - padding_px, bbox[2] + padding_px, bbox[3] + padding_px)
        rgba_fill = _hex_to_rgba(config.bg_color, config.bg_opacity)
        draw.rectangle(bg_box, fill=rgba_fill)

    draw.text(pos, date_text, font=font, fill=config.font_color, anchor=anchor)

    return Image.alpha_composite(img.convert("RGBA"), txt_layer)
