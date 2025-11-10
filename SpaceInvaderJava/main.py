import pygame, sys, os, random, asyncio
from random import shuffle
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv
import requests
from api_server import TIDB_CONFIG, API_SERVER

# --- INIT ---

pygame.init()
pygame.mixer.init()
pygame.mixer.music.set_volume(0.5)

# --- AUDIO SETUP ---
try:
    pygame.mixer.music.load("assets/background.ogg")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
    explosion_sfx = pygame.mixer.Sound("assets/explosion.wav")
    explosion_sfx.set_volume(0.7)
except:
    print("Audio files not found, continuing without sound")

# --- DISPLAY ---
try:
    info = pygame.display.Info()
    WIDTH, HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
except:
    WIDTH, HEIGHT = 1200, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🚀 SpaceShooter Quiz Edition™")

# --- GLOBALS ---
LEVELS = 5
level = 1
score = 0
FONT = pygame.font.Font(None, 50)
BIGFONT = pygame.font.Font(None, 100)
LEADERBOARD_FONT = pygame.font.Font(None, 40)
clock = pygame.time.Clock()
dragging = False
game_over = False
show_leaderboard = False
ASK_NAME = True
IN_GAME = False
quiz_mode = False
pending_quiz = None
player_name = ""
QUIZ_INTERVAL = 10000
quiz_timer = pygame.time.get_ticks()

# --- LOCAL FALLBACK DATABASE (if TiDB fails) ---
class WebDatabase:
    def __init__(self):
        self.scores = []

    def save_score(self, player_name, score, level):
        existing = next((s for s in self.scores if s["player_name"] == player_name), None)
        if existing:
            if score > existing["score"]:
                existing["score"] = score
                existing["level"] = level
                existing["last_played"] = datetime.now().isoformat()
        else:
            self.scores.append({
                "player_name": player_name,
                "score": score,
                "level": level,
                "last_played": datetime.now().isoformat()
            })
        self.scores.sort(key=lambda x: x["score"], reverse=True)
        self.scores = self.scores[:20]

    def get_leaderboard(self, limit=10):
        return [(s["player_name"], s["score"]) for s in self.scores[:limit]]

web_db = WebDatabase()

# --- TIDB DATABASE CONNECTION ---
def get_tidb_connection():
    try:
        conn = mysql.connector.connect(TIDB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ TiDB connection failed: {e}")
        return None

# --- DATABASE FUNCTIONS ---
def save_score_to_db(player_name, score, level):
    try:
        payload = {"player_name": player_name, "score": score, "level": level}
        response = requests.post(f"{API_SERVER}/api/save_score", json=payload)
        if response.status_code == 200:
            print("✅ Score saved via API")
        else:
            print(f"⚠️ API save failed: {response.text}")
            web_db.save_score(player_name, score, level)
    except Exception as e:
        print(f"⚠️ Could not reach API: {e}")
        web_db.save_score(player_name, score, level)

def get_leaderboard():
    try:
        response = requests.get(f"{API_SERVER}/api/leaderboard")
        if response.status_code == 200:
            data = response.json()
            return [(entry["player_name"], entry.get("score", 0)) for entry in data]
        else:
            print("⚠️ Failed to fetch leaderboard:", response.text)
            return web_db.get_leaderboard(10)
    except Exception as e:
        print(f"API fetch failed: {e}")
        return web_db.get_leaderboard(10)

# --- QUESTIONS ---
def load_questions(filepath="questions.txt", levels=LEVELS):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except:
        lines = [
            "What is 2+2?|3|4|5|6|4",
            "Capital of France?|London|Berlin|Paris|Rome|Paris",
            "Largest planet?|Earth|Mars|Jupiter|Saturn|Jupiter",
            "Python is a?|Snake|Language|Both|Neither|Both",
            "2*3?|5|6|7|8|6",
            "Water chemical formula?|H2O|CO2|O2|N2|H2O",
            "Speed of light?|300 m/s|3000 km/s|300,000 km/s|Infinite|300,000 km/s",
            "Gravity on Moon?|Same as Earth|1/6th|1/2th|Double|1/6th",
            "Number of continents?|5|6|7|8|7",
            "Largest ocean?|Atlantic|Indian|Arctic|Pacific|Pacific"
        ]

    chunk_size = len(lines) // levels
    questions = {}
    for lvl in range(1, levels + 1):
        lvl_qs = lines[(lvl - 1) * chunk_size: lvl * chunk_size]
        questions[lvl] = []
        for qline in lvl_qs:
            try:
                q, *options, ans = qline.split('|')
                questions[lvl].append({
                    "q": q,
                    "opts": options,
                    "ans": ans,
                    "asked": False,
                    "answered": False
                })
            except:
                print(f"Malformed question skipped: {qline}")
    return questions

QUESTIONS_BY_LEVEL = load_questions()

# --- The rest of your game logic (quiz, display, etc.) remains unchanged ---
# (You can keep your existing functions: show_quiz_question, draw_leaderboard, main(), etc.)
# Only the Firebase functions were replaced with direct TiDB SQL logic.



# --- IMAGE LOADERS ---
def create_fallback_surface(width, height, color=(100, 100, 100)):
    surf = pygame.Surface((width, height))
    surf.fill(color)
    return surf

def load_image_by_name(base_path, filename_wo_ext):
    for ext in ['.jpg', '.jpeg', '.png']:
        full_path = os.path.join(base_path, filename_wo_ext + ext)
        if os.path.isfile(full_path):
            return pygame.image.load(full_path)
    print(f"Image not found: {filename_wo_ext}, using fallback")
    if "background" in filename_wo_ext:
        return create_fallback_surface(WIDTH, HEIGHT, (0, 0, 50))
    elif "player" in filename_wo_ext:
        return create_fallback_surface(100, 100, (0, 255, 0))
    elif "enemy" in filename_wo_ext:
        return create_fallback_surface(80, 80, (255, 0, 0))
    else:
        return create_fallback_surface(100, 100, (255, 255, 255))

def load_level_assets(level):
    level_path = f"assets/level{level}/"
    bg = pygame.transform.scale(load_image_by_name(level_path, "background"), (WIDTH, HEIGHT))
    player = pygame.transform.scale(load_image_by_name(level_path, "player"), (100, 100))
    enemy = pygame.transform.scale(load_image_by_name(level_path, "enemy"), (80, 80))
    return bg, player, enemy

try:
    bullet_img = pygame.transform.scale(pygame.image.load("assets/bullet.png"), (25, 50))
except:
    bullet_img = create_fallback_surface(25, 50, (255, 255, 0))


# --- QUIZ ---
async def show_quiz_question(level):
    global pending_quiz
    qpool = QUESTIONS_BY_LEVEL[level]
    unanswered = [q for q in qpool if not q['answered']]
    if pending_quiz:
        qdata = pending_quiz
    elif unanswered:
        qdata = unanswered[0]
        pending_quiz = qdata
    else:
        return False

    question = qdata["q"]
    options_raw = qdata["opts"]
    answer = qdata["ans"]
    options = [{"text": opt, "is_correct": (opt == answer)} for opt in options_raw]
    shuffle(options)
    selected = None

    while True:
        screen.fill((0, 0, 40))
        title = BIGFONT.render(f"Level {level} Quiz", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
        qsurf = FONT.render(question, True, (255, 255, 0))
        screen.blit(qsurf, (WIDTH // 2 - qsurf.get_width() // 2, 200))

        rects = []
        for i, opt in enumerate(options):
            r = pygame.Rect(WIDTH // 2 - 300, 300 + i * 100, 600, 80)
            color = (50, 80, 150) if selected != i else (200, 200, 50)
            pygame.draw.rect(screen, color, r)
            txt = FONT.render(opt["text"], True, (255, 255, 255))
            screen.blit(txt, (r.x + 20, r.y + 15))
            rects.append((r, i))

        pygame.display.flip()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for rect, idx in rects:
                    if rect.collidepoint(event.pos):
                        selected = idx
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and selected is not None:
                correct = options[selected]["is_correct"]
                if correct:
                    qdata["answered"] = True
                    pending_quiz = None
                    return True
                else:
                    screen.fill((0, 0, 0))
                    txt = BIGFONT.render(f"❌ Wrong! Answer: {answer}", True, (255, 0, 0))
                    screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 50))
                    pygame.display.flip()
                    await asyncio.sleep(2)  # Non-blocking delay
                    return False


# --- LEADERBOARD ---
def get_leaderboard():
    try:
        # Fetch leaderboard from Firebase via Flask API
        response = requests.get("http://127.0.0.1:5000/api/leaderboard")
        if response.status_code == 200:
            data = response.json()
            # Convert list of dicts into [(name, score), ...]
            return [(entry["player_name"], entry.get("score", 0)) for entry in data]
        else:
            print("⚠️ Failed to fetch leaderboard:", response.text)
            return web_db.get_leaderboard(10)
    except Exception as e:
        print(f"API fetch failed: {e}")
        return web_db.get_leaderboard(10)


async def draw_leaderboard():
    lb = get_leaderboard()
    leaderboard_active = True

    while leaderboard_active:
        screen.fill((10, 10, 30))
        title = BIGFONT.render("🏆 LEADERBOARD", True, (0, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

        headers = FONT.render(f"{'Rank':<6} {'Name':<15} {'Score':>8}", True, (255, 0, 255))
        screen.blit(headers, (WIDTH // 2 - 300, 150))

        glow_colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50)]
        y = 230
        for i, (name, scr) in enumerate(lb):
            color = glow_colors[i] if i < len(glow_colors) else (0, 255, 255)
            text = FONT.render(f"{i + 1:<6} {name:<15} {scr:>8}", True, color)
            screen.blit(text, (WIDTH // 2 - 300, y))
            y += text.get_height() + 20

        note = LEADERBOARD_FONT.render(" Enter Backspace to return ", True, (180, 180, 180))
        screen.blit(note, (WIDTH // 2 - note.get_width() // 2, HEIGHT - 80))
        pygame.display.flip()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                leaderboard_active = False


async def display_leaderboard_after_game():
    """Display top 5 leaderboard entries after game over."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="div*03_08_06",
            database="space_invaders_db"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT player_name, score FROM leaderboard ORDER BY score DESC LIMIT 5")
        leaders = cursor.fetchall()
        conn.close()
    except:
        leaders = web_db.get_leaderboard(5)

    screen.fill((0, 0, 40))
    title = BIGFONT.render("🏆 TOP 5 PLAYERS 🏆", True, (255, 255, 0))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    if not leaders:
        msg = FONT.render("No scores yet!", True, (200, 200, 200))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2))
    else:
        y = 250
        for i, (name, scr) in enumerate(leaders, start=1):
            text = FONT.render(f"{i}. {name:<10} - {scr}", True, (0, 255, 255))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))
            y += 80

    note = FONT.render("Press ENTER to continue", True, (180, 180, 180))
    screen.blit(note, (WIDTH // 2 - note.get_width() // 2, HEIGHT - 150))
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                waiting = False
        await asyncio.sleep(0)


# --- GAME UTILS ---
def reset_game():
    return [], [], WIDTH // 2 - 50, HEIGHT - 150, 0


async def prompt_name():
    name = ""
    input_active = True
    while input_active:
        screen.fill((0, 0, 0))
        prompt = FONT.render("Enter your name and press Enter:", True, (255, 255, 255))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 3))
        name_render = BIGFONT.render(name or "_", True, (255, 255, 0))
        screen.blit(name_render, (WIDTH // 2 - name_render.get_width() // 2, HEIGHT // 2))
        pygame.display.flip()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name:
                    return name
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode.isalnum() and len(name) < 10:
                    name += event.unicode
    return name


async def show_game_over():
    blink = True
    blink_timer = pygame.time.get_ticks()

    while True:
        screen.fill((10, 0, 0))
        title = BIGFONT.render("💀 GAME OVER 💀", True, (255, 0, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))

        if blink:
            msg = FONT.render(f"{player_name}, your score: {score}", True, (255, 255, 255))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2))

        options = [
            "Enter - Resume from current level",
            "L - View Leaderboard",
            "Esc - Exit Game"
        ]
        for i, line in enumerate(options):
            opt = FONT.render(line, True, (200, 200, 200))
            screen.blit(opt, (WIDTH // 2 - opt.get_width() // 2, HEIGHT // 2 + 100 + i * 60))

        pygame.display.flip()

        current_time = pygame.time.get_ticks()
        if current_time - blink_timer > 500:
            blink = not blink
            blink_timer = current_time

        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return True
                elif event.key == pygame.K_l:
                    await draw_leaderboard()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


# --- MAIN GAME LOOP ---
async def main():
    global level, score, game_over, show_leaderboard, player_name, dragging
    global bullets, enemies, player_x, player_y, enemy_spawn_timer
    global background, player_img, enemy_img, bullet_timer, quiz_mode, pending_quiz, quiz_timer

    # Initialize game
    player_name = await prompt_name()
    background, player_img, enemy_img = load_level_assets(level)
    bullets, enemies, player_x, player_y, enemy_spawn_timer = reset_game()
    bullet_timer = pygame.time.get_ticks()
    bullet_interval = 300

    # Main game loop
    while True:
        if show_leaderboard:
            await draw_leaderboard()
            show_leaderboard = False
            continue

        now = pygame.time.get_ticks()
        if now - quiz_timer >= QUIZ_INTERVAL and not quiz_mode:
            quiz_mode = True

        if quiz_mode:
            await show_quiz_question(level)
            quiz_timer = pygame.time.get_ticks()
            quiz_mode = False
            continue

        screen.blit(background, (0, 0))

        # Bullet logic
        if now - bullet_timer > bullet_interval:
            bullets.append({"x": player_x + 35, "y": player_y - 20})
            bullet_timer = now

        for b in bullets[:]:
            b["y"] -= 15
            if b["y"] < 0:
                bullets.remove(b)

        # Enemy logic
        if now - enemy_spawn_timer > max(1200 - level * 150, 400):
            enemies.append({"x": random.randint(50, WIDTH - 100), "y": -100})
            enemy_spawn_timer = now

        for e in enemies[:]:
            e["y"] += level + 3
            if e["y"] > HEIGHT - 80:
                enemies.remove(e)
                continue

            # Player collision
            if (e["x"] < player_x + 80 and player_x < e["x"] + 80 and
                    e["y"] < player_y + 80 and player_y < e["y"] + 80):
                game_over = True
                save_score_to_db(player_name, score, level)
                if await show_game_over():
                    bullets, enemies, player_x, player_y, enemy_spawn_timer = reset_game()
                    game_over = False
                    continue

            # Bullet collision
            for b in bullets[:]:
                if (b["x"] < e["x"] + 80 and e["x"] < b["x"] + 25 and
                        b["y"] < e["y"] + 80 and e["y"] < b["y"] + 50):
                    bullets.remove(b)
                    enemies.remove(e)
                    try:
                        explosion_sfx.play()  # 💥 Boom effect
                    except:
                        pass
                    score += 10
                    break

        # Level completion check
        if all(q["answered"] for q in QUESTIONS_BY_LEVEL[level]):
            if level < LEVELS:
                level += 1
                background, player_img, enemy_img = load_level_assets(level)
                bullets, enemies, player_x, player_y, enemy_spawn_timer = reset_game()
                quiz_timer = pygame.time.get_ticks()
                pending_quiz = None
                save_score_to_db(player_name, score, level)
            else:
                game_over = True
                save_score_to_db(player_name, score, level)
                await display_leaderboard_after_game()
                if await show_game_over():
                    bullets, enemies, player_x, player_y, enemy_spawn_timer = reset_game()
                    game_over = False
                    continue

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                player_x, player_y = event.pos[0] - 50, event.pos[1] - 50
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                show_leaderboard = True

        # Boundary checking
        player_x = max(0, min(WIDTH - 100, player_x))
        player_y = max(0, min(HEIGHT - 100, player_y))

        # Rendering
        screen.blit(player_img, (player_x, player_y))
        for b in bullets:
            screen.blit(bullet_img, (b["x"], b["y"]))
        for e in enemies:
            screen.blit(enemy_img, (e["x"], e["y"]))

        hud = FONT.render(f"{player_name} | Score: {score} | Level: {level}", True, (0, 255, 255))
        screen.blit(hud, (20, 20))

        pygame.display.update()
        await asyncio.sleep(0)
        clock.tick(60)


# Start the game
if __name__ == "__main__":
    asyncio.run(main())


