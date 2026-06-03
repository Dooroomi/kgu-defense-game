# towers/projectile.py
import pygame
import math
import os

# 아메리카노 발사체 이미지 슬라이싱을 위한 프레임 컨테이너 및 헬퍼 함수
americano_frames = []

# 무기별 슬라이싱된 애니메이션 프레임 캐시
weapon_frames = {}

def load_weapon_frames(weapon_type):
    """
    지정된 무기 종류에 따른 스프라이트 시트를 지연 로드(Lazy Load)하고 분할 및 스케일링합니다.
    """
    global weapon_frames
    if weapon_type in weapon_frames:
        return weapon_frames[weapon_type]
        
    # towers/ 의 부모 디렉토리(pygame_defense)를 기준으로 picture/weapon 경로 계산
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 무기별 스프라이트 시트 상세 사양 정의
    specs = {
        "americano": {"file": "americano.png", "cols": 2, "rows": 3, "frames": 6, "size": (32, 32)},
        "book": {"file": "book.png", "cols": 3, "rows": 3, "frames": 8, "size": (32, 32)},
        "thesis": {"file": "thesis_weapon.png", "cols": 2, "rows": 2, "frames": 4, "size": (32, 32)}
    }
    
    if weapon_type not in specs:
        return []
        
    spec = specs[weapon_type]
    img_path = os.path.join(base_dir, "picture", "weapon", spec["file"])
    
    frames = []
    try:
        sheet = pygame.image.load(img_path).convert_alpha()
        sheet_w, sheet_h = sheet.get_size()
        cols, rows = spec["cols"], spec["rows"]
        
        frame_w = sheet_w // cols
        frame_h = sheet_h // rows
        
        count = 0
        for r in range(rows):
            for c in range(cols):
                if count >= spec["frames"]:
                    break
                rect = pygame.Rect(c * frame_w, r * frame_h, frame_w, frame_h)
                frame_img = sheet.subsurface(rect)
                scaled_frame = pygame.transform.scale(frame_img, spec["size"])
                frames.append(scaled_frame)
                count += 1
    except Exception as e:
        print(f"Warning: Failed to load {spec['file']} from {img_path} ({e})")
        frames = []
        
    weapon_frames[weapon_type] = frames
    return frames


def _add_damage_text(laser_effects, enemy, amount):
    """적중한 적 위에 떠오르는 데미지 숫자 이펙트를 추가한다 (색상은 main이 난이도로 결정)."""
    if laser_effects is None:
        return
    laser_effects.append({
        "type": "damage",
        "x": float(enemy.x),
        "y": float(enemy.y) - 18,
        "amount": float(amount),
        "duration": 650.0,
        "initial_duration": 650.0,
    })


def load_americano_frames():
    """
    이전 버전과의 완벽한 호환성을 보장하기 위해 americano_frames를 안전하게 업데이트하는 헬퍼 함수
    """
    global americano_frames
    frames = load_weapon_frames("americano")
    americano_frames.clear()
    americano_frames.extend(frames)


class Projectile:
    def __init__(self, weapon_type, target_enemy, x, y, damage=3.0):
        """
        타워별(학부생, 석사, 박사) 전용 애니메이션 투사체 클래스
        """
        self.weapon_type = weapon_type
        self.target_enemy = target_enemy
        self.x = float(x)
        self.y = float(y)
        
        # 특수 시각 효과(석사 타워 레이저 splash 등)의 원점을 찾기 위한 시작 좌표 보존
        self.start_x = float(x)
        self.start_y = float(y)
        
        self.damage = float(damage)
        self.speed = 7.0                 # 등속 이동 속도
        self.radius = 12
        self.is_active = True

        # 애니메이션 파라미터 구성 (공통 약 12 FPS)
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 83        # 83ms마다 다음 프레임 전환

        # 투사체 소스 프레임 리스트 로드
        load_weapon_frames(self.weapon_type)
        if self.weapon_type == "americano":
            load_americano_frames()

    def update(self, dt=16.667, enemies=None, laser_effects=None):
        """
        발사체를 적을 향해 등속 추적 이동시키고, 프레임 애니메이션 인덱스를 갱신합니다.
        석사 타워 무기(book)의 경우 충돌 시점에 스플래시 대미지 및 레이저 splash 효과를 안전하게 트리거합니다.
        dt: 경과 시간(ms)
        """
        if not self.is_active:
            return

        # 1. 타겟 소멸/본진도입 감지 시 자동 소멸 예외 처리
        if not self.target_enemy.is_alive or self.target_enemy.reached_end:
            self.is_active = False
            return

        # 2. 타겟 적의 실시간 (x, y) 중심 좌표 추적 및 이동
        dx = self.target_enemy.x - self.x
        dy = self.target_enemy.y - self.y
        distance = math.hypot(dx, dy)

        # dt 기반 이동 거리 계산 (60fps 기준 속도와 동일하게 보정)
        step = self.speed * dt / 16.667

        if distance <= step:
            # 충돌 성공! 주 타겟 데미지 적용
            self.target_enemy.take_damage(self.damage)
            _add_damage_text(laser_effects, self.target_enemy, self.damage)

            # 석사 타워의 책(book) 무기 타격 시: 광역 스플래시 데미지 및 레이저 splash 효과 처리
            if self.weapon_type == "book":
                splash_radius = 80.0
                if enemies is not None:
                    for other in enemies:
                        if other != self.target_enemy and other.is_alive and not other.reached_end:
                            dist = math.hypot(other.x - self.target_enemy.x, other.y - self.target_enemy.y)
                            if dist <= splash_radius:
                                other.take_damage(self.damage)
                                _add_damage_text(laser_effects, other, self.damage)
                
                if laser_effects is not None:
                    laser_effects.append({
                        "type": "splash",
                        "start": (self.start_x, self.start_y),
                        "end": (self.target_enemy.x, self.target_enemy.y),
                        "color": (138, 43, 226),  # 석사 타워 시그니처 색상 (PURPLE)
                        "splash_radius": splash_radius,
                        "duration": 117,
                        "initial_duration": 117
                    })
            
            self.is_active = False
        else:
            # 방향 벡터 정규화 및 이동 연산
            self.x += (dx / distance) * step
            self.y += (dy / distance) * step

        # 3. ms 타이머 기반 프레임 번호 순차 증가 (무기 타입별 프레임 개수 자동 호환)
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            frames = weapon_frames.get(self.weapon_type, [])
            if frames:
                self.current_frame = (self.current_frame + 1) % len(frames)

    def draw(self, screen):
        """
        슬라이싱된 전용 무기 스프라이트 이미지의 애니메이션을 그립니다.
        """
        if not self.is_active:
            return

        frames = weapon_frames.get(self.weapon_type, [])
        if frames and self.current_frame < len(frames):
            img = frames[self.current_frame]
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
        else:
            # 이미지 로드 실패 시에 대비한 깔끔한 시그니처 컬러 커피/도형 폴백 렌더링
            fallback_colors = {
                "americano": ((101, 67, 33), (30, 20, 10)),   # 브라운 (커피)
                "book": ((138, 43, 226), (40, 10, 60)),       # 보라 (석사)
                "thesis": ((255, 105, 180), (60, 20, 40))     # 핑크 (박사)
            }
            colors = fallback_colors.get(self.weapon_type, ((128, 128, 128), (30, 30, 30)))
            pygame.draw.circle(screen, colors[0], (int(self.x), int(self.y)), 6)
            pygame.draw.circle(screen, colors[1], (int(self.x), int(self.y)), 6, 1)
