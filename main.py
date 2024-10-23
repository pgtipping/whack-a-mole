from statistics import mode
import tkinter as tk
from tkinter import ttk
import random
import pygame
import os
import json
from PIL import Image, ImageTk
import logging
from enum import Enum
import math
from tkinter import messagebox, Scale

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize pygame for sound
try:
    pygame.mixer.init()
except pygame.error as e:
    logging.warning(f"Pygame mixer initialization failed: {e}")

# Load sound effects
hit_sound = pygame.mixer.Sound(os.path.join(current_dir, 'assets', 'hit_sound.wav'))
start_sound = pygame.mixer.Sound(os.path.join(current_dir, 'assets', 'start_sound.wav'))
pause_sound = pygame.mixer.Sound(os.path.join(current_dir, 'assets', 'pause_sound.wav'))
end_sound = pygame.mixer.Sound(os.path.join(current_dir, 'assets', 'end_sound.wav'))

# Game settings
GRID_SIZE = 3
GAME_DURATION = 30

class DifficultyLevel(Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

MOLE_TIMES = {
    DifficultyLevel.EASY: 1500,
    DifficultyLevel.MEDIUM: 1000,
    DifficultyLevel.HARD: 750
}

class GameMode(Enum):
    CLASSIC = "Classic"
    SILVER = "Silver"

# Add these constants after the existing ones
VOLUME_MIN = 0
VOLUME_MAX = 100

class WhackAMoleGame:
    def __init__(self, root):
        self.root = root
        self.root.title('Whack-A-Mole')
        self.root.configure(bg='#F2F2F7')
        self.settings = self.load_settings()
        self.high_scores = self.settings['high_scores']
        
        self.main_frame = tk.Frame(self.root, bg='#F2F2F7')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.sound_volume = tk.IntVar(value=self.settings.get('sound_volume', 50))
        self.background_music = tk.BooleanVar(value=self.settings.get('background_music', True))
        
        # Load background music if file exists
        bg_music_path = os.path.join(current_dir, 'assets', 'background_music.wav')
        if os.path.exists(bg_music_path):
            self.bg_music = pygame.mixer.Sound(bg_music_path)
            self.bg_music_channel = None
        else:
            logging.warning("Background music file not found. Disabling background music.")
            self.bg_music = None
            self.bg_music_channel = None
            self.background_music.set(False)
        
        self.apply_settings()
        self.show_main_menu()
        self.settings_window = None  # Add this line to initialize the settings window reference
        self.timer_task = None

    def show_main_menu(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        title_label = tk.Label(self.main_frame, text="Whack-A-Mole", font=("SF Pro Display", 36), bg='#F2F2F7', fg='#000000')
        title_label.pack(pady=20)

        button_style = {
            'font': ('SF Pro Text', 18),
            'bg': '#007AFF',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 10,
            'width': 15
        }

        classic_button = tk.Button(self.main_frame, text="Classic Mode", command=lambda: self.start_game(GameMode.CLASSIC), **button_style)
        classic_button.pack(pady=10)

        silver_button = tk.Button(self.main_frame, text="Silver Mode", command=lambda: self.start_game(GameMode.SILVER), **button_style)
        silver_button.pack(pady=10)

        settings_button = tk.Button(self.main_frame, text="Settings", command=self.show_settings, **button_style)
        settings_button.pack(pady=10)

        quit_button = tk.Button(self.main_frame, text="Quit", command=self.root.quit, **button_style)
        quit_button.pack(pady=10)

    def show_settings(self):
        if self.settings_window is not None:
            self.settings_window.lift()
            return
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("300x350")
        self.settings_window.configure(bg='#F2F2F7')
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_settings)  # Handle window close event

        tk.Label(self.settings_window, text="Classic Mode Difficulty", font=("SF Pro Display", 16, "bold"), bg='#F2F2F7').pack(pady=10)
        tk.Label(self.settings_window, text="(Does not affect Silver Mode)", font=("SF Pro Display", 12), bg='#F2F2F7', fg='#666666').pack()

        difficulty_frame = tk.Frame(self.settings_window, bg='#F2F2F7')
        difficulty_frame.pack(pady=10)

        difficulties = [DifficultyLevel.EASY.value, DifficultyLevel.MEDIUM.value, DifficultyLevel.HARD.value]
        self.difficulty = tk.StringVar(value=self.settings['last_difficulty'])

        for diff in difficulties:
            tk.Radiobutton(difficulty_frame, text=diff, variable=self.difficulty, value=diff, 
                           bg='#F2F2F7', activebackground='#E5E5EA', font=("SF Pro Text", 14)).pack(side=tk.LEFT)

        tk.Label(self.settings_window, text="Sound Volume", font=("SF Pro Display", 16), bg='#F2F2F7').pack(pady=10)
        volume_scale = Scale(self.settings_window, from_=VOLUME_MIN, to=VOLUME_MAX, orient=tk.HORIZONTAL, 
                             variable=self.sound_volume, bg='#F2F2F7', length=200)
        volume_scale.pack()

        tk.Checkbutton(self.settings_window, text="Background Music", variable=self.background_music, 
                       bg='#F2F2F7', activebackground='#E5E5EA', font=("SF Pro Text", 14)).pack(pady=10)

        tk.Button(self.settings_window, text="Save", command=self.save_settings, 
                  bg='#007AFF', fg='white', font=("SF Pro Text", 14)).pack(pady=20)

    def close_settings(self):
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None

    def save_settings(self):
        self.settings['last_difficulty'] = self.difficulty.get()
        self.settings['sound_volume'] = self.sound_volume.get()
        self.settings['background_music'] = self.background_music.get()
        
        self.save_settings_to_file()
        self.apply_settings()
        
        messagebox.showinfo("Settings", "Settings saved successfully!")
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None

    def save_settings_to_file(self):
        settings_path = os.path.join(current_dir, 'settings.json')
        with open(settings_path, 'w') as f:
            json.dump(self.settings, f)

    def apply_settings(self):
        # Apply volume settings
        volume = self.sound_volume.get() / 100.0  # Convert to range 0-1
        hit_sound.set_volume(volume)
        start_sound.set_volume(volume)
        pause_sound.set_volume(volume)
        end_sound.set_volume(volume)
        
        # Apply background music settings
        if self.background_music.get() and self.bg_music:
            if not self.bg_music_channel:
                self.bg_music_channel = pygame.mixer.Channel(0)
                self.bg_music_channel.play(self.bg_music, loops=-1)
        else:
            if self.bg_music_channel:
                self.bg_music_channel.stop()
                self.bg_music_channel = None

    def load_settings(self):
        settings_path = os.path.join(current_dir, 'settings.json')
        default_settings = {
            'last_difficulty': DifficultyLevel.MEDIUM.value,
            'high_scores': {level.value: 0 for level in DifficultyLevel},
            'sound_volume': 50,
            'background_music': True
        }
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                return json.load(f)
        return default_settings

    def start_game(self, mode):
        self.apply_settings()
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        if mode == GameMode.CLASSIC:
            self.start_classic_mode()
        elif mode == GameMode.SILVER:
            self.start_silver_mode()

    def start_classic_mode(self):
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.difficulty = tk.StringVar(value=self.settings['last_difficulty'])
        self.mole_task = None  # Initialize mole_task
        
        self.load_images()
        self.create_widgets()
        self.create_controls()
        self.setup_confetti_window()

        # Start the game immediately
        self.start_game_classic()

    def start_game_classic(self):
        pygame.mixer.Sound.play(start_sound)
        self.paused = False
        self.pause_button.config(text="Pause", command=self.pause_game)
        self.spawn_mole()
        self.update_timer()

    def start_silver_mode(self):
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.level = 1
        self.mole_time = 1500  # Start with slower moles
        
        self.load_silver_images()
        self.create_silver_widgets()
        self.create_silver_controls()
        self.setup_confetti_window()

        # Start the game immediately
        self.start_silver_game()

    def load_silver_images(self):
        # Load images for the Silver mode
        image_files = {
            'background': 'silver_background.png',
            'hole': 'silver_hole.png',
            'mole': 'silver_mole.png',
            'bonus_mole': 'silver_bonus_mole.png',
            'hit_mole': 'silver_hit_mole.png'
        }
        
        for name, file in image_files.items():
            try:
                image = Image.open(os.path.join(current_dir, 'assets', file))
                setattr(self, f'{name}_image', ImageTk.PhotoImage(image))
                logging.debug(f"{name.capitalize()} image loaded successfully")
            except Exception as e:
                logging.error(f"Error loading {name} image: {e}")
                setattr(self, f'{name}_image', None)

        # Load mole animation frames
        self.mole_frames = []
        for i in range(1, 5):  # Assuming 4 frames for mole animation
            frame = Image.open(os.path.join(current_dir, 'assets', f'silver_mole_frame_{i}.png'))
            self.mole_frames.append(ImageTk.PhotoImage(frame))

    def create_silver_widgets(self):
        # Create widgets for the Silver mode
        self.silver_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.silver_frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas for the game background
        self.game_canvas = tk.Canvas(self.silver_frame, width=400, height=400)
        self.game_canvas.pack()

        # Set the background image
        self.game_canvas.create_image(0, 0, anchor=tk.NW, image=self.background_image)

        # Create holes and moles
        self.holes = []
        self.moles = []
        for i in range(3):
            for j in range(3):
                x = 50 + j * 150
                y = 50 + i * 150
                hole = self.game_canvas.create_image(x, y, image=self.hole_image)
                mole = self.game_canvas.create_image(x, y, image=self.mole_frames[0], state=tk.HIDDEN)
                self.holes.append(hole)
                self.moles.append(mole)

        # Create score and level labels
        self.score_label = tk.Label(self.silver_frame, text="Score: 0", font=("SF Pro Display", 18))
        self.score_label.pack()

        self.level_label = tk.Label(self.silver_frame, text="Level: 1", font=("SF Pro Display", 18))
        self.level_label.pack()

        # Create timer bar
        self.timer_bar = ttk.Progressbar(self.silver_frame, length=300, mode='determinate')
        self.timer_bar.pack(pady=10)

    def create_silver_controls(self):
        # Create controls for the Silver mode
        control_frame = tk.Frame(self.silver_frame, bg='#F2F2F7')
        control_frame.pack(pady=10)

        button_style = {
            'font': ('SF Pro Text', 15),
            'bg': '#007AFF',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 10
        }

        self.start_button = tk.Button(control_frame, text="Start", command=self.start_silver_game, **button_style)
        self.start_button.grid(row=0, column=0, padx=5)

        self.pause_button = tk.Button(control_frame, text="Pause", command=self.pause_silver_game, state=tk.DISABLED, **button_style)
        self.pause_button.grid(row=0, column=1, padx=5)

        self.quit_button = tk.Button(control_frame, text="Quit", command=self.show_main_menu, **button_style)
        self.quit_button.grid(row=0, column=2, padx=5)

    def start_silver_game(self):
        self.score = 0
        self.level = 1
        self.time_left = GAME_DURATION
        self.paused = False
        self.mole_time = 1500

        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)

        self.update_silver_timer()
        self.spawn_silver_mole()

    def pause_silver_game(self):
        if not self.paused:
            self.paused = True
            self.pause_button.config(text="Resume")
        else:
            self.paused = False
            self.pause_button.config(text="Pause")
            self.update_silver_timer()
            self.spawn_silver_mole()

    def update_silver_timer(self):
        if not self.paused and self.time_left > 0:
            self.time_left -= 1
            self.timer_bar['value'] = (self.time_left / GAME_DURATION) * 100
            self.root.after(1000, self.update_silver_timer)
        elif self.time_left <= 0:
            self.end_silver_game()

    def spawn_silver_mole(self):
        if self.paused or self.time_left <= 0:
            return

        # Hide all moles
        for mole in self.moles:
            self.game_canvas.itemconfig(mole, state=tk.HIDDEN)

        # Choose a random mole to show
        mole = random.choice(self.moles)
        self.animate_mole_appear(mole, 0)

        # Schedule next mole spawn
        self.root.after(self.mole_time, self.spawn_silver_mole)

    def animate_mole_appear(self, mole, frame):
        if frame < len(self.mole_frames):
            self.game_canvas.itemconfig(mole, image=self.mole_frames[frame], state=tk.NORMAL)
            self.root.after(50, self.animate_mole_appear, mole, frame + 1)
        else:
            # Make the mole clickable
            self.game_canvas.tag_bind(mole, '<Button-1>', lambda event, m=mole: self.hit_silver_mole(m))

    def hit_silver_mole(self, mole):
        if not self.paused and self.time_left > 0:
            self.score += 1
            self.score_label.config(text=f"Score: {self.score}")
            pygame.mixer.Sound.play(hit_sound)
            self.animate_mole_disappear(mole, len(self.mole_frames) - 1)

            # Check for level up
            if self.score % 10 == 0:
                self.level_up()

    def animate_mole_disappear(self, mole, frame):
        if frame >= 0:
            self.game_canvas.itemconfig(mole, image=self.mole_frames[frame])
            self.root.after(50, self.animate_mole_disappear, mole, frame - 1)
        else:
            self.game_canvas.itemconfig(mole, state=tk.HIDDEN)

    def level_up(self):
        self.level += 1
        self.level_label.config(text=f"Level: {self.level}")
        self.mole_time = max(500, self.mole_time - 100)  # Decrease mole time, minimum 500ms

    def end_silver_game(self):
        # Stop the game
        self.paused = True
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)

        # Check for high score
        if self.score > self.high_scores.get(GameMode.SILVER.value, 0):
            self.high_scores[GameMode.SILVER.value] = self.score
            self.save_settings()
            self.celebrate_high_score()

        # Show game over message
        tk.messagebox.showinfo("Game Over", f"Your score: {self.score}\nLevel reached: {self.level}")

    def load_images(self):
        image_files = {
            'background': 'background.png',
            'button': 'button.png',
            'mole': 'mole.png'
        }
        
        for name, file in image_files.items():
            try:
                image = Image.open(os.path.join(current_dir, 'assets', file))
                if name in ['mole', 'button']:
                    image = image.resize((80, 80), Image.LANCZOS)
                setattr(self, f'{name}_image', ImageTk.PhotoImage(image))
                logging.debug(f"{name.capitalize()} image loaded successfully")
            except Exception as e:
                logging.error(f"Error loading {name} image: {e}")
                setattr(self, f'{name}_image', None)

        # Load animation images
        for anim_type in ['appear', 'disappear']:
            try:
                images = [ImageTk.PhotoImage(Image.open(os.path.join(current_dir, f'assets/mole_{anim_type}_{i}.png'))) for i in range(1, 4)]
                setattr(self, f'mole_{anim_type}_images', images)
                logging.debug(f"Mole {anim_type} images loaded successfully")
            except Exception as e:
                logging.error(f"Error loading mole {anim_type} images: {e}")
                setattr(self, f'mole_{anim_type}_images', [])

    def create_widgets(self):
        # Modify this method to create widgets inside self.main_frame instead of self.root
        self.score_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.score_frame.pack(pady=10)

        label_style = {'font': ('SF Pro Display', 18), 'bg': '#F2F2F7', 'fg': '#000000'}

        self.score_label = tk.Label(self.score_frame, text=f'Score: {self.score}', **label_style)
        self.score_label.pack(side=tk.LEFT, padx=10)

        self.high_score_label = tk.Label(self.score_frame, text=f'High Score: {self.high_scores[self.difficulty.get()]}', **label_style)
        self.high_score_label.pack(side=tk.LEFT, padx=10)

        # Create timer label
        self.timer_label = tk.Label(self.main_frame, text=f'Time Left: {self.time_left}', **label_style)
        self.timer_label.pack(pady=10)

        # Create a frame to hold the grid
        self.grid_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.grid_frame.pack(pady=20, expand=True)

        # Create a grid of buttons
        self.buttons = []
        for i in range(GRID_SIZE):
            row = []
            for j in range(GRID_SIZE):
                button = tk.Button(self.grid_frame, image=self.button_image, borderwidth=0, highlightthickness=0, command=lambda btn=(i, j): self.hit_mole(btn))
                button.grid(row=i, column=j, padx=5, pady=5)
                row.append(button)
            self.buttons.append(row)

    def create_controls(self):
        # Modify this method to create controls inside self.main_frame instead of self.root
        self.controls_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.controls_frame.pack(pady=20)

        button_style = {
            'font': ('SF Pro Text', 15),
            'bg': '#007AFF',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 10,
            'borderwidth': 0,
            'highlightthickness': 0,
            'activebackground': '#0051A8'
        }

        self.start_button = tk.Button(self.controls_frame, text="Start", command=self.start_game, **button_style)
        self.start_button.grid(row=0, column=0, padx=10)

        self.pause_button = tk.Button(self.controls_frame, text="Pause", command=self.pause_game, **button_style)
        self.pause_button.grid(row=0, column=1, padx=10)

        self.reset_button = tk.Button(self.controls_frame, text="Reset", command=self.reset_game, **button_style)
        self.reset_button.grid(row=0, column=2, padx=10)

        # Add difficulty controls
        self.difficulty_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.difficulty_frame.pack(pady=10, before=self.controls_frame)
        
        tk.Label(self.difficulty_frame, text="Difficulty:", bg='#F2F2F7', fg='#000000', font=('SF Pro Text', 15)).pack(side=tk.LEFT, padx=(0, 10))
        
        difficulty_style = {
            'bg': '#F2F2F7',
            'activebackground': '#007AFF',
            'selectcolor': '#007AFF',
            'font': ('SF Pro Text', 13),
            'bd': 0,
            'highlightthickness': 0,
            'padx': 10,
            'pady': 5
        }
        
        for level in DifficultyLevel:
            rb = tk.Radiobutton(self.difficulty_frame, text=level.value, variable=self.difficulty, value=level.value, **difficulty_style)
            rb.pack(side=tk.LEFT)
            rb.bind("<Enter>", lambda e, btn=rb: btn.config(bg='#E5E5EA'))
            rb.bind("<Leave>", lambda e, btn=rb: btn.config(bg='#F2F2F7'))
        
        # Add this line to save settings when difficulty is changed
        self.difficulty.trace('w', lambda *args: self.save_settings())

    def spawn_mole(self):
        if self.time_left <= 0 or self.paused:
            return

        # Clear all moles
        for row in self.buttons:
            for button in row:
                button.config(image=self.button_image)

        # Choose a random button to place the mole
        i, j = random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)
        self.mole_button = self.buttons[i][j]
        self.animate_mole_appear(self.mole_button, 0)

        # Schedule next mole spawn
        mole_time = MOLE_TIMES[DifficultyLevel(self.difficulty.get())]
        self.mole_task = self.root.after(mole_time, self.spawn_mole)

    def animate_mole_appear(self, button, frame):
        if frame < len(self.mole_appear_images):
            button.config(image=self.mole_appear_images[frame])
            self.root.after(100, self.animate_mole_appear, button, frame + 1)
        else:
            button.config(image=self.mole_image)
            # Schedule mole disappearance
            mole_time = MOLE_TIMES[DifficultyLevel(self.difficulty.get())]
            if self.mole_task:
                self.root.after_cancel(self.mole_task)
            self.mole_task = self.root.after(mole_time, self.hide_mole)

    def hit_mole(self, btn_coords):
        if not self.paused and self.time_left > 0:
            i, j = btn_coords
            clicked_button = self.buttons[i][j]
            print(f"Clicked button: ({i}, {j})")
            if clicked_button == self.mole_button:
                print("Mole hit!")
                self.score += 1
                self.score_label.config(text=f'Score: {self.score}')
                pygame.mixer.Sound.play(hit_sound)
                self.animate_mole_disappear(clicked_button, 0)
                if self.mole_task:
                    self.root.after_cancel(self.mole_task)
                self.mole_task = self.root.after(100, self.spawn_mole)
            else:
                print("Missed!")

    def animate_mole_disappear(self, button, frame):
        if frame < len(self.mole_disappear_images):
            button.config(image=self.mole_disappear_images[frame])
            self.root.after(100, self.animate_mole_disappear, button, frame + 1)
        else:
            button.config(image=self.button_image)
            self.root.after(100, self.spawn_mole)

    def hide_mole(self):
        if self.mole_button:
            self.animate_mole_disappear(self.mole_button, 0)
            self.mole_button = None
        else:
            self.root.after(100, self.spawn_mole)

    def update_timer(self):
        if not self.paused and self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=f'Time Left: {self.time_left}')
            if self.timer_task:
                self.root.after_cancel(self.timer_task)
            self.timer_task = self.root.after(1000, self.update_timer)
        elif self.time_left <= 0:
            self.end_game()
        else:
            if self.timer_task:
                self.root.after_cancel(self.timer_task)
            self.timer_task = self.root.after(1000, self.update_timer)

    def start_game(self, mode):
        self.apply_settings()
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        if mode == GameMode.CLASSIC:
            self.start_classic_mode()
        elif mode == GameMode.SILVER:
            self.start_silver_mode()

    def reset_game(self):
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.score_label.config(text=f'Score: {self.score}')
        self.timer_label.config(text=f'Time Left: {self.time_left}')
        current_difficulty = self.difficulty.get()
        self.high_score_label.config(text=f'High Score: {self.high_scores[current_difficulty]}')
        # Re-enable all buttons and reset their images
        for row in self.buttons:
            for button in row:
                button.config(state='normal', image=self.button_image)
        # Cancel any scheduled tasks
        if self.timer_task:
            self.root.after_cancel(self.timer_task)
        if self.mole_task:
            self.root.after_cancel(self.mole_task)
        self.mole_button = None

    def end_game(self):
        pygame.mixer.Sound.play(end_sound)
        # Disable all buttons
        for row in self.buttons:
            for button in row:
                button.config(state='disabled')
        self.timer_label.config(text='Time\'s Up!')

        # Check and save high score
        current_difficulty = self.difficulty.get()
        if self.score > self.high_scores[current_difficulty]:
            self.high_scores[current_difficulty] = self.score
            self.save_settings()
            self.high_score_label.config(text=f'High Score: {self.high_scores[current_difficulty]}')
            print(f"New high score: {self.score}")  # Debug print
            self.root.after(500, self.celebrate_high_score)
        else:
            print("No new high score")  # Debug print

    def pause_game(self):
        pygame.mixer.Sound.play(pause_sound)
        if self.time_left > 0:  # Only pause if the game is running
            self.paused = True
            self.pause_button.config(text="Resume", command=self.resume_game)
            # Cancel scheduled tasks
            if self.timer_task:
                self.root.after_cancel(self.timer_task)
            if self.mole_task:
                self.root.after_cancel(self.mole_task)

    def resume_game(self):
        if self.paused:
            self.paused = False
            self.pause_button.config(text="Pause", command=self.pause_game)
            self.update_timer()
            self.spawn_mole()

    def setup_confetti_window(self):
        self.confetti_window = tk.Toplevel(self.root)
        self.confetti_window.overrideredirect(True)  # Remove window decorations
        self.confetti_window.attributes('-alpha', 0.0)  # Make it fully transparent
        self.confetti_window.attributes('-topmost', True)  # Keep it on top
        
        # Use a valid transparent color (system-specific)
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            transparent_color = 'SystemButtonFace'
        else:
            transparent_color = 'gray'  # fallback for other systems
        
        self.confetti_canvas = tk.Canvas(self.confetti_window, bg=transparent_color, highlightthickness=0)
        self.confetti_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Position the confetti window
        self.root.update_idletasks()  # Ensure root window's size is updated
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.confetti_window.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{x}+{y}")

        # Make the window transparent (platform-specific)
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            self.confetti_window.wm_attributes("-transparentcolor", transparent_color)
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11':
            self.confetti_window.wait_visibility(self.confetti_window)
            self.confetti_window.wm_attributes("-alpha", 0.0)

    def celebrate_high_score(self):
        print("Celebrating high score!")  # Debug print
        # Play celebratory sound
        pygame.mixer.Sound.play(self.celebration_sound)
        
        # Make confetti window visible and update its size
        self.confetti_window.attributes('-alpha', 1.0)
        self.confetti_window.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self.confetti_canvas.config(width=self.root.winfo_width(), height=self.root.winfo_height())
        
        # Create confetti effect
        for _ in range(200):  # Increased number of confetti pieces
            x = random.randint(0, self.root.winfo_width())
            y = self.root.winfo_height()  # Start from bottom
            color = random.choice(['red', 'yellow', 'blue', 'green', 'purple', 'orange'])
            size = random.randint(5, 15)
            angle = random.uniform(-math.pi/2, math.pi/2)  # Full upward spread
            speed = random.uniform(10, 20)  # Increased speed for higher initial trajectory
            
            confetti = self.confetti_canvas.create_oval(x, y, x+size, y+size, fill=color)
            self.animate_confetti(confetti, x, y, angle, speed, 0)
        
        # Hide confetti window after celebration (increased to 10 seconds)
        self.root.after(10000, lambda: self.confetti_window.attributes('-alpha', 0.0))

    def animate_confetti(self, confetti, x, y, angle, speed, frame):
        if frame < 200:  # Increased animation duration
            new_x = x + speed * math.cos(angle) * math.sin(frame * 0.1)  # Added horizontal oscillation
            new_y = y - speed * math.sin(angle) * frame + 0.5 * frame ** 1.5  # Adjusted gravity effect
            
            # Wrap around horizontally
            new_x = new_x % self.root.winfo_width()
            
            # Remove confetti if it goes off the bottom of the screen
            if new_y > self.root.winfo_height():
                self.confetti_canvas.delete(confetti)
                return
            
            self.confetti_canvas.move(confetti, new_x - x, new_y - y)
            self.root.after(20, self.animate_confetti, confetti, new_x, new_y, angle, speed, frame + 1)
        else:
            self.confetti_canvas.delete(confetti)

# Initialize the game
if __name__ == '__main__':
    root = tk.Tk()
    game = WhackAMoleGame(root)
    root.mainloop()

