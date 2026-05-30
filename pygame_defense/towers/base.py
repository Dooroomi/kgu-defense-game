# towers/base.py
import os
import pygame
import math
from settings import GRAY, WAYPOINTS

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
# 강화 단계별 / 방향별 스프라이트(애니메이션) 프레임 로딩 + 캐시
#
# [픽셀 그림을 넣는 위치 규칙] (아직 그림이 없어도 게임은 폴백으로 정상 작동)
#   picture/towers/<asset_key>/level<N>/<direction>/  폴더 안에 프레임을 넣습니다.
#   direction = front(적이 아래) / back(적이 위) / left(적이 왼쪽) / right(적이 오른쪽)
#   예) picture/towers/undergraduate/level1/left/0.png, 1.png, 2.png ...
#   - 파일명 사전순으로 정렬되어 애니메이션 순서가 됩니다.
#   - 그림이 1장이면 정지 이미지, 여러 장이면 자동으로 애니메이션됩니다.
#
# [폴백 규칙] 해당 방향 폴더가 없으면 아래 순서로 대체:
#   right  -> left 를 좌우 반전(미러)
#   그 외  -> front -> 평면(level<N>/) -> left 순으로 대체
#   끝까지 없으면 색상 사각형(폴백 렌더링).
# ==============================================================================
_tower_frame_cache = {}

# 타워 본체 렌더링 기준 크기 (프레임 이미지를 이 크기로 리사이즈)
TOWER_SPRITE_SIZE = 64

# 지원 방향
DIRECTIONS = ("front", "back", "left", "right")


def _normalize_frame(raw, size=TOWER_SPRITE_SIZE, bottom_margin=2):
    """
    프레임마다 캐릭터 크기/위치가 들쭉날쭉한 문제를 보정한다.
    1) 불투명(캐릭터) 영역만 잘라내고
    2) '키(높이)'를 일정하게 맞춰 비율 유지 스케일 후
    3) 64x64 투명 캔버스에 가로 중앙 + 하단(발) 정렬로 배치.
    → 프레임이 바뀌어도 캐릭터 크기/발 위치가 일정해 떨림/축소가 사라진다.
    """
    bb = raw.get_bounding_rect(min_alpha=1)  # 캐릭터(불투명) 경계
    if bb.width <= 0 or bb.height <= 0:
        return pygame.transform.scale(raw, (size, size))

    cropped = raw.subsurface(bb).copy()
    target_h = size - bottom_margin
    scale = target_h / bb.height
    new_w = max(1, round(bb.width * scale))
    new_h = max(1, round(bb.height * scale))
    scaled = pygame.transform.scale(cropped, (new_w, new_h))

    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    x = (size - new_w) // 2               # 가로 중앙 정렬
    y = size - bottom_margin - new_h      # 하단(발) 정렬
    canvas.blit(scaled, (x, y))
    return canvas


def _load_frames_from_folder(folder):
    """폴더 안의 이미지들을 파일명 순으로 읽어 64px 정규화 프레임 리스트로 반환."""
    frames = []
    if os.path.isdir(folder):
        try:
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith((".png", ".jpg", ".jpeg"))
            )
            for fn in files:
                img = pygame.image.load(os.path.join(folder, fn)).convert_alpha()
                frames.append(_normalize_frame(img))
        except Exception as e:
            print(f"Warning: Failed to load tower frames from {folder} ({e})")
            frames = []
    return frames


def load_tower_frames(asset_key, level, direction="front"):
    """
    특정 타워(asset_key)/강화단계(level)/방향(direction)의 애니메이션 프레임 리스트 반환.
    한 번 로드한 결과는 (asset_key, level, direction)별로 캐시합니다.
    그림이 없으면 위의 폴백 규칙을 따르며, 끝까지 없으면 빈 리스트를 반환합니다.
    """
    cache_key = (asset_key, level, direction)
    if cache_key in _tower_frame_cache:
        return _tower_frame_cache[cache_key]

    # towers/ 의 부모 디렉토리(pygame_defense)를 기준으로 picture 경로 계산
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lvl_dir = os.path.join(base_dir, "picture", "towers", asset_key, f"level{level}")

    # 1) 요청한 방향 폴더
    frames = _load_frames_from_folder(os.path.join(lvl_dir, direction))

    # 2) 좌/우 한쪽만 그렸으면 반대쪽은 자동 좌우반전(미러)
    if not frames and direction in ("left", "right"):
        other = "right" if direction == "left" else "left"
        other_frames = _load_frames_from_folder(os.path.join(lvl_dir, other))
        frames = [pygame.transform.flip(f, True, False) for f in other_frames]

    # 3) 그래도 없으면 front -> 평면 폴더 -> right -> left 순으로 폴백
    if not frames and direction != "front":
        frames = _load_frames_from_folder(os.path.join(lvl_dir, "front"))
    if not frames:
        frames = _load_frames_from_folder(lvl_dir)            # 구버전(평면) 호환
    if not frames:
        frames = _load_frames_from_folder(os.path.join(lvl_dir, "right"))
    if not frames:
        frames = _load_frames_from_folder(os.path.join(lvl_dir, "left"))

    _tower_frame_cache[cache_key] = frames
    return frames


# 합성된 '던지기' 프레임 캐시 (방향별로 한 번만 만들고 재사용)
_throw_cache = {}


def composed_throw_frames(asset_key, level, direction):
    """
    특정 방향의 '던지기' 애니메이션 프레임을 반환.
    - 자체 던지기 프레임이 충분하면(3장 이상) 그대로 사용 (right/left)
    - 부족하면(예: back은 정지 그림뿐) 정지 1장 + right의 2,3번(던지는 순간)을 재활용
    """
    key = (asset_key, level, direction)
    if key in _throw_cache:
        return _throw_cache[key]

    own = load_tower_frames(asset_key, level, direction)
    if len(own) >= 3:
        result = own
    else:
        right = load_tower_frames(asset_key, level, "right")
        release = list(right[2:4]) if len(right) >= 4 else list(right)
        stand = list(own[:1])
        result = stand + release if release else own

    _throw_cache[key] = result
    return result


def _closest_point_on_segment(p, a, b):
    """점 p에서 선분 ab 위의 가장 가까운 점을 반환."""
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return (ax, ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return (ax + t * dx, ay + t * dy)


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
        self.width = 64
        self.height = 64
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)

        # 공통 상태 변수
        self.is_stunned = False
        self.stun_timer = 0
        self.cooldown_tracker = 0
        self.is_selected = False

        # 강화 단계 (1부터 시작)
        self.level = 1
        self.total_invested = self.base_cost  # 판매 환급 계산용 누적 투자금

        # 바라보는 방향 (back/left/right) - 타겟 위치에 따라 갱신
        self.facing = "right"
        # idle(적 없음)일 때 바라볼 방향 = 가장 가까운 길의 방향으로 결정
        # (세로 길 옆이면 정면 / 가로 길 옆이면 뒷모습) - 설치 위치 기준 고정
        self.idle_facing = self._path_facing()
        # 사거리 안에 적이 있는지 (없으면 idle 정지 그림 표시)
        self.has_target = False
        # 던지기 애니메이션 재생 중 여부 (공격 발동 시 1회 재생)
        self.is_attacking = False

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
        # 사거리 내 가장 가까운 적을 한 번만 탐색 (방향 갱신 + 공격에 공용 사용)
        target = self.find_target(enemies)
        self.has_target = target is not None
        if target is not None:
            # 타겟 위치에 따라 바라보는 방향 갱신
            self.facing = self._direction_to(target)

        # 던지기 애니메이션은 '공격(투사체 발사) 시점'에 1회 재생됨 (아래에서 발동)
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
            if target:
                self.attack(target, enemies, laser_effects, projectiles)
                # 공격 발동 = 던지기 애니메이션 1회 재생 (이미 재생 중이면 처음부터 강제 재시작)
                self.is_attacking = True
                self.anim_frame = 0
                self.anim_timer = 0

    def _throw_frames(self, direction):
        """해당 방향의 던지기 애니메이션 프레임(자체 없으면 right 2,3 재활용)."""
        return composed_throw_frames(self.asset_key, self.level, direction)

    def _stand_frames(self, direction):
        """해당 방향의 정지(서있는) 그림. front은 idle 폴더를 사용."""
        if direction == "front":
            f = load_tower_frames(self.asset_key, self.level, "idle")
            if f:
                return f
        return load_tower_frames(self.asset_key, self.level, direction)

    def _current_sprite(self):
        """
        지금 그릴 스프라이트 한 장을 반환(없으면 None → 색상 폴백).
        - 공격 중: 바라보는 방향의 던지기 애니메이션 현재 프레임
        - 적은 있으나 공격 사이: 방향 정지 그림(준비 자세)
        - 적 없음(idle): 가장 가까운 길을 바라보는 정지 그림
        """
        if self.is_attacking:
            frames = self._throw_frames(self.facing)
            idx = self.anim_frame
        elif self.has_target:
            frames = self._stand_frames(self.facing)
            idx = 0
        else:
            frames = self._stand_frames(self.idle_facing)
            idx = 0
        if not frames:
            return None
        return frames[idx if idx < len(frames) else 0]

    def _dir_from_delta4(self, dx, dy):
        """(dx,dy) 방향을 front/back/left/right 4방향으로 판정 (idle용)."""
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        # 화면 좌표는 아래로 갈수록 y 증가 → 아래면 front(정면), 위면 back(뒷모습)
        return "front" if dy > 0 else "back"

    def _direction_to(self, enemy):
        """
        전투(던지기) 방향은 투사체가 날아갈 쪽 = 적의 좌우 위치로만 결정한다.
        적이 캐릭터 중앙보다 조금이라도 왼쪽이면 left, 그 외(중앙/오른쪽)는 right.
        (위/아래 여부는 던지기 방향에 영향 주지 않음 — 뒷모습은 idle에서만 사용)
        """
        return "left" if (enemy.x - self.x) < 0 else "right"

    def _path_facing(self):
        """
        가장 가까운 길 점의 '상대 위치'로 idle 바라보기 방향을 정한다.
        - 길이 타워보다 위쪽(=가로 길 아래에 설치) → 뒷모습(back)  : 길을 올려다봄(등이 보임)
        - 길이 타워보다 아래쪽(=가로 길 위에 설치) → 정면(front)  : 길을 내려다봄
        - 세로 길 옆(길이 좌/우에 있음)            → 정면(front)
        (idle에서는 좌/우 옆모습을 쓰지 않는다.)
        """
        best = None
        best_d = float('inf')
        for i in range(len(WAYPOINTS) - 1):
            cp = _closest_point_on_segment((self.x, self.y), WAYPOINTS[i], WAYPOINTS[i + 1])
            d = math.hypot(cp[0] - self.x, cp[1] - self.y)
            if d < best_d:
                best_d = d
                best = cp
        if best is None:
            return "front"
        dx = best[0] - self.x
        dy = best[1] - self.y
        # 길이 '위쪽'에 더 가깝게 있을 때만 뒷모습, 그 외(아래·세로 옆)는 정면
        if abs(dy) > abs(dx) and dy < 0:
            return "back"
        return "front"

    def _advance_animation(self, dt):
        """
        공격(투사체 발사) 시 시작된 던지기 애니메이션을 1회만 재생한다(one-shot).
        끝까지 재생하면 멈추고, 다음 공격 때 처음(frame 0)부터 다시 시작된다.
        """
        if not self.is_attacking:
            return
        frames = self._throw_frames(self.facing)
        if len(frames) <= 1:
            self.is_attacking = False
            self.anim_frame = 0
            return
        self.anim_timer += dt
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.anim_frame += 1
            if self.anim_frame >= len(frames):
                # 1회 재생 완료 → 정지 (다음 공격 때 다시 시작)
                self.anim_frame = 0
                self.is_attacking = False

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
        sprite = self._current_sprite()
        if sprite is not None:
            img_rect = sprite.get_rect(center=(self.x, self.y))
            screen.blit(sprite, img_rect)
        else:
            # 폴백: 색상 사각형 + 타워 이름 첫 글자
            pygame.draw.rect(screen, self.color, self.rect)
            pygame.draw.rect(screen, (30, 30, 30), self.rect, 3)  # 어두운 테두리
            try:
                tower_font = pygame.font.SysFont("malgungothic", 18, bold=True)
            except:
                tower_font = pygame.font.Font(None, 24)
            t_label = tower_font.render(self.tower_type[0], True, (0, 0, 0))
            lbl_rect = t_label.get_rect(center=(self.x, self.y))
            screen.blit(t_label, lbl_rect)

        # 3. 강화 단계 뱃지 (테두리 없이, 타워 우상단 코너 안쪽에 작은 원형 뱃지로 표시)
        #    길(도로)과 겹치지 않도록 타워 영역(rect) 안쪽에 그립니다.
        tier_color = self.get_tier_color()
        badge_radius = 13
        badge_center = (self.rect.right - badge_radius, self.rect.top + badge_radius)
        pygame.draw.circle(screen, tier_color, badge_center, badge_radius)
        pygame.draw.circle(screen, (255, 255, 255), badge_center, badge_radius, 2)

        try:
            lv_font = pygame.font.SysFont("malgungothic", 14, bold=True)
        except:
            lv_font = pygame.font.Font(None, 18)
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
