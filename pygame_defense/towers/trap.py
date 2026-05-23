# towers/trap.py
import pygame
import math
from settings import ORANGE


class Trap:
    """
    설치기(Trap) - '논문 작성 중인 박사'.
    도로 위에도 설치 가능하며, 3초 뒤 또는 적이 접촉하면 광역 폭발을 일으킵니다.
    """

    def __init__(self, x, y):
        """
        :param x: 트랩 배치 x 좌표
        :param y: 트랩 배치 y 좌표
        """
        self.x = x
        self.y = y
        self.explosion_damage = 30.0     # 설치기 폭발 데미지: 30
        self.trigger_radius = 100.0      # 폭발 사거리 반경 100px
        self.cost = 1500                 # 가격 1500원
        self.color = ORANGE

        self.is_active = True            # 트랩의 활성화 여부
        self.radius = 12                 # 시각적 렌더링 반경
        self.timer = 3000                # 3초 뒤에 폭발 (3000ms)

    def update(self, enemies, laser_effects, dt=16.667):
        """
        폭발 카운트다운 타이머를 깎고, 3초가 지나거나 적이 트랩에 닿으면 대폭발을 일으킵니다.
        dt: 경과 시간(ms). 모든 PC에서 동일한 폭발 타이밍을 보장합니다.
        """
        if not self.is_active:
            return

        self.timer -= dt

        # 적 접촉(터치) 감지
        touched = False
        for enemy in enemies:
            if enemy.is_alive and not enemy.reached_end:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if dist <= (enemy.radius + self.radius):
                    touched = True
                    break

        if self.timer <= 0 or touched:
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

        # 2. 본체 그리기 (주황색 컴퓨터 모니터와 깜박이는 바디)
        pulse = int(2 * math.sin(pygame.time.get_ticks() * 0.01))
        draw_radius = self.radius + pulse

        pygame.draw.circle(screen, self.color, (self.x, self.y), draw_radius)
        pygame.draw.circle(screen, (40, 20, 0), (self.x, self.y), draw_radius, 2)

        # 내부 코어원
        pygame.draw.circle(screen, (255, 255, 255), (self.x, self.y), draw_radius // 2)

        # 3. 텍스트 정보 (남은 초 렌더링)
        try:
            trap_font = pygame.font.SysFont("malgungothic", 10, bold=True)
        except:
            trap_font = pygame.font.Font(None, 14)

        sec_left = max(0.0, self.timer / 1000.0)
        time_text = trap_font.render(f"{sec_left:.1f}s", True, (0, 0, 0))
        t_rect = time_text.get_rect(center=(self.x, self.y))
        screen.blit(time_text, t_rect)

        # 상단 "작성 중" 라벨
        label_text = trap_font.render("논문작성중", True, (255, 255, 255))
        lbl_rect = label_text.get_rect(center=(self.x, self.y - self.radius - 8))
        screen.blit(label_text, lbl_rect)
