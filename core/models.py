import uuid
from dataclasses import dataclass, asdict, fields
from typing import Dict, List, Optional


@dataclass
class WatermarkConfig:
    """워터마크의 스타일 및 설정 값을 담는 데이터 모델입니다.  
    Attributes:
        font_name (Optional[str]): 적용할 글꼴의 이름. None일 경우 시스템 기본 글꼴을 의미합니다.
        font_size (float): 글자 크기. 계산 단위(`size_mode`)에 따라 백분율 또는 픽셀로 처리됩니다.
        font_color (str): 텍스트 색상을 나타내는 Hex 코드.
        bg_color (str): 텍스트 배경 색상을 나타내는 Hex 코드.
        bg_opacity (int): 배경의 불투명도 비율 (0~100).
        bg_padding (float): 텍스트 경계선부터 배경 테두리까지의 여백.
        position (str): 워터마크가 배치될 위치 설정.
        margin (float): 이미지 가장자리부터 워터마크까지의 거리.
        size_mode (str): 크기 및 여백의 계산 단위 ("백분율(%)" 또는 "픽셀(px)").
        date_format (str): 화면 및 이미지에 출력될 날짜 형식.
        save_mode (str): 결과물 저장 방식 ("separate" 또는 "overwrite").
    """
    font_name: Optional[str] = None
    font_size: float = 3.0
    font_color: str = "#000000"
    bg_color: str = "#FFFFFF"
    bg_opacity: int = 50
    bg_padding: float = 1.0
    position: str = "우측 하단"
    margin: float = 3.0
    size_mode: str = "백분율(%)"
    date_format: str = "YYYY-MM-DD"
    save_mode: str = "separate"

    def to_dict(self) -> dict:
        """현재 설정 객체를 딕셔너리 형태로 변환합니다.  
        설정 파일(JSON 등)에 값을 저장하거나 직렬화할 때 사용합니다.  
        Returns:
            dict: 데이터 모델의 속성과 값을 담은 딕셔너리.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'WatermarkConfig':
        """딕셔너리 데이터를 기반으로 설정 객체를 생성합니다.  
        입력 데이터에 없는 필드는 기본값을 유지하고, 클래스에 정의되지 않은 키는 무시합니다.  
        Args:
            data (dict): 설정 파일 등에서 읽어들인 딕셔너리 데이터.
        Returns:
            WatermarkConfig: 파싱이 완료된 데이터 모델 인스턴스.
        """
        valid_keys = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class ImageItem:
    """단일 이미지 파일의 상태와 정보를 관리하는 데이터 모델입니다.  
    Attributes:
        id (str): 애플리케이션 내부에서 이미지를 식별하기 위한 고유 ID.
        path (str): 이미지 파일의 절대 경로.
        date_str (str): 이미지에서 추출되었거나 사용자가 수정한 날짜 정보 (YYYY-MM-DD).
        rotation (int): 이미지의 회전 각도 (0, 90, 180, 270).
    """
    id: str
    path: str
    date_str: str
    rotation: int = 0


class ImageListManager:
    """전체 이미지 목록의 상태를 관리하는 컨트롤러입니다.  
    딕셔너리를 통한 빠른 조회와 리스트를 통한 명시적인 순서 보장을 함께 수행합니다."""
    def __init__(self):
        self._items: Dict[str, ImageItem] = {}
        self._item_ids: List[str] = []
    
    def __len__(self) -> int:
        """현재 관리 중인 이미지 항목의 총 개수를 반환합니다."""
        return len(self._item_ids)

    def add_image(self, path: str, date_str: str) -> ImageItem:
        """새로운 이미지를 목록의 끝에 추가합니다.  
        이미 동일한 경로의 파일이 존재하면 중복 추가를 방지하고 기존 객체를 반환합니다.  
        Args:
            path (str): 추가할 이미지 파일의 경로.
            date_str (str): 대상 이미지의 날짜 정보 (YYYY-MM-DD).
        Returns:
            ImageItem: 새로 추가되었거나 이미 존재하는 이미지 객체.
        """
        for item_id in self._item_ids:
            if self._items[item_id].path == path:
                return self._items[item_id]
        new_id = str(uuid.uuid4())
        item = ImageItem(id=new_id, path=path, date_str=date_str)
        self._items[new_id] = item
        self._item_ids.append(new_id)
        return item

    def remove_image(self, item_id: str) -> bool:
        """특정 이미지를 목록에서 제거합니다.  
        Args:
            item_id (str): 제거할 이미지의 고유 ID.
        Returns:
            bool: 제거에 성공하면 True, 실패하면 False.
        """
        if item_id in self._items:
            del self._items[item_id]
            self._item_ids.remove(item_id)
            return True
        return False

    def get_item(self, item_id: str) -> Optional[ImageItem]:
        """고유 ID를 통해 특정 이미지 객체를 반환합니다.  
        Args:
            item_id (str): 조회할 이미지의 고유 ID.
        Returns:
            Optional[ImageItem]: 해당 이미지 객체. 존재하지 않으면 None.
        """
        return self._items.get(item_id)

    def get_item_at(self, index: int) -> Optional[ImageItem]:
        """리스트의 인덱스를 통해 특정 이미지 객체를 반환합니다.  
        Args:
            index (int): 조회할 이미지의 인덱스.
        Returns:
            Optional[ImageItem]: 해당 이미지 객체. 존재하지 않으면 None.
        """
        if 0 <= index < len(self._item_ids):
            return self._items[self._item_ids[index]]
        return None

    def index_of(self, item_id: str) -> int:
        """특정 이미지 ID의 현재 인덱스 위치를 반환합니다.  
        Args:
            item_id (str): 조회할 이미지의 고유 ID.
        Returns:
            int: 해당 이미지의 인덱스. 존재하지 않으면 -1.
        """
        try:
            return self._item_ids.index(item_id)
        except ValueError:
            return -1

    def get_all_items(self) -> List[ImageItem]:
        """추가되거나 정렬된 순서가 보장된 모든 이미지 객체의 목록을 반환합니다.  
        Returns:
            List[ImageItem]: 순서가 유지된 이미지 객체들의 리스트.
        """
        return [self._items[item_id] for item_id in self._item_ids]

    def update_rotation(self, item_id: str, degrees: int = 90) -> bool:
        """특정 이미지의 회전 상태를 갱신합니다.  
        Args:
            item_id (str): 회전할 이미지의 고유 ID.
            degrees (int, optional): 시계 방향으로 회전할 각도.
        Returns:
            bool: 갱신에 성공하면 True, 실패하면 False.
        """
        item = self.get_item(item_id)
        if item:
            item.rotation = (item.rotation + degrees) % 360
            return True
        return False

    def update_date(self, item_id: str, new_date_str: str) -> bool:
        """특정 이미지의 날짜 정보를 변경합니다.  
        Args:
            item_id (str): 날짜 정보를 변경할 이미지의 고유 ID.
            new_date_str (str): 새로 지정할 날짜 정보 문자열.
        Returns:
            bool: 갱신에 성공하면 True, 실패하면 False.
        """
        item = self.get_item(item_id)
        if item:
            item.date_str = new_date_str
            return True
        return False

    def move_item(self, item_id: str, new_index: int) -> bool:
        """목록 내에서 특정 이미지의 순서를 변경합니다.  
        Args:
            item_id (str): 순서를 변경할 이미지의 고유 ID.
            new_index (int): 이미지가 새로 자리할 리스트 내의 목표 인덱스.
        Returns:
            bool: 순서 변경에 성공하면 True, 실패하면 False.
        """
        if item_id in self._item_ids:
            old_index = self._item_ids.index(item_id)
            new_index = max(0, min(new_index, len(self._item_ids)))
            item = self._item_ids.pop(old_index)
            self._item_ids.insert(new_index, item)
            return True
        return False

    def clear(self) -> None:
        """관리 중인 모든 이미지 목록과 순서 데이터를 초기화합니다."""
        self._items.clear()
        self._item_ids.clear()
