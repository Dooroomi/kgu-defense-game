# towers/tower_data_manager.py
"""
타워 데이터 매니저 (Data-Driven Architecture).

게임 초기화 시 tower_data.json을 단 한 번만 읽어 메모리(딕셔너리)에 캐싱합니다.
각 타워/트랩 클래스는 이 매니저를 통해 스탯 데이터를 조회합니다.
"""
import json
import os


class TowerDataManager:
    """
    타워·트랩 스탯 데이터를 중앙 관리하는 싱글턴 매니저.

    사용법:
        # 게임 시작 시 1회 호출
        TowerDataManager.load()

        # 타워 스탯 조회
        data = TowerDataManager.get_tower_data("undergraduate")
        level_data = TowerDataManager.get_level_data("undergraduate", 1)

        # 트랩 스탯 조회
        trap = TowerDataManager.get_trap_data()

        # 상점 아이템 목록 자동 생성
        shop_items = TowerDataManager.get_shop_items()
    """

    _data = None  # 캐싱된 전체 데이터 딕셔너리

    @classmethod
    def load(cls, json_path=None):
        """
        tower_data.json을 읽어 메모리에 캐싱한다.
        이미 로드되어 있으면 재로드하지 않는다 (I/O 최소화).

        :param json_path: JSON 파일 경로 (기본: pygame_defense/tower_data.json)
        """
        if cls._data is not None:
            return

        if json_path is None:
            # towers/ 의 부모 디렉토리(pygame_defense)를 기준으로 경로 계산
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "tower_data.json")

        with open(json_path, "r", encoding="utf-8") as f:
            cls._data = json.load(f)

    @classmethod
    def _ensure_loaded(cls):
        """데이터가 로드되지 않았으면 자동 로드한다 (안전 장치)."""
        if cls._data is None:
            cls.load()

    @classmethod
    def get_tower_data(cls, asset_key):
        """
        특정 타워(asset_key)의 전체 데이터를 반환한다.

        :param asset_key: 타워 식별 키 (예: "undergraduate", "master", "phd", "base")
        :return: {"tower_type": str, "base_cost": int, "is_aoe": bool, "levels": {...}}
        """
        cls._ensure_loaded()
        return cls._data["towers"][asset_key]

    @classmethod
    def get_level_data(cls, asset_key, level):
        """
        특정 타워/레벨의 스탯 딕셔너리를 반환한다.

        :param asset_key: 타워 식별 키
        :param level: 강화 단계 (1, 2, 3)
        :return: {"damage": float, "range": float, "fire_rate": int, "upgrade_cost": int}
        """
        cls._ensure_loaded()
        return cls._data["towers"][asset_key]["levels"][str(level)]

    @classmethod
    def get_tower_level_data_dict(cls, asset_key):
        """
        특정 타워의 LEVEL_DATA를 기존 코드 호환 형태({int: dict})로 반환한다.
        JSON의 문자열 키("1","2","3")를 정수 키(1,2,3)로 변환한다.

        :param asset_key: 타워 식별 키
        :return: {1: {"damage":..., "range":..., "fire_rate":..., "upgrade_cost":...}, 2: ..., 3: ...}
        """
        cls._ensure_loaded()
        raw = cls._data["towers"][asset_key]["levels"]
        return {int(k): v for k, v in raw.items()}

    @classmethod
    def get_trap_data(cls):
        """
        트랩(논문 작성 중인 박사)의 스탯 데이터를 반환한다.

        :return: {"tower_type": str, "cost": int, "explosion_damage": float,
                  "trigger_radius": float, "timer": int}
        """
        cls._ensure_loaded()
        return cls._data["trap"]

    @classmethod
    def get_shop_items(cls):
        """
        상점 UI에 필요한 아이템 목록을 자동 생성한다.
        main.py의 SHOP_ITEMS와 동일한 구조의 리스트를 반환한다.

        색상(color)과 설명(desc)은 JSON에 포함되지 않으므로,
        asset_key별 매핑 테이블에서 보충한다.

        :return: [{"name": str, "cost": int, "damage": float, "range": float,
                   "type": str, "color": tuple, "desc": str}, ...]
        """
        from settings import CYAN, PURPLE, PINK, ORANGE

        cls._ensure_loaded()

        # 색상 및 설명은 렌더링 전용이므로 코드에서 관리
        _tower_meta = {
            "undergraduate": {
                "color": CYAN,
                "desc": "단일 공격, 기본적인 방어라인 구축",
            },
            "master": {
                "color": PURPLE,
                "desc": "광역(Splash) 공격, 적 무리 처리용",
            },
            "phd": {
                "color": PINK,
                "desc": "강력한 단발 공격, 높은 사거리",
            },
        }

        items = []

        # 타워 순서 고정 (학부생 → 석사 → 박사)
        for key in ("undergraduate", "master", "phd"):
            tower = cls._data["towers"][key]
            level1 = tower["levels"]["1"]
            meta = _tower_meta[key]
            items.append({
                "name": tower["tower_type"],
                "cost": tower["base_cost"],
                "damage": level1["damage"],
                "range": level1["range"],
                "type": "tower",
                "color": meta["color"],
                "desc": meta["desc"],
            })

        # 트랩 (논문 작성 중인 박사)
        trap = cls._data["trap"]
        items.append({
            "name": trap["tower_type"],
            "cost": trap["cost"],
            "damage": trap["explosion_damage"],
            "range": trap["trigger_radius"],
            "type": "trap",
            "color": ORANGE,
            "desc": "설치형 트랩, 3초 후 대폭발",
        })

        return items
