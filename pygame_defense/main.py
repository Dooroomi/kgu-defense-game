# main.py
import pygame
import sys
import math
import os
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    DARK_GRAY, LIGHT_GRAY, WAYPOINT_COLOR,
    WAYPOINTS, CYAN, PURPLE, PINK, ORANGE,
    LIGHT_BG, LIGHT_PATH, DARK_TEXT, SIDEBAR_BG, SIDEBAR_BORDER,
    GOLD, WHITE
)
from enemy import Enemy
from tower import Tower, Trap

# ==============================================================================
# 글로벌 상태 정의
# ==============================================================================
current_credits = 4.5       # 현재 학점 (초기값: 4.5 / 0 도달 시 패배)
scholarship_points = 15000  # 보유 재화(장학금) (초기값: 15,000원 - 밸런스 조정)
path_tile = None            # 길을 나타내는 반복 타일 이미지
game_state = "START_SCREEN" # 게임 대주제 상태 관리 (START_SCREEN, PLAYING, GAME_OVER)

def play_music(filename):
    """
    배경음악 재생 및 예외 처리를 위한 헬퍼 함수
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    music_path = os.path.join(base_dir, filename)
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"Warning: Failed to play music {filename} from {music_path} ({e})")

def load_font(filename, size, bold=False):
    """
    프로젝트 디렉토리에서 ttf 폰트를 로드하고, 실패 시 시스템 폰트로 안전하게 폴백합니다.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, filename)
    try:
        return pygame.font.Font(font_path, size)
    except Exception as e:
        print(f"Warning: Failed to load font {filename} ({e}). Fallback to malgungothic/default.")
        try:
            return pygame.font.SysFont("malgungothic", size, bold=bold)
        except:
            return pygame.font.Font(None, size)

def draw_multicolor_title(screen, font, center_x, center_y):
    """
    경기대 학점 디펜스 타이틀을 각 문자(열)마다 지정된 색상으로 자연스럽게 이어 렌더링합니다.
    """
    parts = [
        ("경", (201, 42, 42)),      # 빨간색
        ("기", (43, 138, 62)),      # 초록색
        ("대", (24, 100, 171)),     # 파란색
        (" 학점 디펜스", (255, 215, 0)) # 황금색
    ]
    
    # 1. 총 픽셀 가로 길이 계산
    total_width = 0
    surfaces = []
    for text, color in parts:
        surf = font.render(text, True, color)
        surfaces.append(surf)
        total_width += surf.get_width()
        
    # 2. 중앙 정렬 시작점 설정 후 한 글자씩 blit
    start_x = center_x - total_width // 2
    current_x = start_x
    for surf in surfaces:
        screen.blit(surf, (current_x, center_y - surf.get_height() // 2))
        current_x += surf.get_width()

# 스테이지 기획 데이터 구성
STAGE_DATA = {
    1: {
        "enemies": ["과제"] * 30,
        "spawn_interval": 90,
        "bonus": 2000
    },
    2: {
        "enemies": ["과제"] * 20 + ["기말고사"] * 10,
        "spawn_interval": 80,
        "bonus": 3000
    },
    3: {
        "enemies": ["과제"] * 15 + ["기말고사"] * 15 + ["논문"] * 5,
        "spawn_interval": 70,
        "bonus": 4000
    },
    4: {
        "enemies": ["기말고사"] * 20 + ["논문"] * 15,
        "spawn_interval": 60,
        "bonus": 5000
    },
    5: {
        "enemies": ["논문"] * 15,
        "spawn_interval": 50,
        "bonus": 0
    }
}

# 상점 품목 데이터 구성
SHOP_ITEMS = [
    {
        "name": "학부생",
        "cost": 1500,
        "damage": 3,
        "range": 120,
        "type": "tower",
        "color": CYAN,
        "desc": "단일 공격, 기본적인 방어라인 구축"
    },
    {
        "name": "석사",
        "cost": 4000,
        "damage": 5,
        "range": 150,
        "type": "tower",
        "color": PURPLE,
        "desc": "광역(Splash) 공격, 적 무리 처리용"
    },
    {
        "name": "박사",
        "cost": 10000,
        "damage": 15,
        "range": 200,
        "type": "tower",
        "color": PINK,
        "desc": "강력한 단발 공격, 높은 사거리"
    },
    {
        "name": "논문 작성 중인 박사",
        "cost": 1500,
        "damage": 30,
        "range": 100,
        "type": "trap",
        "color": ORANGE,
        "desc": "설치형 트랩, 3초 후 또는 접촉 시 대폭발"
    }
]

def dist_to_segment(p, v, w):
    """
    점 p에서 선분 vw 사이의 최단 거리를 계산하는 수학 함수
    """
    px, py = p
    vx, vy = v
    wx, wy = w
    l2 = (vx - wx)**2 + (vy - wy)**2
    if l2 == 0:
        return math.hypot(px - vx, py - vy)
    t = max(0, min(1, ((px - vx) * (wx - vx) + (py - vy) * (wy - vy)) / l2))
    proj_x = vx + t * (wx - vx)
    proj_y = vy + t * (wy - vy)
    return math.hypot(px - proj_x, py - proj_y)

def is_valid_placement(mx, my, item_type, towers, traps):
    """
    타워/트랩의 배치 유효성 검증 함수.
    도로 외곽 경계, 다른 요소를 침범하지 않는지 체크합니다.
    """
    # 1. 맵 영역 내부(x < 800) 경계선 검증 (우측 상점 패널 800~1000 침범 차단)
    if mx < 25 or mx > 775 or my < 25 or my > 575:
        return False
        
    # 2. 다른 타워와의 충돌 및 오버랩 검증 (최소 거리 32px 필요)
    for t in towers:
        if math.hypot(mx - t.x, my - t.y) < 32:
            return False
            
    # 3. 다른 설치기(트랩)와의 오버랩 검증 (최소 거리 25px 필요)
    for tr in traps:
        if math.hypot(mx - tr.x, my - tr.y) < 25:
            return False
            
    # 4. 도로(Waypoint) 선분과의 충돌 검증 (타워 설치 제한)
    # 설치기(트랩)는 도로 위에도 설치할 수 있도록 예외 처리
    if item_type != "논문 작성 중인 박사":
        for i in range(len(WAYPOINTS) - 1):
            if dist_to_segment((mx, my), WAYPOINTS[i], WAYPOINTS[i+1]) < 25:
                return False
                
    return True

def draw_path(screen):
    """
    적들이 이동하는 Waypoint 경로를 path_tile.png 이미지를 이용해 반복 타일링하여 렌더링합니다.
    """
    if len(WAYPOINTS) < 2:
        return
        
    # path_tile 이미지가 성공적으로 로드된 경우 이미지 기반 반복 타일링 렌더링 진행
    if path_tile:
        tile_w = path_tile.get_width()
        tile_h = path_tile.get_height()
        
        # 도로 두께 및 간격(step)에 맞게 촘촘하게 렌더링하도록 설정 (타일 크기의 적절한 최소 크기로 step 계산)
        step = max(8, min(tile_w, tile_h) // 2)
        if step < 1:
            step = 10
            
        for i in range(len(WAYPOINTS) - 1):
            p1 = WAYPOINTS[i]
            p2 = WAYPOINTS[i+1]
            
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.hypot(dx, dy)
            
            if dist == 0:
                continue
                
            vx = dx / dist
            vy = dy / dist
            
            # 길을 연속된 타일로 촘촘히 blit
            curr_dist = 0.0
            while curr_dist <= dist:
                tx = p1[0] + vx * curr_dist
                ty = p1[1] + vy * curr_dist
                screen.blit(path_tile, (int(tx - tile_w / 2), int(ty - tile_h / 2)))
                curr_dist += step
                
            # 각 세그먼트의 끝점에 정밀하게 한번 더 blit
            screen.blit(path_tile, (int(p2[0] - tile_w / 2), int(p2[1] - tile_h / 2)))
            
    else:
        # 폴백: path_tile.png가 없을 때 기존의 세련된 연회색 2중 레이어 도로 렌더링
        # 도로 양쪽의 어두운 경계선 레이어 효과 (두께 34px)
        pygame.draw.lines(screen, (222, 226, 230), False, WAYPOINTS, 34)
        # 도로 본체 (두께 30px, 라이트 그레이)
        pygame.draw.lines(screen, LIGHT_PATH, False, WAYPOINTS, 30)
        # 도로 안쪽 중앙 유도선 (두께 2px)
        pygame.draw.lines(screen, (173, 181, 189), False, WAYPOINTS, 2)

        # 각 회전 구간(Waypoint 관절) 마다 원형 노드 배치
        for wp in WAYPOINTS:
            pygame.draw.circle(screen, WAYPOINT_COLOR, wp, 6)
            pygame.draw.circle(screen, DARK_TEXT, wp, 7, 1)

def draw_shop(screen, font, mouse_pos, selected_item, current_stage, rem_enemies_count):
    """
    우측 상점 UI 및 구매 정보를 세련되고 풍부한 비주얼로 그립니다. (라이트 테마 반영 및 상태 정보 상단 이전)
    """
    # 1. 사이드바 배경 및 구분 외곽선 (흰색 배경, 옅은 회색 테두리)
    pygame.draw.rect(screen, SIDEBAR_BG, (800, 0, 200, 600))
    pygame.draw.line(screen, SIDEBAR_BORDER, (800, 0), (800, 600), 2)
    
    # 폰트 로드 (가독성 향상을 위해 설명 글꼴 크기 미세 조절)
    try:
        title_font = pygame.font.SysFont("malgungothic", 18, bold=True)
        semi_bold_font = pygame.font.SysFont("malgungothic", 12, bold=True)
        small_font = pygame.font.SysFont("malgungothic", 11)
        desc_font = pygame.font.SysFont("malgungothic", 9)
    except:
        title_font = pygame.font.Font(None, 24)
        semi_bold_font = pygame.font.Font(None, 16)
        small_font = pygame.font.Font(None, 14)
        desc_font = pygame.font.Font(None, 11)

    # 2. 플레이어 재화 및 학점 상태 표시 (우측 사이드바 상단으로 이전)
    cred_color = (40, 167, 69) if current_credits >= 2.0 else (220, 53, 69) # 세련된 초록 / 세련된 빨강
    cred_text = semi_bold_font.render(f"보유 학점: {max(0.0, current_credits):.1f} / 4.5", True, cred_color)
    fund_text = title_font.render(f"{scholarship_points:,}원", True, (40, 167, 69)) # 초록색 계좌
    
    stage_text = semi_bold_font.render(f"학기 진행: Stage {current_stage} / 5", True, DARK_TEXT)
    enemies_text = small_font.render(f"남은 과제/시험: {rem_enemies_count}마리", True, (108, 117, 125)) # 서브 회색 텍스트
    
    screen.blit(cred_text, (815, 15))
    screen.blit(fund_text, (815, 35))
    screen.blit(stage_text, (815, 65))
    screen.blit(enemies_text, (815, 85))
    
    # 구분선 (옅은 회색)
    pygame.draw.line(screen, SIDEBAR_BORDER, (810, 112), (990, 112), 1)

    # 3. 상점 타이틀 (이모티콘 제거 및 [ 학술 연구 상점 ] 형태로 강조)
    title_text = title_font.render("[ 학술 연구 상점 ]", True, DARK_TEXT)
    screen.blit(title_text, (815, 120))
    
    subtitle_text = small_font.render("클릭하여 배치 [우클릭 취소]", True, (108, 117, 125))
    screen.blit(subtitle_text, (815, 142))
    
    # 구분선 (옅은 회색)
    pygame.draw.line(screen, SIDEBAR_BORDER, (810, 160), (990, 160), 1)

    # 4. 구매 패널 슬롯 배치 (y = 165부터 시작, 높이 78px, 간격 82px)
    for i, item in enumerate(SHOP_ITEMS):
        y_base = 165 + i * 82
        btn_rect = pygame.Rect(810, y_base, 180, 78)
        
        is_hover = btn_rect.collidepoint(mouse_pos)
        is_selected = (selected_item == item["name"])
        
        # 슬롯 배경색 및 테두리 연출 (라이트 테마 및 세련된 호버 피드백)
        if is_selected:
            bg_color = (225, 235, 245)      # 은은한 라이트 블루 셀렉트
            border_color = CYAN
            border_width = 3
        elif is_hover:
            bg_color = (240, 244, 248)      # 옅은 파스텔 블루 호버
            border_color = item["color"]    # 각 타워의 고유 시그니처 색상
            border_width = 2
        else:
            bg_color = SIDEBAR_BG           # 흰색 기본 배경
            border_color = SIDEBAR_BORDER   # 옅은 회색 테두리
            border_width = 1
            
        pygame.draw.rect(screen, bg_color, btn_rect, 0, 6)
        pygame.draw.rect(screen, border_color, btn_rect, border_width, 6)
        
        # 슬롯 아이콘
        pygame.draw.circle(screen, item["color"], (830, y_base + 18), 8)
        pygame.draw.circle(screen, (30, 30, 30), (830, y_base + 18), 8, 1)

        # 타워 이름 및 가격 렌더링
        name_txt = semi_bold_font.render(item["name"], True, DARK_TEXT)
        cost_color = (40, 167, 69) if scholarship_points >= item["cost"] else (220, 53, 69)
        cost_txt = small_font.render(f"{item['cost']:,}원", True, cost_color)
        
        screen.blit(name_txt, (846, y_base + 6))
        screen.blit(cost_txt, (846, y_base + 22))
        
        # 공격 사양 및 두 줄 줄바꿈 설명 렌더링
        stats_txt = desc_font.render(f"위력:{item['damage']}  사거리:{item['range']}", True, (80, 80, 80))
        screen.blit(stats_txt, (818, y_base + 38))
        
        # 14글자 기준 한글 설명 줄바꿈 알고리즘 적용
        desc_str = item["desc"]
        if len(desc_str) > 14:
            line1 = desc_str[:14]
            line2 = desc_str[14:]
        else:
            line1 = desc_str
            line2 = ""
            
        desc_txt_line1 = desc_font.render(line1, True, (108, 117, 125))
        screen.blit(desc_txt_line1, (818, y_base + 51))
        if line2:
            desc_txt_line2 = desc_font.render(line2.strip(), True, (108, 117, 125))
            screen.blit(desc_txt_line2, (818, y_base + 62))

def draw_state_button(screen, stage_state, current_stage, mouse_pos):
    """
    하단 웨이브 제어 및 시작 버튼을 렌더링합니다. (라이트 테마 보정, 마찰 간격 배치)
    """
    btn_rect = pygame.Rect(810, 495, 180, 60)
    is_hover = btn_rect.collidepoint(mouse_pos)
    
    try:
        btn_font = pygame.font.SysFont("malgungothic", 13, bold=True)
        small_font = pygame.font.SysFont("malgungothic", 10)
    except:
        btn_font = pygame.font.Font(None, 16)
        small_font = pygame.font.Font(None, 12)

    # 상태에 따른 버튼 디자인
    if stage_state in ["WAITING", "COMPLETED"]:
        bg_color = (40, 167, 69) if is_hover else (33, 136, 56) # 세련된 초록
        text_str = "전공 학기 시작 (SPACE)"
        sub_str = f"현재 Stage: {current_stage} / 5"
        txt_color = (255, 255, 255)
    elif stage_state == "PLAYING":
        bg_color = (222, 226, 230)
        text_str = "시험 진행 중..."
        sub_str = "적들을 모두 처치하세요!"
        txt_color = (108, 117, 125)
    elif stage_state == "VICTORY":
        bg_color = (212, 175, 55)
        text_str = "수석 졸업 달성"
        sub_str = "A+ 성적으로 통과"
        txt_color = (255, 255, 255)
    else: # GAME_OVER
        bg_color = (220, 53, 69)
        text_str = "학점 미달 (학사경고)"
        sub_str = "Press ESC to Exit"
        txt_color = (255, 255, 255)

    pygame.draw.rect(screen, bg_color, btn_rect, 0, 6)
    pygame.draw.rect(screen, (206, 212, 218), btn_rect, 1, 6)

    # 텍스트 출력
    txt_surf = btn_font.render(text_str, True, txt_color)
    sub_surf = small_font.render(sub_str, True, txt_color if stage_state != "VICTORY" else (240, 240, 240))
    
    txt_rect = txt_surf.get_rect(center=(900, 517))
    sub_rect = sub_surf.get_rect(center=(900, 539))
    
    screen.blit(txt_surf, txt_rect)
    screen.blit(sub_surf, sub_rect)

def main():
    global current_credits, scholarship_points, path_tile, game_state
    
    # 1. Pygame 및 오디오 믹서 초기화
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception as e:
        print(f"Mixer initialization warning: {e}")
        
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("경기대 학점 디펜스")
    clock = pygame.time.Clock()
    
    try:
        font = pygame.font.SysFont("malgungothic", 20)      # 맑은 고딕
    except:
        font = pygame.font.Font(None, 24)                  # 폴백 폰트

    # 1-2. 효과음(SFX) 로드 (click.mp3 가정 - 절대경로 적용)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    click_sound_path = os.path.join(base_dir, "click.mp3")
    click_sound = None
    try:
        click_sound = pygame.mixer.Sound(click_sound_path)
    except Exception as e:
        print(f"Warning: click.mp3 load failed from {click_sound_path} ({e}). Playing headless/without sound.")

    # 1-3. 길 타일 이미지 로드 (path_tile.png 가정 - 절대경로 적용)
    path_tile_path = os.path.join(base_dir, "path_tile.png")
    try:
        path_tile = pygame.image.load(path_tile_path)
    except Exception as e:
        print(f"Warning: path_tile.png load failed from {path_tile_path} ({e}). Fallback to color road rendering.")

    # 시작 화면 이미지 로드 (title_bg.jpg 가정 - 절대경로 적용)
    title_bg_path = os.path.join(base_dir, "title_bg.jpg")
    title_bg = None
    try:
        title_bg = pygame.image.load(title_bg_path)
        title_bg = pygame.transform.scale(title_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except Exception as e:
        print(f"Warning: title_bg.jpg load failed from {title_bg_path} ({e}). Fallback to solid background.")
        
    # 시작 화면용 텍스트 및 버튼 정의 (커스텀 폰트 로드 및 60px 크기 적용)
    title_font = load_font("cute_font.ttf", 90, bold=True)
    btn_font = load_font("cute_font.ttf", 60, bold=True)
        
    # "게임 시작" 및 "게임 종료" 버튼을 위한 텍스트 surfaces 정의
    start_text_normal = btn_font.render("게임 시작", True, WHITE)
    start_text_hover = btn_font.render("게임 시작", True, GOLD)
    
    exit_text_normal = btn_font.render("게임 종료", True, WHITE)
    exit_text_hover = btn_font.render("게임 종료", True, (255, 100, 100)) # 호버 시 밝은 붉은색
    
    # 텍스트 버튼의 중심을 기준으로 세로로 배치 및 히트박스 정의
    start_btn_rect = start_text_normal.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
    exit_btn_rect = exit_text_normal.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150))
    
    # 시작 BGM 재생
    play_music("title_bgm.mp3")

    # 2. 게임 오브젝트 컨테이너 및 플레이 상태 파라미터 정의
    enemies = []
    towers = []   # 유저가 직접 상점을 통해 배치하도록 빈 리스트로 시작
    traps = []    # 설치기(트랩) 컨테이너 추가
    
    # 레이저 빔 및 폭발 입자 등의 시각적 특수 효과를 저장하는 리스트
    laser_effects = []
    
    # 글로벌 변수 초기화
    current_credits = 4.5
    scholarship_points = 15000
    
    current_stage = 1
    stage_state = "WAITING"  # WAITING, PLAYING, COMPLETED, VICTORY, GAME_OVER
    spawn_queue = []
    spawn_timer = 0
    spawn_cooldown = 90
    boss_spawn_timer = 600
    boss_spawned = False
    
    # 구매를 위해 상점에서 선택된 현재 타워/트랩 종류 식별 문자열
    selected_item = None

    # 3. 게임 실행 메인 루프 시작
    running = True
    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        # ----------------------------------------------------
        # 1. 사용자 이벤트 처리
        # ----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if game_state == "PLAYING":
                        # 스페이스바 키 입력으로 웨이브 단계 시작
                        if stage_state in ["WAITING", "COMPLETED"]:
                            stage_state = "PLAYING"
                            spawn_queue = list(STAGE_DATA[current_stage]["enemies"])
                            spawn_cooldown = STAGE_DATA[current_stage]["spawn_interval"]
                            spawn_timer = 0
                            if current_stage == 5:
                                boss_spawn_timer = 600
                                boss_spawned = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                
                # 마우스 좌클릭 이벤트 처리
                if event.button == 1:
                    if game_state == "START_SCREEN":
                        if start_btn_rect.collidepoint((mx, my)):
                            game_state = "PLAYING"
                            play_music("game_bgm.mp3")
                            if click_sound:
                                click_sound.play()
                        elif exit_btn_rect.collidepoint((mx, my)):
                            running = False
                            
                    elif game_state == "PLAYING":
                        clicked_shop_slot = False
                        
                        # 우측 상점 슬롯 충돌 감지 (y=165, 간격 82, 높이 78 적용)
                        for i, item in enumerate(SHOP_ITEMS):
                            btn_rect = pygame.Rect(810, 165 + i * 82, 180, 78)
                            if btn_rect.collidepoint((mx, my)):
                                clicked_shop_slot = True
                                if scholarship_points >= item["cost"]:
                                    if selected_item == item["name"]:
                                        selected_item = None  # 토글하여 선택 취소
                                    else:
                                        selected_item = item["name"]
                                        # 상점에서 새로 타워를 고르면 기존에 선택된 타워는 선택 해제
                                        for t in towers:
                                            t.is_selected = False
                                    # 상점 슬롯 클릭 효과음 재생
                                    if click_sound:
                                        click_sound.play()
                                break
                                
                        # 하단 학기 시작 버튼 충돌 감지 (y=495 보정)
                        btn_start_rect = pygame.Rect(810, 495, 180, 60)
                        if btn_start_rect.collidepoint((mx, my)):
                            clicked_shop_slot = True
                            if stage_state in ["WAITING", "COMPLETED"]:
                                stage_state = "PLAYING"
                                spawn_queue = list(STAGE_DATA[current_stage]["enemies"])
                                spawn_cooldown = STAGE_DATA[current_stage]["spawn_interval"]
                                spawn_timer = 0
                                if current_stage == 5:
                                    boss_spawn_timer = 600
                                    boss_spawned = False
                                # 시작 버튼 클릭 효과음 재생
                                if click_sound:
                                    click_sound.play()
    
                        # 상점 버튼 외부(게임 맵 내)를 클릭했고 타워가 선택된 상태이면 배치 진행
                        if not clicked_shop_slot and selected_item:
                            if mx < 800:
                                if is_valid_placement(mx, my, selected_item, towers, traps):
                                    # 타워 비용 추출 및 공제
                                    cost = 0
                                    for item in SHOP_ITEMS:
                                        if item["name"] == selected_item:
                                            cost = item["cost"]
                                            break
                                    
                                    scholarship_points -= cost
                                    
                                    # 타워 또는 트랩 인스턴스 생성 및 배치
                                    if selected_item == "논문 작성 중인 박사":
                                        traps.append(Trap(mx, my))
                                    else:
                                        towers.append(Tower(selected_item, mx, my))
                                    
                                    # 배치 성공 효과음 재생
                                    if click_sound:
                                        click_sound.play()
                                    
                                    # 재화가 바닥났다면 선택 자동해제, 남아있다면 편의상 유지
                                    if scholarship_points < cost:
                                        selected_item = None
                                        
                        # 상점 버튼 외부(게임 맵 내)를 클릭했고 타워 배치 대기 상태가 아니면, 타워 선택/선택취소 진행
                        elif not clicked_shop_slot and not selected_item:
                            if mx < 800:
                                clicked_tower = None
                                for t in towers:
                                    if t.rect.collidepoint((mx, my)):
                                        clicked_tower = t
                                        break
                                
                                if clicked_tower:
                                    # 클릭한 타워 선택 상태 활성화, 다른 타워는 비활성화
                                    for t in towers:
                                        t.is_selected = (t == clicked_tower)
                                    if click_sound:
                                        click_sound.play()
                                else:
                                    # 빈 맵 공간 클릭 시 모든 타워 선택 해제
                                    for t in towers:
                                        t.is_selected = False
                
                # 마우스 우클릭 이벤트 처리 (타워 배치 선택 취소)
                elif event.button == 3:
                    if game_state == "PLAYING":
                        selected_item = None

        # ----------------------------------------------------
        # 2. 게임 상태 업데이트 로직 (학점이 존재하고 PLAYING 상태일 때만 실행)
        # ----------------------------------------------------
        if game_state == "PLAYING" and current_credits > 0.0 and stage_state != "VICTORY":
            
            # 플레이 단계인 경우 적들의 스폰 진행
            if stage_state == "PLAYING":
                if len(spawn_queue) > 0:
                    spawn_timer += 1
                    if spawn_timer >= spawn_cooldown:
                        # 큐에서 적을 한 마리씩 추출하여 스폰
                        enemy_type = spawn_queue.pop(0)
                        enemies.append(Enemy(enemy_type, WAYPOINTS))
                        spawn_timer = 0
                elif current_stage == 5 and not boss_spawned:
                    # 5단계의 경우 논문 10마리 스폰 후 10초 뒤 최종 보스 스폰
                    boss_spawn_timer -= 1
                    if boss_spawn_timer <= 0:
                        enemies.append(Enemy("교수님", WAYPOINTS))
                        boss_spawned = True
                
                # 스폰 큐가 비었고 최종 보스도 스폰되었으며(5단계의 경우) 화면에 적이 모두 제거되었을 때 클리어 처리
                elif len(enemies) == 0:
                    if current_stage == 5:
                        if boss_spawned:
                            stage_state = "VICTORY"
                    else:
                        # 스테이지 클리어 보너스 지급 및 상태 변경
                        bonus = STAGE_DATA[current_stage]["bonus"]
                        scholarship_points += bonus
                        current_stage += 1
                        stage_state = "COMPLETED"

            # 2-1. 모든 적 생명체 좌표 업데이트 (보스 방어타 기절 스킬용 타워 리스트 참조 전달)
            for enemy in enemies:
                enemy.update(towers)

            # 2-2. 모든 방어탑 타겟 조준 및 레이저 공격 연산
            for tower in towers:
                tower.update(enemies, laser_effects)
                
            # 2-3. 모든 설치기(트랩) 3초 카운트다운 폭발 감지
            next_traps = []
            for trap in traps:
                trap.update(enemies, laser_effects)
                if trap.is_active:
                    next_traps.append(trap)
            traps = next_traps

            # 2-4. 적의 소멸 판정 및 차등 장학금 보상/학점 패널티 부여
            next_enemies = []
            for enemy in enemies:
                if enemy.reached_end:
                    # 적 종류별 학점 피해량 차등 조절
                    if enemy.enemy_type == "과제":
                        deduct = 0.5
                    elif enemy.enemy_type == "기말고사":
                        deduct = 1.0
                    elif enemy.enemy_type == "논문":
                        deduct = 1.5
                    elif enemy.enemy_type == "교수님":
                        deduct = 4.5 # 보스는 한마리만 닿아도 게임오버(4.5점 모두 차감)
                    else:
                        deduct = 0.5
                        
                    current_credits -= deduct
                    current_credits = round(max(0.0, current_credits), 1)
                elif not enemy.is_alive:
                    # 최종 보스 교수님 처치 시 장학금 대신 즉시 게임 클리어 처리
                    if enemy.is_boss:
                        stage_state = "VICTORY"
                    else:
                        scholarship_points += enemy.reward
                else:
                    next_enemies.append(enemy)
            enemies = next_enemies

            # 학점이 0에 다다르면 게임오버 처리
            if current_credits <= 0.0:
                stage_state = "GAME_OVER"
                game_state = "GAME_OVER"

        # ----------------------------------------------------
        # 3. 화면 드로잉 및 렌더링
        # ----------------------------------------------------
        if game_state == "START_SCREEN":
            if title_bg:
                screen.blit(title_bg, (0, 0))
            else:
                screen.fill(DARK_GRAY)
            
            # 반투명 검정 오버레이
            title_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            title_overlay.fill((0, 0, 0, 128))
            screen.blit(title_overlay, (0, 0))
            
            # 타이틀 다중 색상 렌더링 함수 호출
            draw_multicolor_title(screen, title_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)
            
            # 버튼 그리기 (배경 박스 삭제, 마우스 호버 이펙트 텍스트 렌더링)
            is_start_hover = start_btn_rect.collidepoint(mouse_pos)
            if is_start_hover:
                screen.blit(start_text_hover, start_btn_rect)
            else:
                screen.blit(start_text_normal, start_btn_rect)
                
            is_exit_hover = exit_btn_rect.collidepoint(mouse_pos)
            if is_exit_hover:
                screen.blit(exit_text_hover, exit_btn_rect)
            else:
                screen.blit(exit_text_normal, exit_btn_rect)
            
            pygame.display.flip()
            continue
            
        screen.fill(LIGHT_BG)

        # 맵 도로망 밑 그리기
        draw_path(screen)

        # 설치기(트랩) 그리기
        for trap in traps:
            trap.draw(screen)

        # 타워 그리기
        for tower in towers:
            tower.draw(screen)

        # 적 그리기
        for enemy in enemies:
            enemy.draw(screen)

        # 3-1. 레이저 사격선 및 구형 충격파 시각 효과 렌더링
        next_lasers = []
        for fx in laser_effects:
            duration = fx["duration"]
            if duration <= 0:
                continue
                
            fx_type = fx.get("type", "beam")
            
            if fx_type == "beam":
                # 단일 대상 다중 레이저
                color = fx["color"]
                start = fx["start"]
                end = fx["end"]
                width = max(1, duration // 2)
                pygame.draw.line(screen, color, start, end, width + 2)
                pygame.draw.line(screen, (255, 255, 255), start, end, max(1, width))
                
            elif fx_type == "splash":
                # 광역 스플래시 타격 (석사 타워 사격)
                color = fx["color"]
                start = fx["start"]
                end = fx["end"]
                r = fx["splash_radius"]
                
                # 타격 지점까지 줄기 사격선
                pygame.draw.line(screen, color, start, end, 3)
                pygame.draw.line(screen, (255, 255, 255), start, end, 1)
                
                # 구형 충격파 팽창 효과 연출
                splash_surf = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
                alpha = int(180 * (duration / 7.0))
                # 퍼지는 테두리 원
                curr_r = int(r * (1.0 - duration / 7.0))
                pygame.draw.circle(splash_surf, (color[0], color[1], color[2], alpha), (int(r), int(r)), max(1, curr_r), 3)
                pygame.draw.circle(splash_surf, (color[0], color[1], color[2], alpha // 3), (int(r), int(r)), int(r))
                screen.blit(splash_surf, (end[0] - r, end[1] - r))
                
            elif fx_type == "explosion":
                # 설치기(트랩) 대규모 화염 원형 폭발
                ex = fx["x"]
                ey = fx["y"]
                max_r = fx["max_radius"]
                total_dur = 18.0
                curr_ratio = 1.0 - (duration / total_dur)
                
                # 3단 그라데이션 원형 섬광
                r = max(1, int(max_r * curr_ratio))
                alpha = int(220 * (duration / total_dur))
                
                explosion_surf = pygame.Surface((int(max_r * 2), int(max_r * 2)), pygame.SRCALPHA)
                pygame.draw.circle(explosion_surf, (255, 69, 0, alpha), (int(max_r), int(max_r)), r)
                pygame.draw.circle(explosion_surf, (255, 215, 0, alpha // 2), (int(max_r), int(max_r)), int(r * 0.7))
                pygame.draw.circle(explosion_surf, (255, 255, 255, alpha // 3), (int(max_r), int(max_r)), int(r * 0.4))
                screen.blit(explosion_surf, (ex - max_r, ey - max_r))
                
            fx["duration"] -= 1
            if fx["duration"] > 0:
                next_lasers.append(fx)
        laser_effects = next_lasers

        # 3-2. 타워 배치 설치 예고용 고스트 실루엣 및 사거리 표시
        if selected_item:
            mx, my = mouse_pos
            if mx < 800:
                r = 100
                color = (255, 255, 255)
                for item in SHOP_ITEMS:
                    if item["name"] == selected_item:
                        r = item["range"]
                        color = item["color"]
                        break
                        
                valid = is_valid_placement(mx, my, selected_item, towers, traps)
                preview_color = (50, 255, 50) if valid else (255, 50, 50)
                
                # 반투명 사거리 원
                range_surf = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
                pygame.draw.circle(range_surf, (preview_color[0], preview_color[1], preview_color[2], 40), (int(r), int(r)), int(r))
                screen.blit(range_surf, (mx - r, my - r))
                pygame.draw.circle(screen, preview_color, (mx, my), int(r), 1)
                
                # 설치 미리보기 도큐먼트 사각형/원형 표현
                if selected_item == "논문 작성 중인 박사":
                    pygame.draw.circle(screen, color, (mx, my), 12, 2)
                else:
                    pygame.draw.rect(screen, color, (mx - 16, my - 16, 32, 32), 2)

        # 3-3. 게임 플레이 필드 좌상단 기본 정보 UI (우측 상점 패널 상단으로 이전 완료)
        pass

        # 3-4. 우측 상점 패널 렌더링
        draw_shop(screen, font, mouse_pos, selected_item, current_stage, len(enemies) + len(spawn_queue))
        
        # 3-5. 시작 및 전투 통제용 하단 버튼
        draw_state_button(screen, stage_state, current_stage, mouse_pos)

        # 3-6. 준비 기간 알림 깜빡이 텍스트 배너 (라이트 테마 보정)
        if stage_state in ["WAITING", "COMPLETED"]:
            try:
                banner_font = pygame.font.SysFont("malgungothic", 20, bold=True)
            except:
                banner_font = pygame.font.Font(None, 24)
            
            # 깜빡이는 효과 (사인 곡선 프레임 계산)
            flash = int(100 + 100 * math.sin(pygame.time.get_ticks() * 0.007))
            banner_color = (40, 167 - flash // 2, 69) # 세련된 다크그린 깜빡임
            
            banner_text = banner_font.render(f"Stage {current_stage} 준비 완료! [SPACE] 키를 눌러 시험을 시작하세요", True, banner_color)
            b_rect = banner_text.get_rect(center=(800 // 2, 80))
            
            # 텍스트 백그라운드 띠 렌더링 (반투명 흰색 띠)
            banner_bg = pygame.Surface((800, 45), pygame.SRCALPHA)
            banner_bg.fill((255, 255, 255, 200))
            screen.blit(banner_bg, (0, 80 - 22))
            screen.blit(banner_text, b_rect)

        # 3-7. 게임 클리어 (승리) 화면 렌더링
        if stage_state == "VICTORY":
            try:
                victory_font = pygame.font.SysFont("malgungothic", 42, bold=True)
            except:
                victory_font = pygame.font.Font(None, 48)
            victory_text = victory_font.render("수석 졸업 달성 (VICTORY)", True, GOLD)
            sub_text = font.render("축하합니다! 보스 교수님을 통과하고 평점 4.5 수석 졸업을 달성했습니다!", True, DARK_TEXT)
            exit_text = font.render("ESC 키를 누르면 게임을 종료합니다.", True, (108, 117, 125))
            
            go_rect = victory_text.get_rect(center=(800 // 2, 600 // 2 - 40))
            sub_rect = sub_text.get_rect(center=(800 // 2, 600 // 2 + 10))
            exit_rect = exit_text.get_rect(center=(800 // 2, 600 // 2 + 60))
            
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220)) # 라이트 테마 투명 오버레이
            screen.blit(overlay, (0, 0))
            
            screen.blit(victory_text, go_rect)
            screen.blit(sub_text, sub_rect)
            screen.blit(exit_text, exit_rect)
            
        # 3-8. 학사경고 제적 (패배) 화면 렌더링
        elif stage_state == "GAME_OVER":
            try:
                game_over_font = pygame.font.SysFont("malgungothic", 42, bold=True)
            except:
                game_over_font = pygame.font.Font(None, 48)
            game_over_text = game_over_font.render("학사경고 제적 (GAME OVER)", True, (220, 53, 69))
            sub_text = font.render("학점이 0.0에 도달하여 제적되었습니다. 다음 학기에 재수강하세요.", True, DARK_TEXT)
            exit_text = font.render("ESC 키를 누르면 게임을 종료합니다.", True, (108, 117, 125))
            
            go_rect = game_over_text.get_rect(center=(800 // 2, 600 // 2 - 40))
            sub_rect = sub_text.get_rect(center=(800 // 2, 600 // 2 + 10))
            exit_rect = exit_text.get_rect(center=(800 // 2, 600 // 2 + 60))
            
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220)) # 라이트 테마 투명 오버레이
            screen.blit(overlay, (0, 0))
            
            screen.blit(game_over_text, go_rect)
            screen.blit(sub_text, sub_rect)
            screen.blit(exit_text, exit_rect)

        # 버퍼 교체 (화면 갱신)
        pygame.display.flip()

    # Pygame 및 시스템 정리 종료
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

