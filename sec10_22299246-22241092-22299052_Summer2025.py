from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random, sys, time, math



WIN_W, WIN_H = 1000, 800
GRID_LENGTH = 600



camera_angle = 0.0
camera_distance = 650.0
CAM_DIST_MIN, CAM_DIST_MAX = 300.0, 1200.0



stars = []
num_stars = 300


#canon er orientation
cannon_yaw = 180.0
cannon_pitch = 0.0
PITCH_MIN = -90.0
PITCH_MAX = 90.0
YAW_STEP = 4.5
PITCH_STEP = 3.5
def clamp(v, lo, hi):
    if v < lo:
        return lo
    elif v > hi:
        return hi
    else:
        return v


#gamer er init state
score = 0 
lives = 3
game_over = False
consecutive_hits = 0
cheat_mode_ready = False
can_activate_cheat = False
is_cheat_active = False
is_recharge_period = False
cheat_activation_message = ""
cheat_activation_message_timer = 0.0
normal_meteors_since_boss = 0
is_first_boss_spawned = False


cheat_timers = {
    "multi_shot": 0.0,
    "slow_mo": 0.0,
    "infinite_lives": 0.0
}


#meteor er init state
meteor = {}
meteor_tail = []
meteor_speed = 0.5


def new_meteor():
    global meteor, meteor_tail, meteor_speed, normal_meteors_since_boss, is_first_boss_spawned, score

    if cheat_timers["slow_mo"] > 0:
        meteor_speed = 0.25
    else:
        meteor_speed = 0.5 + (score // 7) * 0.2

    spawn_boss = False
    if score > 7 and not is_first_boss_spawned:
        spawn_boss = True
        is_first_boss_spawned = True
    elif is_first_boss_spawned and normal_meteors_since_boss >= 10:
        spawn_boss = True

    if spawn_boss:
        normal_meteors_since_boss = 0
    elif is_first_boss_spawned:
        normal_meteors_since_boss += 1
            
    meteor = {
        "x": random.uniform(-250, 250), "y": random.uniform(-200, 200),
        "z": random.uniform(500, 750), "size": 60.0 if spawn_boss else 30.0,
        "health": 3 if spawn_boss else 1, "is_boss": spawn_boss, "hit_timer": 0.0
    }
    meteor_tail.clear()



bullets = []  #bullet init
FIRE_INTERVAL = 0.12
BULLET_SPEED = 20.0
BULLET_TTL = 6.0
is_firing = False
_last_fire_time = 0.0
_prev_time = None



def deg2rad(a): return a * math.pi / 180.0    #extra helpers fuct
def rotate_x(v, ang_deg):
    x, y, z = v; a = deg2rad(ang_deg); c, s = math.cos(a), math.sin(a)
    return (x, y * c - z * s, y * s + z * c)
def rotate_z(v, ang_deg):
    x, y, z = v; a = deg2rad(ang_deg); c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c, z)
def add3(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul3(v, s): return (v[0] * s, v[1] * s, v[2] * s)
def length3(v): return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
def norm3(v):
    L = length3(v)

    if L == 0:
      return (0, 0, 0)
    else:
      return (v[0]/L, v[1]/L, v[2]/L)
def cannon_base_world(): return (0.0, GRID_LENGTH - 90.0, 75.0)


def muzzle_world_and_forward():
    base = cannon_base_world(); scale = 1.0; pivot = (0.0, 50.0, 45.0)
    offset = (0.0, 5.0, 0.0); length = 160.0; yaw = cannon_yaw
    pitch = -12.0 + cannon_pitch; f_initial = (0.0, 1.0, 0.0)
    f_pitched = rotate_x(f_initial, pitch); fwd = norm3(rotate_z(f_pitched, yaw))
    muz_local = (0.0, length, 0.0); muz_pitched = rotate_x(muz_local, pitch)
    total_off = add3(add3(pivot, offset), muz_pitched)
    scaled_off = mul3(total_off, scale); yawed_off = rotate_z(scaled_off, yaw)
    world_pos = add3(base, yawed_off)
    return world_pos, fwd


quad_sphere = None; quad_cylinder = None


def reset_game():
    global score, lives, game_over, consecutive_hits, cheat_mode_ready, can_activate_cheat
    global is_cheat_active, is_recharge_period, cheat_activation_message, cheat_activation_message_timer
    global camera_angle, camera_distance, cheat_timers, cannon_yaw, cannon_pitch
    global normal_meteors_since_boss, is_first_boss_spawned
    
    score = 0; lives = 3; game_over = False
    consecutive_hits = 0; cheat_mode_ready = False; can_activate_cheat = False
    is_cheat_active = False; is_recharge_period = False
    cheat_activation_message = ""; cheat_activation_message_timer = 0.0
    camera_angle = 0.0; camera_distance = 650.0
    cannon_yaw = 180.0; cannon_pitch = 0.0
    normal_meteors_since_boss = 0; is_first_boss_spawned = False
    
    for cheat in cheat_timers: cheat_timers[cheat] = 0.0
    new_meteor()


def init():
    global stars, quad_sphere, quad_cylinder, _prev_time
    glClearColor(0.0, 0.0, 0.0, 1.0); glEnable(GL_DEPTH_TEST)
    for _ in range(num_stars):
        stars.append({
            "x": random.uniform(-1500, 1500), "y": random.uniform(-1500, 1500),
            "z": random.uniform(-400, 400), "brightness": random.uniform(0.2, 1.0),
            "size": random.uniform(1.0, 2.5)
        })
    quad_sphere = gluNewQuadric(); quad_cylinder = gluNewQuadric()
    reset_game()
    _prev_time = time.perf_counter()



def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):  #drawing and ui
    glColor3f(1, 1, 1); glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H); glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text: glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)


def draw_starry_sky():
    glBegin(GL_QUADS)
    glColor3f(0.0, 0.0, 0.2); glVertex3f(-1500, 1500, -500)
    glVertex3f(1500, 1500, -500)
    glColor3f(0.15, 0.0, 0.15); glVertex3f(1500, -1500, -500)
    glVertex3f(-1500, -1500, -500)
    glEnd()
    for s in stars:
        glPointSize(s["size"])
        glBegin(GL_POINTS)
        twinkle = random.uniform(-0.1, 0.1)
        c = clamp(s["brightness"] + twinkle, 0.0, 1.0)
        glColor3f(c, c, c * 0.9)
        glVertex3f(s["x"], s["y"], s["z"])
        glEnd()


def draw_cannon():
    glPushMatrix(); glTranslatef(0, GRID_LENGTH - 90, 75); glScalef(1.0, 1.0, 1.0)
    glColor3f(0.12, 0.12, 0.14); glPushMatrix(); glScalef(1.8, 0.4, 0.55); glutSolidCube(100); glPopMatrix()
    glColor3f(0.18, 0.18, 0.2); glPushMatrix(); glTranslatef(0, 25, 25); glScalef(1.0, 0.6, 0.7); glutSolidCube(80); glPopMatrix()
    glPushMatrix(); glRotatef(cannon_yaw, 0, 0, 1); glTranslatef(0, 50, 45)
    glColor3f(0.55, 0.55, 0.58); glPushMatrix(); gluSphere(quad_sphere, 22, 24, 24); glPopMatrix()
    glPushMatrix(); glTranslatef(0, 5, 0); glRotatef(-12.0 + cannon_pitch, 1, 0, 0)
    glColor3f(0.7, 0.7, 0.72); glPushMatrix(); glRotatef(-90, 1, 0, 0); gluCylinder(quad_cylinder, 18, 12, 160, 24, 1); glPopMatrix()
    glColor3f(0.4, 0.4, 0.42); glPushMatrix(); glTranslatef(0, 150, 0); glRotatef(-90, 1, 0, 0); gluCylinder(quad_cylinder, 20, 20, 20, 24, 1); glPopMatrix()
    glColor3f(0.6, 0.6, 0.6)
    glPushMatrix(); glTranslatef(22, 0, 0); glRotatef(-90, 1, 0, 0); gluCylinder(quad_cylinder, 3, 3, 150, 8, 1); glPopMatrix()
    glPushMatrix(); glTranslatef(-22, 0, 0); glRotatef(-90, 1, 0, 0); gluCylinder(quad_cylinder, 3, 3, 150, 8, 1); glPopMatrix()
    glPopMatrix(); glPopMatrix(); glPopMatrix()


def draw_meteor(dt):
    global meteor, lives, game_over, consecutive_hits
    if not meteor: return
    if meteor["hit_timer"] > 0: meteor["hit_timer"] -= dt
    glPushMatrix(); glTranslatef(meteor["x"], meteor["y"], meteor["z"])
    if meteor["hit_timer"] > 0:
        glColor3f(1.0, 1.0, 1.0)
    else:
        glColor3f(0.9, 0.4, 0.1)
    gluSphere(quad_sphere, meteor["size"], 20, 20)
    glPopMatrix()
    meteor_tail.append((meteor["x"], meteor["y"], meteor["z"]))
    if len(meteor_tail) > 14: meteor_tail.pop(0)
    fade = 1.0
    for tx, ty, tz in reversed(meteor_tail):
        glPushMatrix(); glColor3f(1.0 * fade, 0.4 * fade, 0.0); glTranslatef(tx,ty,tz)
        gluSphere(quad_sphere, max(2.0, 8.0 * fade), 8, 8); glPopMatrix(); fade -= 0.07
    meteor["z"] -= meteor_speed
    if meteor["z"] < 0.0:
        if cheat_timers["infinite_lives"] <= 0: lives -= 1
        consecutive_hits = 0
        if lives <= 0 and cheat_timers["infinite_lives"] <= 0: game_over = True
        else: new_meteor()


def draw_bullets():
    for b in bullets:
        glPushMatrix(); glTranslatef(b["x"], b["y"], b["z"])
        glColor3f(1.0, 0.2, 0.2); gluSphere(quad_sphere, 8, 12, 12)
        glPopMatrix()



def fire_bullet(now):   # game main logic
    global bullets, _last_fire_time
    if not is_firing or (now - _last_fire_time) < FIRE_INTERVAL: return
    _last_fire_time = now
    if cheat_timers["multi_shot"] > 0:
        for angle in [-15, -7.5, 0, 7.5, 15]:
            _, fwd = muzzle_world_and_forward(); rot_fwd = rotate_z(fwd, angle)
            sx,sy,sz = add3(muzzle_world_and_forward()[0], mul3(rot_fwd, 5.0))
            vx,vy,vz = mul3(rot_fwd, BULLET_SPEED)
            bullets.append({"x":sx,"y":sy,"z":sz,"vx":vx,"vy":vy,"vz":vz,"ttl":BULLET_TTL})
    else:
        (mx,my,mz), fwd = muzzle_world_and_forward()
        sx,sy,sz = mx+fwd[0]*5, my+fwd[1]*5, mz+fwd[2]*5
        vx,vy,vz = fwd[0]*BULLET_SPEED, fwd[1]*BULLET_SPEED, fwd[2]*BULLET_SPEED
        bullets.append({"x":sx,"y":sy,"z":sz,"vx":vx,"vy":vy,"vz":vz,"ttl":BULLET_TTL})


def update_bullets(dt):
    global bullets; alive = []
    for b in bullets:
        b["x"] += b["vx"]*dt*100; b["y"] += b["vy"]*dt*100; b["z"] += b["vz"]*dt*100
        b["ttl"] -= dt
        if b["ttl"] > 0 and -GRID_LENGTH <= b["x"] <= GRID_LENGTH and -GRID_LENGTH <= b["y"] <= GRID_LENGTH and 0 <= b["z"] <= 1200:
            alive.append(b)
    bullets = alive


def check_collisions():
    global bullets, score, meteor, consecutive_hits, cheat_mode_ready, can_activate_cheat, is_recharge_period
    if not meteor: return
    surviving_bullets = []
    for b in bullets:
        dist_sq = (b["x"] - meteor["x"])**2 + (b["y"] - meteor["y"])**2 + (b["z"] - meteor["z"])**2
        radii_sum_sq = (8 + meteor["size"])**2
        if dist_sq < radii_sum_sq:
            meteor["health"] -= 1
            meteor["hit_timer"] = 0.1
            if meteor["health"] <= 0:
                score += 1
                
                if score >= 5 and not can_activate_cheat:
                    can_activate_cheat = True
                    cheat_mode_ready = True
                
                if is_recharge_period and not cheat_mode_ready:
                    consecutive_hits += 1
                    if consecutive_hits >= 3:
                        cheat_mode_ready = True
                        is_recharge_period = False
                        consecutive_hits = 0

                new_meteor()
        else:
            surviving_bullets.append(b)
    bullets = surviving_bullets



def keyboardListener(key, x, y):  #input dicchi
    global cheat_mode_ready, camera_distance, camera_angle, can_activate_cheat
    global cheat_activation_message, cheat_activation_message_timer, is_recharge_period
    try:
        key_char = key.decode('utf-8').lower()
    except (UnicodeDecodeError, AttributeError): return

    if game_over:
        if key_char == 'r': reset_game()
        return

    if key_char in ['b', 'v', 'c']:
        if cheat_mode_ready:
            if key_char == 'b': cheat_timers["multi_shot"] = 10.0
            elif key_char == 'v': cheat_timers["slow_mo"] = 10.0; new_meteor()
            elif key_char == 'c': cheat_timers["infinite_lives"] = 10.0
            cheat_mode_ready = False
        elif can_activate_cheat:
            message = "Hit 3 meteors to reactivate cheat!" if is_recharge_period else "Cheat not ready!"
            cheat_activation_message = message
            cheat_activation_message_timer = 3.0
    
    if key_char == 'w': camera_distance = max(CAM_DIST_MIN, camera_distance - 20)
    elif key_char == 's': camera_distance = min(CAM_DIST_MAX, camera_distance + 20)
    elif key_char == 'a': camera_angle -= 3.0
    elif key_char == 'd': camera_angle += 3.0


def specialKeyListener(key, x, y):
    global cannon_yaw, cannon_pitch
    if game_over: return
    if key == GLUT_KEY_LEFT: cannon_yaw += YAW_STEP
    elif key == GLUT_KEY_RIGHT: cannon_yaw -= YAW_STEP
    elif key == GLUT_KEY_UP: cannon_pitch = clamp(cannon_pitch + PITCH_STEP, PITCH_MIN, PITCH_MAX)
    elif key == GLUT_KEY_DOWN: cannon_pitch = clamp(cannon_pitch - PITCH_STEP, PITCH_MIN, PITCH_MAX)
    glutPostRedisplay()


def mouseListener(button, state, x, y):
    global is_firing, _last_fire_time
    if game_over: return
    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            is_firing = True
            _last_fire_time = 0
        elif state == GLUT_UP:
            is_firing = False


def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(75.0, float(WIN_W)/WIN_H, 0.1, 2000.0); glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    cam_x = camera_distance * math.sin(deg2rad(camera_angle))
    cam_y = camera_distance * math.cos(deg2rad(camera_angle))
    gluLookAt(cam_x, cam_y, 400, 0, 0, 150, 0, 0, 1)


def idle():
    global _prev_time, cheat_activation_message_timer, is_cheat_active, is_recharge_period
    if game_over:
        glutPostRedisplay(); return
    now = time.perf_counter(); dt = max(0.0, now - (_prev_time if _prev_time is not None else now))
    _prev_time = now

    if cheat_activation_message_timer > 0:
        cheat_activation_message_timer -= dt
        if cheat_activation_message_timer <= 0:
            cheat_activation_message = ""

    
    was_cheat_active = is_cheat_active  #cheat active naki check
    is_cheat_active = any(timer > 0 for timer in cheat_timers.values())

    
    if was_cheat_active and not is_cheat_active: #chaet use korar por recharge
        is_recharge_period = True
        consecutive_hits = 0

    for cheat in cheat_timers:
        if cheat_timers[cheat] > 0:
            cheat_timers[cheat] -= dt
            if cheat_timers[cheat] <= 0 and cheat == "slow_mo":
                new_meteor()
    
    fire_bullet(now); update_bullets(dt); check_collisions()
    glutPostRedisplay()


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); glViewport(0, 0, WIN_W, WIN_H); setupCamera()
    draw_starry_sky()
    glBegin(GL_QUADS); 
    glColor3f(0.1, 0.1, 0.15); glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0); glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glColor3f(0.05, 0.05, 0.07); glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0); glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glEnd()
    if not game_over:
        draw_meteor(time.perf_counter() - _prev_time if _prev_time else 0)
        draw_bullets(); draw_cannon()
    
    y_offset = WIN_H - 30
    draw_text(10, y_offset, f"Score: {score}"); y_offset -= 30
    lives_text = "Infinite" if cheat_timers["infinite_lives"] > 0 else str(lives)
    draw_text(10, y_offset, f"Lives: {lives_text}"); y_offset -= 30
    if meteor.get("is_boss") and not game_over:
        draw_text(10, y_offset, f"BOSS Health: {meteor.get('health', 0)}"); y_offset -= 30

    if game_over:
        draw_text(WIN_W/2-120, WIN_H/2+20, "GAME OVER", font=GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(WIN_W/2-120, WIN_H/2-20, "Press 'R' to Restart", font=GLUT_BITMAP_HELVETICA_18)
    
    if cheat_mode_ready:
        draw_text(10, y_offset, "CHEAT READY! (B, C, or V)"); y_offset -= 30
    elif is_recharge_period:
        draw_text(10, y_offset, f"Hit {3 - consecutive_hits} more to reactivate cheat!"); y_offset -= 30
    elif cheat_activation_message_timer > 0:
        draw_text(10, y_offset, cheat_activation_message); y_offset -= 30
        
    if cheat_timers["multi_shot"] > 0:
        draw_text(10, y_offset, f"Multi-Shot: {cheat_timers['multi_shot']:.1f}s"); y_offset -= 30
    if cheat_timers["slow_mo"] > 0:
        draw_text(10, y_offset, f"Slow-Mo: {cheat_timers['slow_mo']:.1f}s"); y_offset -= 30
    if cheat_timers["infinite_lives"] > 0:
        draw_text(10, y_offset, f"Infinite Lives: {cheat_timers['infinite_lives']:.1f}s")
    
    glutSwapBuffers()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H); glutInitWindowPosition(50, 50)
    glutCreateWindow(b"3D Sky Defender"); init()
    glutDisplayFunc(showScreen); glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener); glutMouseFunc(mouseListener)
    glutIdleFunc(idle); glutMainLoop()


if __name__ == "__main__":
    main()
