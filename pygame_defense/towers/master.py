# towers/master.py
import math
from settings import PURPLE
from .base import Tower
from .projectile import Projectile


class MasterTower(Tower):
    """
    석사 타워.
    주 타겟과 그 주변 반경 내의 적들에게 광역(Splash) 데미지를 입힙니다.
    적 무리를 한 번에 처리하기 좋습니다.

    강화는 공격력 위주로 증가하며, 사거리/연사속도는 단계와 무관하게 동일합니다.
    """

    tower_type = "석사"
    asset_key = "master"          # picture/towers/master/level<N>/
    color = PURPLE
    base_cost = 4000
    is_aoe = True

    # 단계별 능력치 표 (공격력 위주 증가) / upgrade_cost = 다음 단계로 갈 때 비용
    # [테스트용] 강화 비용 전부 1원 (정식 값: 4000 / 8000)
    LEVEL_DATA = {
        1: {"damage": 5.0, "range": 195.0, "fire_rate": 1000, "upgrade_cost": 1},
        2: {"damage": 9.0, "range": 195.0, "fire_rate": 1000, "upgrade_cost": 1},
        3: {"damage": 15.0, "range": 195.0, "fire_rate": 1000, "upgrade_cost": 0},
    }

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """석사는 주 타겟을 향해 전공 서적 발사체(Projectile)를 던집니다."""
        if projectiles is not None:
            projectiles.append(Projectile("book", enemy, self.x, self.y, self.attack_damage))
        self.cooldown_tracker = self.fire_rate
