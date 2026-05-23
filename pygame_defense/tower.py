# tower.py
import pygame
import math
from settings import GRAY, CYAN, PURPLE, PINK, ORANGE

class Tower:
    def __init__(self, tower_type, x, y):
        """
        방어탑 데이터 모델 초기화
        :param tower_type: 타워 종류 식별자 (학부생, 석사, 박사)
        :param x: 타워의 x 좌표
        :param y: 타워의 y 좌표
        """
        self.tower_type = tower_type
        self.x = x
        self.y = y
        self.width = 32
        self.height = 32
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
        
        self.is_stunned = False
        self.stun_timer = 0
        self.cooldown_tracker = 0
        self.is_selected = False

        # 기획서 사양에 따른 등급별 밸런스 설정
        if tower_type == "학부생":
            self.attack_damage = 3.0        # 공격력 3 (상향 버프)
            self.attack_range = 120.0       # 사거리 120
            self.is_aoe = False
            self.fire_rate = 20             # 빠른 연사 (0.33초당 1회)
            self.cost = 1500
            self.color = CYAN
        elif tower_type == "석사":
            self.attack_damage = 5.0        # 공격력 5 (상향 버프)
            self.attack_range = 150.0       # 사거리 150
            self.is_aoe = True              # 광역 공격 필수 적용
            self.fire_rate = 60             # 1.0초당 1회 공격
            self.cost = 4000
            self.color = PURPLE
        elif tower_type == "박사":
            self.attack_damage = 15.0       # 공격력 15 (느리지만 강력한 단일)
            self.attack_range = 200.0       # 사거리 200
            self.is_aoe = False
            self.fire_rate = 60             # 1.0초당 1회 공격 (2배 속도로 밸런스 조정)
            self.cost = 10000
            self.color = PINK
        else:
            self.attack_damage = 1.0
            self.attack_range = 100.0
            self.is_aoe = False
            self.fire_rate = 60
            self.cost = 1500
            self.color = GRAY

    def update(self, enemies, laser_effects):
        """
        타워 동작 업데이트. 범위 내의 적을 탐색하고 주기적으로 공격합니다.
        보스의 스턴 공격을 받았을 때는 카운트다운을 하며 작동을 멈춥니다.
        """
        # 스턴 관리
        if self.is_stunned:
            self.stun_timer -= 1
            if self.stun_timer <= 0:
                self.is_stunned = False
            return

        # 쿨다운 감소
        if self.cooldown_tracker > 0:
            self.cooldown_tracker -= 1

        # 쿨다운이 끝나면 공격 진행
        if self.cooldown_tracker == 0:
            target = self.find_target(enemies)
            if target:
                self.attack(target, enemies, laser_effects)

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

    def attack(self, enemy, enemies, laser_effects):
        """
        타겟으로 정한 적에게 피해를 입히고 사격 쿨다운을 리셋합니다.
        광역 공격 타워(석사)인 경우 스플래시 데미지를 가합니다.
        """
        if self.is_aoe:
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
                "duration": 7
            })
        else:
            # 단일 타겟 데미지
            enemy.take_damage(self.attack_damage)
            
            # 단일 사격 레이저 추가
            laser_effects.append({
                "type": "beam",
                "start": (self.x, self.y),
                "end": (enemy.x, enemy.y),
                "color": self.color,
                "duration": 5
            })

        self.cooldown_tracker = self.fire_rate

    def draw(self, screen):
        """
        화면에 타워를 렌더링하고, 감지 영역 가이드를 그립니다.
        """
        # 1. 타워 범위 가이드라인 (선택 상태일 때만 반투명 서클 그리기)
        if self.is_selected:
            guide_color = (self.color[0], self.color[1], self.color[2], 25)
            guide_surface = pygame.Surface((int(self.attack_range * 2), int(self.attack_range * 2)), pygame.SRCALPHA)
            pygame.draw.circle(guide_surface, guide_color, (int(self.attack_range), int(self.attack_range)), int(self.attack_range))
            screen.blit(guide_surface, (self.x - self.attack_range, self.y - self.attack_range))
            
            # 가이드 외곽선
            pygame.draw.circle(screen, (80, 80, 80), (self.x, self.y), int(self.attack_range), 1)

        # 2. 타워 본체 드로잉
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, (30, 30, 30), self.rect, 2)  # 어두운 테두리
        
        # 타워 등급에 따른 텍스트 표시
        try:
            tower_font = pygame.font.SysFont("malgungothic", 10, bold=True)
        except:
            tower_font = pygame.font.Font(None, 14)
        t_label = tower_font.render(self.tower_type[0], True, (0, 0, 0))
        lbl_rect = t_label.get_rect(center=(self.x, self.y))
        screen.blit(t_label, lbl_rect)

        # 3. 스턴 상태 이펙트 렌더링
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


class Trap:
    def __init__(self, x, y):
        """
        설치기(Trap) 데이터 모델 초기화 - '논문 작성 중인 박사'
        :param x: 트랩 배치 x 좌표
        :param y: 트랩 배치 y 좌표
        """
        self.x = x
        self.y = y
        self.explosion_damage = 30.0     # 설치기 폭발 데미지: 30
        self.trigger_radius = 100.0     # 폭발 사거리 반경 100px
        self.cost = 1500                 # 가격 1500원
        self.color = ORANGE
        
        self.is_active = True            # 트랩의 활성화 여부
        self.radius = 12                 # 시각적 렌더링 반경
        self.timer = 180                 # 3초 뒤에 폭발 (60 FPS * 3초 = 180프레임)

    def update(self, enemies, laser_effects):
        """
        폭발 카운트다운 타이머를 깎고, 3초가 지나거나 적이 트랩에 닿으면 대폭발을 일으킵니다.
        """
        if not self.is_active:
            return

        self.timer -= 1
        
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
            "duration": 18
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
        
        sec_left = max(0.0, self.timer / 60.0)
        time_text = trap_font.render(f"{sec_left:.1f}s", True, (0, 0, 0))
        t_rect = time_text.get_rect(center=(self.x, self.y))
        screen.blit(time_text, t_rect)
        
        # 상단 "작성 중" 라벨
        label_text = trap_font.render("논문작성중", True, (255, 255, 255))
        lbl_rect = label_text.get_rect(center=(self.x, self.y - self.radius - 8))
        screen.blit(label_text, lbl_rect)


class Projectile:
    def __init__(self, weapon_type, target_enemy, x, y):
        """
        (하위 호환성을 위해 유지되는 뼈대 모델)
        """
        self.weapon_type = weapon_type
        self.target_enemy = target_enemy
        self.x = x
        self.y = y
        self.speed = 5.0
        self.radius = 5
        self.is_active = True

    def update(self):
        pass

    def draw(self, screen):
        pass
