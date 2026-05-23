# towers/base.py
import os
import pygame
import math
from settings import GRAY

# ==============================================================================
# 강화 단계(레벨)별 표시 색상 - 노랑(1) > 초록(2) > 빨강(3)
# 타워 본체 그림 위에 테두리/뱃지로 현재 강화 단계를 보여주는 용도.
# ==============================================================================
TIER_COLORS = {
    1: (255, 215, 0),    # 노랑 (1단계)
    2: (40, 167, 69),    # 초록 (2단계)
    3: (220, 53, 69),    # 빨강 (3단계, 최대)
}

# ==============================================================================
# 강화 단계별 스프라이트(애니메이션) 프레임 로딩 + 캐시
#
# [픽셀 그림을 넣는 위치 규칙] (아직 그림이 없어도 게임은 폴백으로 정상 작동)
#   picture/towers/<asset_key>/level<N>/  폴더 안에 프레임 이미지를 넣으면 됩니다.
#   예) picture/towers/undergraduate/level1/0.png, 1.png, 2.png ...
#   - 파일명 사전순으로 정렬되어 애니메이션 순서가 됩니다.
#   - 그림이 1장이면 정지 이미지, 여러 장이면 자동으로 애니메이션됩니다.
#   - 폴더가 없거나 비어있으면 색상 사각형(폴백)으로 그려집니다.
# ==============================================================================
_tower_frame_cache = {}

# 타워 본체 렌더링 기준 크기 (프레임 이미지를 이 크기로 리사이즈)
TOWER_SPRITE_SIZE = 36


def load_tower_frames(asset_key, level):
    """
    특정 타워(asset_key)의 특정 강화 단계(level)에 해당하는 애니메이션 프레임 리스트를 반환.
    한 번 로드한 결과는 캐시하여 디스크 재접근을 피합니다.
    그림이 없으면 빈 리스트([])를 반환하여 호출부가 폴백 렌더링을 하도록 합니다.
    """
    cache_key = (asset_key, level)
    if cache_key in _tower_frame_cache:
        return _tower_frame_cache[cache_key]

    frames = []
    # towers/ 의 부모 디렉토리(pygame_defense)를 기준으로 picture 경로 계산
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(base_dir, "picture", "towers", asset_key, f"level{level}")

    if os.path.isdir(folder):
        try:
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith((".png", ".jpg", ".jpeg"))
            )
            for fn in files:
                img = pygame.image.load(os.path.join(folder, fn)).convert_alpha()
                img = pygame.transform.scale(img, (TOWER_SPRITE_SIZE, TOWER_SPRITE_SIZE))
                frames.append(img)
        except Exception as e:
            print(f"Warning: Failed to load tower frames from {folder} ({e})")
            frames = []

    _tower_frame_cache[cache_key] = frames
    return frames


class Tower:
    """
    모든 방어탑(학부생/석사/박사)의 공통 부모 클래스.

    [강화 시스템]
    - 모든 타워는 1 ~ MAX_LEVEL(3) 단계로 개별 강화됩니다.
    - 단계별 능력치는 자식 클래스의 LEVEL_DATA 표에서 정의합니다 (공격력 위주 증가).
    - 단계별 그림(애니메이션)은 picture/towers/<asset_key>/level<N>/ 에서 로드됩니다.

    [자식 클래스가 정의해야 하는 클래스 속성]
        tower_type : 화면 표시용 한글 이름 (예: "학부생")
        asset_key  : 그림 폴더명 (예: "undergraduate")
        color      : 시그니처 색상 (레이저/사거리 표시에 사용)
        base_cost  : 최초 설치 비용 (판매 환급 계산 기준)
        is_aoe     : 광역 공격 여부
        LEVEL_DATA : {레벨: {"damage", "range", "fire_rate", "upgrade_cost"}}
    """

    MAX_LEVEL = 3

    # --- 자식 클래스에서 덮어쓰는 기본값들 ---
    tower_type = "기본"
    asset_key = "base"
    color = GRAY
    base_cost = 1500
    is_aoe = False
    LEVEL_DATA = {
        1: {"damage": 1.0, "range": 100.0, "fire_rate": 1000, "upgrade_cost": 1000},
        2: {"damage": 2.0, "range": 100.0, "fire_rate": 1000, "upgrade_cost": 2000},
        3: {"damage": 3.0, "range": 100.0, "fire_rate": 1000, "upgrade_cost": 0},
    }

    # 애니메이션 프레임 전환 속도 (ms/프레임)
    anim_speed = 120

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)

        # 공통 상태 변수
        self.is_stunned = False
        self.stun_timer = 0
        self.cooldown_tracker = 0
        self.is_selected = False

        # 강화 단계 (1부터 시작)
        self.level = 1
        self.total_invested = self.base_cost  # 판매 환급 계산용 누적 투자금

        # 애니메이션 상태
        self.anim_frame = 0
        self.anim_timer = 0

        # 현재 레벨 능력치 적용 (attack_damage / attack_range / fire_rate 세팅)
        self.apply_level()

    # ------------------------------------------------------------------
    # 강화(레벨) 관련 로직
    # ------------------------------------------------------------------
    def apply_level(self):
        """현재 self.level에 맞는 능력치를 LEVEL_DATA에서 읽어 적용한다."""
        data = self.LEVEL_DATA[self.level]
        self.attack_damage = data["damage"]
        self.attack_range = data["range"]
        self.fire_rate = data["fire_rate"]
        # 단계가 바뀌면 새 그림으로 애니메이션을 처음부터 재생
        self.anim_frame = 0
        self.anim_timer = 0

    def can_upgrade(self):
        """더 강화할 수 있는지 (최대 단계 미만인지) 여부."""
        return self.level < self.MAX_LEVEL

    def get_upgrade_cost(self):
        """다음 단계로 강화하는 데 드는 비용. 최대 단계면 None."""
        if not self.can_upgrade():
            return None
        return self.LEVEL_DATA[self.level]["upgrade_cost"]

    def upgrade(self):
        """
        한 단계 강화한다 (능력치/그림 갱신).
        재화 차감은 호출부(main.py)에서 처리하므로 여기서는 단계만 올린다.
        성공하면 True, 이미 최대 단계면 False.
        """
        if not self.can_upgrade():
            return False
        cost = self.get_upgrade_cost()
        self.total_invested += cost
        self.level += 1
        self.apply_level()
        return True

    def get_sell_value(self):
        """판매 시 돌려받는 환급액 (누적 투자금의 70%)."""
        return int(self.total_invested * 0.7)

    def get_tier_color(self):
        """현재 강화 단계에 해당하는 표시 색상 (노랑/초록/빨강)."""
        return TIER_COLORS.get(self.level, (255, 255, 255))

    # ------------------------------------------------------------------
    # 매 프레임 업데이트
    # ------------------------------------------------------------------
    def update(self, enemies, laser_effects, projectiles=None, dt=16.667):
        """
        타워 동작 업데이트. 범위 내의 적을 탐색하고 주기적으로 공격합니다.
        보스의 스턴 공격을 받았을 때는 카운트다운을 하며 작동을 멈춥니다.
        dt: 경과 시간(ms). 모든 PC에서 일정한 공격 속도를 보장합니다.
        """
        # 애니메이션은 스턴 여부와 상관없이 항상 갱신
        self._advance_animation(dt)

        # 스턴 관리 (ms 기반 차감)
        if self.is_stunned:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.is_stunned = False
            return

        # 쿨다운 감소 (ms 기반)
        if self.cooldown_tracker > 0:
            self.cooldown_tracker -= dt

        # 쿨다운이 끝나면 공격 진행
        if self.cooldown_tracker <= 0:
            target = self.find_target(enemies)
            if target:
                self.attack(target, enemies, laser_effects, projectiles)

    def _advance_animation(self, dt):
        """현재 단계의 프레임이 2장 이상이면 ms 기반으로 프레임을 순환시킨다."""
        frames = load_tower_frames(self.asset_key, self.level)
        if len(frames) > 1:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % len(frames)

    def find_target(self, enemies):
        """
        공격 범위 내의 살아있고 끝에 도달하지 않은 적 중 가장 가까운 적을 조준합니다.
        """
        best_target = None
        min_distance = float('inf')

        for enemy in enemies:
            if not enemy.is_alive or enemy.reached_end:
                continue

            dx = enemy.x - self.x
            dy = enemy.y - self.y
            distance = math.hypot(dx, dy)

            # 탐지 범위 내에 들어왔는지 판별
            if distance <= self.attack_range:
                if distance < min_distance:
                    min_distance = distance
                    best_target = enemy

        return best_target

    def attack(self, enemy, enemies, laser_effects, projectiles=None):
        """
        기본 공격: 단일 타겟 빔 사격 (박사 타워 및 폴백이 사용).
        석사(광역)·학부생(발사체)은 각 자식 클래스에서 이 메서드를 오버라이드합니다.
        """
        # 단일 타겟 데미지
        enemy.take_damage(self.attack_damage)

        # 단일 사격 레이저 추가
        laser_effects.append({
            "type": "beam",
            "start": (self.x, self.y),
            "end": (enemy.x, enemy.y),
            "color": self.color,
            "duration": 83,
            "initial_duration": 83
        })

        self.cooldown_tracker = self.fire_rate

    # ------------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------------
    def draw(self, screen):
        """
        화면에 타워를 렌더링하고, 감지 영역 가이드를 그립니다.
        단계별 그림이 있으면 스프라이트를, 없으면 색상 사각형(폴백)을 사용합니다.
        """
        # 1. 타워 범위 가이드라인 (선택 상태일 때만 반투명 서클 그리기)
        if self.is_selected:
            guide_color = (self.color[0], self.color[1], self.color[2], 25)
            guide_surface = pygame.Surface((int(self.attack_range * 2), int(self.attack_range * 2)), pygame.SRCALPHA)
            pygame.draw.circle(guide_surface, guide_color, (int(self.attack_range), int(self.attack_range)), int(self.attack_range))
            screen.blit(guide_surface, (self.x - self.attack_range, self.y - self.attack_range))

            # 가이드 외곽선
            pygame.draw.circle(screen, (80, 80, 80), (self.x, self.y), int(self.attack_range), 1)

        # 2. 타워 본체 드로잉 (그림 우선, 없으면 색상 사각형 폴백)
        frames = load_tower_frames(self.asset_key, self.level)
        if frames:
            idx = self.anim_frame if self.anim_frame < len(frames) else 0
            img = frames[idx]
            img_rect = img.get_rect(center=(self.x, self.y))
            screen.blit(img, img_rect)
        else:
            # 폴백: 색상 사각형 + 타워 이름 첫 글자
            pygame.draw.rect(screen, self.color, self.rect)
            pygame.draw.rect(screen, (30, 30, 30), self.rect, 2)  # 어두운 테두리
            try:
                tower_font = pygame.font.SysFont("malgungothic", 10, bold=True)
            except:
                tower_font = pygame.font.Font(None, 14)
            t_label = tower_font.render(self.tower_type[0], True, (0, 0, 0))
            lbl_rect = t_label.get_rect(center=(self.x, self.y))
            screen.blit(t_label, lbl_rect)

        # 3. 강화 단계 뱃지 (테두리 없이, 타워 우상단 코너 안쪽에 작은 원형 뱃지로 표시)
        #    길(도로)과 겹치지 않도록 타워 영역(rect) 안쪽에 그립니다.
        tier_color = self.get_tier_color()
        badge_radius = 8
        badge_center = (self.rect.right - badge_radius, self.rect.top + badge_radius)
        pygame.draw.circle(screen, tier_color, badge_center, badge_radius)
        pygame.draw.circle(screen, (255, 255, 255), badge_center, badge_radius, 1)

        try:
            lv_font = pygame.font.SysFont("malgungothic", 10, bold=True)
        except:
            lv_font = pygame.font.Font(None, 13)
        lv_text = lv_font.render(str(self.level), True, (255, 255, 255))
        screen.blit(lv_text, lv_text.get_rect(center=badge_center))

        # 4. 스턴 상태 이펙트 렌더링
        if self.is_stunned:
            # 기절 소용돌이 / 번개 및 텍스트 렌더링
            pulse = int(5 * math.sin(pygame.time.get_ticks() * 0.02))
            try:
                stun_font = pygame.font.SysFont("malgungothic", 11, bold=True)
            except:
                stun_font = pygame.font.Font(None, 14)
            stun_text = stun_font.render("STUNNED!", True, (255, 50, 50))
            st_rect = stun_text.get_rect(center=(self.x, self.rect.top - 12 + pulse))
            screen.blit(stun_text, st_rect)

            # 타워 바디를 붉은 기절 전기장으로 덮음
            pygame.draw.rect(screen, (255, 50, 50), self.rect, 2)
