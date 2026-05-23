# towers/projectile.py
import pygame
import math
import os

# 아메리카노 발사체 이미지 슬라이싱을 위한 프레임 컨테이너 및 헬퍼 함수
americano_frames = []


def load_americano_frames():
    """
    americano.png 스프라이트 시트를 로드하고 subsurface를 이용하여 6개의 개별 프레임으로 분할합니다.
    """
    global americano_frames
    if americano_frames:
        return
    # towers/ 의 부모 디렉토리(pygame_defense)를 기준으로 picture 경로 계산
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_path = os.path.join(base_dir, "picture", "americano.png")
    try:
        sheet = pygame.image.load(img_path).convert_alpha()
        sheet_w, sheet_h = sheet.get_size()
        frame_w = sheet_w // 2
        frame_h = sheet_h // 3
        for row in range(3):
            for col in range(2):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame_img = sheet.subsurface(rect)
                # 발사체가 눈에 잘 띄도록 32x32로 예쁘게 리사이즈 (1280 화면 기준)
                scaled_frame = pygame.transform.scale(frame_img, (32, 32))
                americano_frames.append(scaled_frame)
    except Exception as e:
        print(f"Warning: Failed to load americano.png from {img_path} ({e})")


class Projectile:
    def __init__(self, weapon_type, target_enemy, x, y, damage=3.0):
        """
        학부생 타워가 발사하는 아메리카노(커피 컵) 투척용 투사체 클래스
        """
        self.weapon_type = weapon_type
        self.target_enemy = target_enemy
        self.x = float(x)
        self.y = float(y)
        self.damage = float(damage)
        self.speed = 7.0                 # 등속 이동 속도
        self.radius = 12
        self.is_active = True

        # 애니메이션 파라미터 구성
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 83        # 83ms마다 다음 애니메이션 프레임으로 전환 (약 12 FPS)

        # 투사체 소스 프레임 리스트 로드
        load_americano_frames()

    def update(self, dt=16.667):
        """
        발사체를 적을 향해 등속 추적 이동시키고, 프레임 애니메이션 인덱스를 갱신합니다.
        dt: 경과 시간(ms). 모든 PC에서 동일한 발사체 속도를 보장합니다.
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
            # 충돌 성공! 데미지 적용 및 발사체 소멸
            self.target_enemy.take_damage(self.damage)
            self.is_active = False
        else:
            # 방향 벡터 정규화 및 이동 연산
            self.x += (dx / distance) * step
            self.y += (dy / distance) * step

        # 3. ms 타이머 기반 프레임 번호 순차 증가 (0~5프레임 순환)
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % 6

    def draw(self, screen):
        """
        슬라이싱된 아메리카노 스프라이트 이미지의 애니메이션을 그립니다.
        """
        if not self.is_active:
            return

        # 로드된 6개의 이미지 리스트 중에서 렌더링 진행
        if americano_frames and self.current_frame < len(americano_frames):
            img = americano_frames[self.current_frame]
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(img, rect)
        else:
            # 이미지 로드 실패 시에 대비한 깔끔한 브라운 컬러 커피 구체 폴백 렌더링
            pygame.draw.circle(screen, (101, 67, 33), (int(self.x), int(self.y)), 6)
            pygame.draw.circle(screen, (30, 20, 10), (int(self.x), int(self.y)), 6, 1)
