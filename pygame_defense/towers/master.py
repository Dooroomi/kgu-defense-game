# towers/master.py
import math
from settings import PURPLE
from .base import Tower


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
    LEVEL_DATA = {
        1: {"damage": 5.0, "range": 150.0, "fire_rate": 1000, "upgrade_cost": 4000},
        2: {"damage": 9.0, "range": 150.0, "fire_rate": 1000, "upgrade_cost": 8000},
        3: {"damage": 15.0, "range": 150.0, "fire_rate": 1000, "upgrade_cost": 0},
    }

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """석사는 주 타겟 + 주변 반경 60px 적들에게 스플래시 데미지를 가한다."""
        # 1. 주 타겟 데미지
        enemy.take_damage(self.attack_damage)

        # 2. 광역 범위 데미지 (주 타겟 반경 60px 내의 모든 적에게)
        splash_radius = 60.0
        for other in enemies:
            if other != enemy and other.is_alive and not other.reached_end:
                dist = math.hypot(other.x - enemy.x, other.y - enemy.y)
                if dist <= splash_radius:
                    other.take_damage(self.attack_damage)

        # 광역 사격 레이저 및 폭발 충격파 추가
        laser_effects.append({
            "type": "splash",
            "start": (self.x, self.y),
            "end": (enemy.x, enemy.y),
            "color": self.color,
            "splash_radius": splash_radius,
            "duration": 117,
            "initial_duration": 117
        })

        self.cooldown_tracker = self.fire_rate
