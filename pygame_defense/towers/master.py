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
    스탯 데이터는 tower_data.json에서 로드됩니다.
    """

    tower_type = "석사"
    asset_key = "master"          # picture/towers/master/level<N>/
    color = PURPLE

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """석사는 주 타겟을 향해 전공 서적 발사체(Projectile)를 던집니다."""
        if projectiles is not None:
            projectiles.append(Projectile("book", enemy, self.x, self.y, self.attack_damage))
        self.cooldown_tracker = self.fire_rate
