import pygame
import random
import cv2
import numpy as np
import math
import os
import mediapipe as mp
from gtts import gTTS

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FOOD_COLOR = (220, 200, 100)
FISH_SIZE = 40
FOOD_SIZE = 5
SHOW_CAMERA_FEED = True

if not os.path.exists("audio_cache"):
    os.makedirs("audio_cache")

# --- Asset Loading ---
def load_image(name, size=None):
    if not os.path.exists(name):
        print(f"\n--- FATAL ERROR ---")
        print(f"Image file not found at: '{name}'")
        print(f"Please make sure all image files are in the same folder as your script.")
        print(f"-------------------\n")
        raise SystemExit()
    
    try:
        image = pygame.image.load(name).convert_alpha()
        if size:
            image = pygame.transform.scale(image, size)
        return image
    except pygame.error as e:
        print(f"Cannot load image: {name}")
        raise SystemExit(e)

# --- Text-to-Speech Function ---
def speak(text, lang='en'):
    if pygame.mixer.music.get_busy():
        return
    try:
        filename = os.path.join("audio_cache", f"{abs(hash(text))}.mp3")
        if not os.path.exists(filename):
            print(f"Internet required: Generating new audio for '{text}'...")
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(filename)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"--- TTS ERROR ---")
        print(f"Could not process text-to-speech for text: '{text}'")
        print(f"Error details: {e}")
        print(f"-----------------")

# --- Procedural Soil Texture ---
def create_soil_texture(width, height):
    soil_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    soil_surface.fill((94, 69, 45, 180)) 
    for _ in range(500): 
        pos = (random.randint(0, width), random.randint(0, height))
        radius = random.randint(2, 6)
        color = random.choice([(115, 84, 54), (82, 60, 40), (138, 107, 80), (70, 70, 70)])
        pygame.draw.circle(soil_surface, color, pos, radius)
    return soil_surface

# --- Classes ---
class Food:
    def __init__(self, x, y): self.x,self.y,self.sink_speed = x,y,0.5
    def update(self): self.y += self.sink_speed; return self.y <= SCREEN_HEIGHT+FOOD_SIZE
    def draw(self, screen): pygame.draw.circle(screen, FOOD_COLOR, (int(self.x),int(self.y)), FOOD_SIZE)

class Bubble:
    def __init__(self):
        self.x=random.randint(0,SCREEN_WIDTH); self.y=random.randint(SCREEN_HEIGHT,SCREEN_HEIGHT+100)
        self.radius=random.randint(5, 15); self.speed=random.uniform(0.5,2.0); self.color=(200,220,255)
    def update(self): self.y-=self.speed; return self.y > -self.radius
    def draw(self, screen): pygame.draw.circle(screen,self.color,(int(self.x),int(self.y)),self.radius, 1)

class Plant:
    def __init__(self, x, y, image):
        self.image_original = image
        self.image_flipped = pygame.transform.flip(self.image_original, True, False)
        self.is_flipped = False
        self.current_image = self.image_original
        self.rect = self.current_image.get_rect(midbottom=(x, y))
        self.flip_interval = random.randint(120, 300) 
        self.flip_timer = self.flip_interval
    def update(self):
        self.flip_timer -= 1
        if self.flip_timer <= 0:
            self.is_flipped = not self.is_flipped
            if self.is_flipped: self.current_image = self.image_flipped
            else: self.current_image = self.image_original
            self.flip_timer = self.flip_interval
    def draw(self, screen): screen.blit(self.current_image, self.rect)

class Fish:
    def __init__(self, image):
        self.original_image = image
        self.image = image
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        self.position = pygame.math.Vector2(self.rect.center)
        self.velocity = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * 2
        self.acceleration = pygame.math.Vector2()
        
        self.max_speed = 4.5
        self.max_force = 0.15
        self.panic_speed_multiplier = 2.5
        self.panic_force_multiplier = 5.0
        self.wander_angle = 0
        self.facing_left = False
        self.max_stomach = 100
        self.stomach = self.max_stomach
        self.hunger_rate = 30 / 3600 
        self.hunger_threshold = 70
        self.food_value = 50
        self.is_currently_hungry = False
        self.status_text = ""
        self.status_text_timer = 0
        
        self.is_spinning = False
        self.spin_angle = 0
        self.spin_total_rotation = 0
        self.spin_target_rotation = 0
        self.spin_speed = 30
        self.random_spin_timer = random.randint(300, 900)

        self.is_dancing = False
        self.dance_timer = 0
        self.dance_anchor_y = 0

    def start_dancing(self, duration_seconds, song_channel, dance_song):
        if not self.is_dancing and not self.is_spinning:
            self.is_dancing = True
            self.dance_timer = duration_seconds * 60
            self.velocity = pygame.math.Vector2(0, 0)
            self.dance_anchor_y = self.position.y
            song_channel.play(dance_song, maxtime=(duration_seconds * 1000) - 500)

    def perform_dance(self):
        offset = math.sin(self.dance_timer * 0.1) * 15
        self.position.y = self.dance_anchor_y + offset
    
    def apply_force(self, force):
        self.acceleration += force

    def seek(self, target_pos, speed):
        desired = (pygame.math.Vector2(target_pos) - self.position).normalize() * speed
        steering = desired - self.velocity
        if steering.length() > self.max_force:
            steering.scale_to_length(self.max_force)
        return steering

    def flee(self, target_pos, speed):
        desired = (self.position - pygame.math.Vector2(target_pos)).normalize() * speed
        steering = desired - self.velocity
        if steering.length() > self.max_force:
            steering.scale_to_length(self.max_force)
        return steering

    def wander(self, speed):
        circle_center = self.velocity.normalize() * 75
        self.wander_angle += random.uniform(-0.4, 0.4)
        displacement = pygame.math.Vector2(math.cos(self.wander_angle), math.sin(self.wander_angle)) * 30
        wander_target = self.position + circle_center + displacement
        return self.seek(wander_target, speed)

    def find_nearest_food(self, food_list):
        if not food_list: return None
        return min(food_list, key=lambda food: self.position.distance_to((food.x, food.y)))

    # MODIFIED: Update signature to accept dance_channel for interruption
    def update(self, food_list, hand_pos=None, roast_quotes=[], taunt_quotes=[], dance_channel=None):
        flee_distance = 150
        is_hungry = self.stomach < self.hunger_threshold
        
        # MODIFIED: Fleeing now interrupts dancing
        if self.is_dancing:
            should_interrupt = not is_hungry and hand_pos and self.position.distance_to(hand_pos) < flee_distance
            if should_interrupt:
                self.is_dancing = False
                if dance_channel:
                    dance_channel.stop()
            else:
                self.perform_dance()
                self.dance_timer -= 1
                if self.dance_timer <= 0:
                    self.is_dancing = False
                    self.position.y = self.dance_anchor_y
                    self.velocity = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * 2
                self.rect.center = self.position
                return

        if self.is_spinning:
            self.spin_angle += self.spin_speed
            self.spin_total_rotation += self.spin_speed
            if self.spin_total_rotation >= self.spin_target_rotation:
                self.is_spinning = False; self.spin_angle = 0; self.spin_total_rotation = 0
                self.velocity = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize() * self.max_speed / 2
            return

        if self.status_text_timer > 0: self.status_text_timer -= 1
        else: self.status_text = ""
        self.stomach = max(0, self.stomach - self.hunger_rate)

        if is_hungry and not self.is_currently_hungry:
            self.status_text = "I'm hungry!"; self.status_text_timer = 180; self.is_currently_hungry = True; speak(self.status_text, 'en')
        elif not is_hungry and self.is_currently_hungry:
            self.status_text = "Yum! I'm full."; self.status_text_timer = 180; self.is_currently_hungry = False; speak(self.status_text, 'en')
        
        taunt_distance = 300
        is_fleeing = False
        current_max_speed = self.max_speed
        
        steering_force = pygame.math.Vector2()
        effective_force = self.max_force

        if not is_hungry and hand_pos and self.position.distance_to(hand_pos) < flee_distance:
            is_fleeing = True
            distance = self.position.distance_to(hand_pos)
            urgency = 1.0 - (distance / flee_distance) 
            current_max_speed = self.max_speed * (1 + self.panic_speed_multiplier * urgency)
            effective_force = self.max_force * (1 + self.panic_force_multiplier * urgency)
            steering_force = self.flee(hand_pos, current_max_speed)
        
        elif is_hungry:
            nearest_food = self.find_nearest_food(food_list)
            if nearest_food:
                steering_force = self.seek((nearest_food.x, nearest_food.y), 3.5)
                if self.position.distance_to((nearest_food.x, nearest_food.y)) < (self.rect.width / 4):
                    food_list.remove(nearest_food); self.stomach = min(self.max_stomach, self.stomach + self.food_value)
            else:
                steering_force = self.wander(2.0)
        else:
            steering_force = self.wander(1.5)
            if hand_pos and self.status_text_timer <= 0:
                if flee_distance <= self.position.distance_to(hand_pos) < taunt_distance:
                    quote = random.choice(taunt_quotes); self.status_text = quote; self.status_text_timer = 180; speak(quote, 'en')
            
            self.random_spin_timer -= 1
            if self.random_spin_timer <= 0:
                self.is_spinning = True; self.spin_target_rotation = 360; self.velocity = pygame.math.Vector2(0,0)
                self.random_spin_timer = random.randint(300, 900)
        
        if steering_force.length() > effective_force:
            steering_force.scale_to_length(effective_force)
        self.apply_force(steering_force)

        self.velocity += self.acceleration
        if self.velocity.length() > current_max_speed:
            self.velocity.scale_to_length(current_max_speed)
        self.position += self.velocity
        self.acceleration *= 0
        self.rect.center = self.position

        def trigger_panic_spin():
            if not self.is_spinning:
                self.is_spinning=True; self.velocity = pygame.math.Vector2(0,0)
                self.spin_target_rotation = 720
                if roast_quotes: 
                    quote = random.choice(roast_quotes); self.status_text = quote; self.status_text_timer = 180; speak(quote, 'en')
        
        if self.rect.left < 0:
            self.rect.left = 0; self.velocity.x *= -1
            if is_fleeing: trigger_panic_spin()
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH; self.velocity.x *= -1
            if is_fleeing: trigger_panic_spin()
        if self.rect.top < 0:
            self.rect.top = 0; self.velocity.y *= -1
            if is_fleeing: trigger_panic_spin()
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT; self.velocity.y *= -1
            if is_fleeing: trigger_panic_spin()

        if not self.is_spinning:
            if self.velocity.x < 0 and not self.facing_left:
                self.facing_left = True; self.image = pygame.transform.flip(self.original_image, True, False)
            elif self.velocity.x > 0 and self.facing_left:
                self.facing_left = False; self.image = self.original_image

    def draw(self, screen):
        if self.is_dancing:
            angle = math.sin(self.dance_timer * 0.4) * 15
            # MODIFIED: Changed -90 to 90 to make the fish face upwards
            rotated_image = pygame.transform.rotozoom(self.original_image, 90 + angle, 1)
            new_rect = rotated_image.get_rect(center=self.rect.center)
            screen.blit(rotated_image, new_rect)
        elif self.is_spinning:
            base_image = self.original_image if not self.facing_left else pygame.transform.flip(self.original_image, True, False)
            rotated_image = pygame.transform.rotozoom(base_image, -self.spin_angle, 1)
            new_rect = rotated_image.get_rect(center=self.rect.center)
            screen.blit(rotated_image, new_rect)
        else:
            screen.blit(self.image, self.rect)


# --- Main Program ---
def main():
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.set_num_channels(8)
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("AI Fish Tank")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    
    fish_img = load_image("fish.png", (FISH_SIZE*2, FISH_SIZE))
    plant_img = load_image("plant.png", size=(150, 200))
    tank_bg = load_image("fish_tank.jpg", (SCREEN_WIDTH, SCREEN_HEIGHT))
    hook_img = load_image("hook.png", size=(40, 60))

    try:
        bubble_sound = pygame.mixer.Sound("bubbling.mp3")
        bubble_sound.set_volume(0.2)
        bubble_sound.play(loops=-1)
    except pygame.error:
        print("\n--- WARNING: 'bubbling.mp3' not found. No background sound. ---\n")
        bubble_sound = None
        
    try:
        dance_song = pygame.mixer.Sound("dance_song.mp3")
        dance_song.set_volume(0.5)
    except pygame.error:
        print("\n--- WARNING: 'dance_song.mp3' not found. Dance feature will have no music. ---\n")
        dance_song = None
        
    dance_channel = pygame.mixer.Channel(1)

    roast_quotes = [
        "What a farce this is, Saji!", "This whole thing is a flop.", "Okay, thank you!"
    ]
    taunt_quotes = [
        "You can't just say that, dude. I need time.",
        "Get lost, son Dinesha...",
        "We'll settle this at the competition."
    ]
    speak_quote = "What is it, dude? Showing attitude?"
    
    soil_texture = create_soil_texture(SCREEN_WIDTH, 80)

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils 
    hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): print("Error: Cannot open webcam."); return

    my_fish = Fish(fish_img)
    food_list, bubble_list = [], []
    plant_list = [Plant(150, SCREEN_HEIGHT, plant_img), Plant(650, SCREEN_HEIGHT, plant_img)]
    
    running = True
    while running:
        success, frame = cap.read()
        if not success: break
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        hand_pos = None
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                h,w,_ = frame.shape
                cx,cy = int(hand_landmarks.landmark[8].x*w), int(hand_landmarks.landmark[8].y*h)
                hand_pos = (int(cx*(SCREEN_WIDTH/w)), int(cy*(SCREEN_HEIGHT/h)))
                
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    food_list.append(Food(random.randint(0, SCREEN_WIDTH), 0))
                if event.key == pygame.K_s:
                    my_fish.status_text = speak_quote; my_fish.status_text_timer = 180
                    speak(speak_quote, 'en')
                if event.key == pygame.K_d:
                    if dance_song:
                        my_fish.start_dancing(15, dance_channel, dance_song)

        if random.randint(1, 20) == 1:
            bubble_list.append(Bubble())
        
        # MODIFIED: Pass the dance_channel to the update function
        my_fish.update(food_list, hand_pos, roast_quotes=roast_quotes, taunt_quotes=taunt_quotes, dance_channel=dance_channel)
        
        food_list[:] = [food for food in food_list if food.update()]
        bubble_list[:] = [b for b in bubble_list if b.update()]
        for plant in plant_list: plant.update()

        screen.blit(tank_bg, (0, 0))
        screen.blit(soil_texture, (0, SCREEN_HEIGHT - 80))
        for item in plant_list + bubble_list: item.draw(screen)
        for food in food_list: food.draw(screen)
        my_fish.draw(screen)

        if my_fish.status_text:
            text_surface = font.render(my_fish.status_text, True, (255,255,255))
            text_rect = text_surface.get_rect()
            padding = 10
            pointer_height = 10
            bubble_body_rect = text_rect.inflate(padding * 2, padding * 2)
            bubble_surface = pygame.Surface((bubble_body_rect.width, bubble_body_rect.height + pointer_height), pygame.SRCALPHA)
            bubble_color = (0, 0, 0, 170)
            pygame.draw.rect(bubble_surface, bubble_color, (0, 0, bubble_body_rect.width, bubble_body_rect.height), border_radius=15)
            p_mid = bubble_body_rect.centerx
            p_top = bubble_body_rect.bottom - 1
            p_bottom = bubble_body_rect.height + pointer_height
            pygame.draw.polygon(bubble_surface, bubble_color, [(p_mid - 10, p_top), (p_mid + 10, p_top), (p_mid, p_bottom)])
            bubble_full_rect = bubble_surface.get_rect()
            bubble_full_rect.midbottom = (my_fish.rect.centerx, my_fish.rect.top)
            text_rect.center = (bubble_full_rect.centerx, bubble_full_rect.centery - pointer_height / 2)
            screen.blit(bubble_surface, bubble_full_rect)
            screen.blit(text_surface, text_rect)

        if hand_pos:
            hook_rect = hook_img.get_rect(midtop=hand_pos)
            screen.blit(hook_img, hook_rect)
        
        hunger_text=font.render("Hunger",True,(255,255,255))
        screen.blit(hunger_text,(SCREEN_WIDTH-120,10))
        pygame.draw.rect(screen,(50,50,50),[SCREEN_WIDTH-120,30,100,15])
        hunger_percent=my_fish.stomach/my_fish.max_stomach
        bar_color=(255,60,60) if my_fish.stomach<my_fish.hunger_threshold else (60,200,60)
        pygame.draw.rect(screen,bar_color,[SCREEN_WIDTH-120,30,100*hunger_percent,15])
        
        if SHOW_CAMERA_FEED:
            frame_for_display=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            frame_small=cv2.resize(frame_for_display,(160,120))
            frame_surface=pygame.surfarray.make_surface(np.rot90(frame_small))
            screen.blit(frame_surface, (10,SCREEN_HEIGHT-130))
            
        fps_text=font.render(f"FPS: {int(clock.get_fps())}",True,(255,255,255))
        screen.blit(fps_text,(10,10))

        pygame.display.flip()
        clock.tick(60)
        
    hands.close()
    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()