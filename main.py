# Standard library imports
import os
import json
import random
import logging
from enum import Enum
import math
from statistics import mode

# Third-party imports
import tkinter as tk
from tkinter import ttk, messagebox, Scale
import pygame
from PIL import Image, ImageTk

# Constants
GRID_SIZE = 3
GAME_DURATION = 30
VOLUME_MIN = 0
VOLUME_MAX = 100

# Enums
class DifficultyLevel(Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class GameMode(Enum):
    CLASSIC = "Classic"
    SILVER = "Silver"

# Game settings
MOLE_TIMES = {
    DifficultyLevel.EASY: 1500,
    DifficultyLevel.MEDIUM: 1000,
    DifficultyLevel.HARD: 750
}

class BaseGameMode:
    def __init__(self, root, settings, sound_manager, main_frame):
        self.root = root
        self.settings = settings
        self.sound_manager = sound_manager
        self.main_frame = main_frame  # Store the existing frame
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.mole_task = None
        self.timer_task = None

    def setup_game(self):
        """Initialize game components"""
        raise NotImplementedError

    def start_game(self):
        """Start the game"""
        raise NotImplementedError

    def pause_game(self):
        """Pause the game"""
        raise NotImplementedError

    def resume_game(self):
        """Resume the game"""
        raise NotImplementedError

    def end_game(self):
        """End the game"""
        raise NotImplementedError

    def reset_game(self):
        """Reset the game state"""
        raise NotImplementedError

    def update_timer(self):
        """Update game timer"""
        raise NotImplementedError

class ClassicMode(BaseGameMode):
    def __init__(self, root, settings, sound_manager, main_frame):
        super().__init__(root, settings, sound_manager, main_frame)
        self.difficulty = tk.StringVar(value=settings['last_difficulty'])
        self.buttons = []
        self.mole_button = None
        self.setup_game()

    def load_images(self):
        """Load game images"""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        image_files = {
            'background': 'background.png',
            'button': 'button.png',
            'mole': 'mole.png'
        }
        
        for name, file in image_files.items():
            try:
                image = Image.open(os.path.join(self.current_dir, 'assets', file))
                if name in ['mole', 'button']:
                    image = image.resize((100, 100), Image.LANCZOS)  # Increased size
                setattr(self, f'{name}_image', ImageTk.PhotoImage(image))
            except Exception as e:
                logging.error(f"Error loading {name} image: {e}")
                setattr(self, f'{name}_image', None)

        # Load animation images with larger size
        self.mole_appear_images = []
        self.mole_disappear_images = []
        for i in range(1, 4):
            try:
                appear = Image.open(os.path.join(self.current_dir, f'assets/mole_appear_{i}.png'))
                disappear = Image.open(os.path.join(self.current_dir, f'assets/mole_disappear_{i}.png'))
                appear = appear.resize((100, 100), Image.LANCZOS)  # Increased size
                disappear = disappear.resize((100, 100), Image.LANCZOS)  # Increased size
                self.mole_appear_images.append(ImageTk.PhotoImage(appear))
                self.mole_disappear_images.append(ImageTk.PhotoImage(disappear))
            except Exception as e:
                logging.error(f"Error loading animation images: {e}")

    def create_widgets(self):
        """Create responsive game widgets"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        min_width = 320  # Minimum width for mobile
        
        # Calculate responsive sizes
        label_size = max(12, min(24, screen_width // 40))
        grid_padding = min(10, screen_width // 50)
        
        # Score frame with responsive text
        self.score_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.score_frame.pack(pady=grid_padding * 2)

        label_style = {
            'font': ('SF Pro Display', label_size),
            'bg': '#F2F2F7',
            'fg': '#000000'
        }

        # Use shorter text on mobile
        score_text = f'Score: {self.score}'
        high_score_text = f'{"HS" if screen_width < min_width else "High Score"}: {self.settings["high_scores"][self.difficulty.get()]}'

        self.score_label = tk.Label(self.score_frame, text=score_text, **label_style)
        self.score_label.pack(side=tk.LEFT, padx=grid_padding)

        self.high_score_label = tk.Label(self.score_frame, text=high_score_text, **label_style)
        self.high_score_label.pack(side=tk.LEFT, padx=grid_padding)

        # Timer label
        self.timer_label = tk.Label(self.main_frame, text=f'Time Left: {self.time_left}', **label_style)
        self.timer_label.pack(pady=grid_padding * 2)

        # Game grid with responsive sizing
        self.grid_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.grid_frame.pack(pady=grid_padding * 2)

        # Calculate button size based on screen width
        button_size = max(60, min(100, screen_width // 6))

        # Create grid of buttons
        self.buttons = []
        for row in range(GRID_SIZE):
            button_row = []
            for col in range(GRID_SIZE):
                btn = tk.Button(
                    self.grid_frame,
                    image=self.button_image,
                    width=button_size,
                    height=button_size,
                    borderwidth=0,
                    highlightthickness=0,
                    command=lambda r=row, c=col: self.hit_mole((r, c))
                )
                btn.grid(row=row, column=col, padx=grid_padding, pady=grid_padding)
                button_row.append(btn)
            self.buttons.append(button_row)

        # Configure grid columns and rows to be uniform
        for i in range(GRID_SIZE):
            self.grid_frame.grid_columnconfigure(i, weight=1)
            self.grid_frame.grid_rowconfigure(i, weight=1)

    def create_controls(self):
        """Create game control buttons with proper sizing"""
        # Difficulty frame remains unchanged
        self.difficulty_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.difficulty_frame.pack(pady=(0, 20))
        
        # Stack controls vertically on narrow screens
        pack_side = tk.TOP if self.root.winfo_screenwidth() < 320 else tk.LEFT
        
        # Difficulty label with responsive font
        if self.root.winfo_screenwidth() < 320:
            difficulty_text = "Difficulty:"
        else:
            difficulty_text = "Difficulty:"
        
        tk.Label(self.difficulty_frame, 
                 text=difficulty_text,
                 bg='#F2F2F7', 
                 fg='#000000',
                 font=('SF Pro Text', 15)).pack(
                     side=pack_side, 
                     padx=(0, 10),
                     pady=10 if pack_side == tk.TOP else 0
                 )
        
        # Difficulty radio buttons
        for level in DifficultyLevel:
            rb = tk.Radiobutton(self.difficulty_frame,
                               text=level.value,
                               variable=self.difficulty,
                               value=level.value,
                               bg='#F2F2F7',
                               font=('SF Pro Text', 15),
                               command=self.update_high_score)
            rb.pack(
                side=pack_side,
                padx=10,
                pady=10 if pack_side == tk.TOP else 0
            )

        # Game controls frame with fixed width container
        self.controls_frame = tk.Frame(self.main_frame, bg='#F2F2F7')
        self.controls_frame.pack(pady=(0, 30))

        # Container for centered buttons
        button_container = tk.Frame(self.controls_frame, bg='#F2F2F7')
        button_container.pack(expand=True)

        button_style = {
            'font': ('SF Pro Text', 15),
            'bg': '#007AFF',
            'fg': 'white',
            'width': 12,  # Increased width
            'height': 2,  # Fixed height
            'bd': 0,
            'borderwidth': 0,
            'highlightthickness': 0,
            'activebackground': '#0051A8'
        }

        # Create buttons with consistent spacing
        self.start_button = tk.Button(button_container, text="Start", 
                                    command=self.start_game, **button_style)
        self.start_button.pack(side=tk.LEFT, padx=15)

        self.pause_button = tk.Button(button_container, text="Pause", 
                                    command=self.pause_game, 
                                    state=tk.DISABLED, **button_style)
        self.pause_button.pack(side=tk.LEFT, padx=15)

        self.reset_button = tk.Button(button_container, text="Reset", 
                                    command=self.reset_game, **button_style)
        self.reset_button.pack(side=tk.LEFT, padx=15)

        # Run button sizing test
        self.root.update_idletasks()  # Ensure widgets are rendered
        self.test_button_sizing()

    def setup_game(self):
        self.load_images()
        self.create_widgets()
        self.create_controls()
        self.setup_confetti_window()

    def start_game(self):
        """Start or restart the game"""
        # Reset game state before starting
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.score_label.config(text=f'Score: {self.score}')
        self.timer_label.config(text=f'Time Left: {self.time_left}')
        
        # Cancel any existing tasks
        if self.timer_task:
            self.root.after_cancel(self.timer_task)
        if self.mole_task:
            self.root.after_cancel(self.mole_task)
        
        # Reset all buttons
        for row in self.buttons:
            for button in row:
                button.config(state='normal', image=self.button_image)
        
        # Start the game
        self.sound_manager.play_sound('start')
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.spawn_mole()
        self.update_timer()

    def pause_game(self):
        """Pause the current game"""
        if not self.paused:
            self.sound_manager.play_sound('pause')
            self.paused = True
            self.pause_button.config(text="Resume", command=self.resume_game)
            if self.timer_task:
                self.root.after_cancel(self.timer_task)
            if self.mole_task:
                self.root.after_cancel(self.mole_task)
        
    def resume_game(self):
        """Resume the paused game"""
        self.paused = False
        self.pause_button.config(text="Pause", command=self.pause_game)
        self.update_timer()
        self.spawn_mole()

    def reset_game(self):
        """Reset the game to initial state"""
        self.score = 0
        self.time_left = GAME_DURATION
        self.paused = False
        self.score_label.config(text=f'Score: {self.score}')
        self.timer_label.config(text=f'Time Left: {self.time_left}')
        
        # Reset buttons
        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled', text="Pause", command=self.pause_game)
        
        # Reset game grid
        for row in self.buttons:
            for button in row:
                button.config(state='normal', image=self.button_image)
        
        # Cancel scheduled tasks
        if self.timer_task:
            self.root.after_cancel(self.timer_task)
        if self.mole_task:
            self.root.after_cancel(self.mole_task)
        self.mole_button = None

    def update_timer(self):
        """Update the game timer"""
        if not self.paused and self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=f'Time Left: {self.time_left}')
            self.timer_task = self.root.after(1000, self.update_timer)
        elif self.time_left <= 0:
            self.end_game()

    def spawn_mole(self):
        """Spawn a new mole at random position"""
        if self.time_left <= 0 or self.paused:
            return

        # Cancel existing mole task
        if self.mole_task:
            self.root.after_cancel(self.mole_task)
            self.mole_task = None

        # Clear all moles
        for row in self.buttons:
            for button in row:
                button.config(image=self.button_image)

        # Choose random position
        i, j = random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)
        self.mole_button = self.buttons[i][j]
        self.animate_mole_appear(self.mole_button, 0)

    def animate_mole_appear(self, button, frame):
        """Animate mole appearing"""
        if frame < len(self.mole_appear_images):
            button.config(image=self.mole_appear_images[frame])
            self.root.after(100, self.animate_mole_appear, button, frame + 1)
        else:
            button.config(image=self.mole_image)
            # Schedule next mole spawn
            mole_time = MOLE_TIMES[DifficultyLevel(self.difficulty.get())]
            self.mole_task = self.root.after(mole_time, self.spawn_mole)

    def animate_mole_disappear(self, button, frame):
        """Animate mole disappearing"""
        if frame < len(self.mole_disappear_images):
            button.config(image=self.mole_disappear_images[frame])
            self.root.after(100, self.animate_mole_disappear, button, frame + 1)
        else:
            button.config(image=self.button_image)
            self.mole_button = None
            self.spawn_mole()

    def hit_mole(self, btn_coords):
        """Handle mole hit attempt"""
        if not self.paused and self.time_left > 0:
            i, j = btn_coords
            clicked_button = self.buttons[i][j]
            if clicked_button == self.mole_button:
                # Prevent multiple hits on the same mole
                self.mole_button = None  # Clear mole_button reference immediately
                
                # Update score and display
                self.score += 1
                self.score_label.config(text=f'Score: {self.score}')
                self.sound_manager.play_sound('hit')
                
                # Cancel any existing mole task
                if self.mole_task:
                    self.root.after_cancel(self.mole_task)
                    self.mole_task = None
                
                # Start disappear animation
                self.animate_mole_disappear(clicked_button, 0)

    def end_game(self):
        """End the current game"""
        self.sound_manager.play_sound('end')
        # Disable all buttons
        for row in self.buttons:
            for button in row:
                button.config(state='disabled')
        self.timer_label.config(text='Time\'s Up!')
        self.pause_button.config(state='disabled')
        self.start_button.config(state='normal')

        # Check for high score with current difficulty
        current_difficulty = self.difficulty.get()
        current_high_score = self.settings['high_scores'].get(current_difficulty, 0)
        
        if self.score > current_high_score:
            print(f"New high score! {self.score} > {current_high_score}")  # Debug print
            self.settings['high_scores'][current_difficulty] = self.score
            self.high_score_label.config(text=f'High Score: {self.score}')
            self.save_settings_to_file()
            
            # Ensure celebration happens
            self.root.after(500, self.celebrate_high_score)
            self.sound_manager.play_sound('celebration')

    def setup_confetti_window(self):
        """Set up the confetti celebration window"""
        self.confetti_window = tk.Toplevel(self.root)
        self.confetti_window.overrideredirect(True)
        self.confetti_window.attributes('-alpha', 0.0)
        self.confetti_window.attributes('-topmost', True)
        
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            transparent_color = 'SystemButtonFace'
        else:
            transparent_color = 'gray'
        
        self.confetti_canvas = tk.Canvas(self.confetti_window, 
                                       bg=transparent_color, 
                                       highlightthickness=0)
        self.confetti_canvas.pack(fill=tk.BOTH, expand=True)

    def update_high_score(self):
        """Update high score display when difficulty changes"""
        current_difficulty = self.difficulty.get()
        self.high_score_label.config(
            text=f'High Score: {self.settings["high_scores"].get(current_difficulty, 0)}'
        )

    def celebrate_high_score(self):
        """Display celebration effects for new high score"""
        print("Celebrating high score!")  # Debug print
        
        # Update confetti window position
        self.confetti_window.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self.confetti_canvas.config(width=self.root.winfo_width(), height=self.root.winfo_height())
        
        # Make confetti window visible
        self.confetti_window.lift()
        self.confetti_window.attributes('-alpha', 1.0)
        
        # Create confetti effect
        for _ in range(200):  # More confetti pieces
            x = random.randint(0, self.root.winfo_width())
            y = self.root.winfo_height()  # Start from bottom
            color = random.choice(['red', 'yellow', 'blue', 'green', 'purple', 'orange'])
            size = random.randint(5, 15)
            angle = random.uniform(-math.pi/2, math.pi/2)  # Full upward spread
            speed = random.uniform(10, 20)  # Increased speed
            
            confetti = self.confetti_canvas.create_oval(x, y, x+size, y+size, fill=color)
            self.animate_confetti(confetti, x, y, angle, speed, 0)
        
        # Hide confetti window after celebration
        self.root.after(10000, lambda: self.confetti_window.attributes('-alpha', 0.0))

    def test_button_sizing(self):
        """Test method to verify button dimensions and layout"""
        logging.info("Testing button sizing...")
        
        # Test button dimensions
        for button_name in ['start_button', 'pause_button', 'reset_button']:
            button = getattr(self, button_name)
            width = button.winfo_width()
            height = button.winfo_height()
            
            logging.info(f"{button_name} dimensions: {width}x{height}")
            
            # Verify minimum touch target size (44x44 pixels)
            assert width >= 44, f"{button_name} width too small: {width}"
            assert height >= 44, f"{button_name} height too small: {height}"

class SilverMode(BaseGameMode):
    def __init__(self, root, settings, sound_manager, main_frame):
        super().__init__(root, settings, sound_manager, main_frame)
        self.level = 1
        self.mole_time = 1500
        self.setup_game()

    def setup_game(self):
        self.load_silver_images()
        self.create_silver_widgets()
        self.create_silver_controls()
        self.setup_confetti_window()

    # ... (continue with Silver Mode implementation)

class SoundManager:
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.initialize_pygame()
        self.load_sounds()

    def initialize_pygame(self):
        try:
            pygame.mixer.init()
        except pygame.error as e:
            logging.warning(f"Pygame mixer initialization failed: {e}")

    def load_sounds(self):
        self.hit_sound = self.load_sound('hit_sound.wav')
        self.start_sound = self.load_sound('start_sound.wav')
        self.pause_sound = self.load_sound('pause_sound.wav')
        self.end_sound = self.load_sound('end_sound.wav')
        self.celebration_sound = self.load_sound('celebration_sound.wav')

    def load_sound(self, filename):
        try:
            return pygame.mixer.Sound(os.path.join(self.current_dir, 'assets', filename))
        except pygame.error as e:
            logging.warning(f"Failed to load sound {filename}: {e}")
            return None

    def play_sound(self, sound_type):
        sound = getattr(self, f"{sound_type}_sound", None)
        if sound:
            pygame.mixer.Sound.play(sound)

class UIManager:
    def __init__(self, root):
        self.root = root
        self.main_frame = tk.Frame(root, bg='#F2F2F7')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def create_main_menu(self, callbacks):
        """Create the main menu UI"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        title_label = tk.Label(self.main_frame, text="Whack-A-Mole", 
                              font=("SF Pro Display", 36), bg='#F2F2F7', fg='#000000')
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

        tk.Button(self.main_frame, text="Classic Mode", 
                 command=lambda: callbacks['classic'](), **button_style).pack(pady=10)
        
        tk.Button(self.main_frame, text="Silver Mode", 
                 command=lambda: callbacks['silver'](), **button_style).pack(pady=10)
        
        tk.Button(self.main_frame, text="Settings", 
                 command=callbacks['settings'], **button_style).pack(pady=10)
        
        tk.Button(self.main_frame, text="Quit", 
                 command=callbacks['quit'], **button_style).pack(pady=10)

    def clear_screen(self):
        """Clear all widgets from the main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

class SettingsManager:
    def __init__(self, current_dir):
        self.current_dir = current_dir
        self.settings = self.load_settings()
        self.settings_window = None

    def load_settings(self):
        settings_path = os.path.join(self.current_dir, 'settings.json')
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

    def save_settings(self):
        settings_path = os.path.join(self.current_dir, 'settings.json')
        with open(settings_path, 'w') as f:
            json.dump(self.settings, f)

class WhackAMoleGame:
    def __init__(self, root):
        self.root = root
        self.root.title('Whack-A-Mole')
        self.root.configure(bg='#F2F2F7')
        
        # Initialize managers
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings_manager = SettingsManager(self.current_dir)
        self.sound_manager = SoundManager()
        self.ui_manager = UIManager(root)
        
        # Initialize game modes
        self.current_mode = None
        self.setup_game()

    def setup_game(self):
        """Initialize the game and show main menu"""
        callbacks = {
            'classic': lambda: self.start_game(GameMode.CLASSIC),
            'silver': lambda: self.start_game(GameMode.SILVER),
            'settings': self.show_settings,
            'quit': self.root.quit
        }
        self.ui_manager.create_main_menu(callbacks)

    def start_game(self, mode):
        """Start a new game in the specified mode"""
        # Clear the UI manager's main frame
        self.ui_manager.clear_screen()
        
        # Create new game mode with existing frame
        if mode == GameMode.CLASSIC:
            self.current_mode = ClassicMode(self.root, 
                                          self.settings_manager.settings,
                                          self.sound_manager,
                                          self.ui_manager.main_frame)
        elif mode == GameMode.SILVER:
            self.current_mode = SilverMode(self.root,
                                         self.settings_manager.settings,
                                         self.sound_manager,
                                         self.ui_manager.main_frame)

    def show_settings(self):
        """Show the settings window"""
        if self.settings_manager.settings_window is not None:
            self.settings_manager.settings_window.lift()
            return
            
        self.settings_manager.settings_window = tk.Toplevel(self.root)
        # ... (implement settings window UI)

# Initialize the game
if __name__ == '__main__':
    root = tk.Tk()
    game = WhackAMoleGame(root)
    root.mainloop()
