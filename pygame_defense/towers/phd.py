# towers/phd.py
from settings import PINK
from .base import Tower
from .projectile import Projectile


class PhdTower(Tower):
    """
    박사 타워.
    강력한 단일 공격과 긴 사거리를 가집니다.
    공격 방식은 부모(Tower)의 기본 단일 타겟 빔 사격을 그대로 사용합니다.

    강화는 공격력 위주로 증가하며, 사거리/연사속도는 단계와 무관하게 동일합니다.
    """

    tower_type = "박사"
    asset_key = "phd"             # picture/towers/phd/level<N>/
    color = PINK
    base_cost = 12000
    is_aoe = False

    # 단계별 능력치 표 (공격력 위주 증가) / upgrade_cost = 다음 단계로 갈 때 비용
    # [테스트용] 강화 비용 전부 1원 (정식 값: 10000 / 20000)
    LEVEL_DATA = {
        1: {"damage": 25.0, "range": 260.0, "fire_rate": 1000, "upgrade_cost": 1},
        2: {"damage": 45.0, "range": 260.0, "fire_rate": 1000, "upgrade_cost": 1},
        3: {"damage": 75.0, "range": 260.0, "fire_rate": 1000, "upgrade_cost": 0},
    }

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """박사는 강력한 논문 발사체(Projectile)를 날려 단일 대상을 공격합니다."""
        if projectiles is not None:
            projectiles.append(Projectile("thesis", enemy, self.x, self.y, self.attack_damage))
        self.cooldown_tracker = self.fire_rate
