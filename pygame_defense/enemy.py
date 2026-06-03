# enemy.py
import pygame
import math
import os
from settings import GREEN, RED

# 스턴 효과음 로딩 (믹서 기동 오류 방지를 위해 지연 로드 지원)
stun_sound = None

# 교수님 광역 스턴 공용 쿨다운 — 여러 교수가 동시에 도배하지 않게 한 번에 크게 한 번만
STUN_COOLDOWN_MS = 4000
_last_stun_tick = -999999

# 하드 난이도 일반 적별 체력 배율 — main.apply_difficulty가 설정
HP_MULT = {"과제": 1.0, "기말고사": 1.0, "논문": 1.0}

# 적 애니메이션 스프라이트 및 폰트 지연 로딩 캐시
enemy_sprites = {}
name_tag_font = None

def load_enemy_assets():
    global name_tag_font, enemy_sprites
    if name_tag_font is not None:
        return
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 가독성을 위해 cute_font/cute_light_font.ttf 폰트 로드 (크기 16)
    font_path = os.path.join(base_dir, "cute_font", "cute_light_font.ttf")
    try:
        name_tag_font = pygame.font.Font(font_path, 16)
    except Exception as e:
        print(f"Warning: Failed to load name tag font {font_path} ({e})")
        try:
            name_tag_font = pygame.font.SysFont("malgungothic", 15)
        except:
            name_tag_font = pygame.font.Font(None, 18)
            
    # 적 몬스터 스프라이트 시트 사양 정의
    sheets_info = {
        "과제": {"file": "assignment.png", "cols": 3, "rows": 3, "frames": 7},
        "기말고사": {"file": "finalTest.png", "cols": 2, "rows": 3, "frames": 5},
        "논문": {"file": "thesis.png", "cols": 2, "rows": 2, "frames": 3}
    }
    
    for key, info in sheets_info.items():
        img_path = os.path.join(base_dir, "picture", "enemy", info["file"])
        try:
            # 투명성 보존을 위해 convert_alpha() 사용
            sheet = pygame.image.load(img_path).convert_alpha()
            sheet_w, sheet_h = sheet.get_size()
            cols, rows = info["cols"], info["rows"]
            
            frame_w = sheet_w // cols
            frame_h = sheet_h // rows
            
            frames_list = []
            count = 0
            for r in range(rows):
                for c in range(cols):
                    if count >= info["frames"]:
                        break
                    
                    # subsurface를 활용하여 투명 픽셀 프레임(빈칸)을 제외하고 정확한 프레임만 잘라내기
                    rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                    frame_surf = sheet.subsurface(rect)
                    
                    # 48x48 크기로 스케일링 (radius = 24 -> 지름 = 48)
                    scaled_surf = pygame.transform.scale(frame_surf, (48, 48))
                    frames_list.append(scaled_surf)
                    count += 1
                    
            enemy_sprites[key] = frames_list
        except Exception as e:
            print(f"Error loading sprite sheet for {key} from {img_path}: {e}")
            enemy_sprites[key] = []


# 보스(교수님) 스프라이트 지연 로드 캐시
_boss_frames = None
_boss_loaded = False


def load_boss_assets():
    """
    보스(교수님) 스프라이트를 한 번만 로드해 96px 박스에 비율 유지 스케일.
    반환: {"base": Surface|None, "throw": [Surface, ...]}
      - base : 기본/걷기 그림 (0.png)
      - throw: 스턴 시전(시험지 던지기) 프레임 [기본, throw_1, throw_2]
    """
    global _boss_frames, _boss_loaded
    if _boss_loaded:
        return _boss_frames
    _boss_loaded = True
    base_dir = os.path.dirname(os.path.abspath(__file__))
    boss_dir = os.path.join(base_dir, "picture", "enemy", "boss")

    def _load(fname):
        try:
            img = pygame.image.load(os.path.join(boss_dir, fname)).convert_alpha()
            bb = img.get_bounding_rect(min_alpha=1)  # 투명 여백 제거
            if bb.width > 0 and bb.height > 0:
                img = img.subsurface(bb).copy()
            target = 96  # 보스 크기 (일반 적 48 / 타워 64보다 큼)
            scale = target / max(img.get_width(), img.get_height())
            w = max(1, round(img.get_width() * scale))
            h = max(1, round(img.get_height() * scale))
            return pygame.transform.scale(img, (w, h))
        except Exception as e:
            print(f"Warning: boss sprite load failed ({fname}): {e}")
            return None

    base = _load("0.png")
    throw = [f for f in [base, _load("throw_1.png"), _load("throw_2.png")] if f is not None]
    _boss_frames = {"base": base, "throw": throw}
    return _boss_frames


# 악마교수(하드 전용 보스) 스프라이트 캐시
_demon_frames = None
_demon_loaded = False


def load_demon_boss_assets():
    """악마교수 스프라이트 로드 (96px). 반환: {"idle":[...], "cast":[...], "base":Surface|None}."""
    global _demon_frames, _demon_loaded
    if _demon_loaded:
        return _demon_frames
    _demon_loaded = True
    base_dir = os.path.dirname(os.path.abspath(__file__))
    demon_dir = os.path.join(base_dir, "picture", "enemy", "demon")

    def _load_dir(sub):
        frames = []
        d = os.path.join(demon_dir, sub)
        if os.path.isdir(d):
            files = sorted(
                (f for f in os.listdir(d) if f.lower().endswith(".png")),
                key=lambda s: int(s.split(".")[0]) if s.split(".")[0].isdigit() else 0,
            )
            for fn in files:
                try:
                    img = pygame.image.load(os.path.join(d, fn)).convert_alpha()
                    bb = img.get_bounding_rect(min_alpha=1)
                    if bb.width > 0 and bb.height > 0:
                        img = img.subsurface(bb).copy()
                    target = 96
                    scale = target / max(img.get_width(), img.get_height())
                    img = pygame.transform.scale(img, (max(1, round(img.get_width() * scale)), max(1, round(img.get_height() * scale))))
                    frames.append(img)
                except Exception as e:
                    print(f"Warning: demon frame load failed ({fn}): {e}")
        return frames

    idle = _load_dir("idle")
    cast = _load_dir("cast")
    _demon_frames = {"idle": idle, "cast": cast, "base": idle[0] if idle else None}
    return _demon_frames


class Enemy:
    def __init__(self, enemy_type, waypoints):
        """
        적 몬스터 데이터 모델 초기화
        :param enemy_type: 적 종류 식별자 (과제, 기말고사, 논문, 교수님)
        :param waypoints: 적이 이동할 (x, y) 좌표 튜플 리스트
        """
        self.enemy_type = enemy_type
        self.waypoints = waypoints
        
        # 기획서 및 밸런스 설정에 따른 데이터 세팅
        if enemy_type == "과제":
            hp = 10.0
            speed = 2.0                     # 속도 보통
            self.reward = 150               # 보상 150원
            self.is_boss = False
            self.color = (220, 50, 80)      # 장밋빛 붉은색
        elif enemy_type == "기말고사":
            hp = 30.0
            speed = 3.0                     # 속도 빠름
            self.reward = 400               # 보상 400원
            self.is_boss = False
            self.color = (255, 140, 0)      # 주황색
        elif enemy_type == "논문":
            hp = 150.0
            speed = 1.2                     # 속도 느림
            self.reward = 1500              # 보상 1500원
            self.is_boss = False
            self.color = (138, 43, 226)     # 보라색
        elif enemy_type == "교수님":
            hp = 2000.0                     # 보스 체력 2000 상향
            speed = 0.6                     # 속도 매우 느림
            self.reward = 2000              # 처치 보상 2000원 (탱키한 미니보스)
            self.is_boss = True
            self.color = (139, 0, 0)        # 다크 레드
            self.stun_triggered_66 = False   # 2/3 체력 스턴 플래그
            self.stun_triggered_33 = False   # 1/3 체력 스턴 플래그
        elif enemy_type == "악마교수":
            hp = 2500.0                     # 하드 전용 보스 (교수님보다 강함)
            speed = 0.6
            self.reward = 5000              # 처치 보상 5000원 (최종 보스)
            self.is_boss = True
            self.color = (30, 60, 120)      # 어두운 파랑
            self.stun_triggered_66 = False   # 스킬(소환) 발동 플래그
            self.stun_triggered_33 = False
        else:
            hp = 3.0
            speed = 2.0
            self.reward = 1000
            self.is_boss = False
            self.color = (220, 20, 60)

        # 하드 난이도: 일반 적별 체력 배율 적용 (보스 제외)
        hp *= HP_MULT.get(enemy_type, 1.0)
        self.hp = float(hp)
        self.max_health = float(hp)
        self.speed = float(speed)
        
        # 기본 좌표 및 위치 추적 속성
        self.waypoint_index = 0
        if self.waypoints:
            self.x = float(self.waypoints[0][0])
            self.y = float(self.waypoints[0][1])
        else:
            self.x = 0.0
            self.y = 0.0
            
        self.radius = 48 if self.is_boss else 24  # 보스 96px / 일반 적 48px
        self.reached_end = False
        self.is_alive = True
        
        # 애니메이션 상태 변수 추가
        self.anim_frame = 0
        self.anim_timer = 0.0

        # 보스 스턴 시전(시험지 던지기) 애니메이션 상태
        self.is_casting = False      # 시전 중이면 이동을 멈추고 던지기 프레임 재생
        self.cast_timer = 0.0        # 시전 남은 시간(ms)
        self.cast_frame = 0          # 던지기 프레임 인덱스
        self.cast_frame_timer = 0.0

        # 악마교수 스킬: main.py가 처리할 소환/파괴 대기 수
        self.summon_pending = 0
        self.destroy_pending = 0

    def update(self, towers=None, dt=16.667, enemies=None):
        """
        적 캐릭터의 이동 및 상태 업데이트 메서드.
        주어진 Waypoint 경로 리스트를 순서대로 추적하여 이동합니다.
        보스(교수님)의 경우 필드 상의 타워들을 기절(Stun)시키는 스킬을 시전합니다.
        dt: 이전 프레임과의 경과 시간(ms). 모든 PC에서 동일한 체감 속도를 보장합니다.
        """
        if not self.is_alive or self.reached_end:
            return

        # 몬스터 스프라이트 애니메이션 프레임 업데이트
        if self.enemy_type in ["과제", "기말고사", "논문"]:
            load_enemy_assets()
            self.anim_timer += dt
            if self.anim_timer >= 120.0:  # 120ms마다 프레임 전환
                self.anim_timer = 0.0
                frames = enemy_sprites.get(self.enemy_type)
                if frames:
                    self.anim_frame = (self.anim_frame + 1) % len(frames)
        elif self.enemy_type == "악마교수" and not self.is_casting:
            # 악마교수 idle 4프레임 순환
            idle = load_demon_boss_assets()["idle"]
            if idle:
                self.anim_timer += dt
                if self.anim_timer >= 160.0:
                    self.anim_timer = 0.0
                    self.anim_frame = (self.anim_frame + 1) % len(idle)

        # 보스 스킬 (2/3, 1/3 체력) — 교수님: 둘 다 타워 기절 / 악마교수: 2/3=교수님 3소환, 1/3=타워 3파괴
        if self.is_boss:
            if self.hp <= self.max_health * 2 / 3 and not self.stun_triggered_66:
                self.stun_triggered_66 = True
                self._cast_skill(towers, phase=1, enemies=enemies)
            if self.hp <= self.max_health * 1 / 3 and not self.stun_triggered_33:
                self.stun_triggered_33 = True
                self._cast_skill(towers, phase=2, enemies=enemies)

        # 보스가 시전 중이면 잠깐 멈춰서 시전 프레임만 재생 (교수님=던지기 / 악마교수=소환)
        if self.is_boss and self.is_casting:
            self.cast_timer -= dt
            cast_frames = self._boss_cast_frames()
            if cast_frames:
                self.cast_frame_timer += dt
                if self.cast_frame_timer >= 180.0 and self.cast_frame < len(cast_frames) - 1:
                    self.cast_frame_timer = 0.0
                    self.cast_frame += 1
            if self.cast_timer <= 0:
                self.is_casting = False
            return  # 시전 중에는 이동하지 않음

        # 다음 목표 웨이포인트가 남아있는지 확인
        next_index = self.waypoint_index + 1
        if next_index >= len(self.waypoints):
            self.reached_end = True
            return

        target_x, target_y = self.waypoints[next_index]
        
        # 목표 지점까지의 거리 계산
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)

        # 이번 프레임에 이동할 거리 (dt 기반 → 60fps 기준 속도와 동일하게 보정)
        step = self.speed * dt / 16.667

        # 이번 프레임에 목표 웨이포인트 도달 가능 여부
        if distance <= step:
            self.x = float(target_x)
            self.y = float(target_y)
            self.waypoint_index += 1

            if self.waypoint_index >= len(self.waypoints) - 1:
                self.reached_end = True
        else:
            # 방향 벡터 정규화 및 이동 처리
            self.x += (dx / distance) * step
            self.y += (dy / distance) * step

    def _start_cast(self):
        """보스 스턴 시전(시험지 던지기) 애니메이션 시작 — 잠깐 멈춰서 던진다."""
        self.is_casting = True
        self.cast_timer = 700.0     # 약 0.7초간 멈춰서 시험지 던짐
        self.cast_frame = 0
        self.cast_frame_timer = 0.0

    def _cast_skill(self, towers, phase, enemies=None):
        """보스 스킬 시전. 악마교수: phase1=교수님 3소환 / phase2=타워 3파괴. 교수님: 타워 기절."""
        self._start_cast()
        if self.enemy_type == "악마교수":
            if phase == 1:
                self.summon_pending = 3
            else:
                self.destroy_pending = 3
        else:
            # 살아있는 교수님 수 × 3개의 서로 다른 타워를 한 번에 기절 (공용 쿨다운으로 도배 방지)
            alive_profs = sum(1 for e in (enemies or [])
                              if getattr(e, "enemy_type", "") == "교수님" and e.is_alive)
            self.cast_boss_stun(towers or [], max(1, alive_profs) * 3)

    def _boss_cast_frames(self):
        """현재 보스의 시전(캐스팅) 프레임 리스트."""
        if self.enemy_type == "악마교수":
            return load_demon_boss_assets()["cast"]
        return load_boss_assets()["throw"]

    def cast_boss_stun(self, towers, stun_count=3):
        """
        교수님의 광역 기절 스킬. 무작위 타워 최대 stun_count개를 동시에 2초간 기절시킵니다.
        (악마교수가 여러 교수님을 소환하면 stun_count = 살아있는 교수님 수 × 3)
        """
        global stun_sound, _last_stun_tick
        # 공용 쿨다운 중이면 중복 스턴 무시 (여러 교수가 도배하지 않고 한 번에 크게 한 번만)
        now = pygame.time.get_ticks()
        if now - _last_stun_tick < STUN_COOLDOWN_MS:
            return
        _last_stun_tick = now

        if stun_sound is None:
            try:
                if pygame.mixer.get_init():
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    stun_sound_path = os.path.join(base_dir, "music", "stun.mp3")
                    stun_sound = pygame.mixer.Sound(stun_sound_path)
            except Exception as e:
                print(f"Warning: Failed to load stun.mp3 ({e})")
                
        if stun_sound:
            stun_sound.play()
            
        # 기절하지 않은 타워만 대상으로 (이미 스턴된 타워는 제외)
        unstunned = [t for t in towers if not t.is_stunned]

        if unstunned:
            import random
            targets = random.sample(unstunned, min(len(unstunned), stun_count))
            for t in targets:
                t.is_stunned = True
                t.stun_timer = 2000  # 2초(2000ms) 기절 적용

    def take_damage(self, amount):
        """
        피해를 입었을 때의 처리 메서드
        """
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0.0
            self.is_alive = False

    def draw(self, screen):
        """
        화면에 적 캐릭터 및 상단 체력바를 그립니다.
        """
        if not self.is_alive:
            return

        # 보스는 그림/체력바/이름표를 함께 위로 올려 그린다 (값 키우면 더 위로)
        boss_raise = 24 if self.is_boss else 0

        # 1. 적 캐릭터 본체 및 애니메이션 그리기
        if self.enemy_type in ["과제", "기말고사", "논문"]:
            load_enemy_assets()
            frames = enemy_sprites.get(self.enemy_type)
            if frames:
                img = frames[self.anim_frame]
                rect = img.get_rect(center=(int(self.x), int(self.y)))
                screen.blit(img, rect)
            else:
                # 폴백: 스프라이트가 로드되지 않은 경우 단색 원형 그리기
                pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
                pygame.draw.circle(screen, (40, 10, 15), (int(self.x), int(self.y)), self.radius, 2)
        else:
            if self.is_boss:
                is_demon = self.enemy_type == "악마교수"
                # 아우라 (악마교수=파랑 / 교수님=빨강)
                pulse = int(8 * math.sin(pygame.time.get_ticks() * 0.01))
                aura = (80, 120, 255) if is_demon else (255, 50, 50)
                pygame.draw.circle(screen, aura, (int(self.x), int(self.y)), self.radius + 10 + pulse, 3)

                if is_demon:
                    d = load_demon_boss_assets()
                    if self.is_casting and d["cast"]:
                        sprite = d["cast"][min(self.cast_frame, len(d["cast"]) - 1)]
                        sway_x, bob_y = 0, 0
                    elif d["idle"]:
                        sprite = d["idle"][self.anim_frame % len(d["idle"])]
                        t = pygame.time.get_ticks() * 0.006
                        sway_x = int(4 * math.sin(t)); bob_y = int(3 * abs(math.sin(t)))
                    else:
                        sprite = d["base"]; sway_x, bob_y = 0, 0
                else:
                    boss = load_boss_assets()
                    if self.is_casting and boss["throw"]:
                        sprite = boss["throw"][min(self.cast_frame, len(boss["throw"]) - 1)]
                        sway_x, bob_y = 0, 0
                    else:
                        sprite = boss["base"]
                        t = pygame.time.get_ticks() * 0.006
                        sway_x = int(4 * math.sin(t)); bob_y = int(3 * abs(math.sin(t)))

                if sprite is not None:
                    rect = sprite.get_rect(center=(int(self.x) + sway_x, int(self.y) - bob_y - boss_raise))
                    screen.blit(sprite, rect)
                else:
                    pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
                    pygame.draw.circle(screen, (40, 10, 15), (int(self.x), int(self.y)), self.radius, 2)
                # (이름표는 아래 공용 이름표 코드에서 그려짐)
            else:
                # 기타 정의되지 않은 적: 기존 원형
                pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
                pygame.draw.circle(screen, (40, 10, 15), (int(self.x), int(self.y)), self.radius, 2)

        # 2. 상단 체력바(Health Bar) 렌더링
        bar_width = 80 if self.is_boss else 50
        bar_height = 10 if self.is_boss else 6
        bar_x = int(self.x) - (bar_width // 2)
        bar_y = int(self.y) - self.radius - 16 - boss_raise
        
        # 체력 비율 계산
        health_ratio = self.hp / self.max_health if self.max_health > 0 else 0
        
        # 배경 (잃어버린 체력 - 빨간색)
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        # 전경 (남아있는 체력 - 초록색)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        # 체력바 테두리
        pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 1)

        # 3. 체력 바 바로 위에 적 이름표(Name Tag) 렌더링
        load_enemy_assets()  # 폰트 안전 확보
        if name_tag_font:
            # 적 종류에 따른 깔끔한 이름 표시
            name_str = self.enemy_type
            
            # 가독성을 높이기 위해 흰색 텍스트와 약간의 검은색 섀도우 효과 적용
            name_surf = name_tag_font.render(name_str, True, (255, 255, 255))
            shadow_surf = name_tag_font.render(name_str, True, (20, 20, 20))
            
            name_rect = name_surf.get_rect()
            name_rect.centerx = int(self.x)
            name_rect.bottom = bar_y - 2
            
            shadow_rect = shadow_surf.get_rect()
            shadow_rect.centerx = name_rect.centerx + 1
            shadow_rect.top = name_rect.top + 1
            
            # 그림자 먼저 blit, 그 위에 텍스트 blit
            screen.blit(shadow_surf, shadow_rect)
            screen.blit(name_surf, name_rect)
