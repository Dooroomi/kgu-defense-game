# enemy.py
import pygame
import math
from settings import GREEN, RED

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
            hp = 1000.0
            speed = 0.6                     # 속도 매우 느림
            self.reward = 0                 # 보상 없음
            self.is_boss = True
            self.color = (139, 0, 0)        # 다크 레드
            self.stun_cooldown = 180        # 3초마다 스턴 스킬 시전
        else:
            hp = 3.0
            speed = 2.0
            self.reward = 1000
            self.is_boss = False
            self.color = (220, 20, 60)

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
            
        self.radius = 22 if self.is_boss else 14
        self.reached_end = False
        self.is_alive = True

    def update(self, towers=None):
        """
        적 캐릭터의 이동 및 상태 업데이트 메서드.
        주어진 Waypoint 경로 리스트를 순서대로 추적하여 이동합니다.
        보스(교수님)의 경우 필드 상의 타워들을 기절(Stun)시키는 스킬을 시전합니다.
        """
        if not self.is_alive or self.reached_end:
            return

        # 보스 스킨(기절) 스킬 사용 로직
        if self.is_boss and towers:
            self.stun_cooldown -= 1
            if self.stun_cooldown <= 0:
                self.stun_cooldown = 180  # 3초 초기화
                # 현재 기절하지 않은 타워 후보 검색
                unstunned_towers = [t for t in towers if not t.is_stunned]
                if unstunned_towers:
                    import random
                    target_tower = random.choice(unstunned_towers)
                    target_tower.is_stunned = True
                    target_tower.stun_timer = 120  # 2초(120프레임) 기절 적용

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

        # 이번 프레임에 목표 웨이포인트 도달 가능 여부
        if distance <= self.speed:
            self.x = float(target_x)
            self.y = float(target_y)
            self.waypoint_index += 1
            
            if self.waypoint_index >= len(self.waypoints) - 1:
                self.reached_end = True
        else:
            # 방향 벡터 정규화 및 이동 처리
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed

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

        # 1. 적 캐릭터 본체 (원형 구체로 묘사)
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (40, 10, 15), (int(self.x), int(self.y)), self.radius, 2)

        # 보스 장식 및 텍스트 렌더링
        if self.is_boss:
            pulse = int(5 * math.sin(pygame.time.get_ticks() * 0.01))
            # 아우라 효과
            pygame.draw.circle(screen, (255, 50, 50), (int(self.x), int(self.y)), self.radius + 6 + pulse, 2)
            try:
                boss_font = pygame.font.SysFont("malgungothic", 12, bold=True)
            except:
                boss_font = pygame.font.Font(None, 16)
            text = boss_font.render("교수님", True, (255, 255, 255))
            rect = text.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(text, rect)
        else:
            # 일반 적 식별 이름
            try:
                name_font = pygame.font.SysFont("malgungothic", 10)
            except:
                name_font = pygame.font.Font(None, 14)
            text = name_font.render(self.enemy_type, True, (255, 255, 255))
            rect = text.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(text, rect)

        # 2. 상단 체력바(Health Bar) 렌더링
        bar_width = 40 if self.is_boss else 28
        bar_height = 7 if self.is_boss else 4
        bar_x = int(self.x) - (bar_width // 2)
        bar_y = int(self.y) - self.radius - 12
        
        # 체력 비율 계산
        health_ratio = self.hp / self.max_health if self.max_health > 0 else 0
        
        # 배경 (잃어버린 체력 - 빨간색)
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        # 전경 (남아있는 체력 - 초록색)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        # 체력바 테두리
        pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 1)
