# enemy.py
import pygame
import math
import os
from settings import GREEN, RED

# 스턴 효과음 로딩 (믹서 기동 오류 방지를 위해 지연 로드 지원)
stun_sound = None

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
            self.reward = 0                 # 보상 없음
            self.is_boss = True
            self.color = (139, 0, 0)        # 다크 레드
            self.stun_triggered_66 = False   # 2/3 체력 스턴 플래그
            self.stun_triggered_33 = False   # 1/3 체력 스턴 플래그
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
            
        self.radius = 48 if self.is_boss else 24  # 보스 96px / 일반 적 48px
        self.reached_end = False
        self.is_alive = True
        
        # 애니메이션 상태 변수 추가
        self.anim_frame = 0
        self.anim_timer = 0.0

    def update(self, towers=None, dt=16.667):
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

        # 보스 광역 기절 스킬 조건 검사 (2/3, 1/3 체력)
        if self.is_boss and towers:
            # 1. 2/3 체력 이하 도달 시 (첫 시전)
            if self.hp <= self.max_health * 2 / 3 and not self.stun_triggered_66:
                self.stun_triggered_66 = True
                self.cast_boss_stun(towers)
                
            # 2. 1/3 체력 이하 도달 시 (두 번째 시전)
            if self.hp <= self.max_health * 1 / 3 and not self.stun_triggered_33:
                self.stun_triggered_33 = True
                self.cast_boss_stun(towers)

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

    def cast_boss_stun(self, towers):
        """
        교수님의 광역 기절 스킬. 무작위 타워 최대 3개를 동시에 2초간 기절시킵니다.
        """
        global stun_sound
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
            
        # 기절하지 않은 타워 목록 추출
        unstunned = [t for t in towers if not t.is_stunned]
        if not unstunned:
            unstunned = list(towers)
            
        if unstunned:
            import random
            targets = random.sample(unstunned, min(len(unstunned), 3))
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
            # 보스(교수님) 또는 기타 정의되지 않은 적 타입: 기존 원형 렌더링 유지
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (40, 10, 15), (int(self.x), int(self.y)), self.radius, 2)

            # 보스 장식 및 텍스트 렌더링 (이름표가 위에 추가되더라도 기존 본체 내부 텍스트도 유지)
            if self.is_boss:
                pulse = int(8 * math.sin(pygame.time.get_ticks() * 0.01))
                # 아우라 효과
                pygame.draw.circle(screen, (255, 50, 50), (int(self.x), int(self.y)), self.radius + 10 + pulse, 3)
                try:
                    boss_font = pygame.font.SysFont("malgungothic", 18, bold=True)
                except:
                    boss_font = pygame.font.Font(None, 24)
                text = boss_font.render("교수님", True, (255, 255, 255))
                rect = text.get_rect(center=(int(self.x), int(self.y)))
                screen.blit(text, rect)

        # 2. 상단 체력바(Health Bar) 렌더링
        bar_width = 80 if self.is_boss else 50
        bar_height = 10 if self.is_boss else 6
        bar_x = int(self.x) - (bar_width // 2)
        bar_y = int(self.y) - self.radius - 16
        
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
