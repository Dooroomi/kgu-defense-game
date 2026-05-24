# towers/__init__.py
"""
타워 관련 클래스들을 한곳에서 import 할 수 있게 묶어주는 패키지 초기화 파일.

사용 예시:
    from towers import create_tower, Trap, Projectile
    tower = create_tower("학부생", x, y)   # 한글 이름으로 알맞은 타워 생성
"""
from .base import Tower
from .undergraduate import UndergraduateTower
from .master import MasterTower
from .phd import PhdTower
from .trap import Trap
from .projectile import Projectile, load_americano_frames

# 상점에서 쓰는 한글 타워 이름 → 실제 클래스 매핑 테이블
TOWER_CLASSES = {
    "학부생": UndergraduateTower,
    "석사": MasterTower,
    "박사": PhdTower,
}


def create_tower(tower_type, x, y):
    """
    한글 타워 이름(예: "학부생")으로 알맞은 타워 인스턴스를 생성하는 팩토리 함수.
    매칭되는 이름이 없으면 기본 Tower를 반환합니다.
    """
    cls = TOWER_CLASSES.get(tower_type, Tower)
    return cls(x, y)


__all__ = [
    "Tower",
    "UndergraduateTower",
    "MasterTower",
    "PhdTower",
    "Trap",
    "Projectile",
    "load_americano_frames",
    "create_tower",
    "TOWER_CLASSES",
]
