from matplotlib import font_manager
from PIL import ImageFont
from typing import List, Optional


class FontRegistry:
    """시스템에 설치된 글꼴을 탐색하고 이름과 파일 경로 매핑을 관리하는 레지스트리입니다."""
    def __init__(self):
        self._font_map = {}
        self._load_system_fonts()

    def _load_system_fonts(self) -> None:
        """[내부 함수] 시스템 내부의 .ttf 글꼴을 탐색하여 딕셔너리에 저장합니다.  
        글꼴 이름을 Key로, 파일 절대 경로를 Value로 저장한 후, 이름을 기준으로 오름차순 정렬을 수행합니다."""
        fonts = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
        for font_path in fonts:
            try:
                name, style = ImageFont.truetype(font_path).getname()
                font_display_name = name if style.lower() in ["regular", "normal"] or name.endswith(style) else f"{name} {style}"
                if font_display_name not in self._font_map:
                    self._font_map[font_display_name] = font_path
            except Exception:
                continue
        self._font_map = dict(sorted(self._font_map.items()))

    def reload_fonts(self) -> None:
        """시스템 내부의 .ttf 폰트를 다시 탐색하여 딕셔너리를 갱신합니다.  
        런타임 중 새로운 폰트가 설치되었거나 캐시를 초기화해야 할 때 사용합니다."""
        self._font_map.clear()
        self._load_system_fonts()

    def get_available_font_names(self) -> List[str]:
        """사용 가능한 모든 글꼴의 이름 목록을 반환합니다.  
        Returns:
            List[str]: 정렬된 글꼴 이름 문자열의 리스트.
        """
        return list(self._font_map.keys())

    def get_font_path(self, font_name: Optional[str]) -> Optional[str]:
        """글꼴 이름을 기반으로 해당 글꼴 파일의 절대 경로를 반환합니다.  
        Args:
            font_name (Optional[str]): 경로를 조회할 글꼴 이름.
        Returns:
            Optional[str]: 글꼴 파일의 절대 경로. 찾을 수 없거나 입력이 None이면 None.
        """
        return self._font_map.get(font_name) if font_name else None
