import os
from datetime import datetime
from PIL import Image, ExifTags


def get_exif_date(path: str) -> str:
    """사진 파일의 EXIF 데이터에서 촬영일을 추출합니다.  
    우선순위(DateTimeOriginal > DateTimeDigitized > DateTime)에 따라 값을 찾아 정해진 형식으로 반환합니다.  
    Args:
        path (str): 분석할 이미지 파일의 경로.
    Returns:
        str: 추출된 날짜 문자열 ("YYYY-MM-DD"). 데이터가 없거나 파싱 중 오류 발생 시 빈 문자열.
    """
    try:
        with Image.open(path) as img:
            exif_data = img.getexif()
            if exif_data:
                tag_ids = {name: tid for tid, name in ExifTags.TAGS.items()}
                tag_priority = [
                    ('DateTimeOriginal', 1),    # EXIF IFD: 1
                    ('DateTimeDigitized', 1),   # EXIF IFD: 1
                    ('DateTime', 0)             # Main IFD: 0
                ]

                exif_ifd_pointer_id = tag_ids.get('ExifOffset')
                exif_ifd = {}
                if exif_ifd_pointer_id in exif_data:
                    exif_ifd = exif_data.get_ifd(exif_ifd_pointer_id)

                for tag_name, ifd_type in tag_priority:
                    tag_id = tag_ids.get(tag_name)
                    if not tag_id: continue

                    ifd_to_search = exif_data if ifd_type == 0 else exif_ifd
                    date_str = ifd_to_search.get(tag_id)

                    if date_str:
                        date_part = date_str.split(" ")[0]
                        return date_part.replace(":", "-")
    except Exception:
        pass
    return ""


def format_date(date_str: str, fmt: str) -> str:
    """표준 날짜 문자열을 사용자가 지정한 형식으로 변환합니다.  
    Args:
        date_str (str): 원본 날짜 문자열 (예: "1999-01-31").
        fmt (str): 목표 날짜 형식 (예: "YYYY년 MM월 DD일").
    Returns:
        str: 지정 형식으로 변환한 날짜 문자열. 변환 실패 시 입력받은 원본 문자열.
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str

    fmt_map = {
        "YYYY": "%Y", "YY": "%y",
        "MM": "%m", "M": "%#m" if os.name == 'nt' else "%-m",
        "DD": "%d", "D": "%#d" if os.name == 'nt' else "%-d",
        "AA": "%A", "A": "%a",
    }
    output_fmt = fmt.upper()
    for key in sorted(fmt_map.keys(), key=len, reverse=True):
        output_fmt = output_fmt.replace(key, fmt_map[key])

    return date_obj.strftime(output_fmt)
