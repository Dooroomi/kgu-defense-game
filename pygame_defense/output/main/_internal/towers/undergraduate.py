# towers/undergraduate.py
from settings import CYAN
from .base import Tower
from .projectile import Projectile


class UndergraduateTower(Tower):
    """
    학부생 타워.
    즉발 데미지 대신 아메리카노 발사체(Projectile)를 생성해 날려보냅니다.
    공격력은 낮지만 연사 속도가 빨라 기본 방어라인 구축에 적합합니다.

    강화는 공격력 위주로 증가하며, 사거리/연사속도는 단계와 무관하게 동일합니다.
    """

    tower_type = "학부생"
    asset_key = "undergraduate"   # picture/towers/undergraduate/level<N>/
    color = CYAN
    base_cost = 1500
    is_aoe = False

    # 단계별 능력치 표 (공격력 위주 증가) / upgrade_cost = 다음 단계로 갈 때 비용
    LEVEL_DATA = {
        1: {"damage": 3.0, "range": 160.0, "fire_rate": 1000, "upgrade_cost": 800},
        2: {"damage": 6.0, "range": 160.0, "fire_rate": 1000, "upgrade_cost": 1200},
        3: {"damage": 10.0, "range": 160.0, "fire_rate": 1000, "upgrade_cost": 0},
    }

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """학부생은 아메리카노 발사체를 생성한다 (현재 강화 단계의 공격력 적용)."""
        if projectiles is not None:
            projectiles.append(Projectile("americano", enemy, self.x, self.y, self.attack_damage))
        self.cooldown_tracker = self.fire_rate
