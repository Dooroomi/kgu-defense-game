# towers/trap.py
import os
import pygame
import math
from settings import ORANGE


# 트랩 스프라이트('논문 작성 중인 박사') 지연 로드 + 캐시
_trap_sprite = None
_trap_sprite_loaded = False


def _get_trap_sprite():
    """picture/towers/trap/0.png 를 한 번만 로드해 64px 박스에 맞춰 비율 유지 스케일(잘림 없음)."""
    global _trap_sprite, _trap_sprite_loaded
    if _trap_sprite_loaded:
        return _trap_sprite
    _trap_sprite_loaded = True
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "picture", "towers", "trap", "0.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        bb = img.get_bounding_rect(min_alpha=1)  # 투명 여백 제거
        if bb.width > 0 and bb.height > 0:
            img = img.subsurface(bb).copy()
        target = 64  # 가로/세로 중 큰 쪽을 64px로 맞춤
        scale = target / max(img.get_width(), img.get_height())
        w = max(1, round(img.get_width() * scale))
        h = max(1, round(img.get_height() * scale))
        _trap_sprite = pygame.transform.scale(img, (w, h))
    except Exception as e:
        print(f"Warning: trap sprite load failed from {path} ({e})")
        _trap_sprite = None
    return _trap_sprite


class Trap:
    """
    설치기(Trap) - '논문 작성 중인 박사'.
    도로 위에도 설치 가능하며, 설치 후 3초가 지나면 광역 폭발을 일으킵니다.
    """

    def __init__(self, x, y):
        """
        :param x: 트랩 배치 x 좌표
        :param y: 트랩 배치 y 좌표
        """
        self.x = x
        self.y = y
        self.explosion_damage = 30.0     # 설치기 폭발 데미지: 30
        self.trigger_radius = 130.0      # 폭발 사거리 반경 130px (1280 화면 기준)
        self.cost = 1500                 # 가격 1500원
        self.color = ORANGE

        self.is_active = True            # 트랩의 활성화 여부
        self.radius = 24                 # 시각적 렌더링 반경 (48px)
        self.timer = 3000                # 3초 뒤에 폭발 (3000ms)

    def update(self, enemies, laser_effects, dt=16.667):
        """
        폭발 카운트다운 타이머를 깎고, 시간(3초)이 다 지나면 대폭발을 일으킵니다.
        적이 닿아도 시간 전에는 터지지 않습니다 — 무조건 타이머가 0이 되어야 폭발.
        dt: 경과 시간(ms). 모든 PC에서 동일한 폭발 타이밍을 보장합니다.
        """
        if not self.is_active:
            return

        self.timer -= dt

        # 타이머가 0 이하가 되면(설치 후 3초 경과) 폭발. 적 접촉으로는 터지지 않음.
        if self.timer <= 0:
            self.explode(enemies, laser_effects)

    def explode(self, enemies, laser_effects):
        """
        광역 데미지를 입히고 트랩을 소멸시키는 메서드
        """
        # 폭발 범위(100px) 이내의 모든 적에게 데미지 30 부여
        for enemy in enemies:
            if enemy.is_alive and not enemy.reached_end:
                distance = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if distance <= self.trigger_radius:
                    enemy.take_damage(self.explosion_damage)

        # 폭발 비주얼 이펙트 추가
        laser_effects.append({
            "type": "explosion",
            "x": self.x,
            "y": self.y,
            "max_radius": self.trigger_radius,
            "duration": 300,
            "initial_duration": 300
        })

        self.is_active = False

    def draw(self, screen):
        """
        화면에 트랩을 그립니다. 논문을 땀 흘려 쓰는 박사님의 모습을 아기자기하게 묘사합니다.
        """
        if not self.is_active:
            return

        # 1. 폭발 예정 범위 은은하게 가이드
        guide_surf = pygame.Surface((int(self.trigger_radius * 2), int(self.trigger_radius * 2)), pygame.SRCALPHA)
        pygame.draw.circle(guide_surf, (255, 140, 0, 18), (int(self.trigger_radius), int(self.trigger_radius)), int(self.trigger_radius))
        screen.blit(guide_surf, (self.x - self.trigger_radius, self.y - self.trigger_radius))
        pygame.draw.circle(screen, (200, 100, 0), (self.x, self.y), int(self.trigger_radius), 1)

        # 2. 본체 그리기 (스프라이트: 논문 작성 중인 박사 / 그림 없으면 주황 원 폴백)
        #    폭발 임박(1초 이하)이면 부들부들 떨리는 효과
        sprite = _get_trap_sprite()
        shake = int(2 * math.sin(pygame.time.get_ticks() * 0.05)) if self.timer <= 1000 else 0
        if sprite is not None:
            rect = sprite.get_rect(center=(self.x + shake, self.y))
            screen.blit(sprite, rect)
        else:
            # 폴백: 기존 주황 원
            pulse = int(2 * math.sin(pygame.time.get_ticks() * 0.01))
            draw_radius = self.radius + pulse
            pygame.draw.circle(screen, self.color, (self.x, self.y), draw_radius)
            pygame.draw.circle(screen, (40, 20, 0), (self.x, self.y), draw_radius, 2)
            pygame.draw.circle(screen, (255, 255, 255), (self.x, self.y), draw_radius // 2)

        # 3. 남은 시간 카운트다운 (스프라이트 위쪽 / 1초 이하면 빨간 경고)
        try:
            trap_font = pygame.font.SysFont("malgungothic", 14, bold=True)
        except:
            trap_font = pygame.font.Font(None, 18)

        sec_left = max(0.0, self.timer / 1000.0)
        time_color = (220, 53, 69) if self.timer <= 1000 else (40, 20, 0)
        time_text = trap_font.render(f"{sec_left:.1f}s", True, time_color)
        t_rect = time_text.get_rect(center=(self.x, self.y - 40))
        # 가독성용 반투명 흰 배경 띠
        bg = pygame.Surface((t_rect.width + 8, t_rect.height + 2), pygame.SRCALPHA)
        bg.fill((255, 255, 255, 200))
        screen.blit(bg, (t_rect.x - 4, t_rect.y - 1))
        screen.blit(time_text, t_rect)
