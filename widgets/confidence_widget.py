#!/usr/bin/env python3
"""
SmartClip CZ - Real-time Confidence Visualization Widget
A streamable widget showing live confidence levels for all detection types
"""

# Set environment variables before any imports
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'

import sys
import json
import time
import threading
from datetime import datetime

# Suppress ALL warnings and errors
import warnings
warnings.filterwarnings("ignore")

# Redirect stderr to suppress locale errors
import io
sys.stderr = io.StringIO()

try:
    # Set locale before tkinter import
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'C')
    except:
        pass

    # Import tkinter with error handling
    import tkinter as tk
    from tkinter import ttk

    # Restore stderr after successful import
    sys.stderr = sys.__stderr__

except ImportError as e:
    sys.stderr = sys.__stderr__
    print(f"Error importing tkinter: {e}")
    print("Please ensure Python tkinter is installed")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    sys.stderr = sys.__stderr__
    print(f"Error during import: {e}")
    print("Trying to continue anyway...")
    try:
        import tkinter as tk
        from tkinter import ttk
    except:
        print("Failed to import tkinter")
        input("Press Enter to exit...")
        sys.exit(1)

class ConfidenceWidget:
    """Real-time confidence visualization widget for streaming"""
    
    def __init__(self):
        try:
            # Create root window with minimal configuration
            self.root = tk.Tk()
            self.root.withdraw()  # Hide initially to avoid flashing

            # Basic window setup
            self.root.title("SmartClip CZ - Live Confidence")
            self.root.geometry("600x400")
            self.root.configure(bg='#1a1a1a')

            # Handle window close event
            self.root.protocol("WM_DELETE_WINDOW", self.close)

            print("Widget window created successfully")

        except Exception as e:
            print(f"Error initializing widget window: {e}")
            # Try with minimal setup
            try:
                self.root = tk.Tk()
                self.root.title("SmartClip CZ")
                print("Minimal widget window created")
            except Exception as e2:
                print(f"Failed to create any window: {e2}")
                raise
        
        # Data storage
        self.max_history = 100  # Keep last 100 data points
        self.data_lock = threading.Lock()
        
        # Detection data
        self.basic_emotion_data = []
        self.opensmile_data = []
        self.vosk_data = []
        self.timestamps = []
        
        # Current values
        self.current_basic = 0.0
        self.current_opensmile = 0.0
        self.current_vosk = 0.0
        self.last_emotion = "neutral"
        self.last_phrase = ""
        
        # Setup UI with error handling
        try:
            self.setup_ui()
            print("UI setup completed")
        except Exception as e:
            print(f"Error setting up UI: {e}")
            # Create minimal UI
            self.setup_minimal_ui()

        # Start data monitoring
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_data, daemon=True)
        self.monitor_thread.start()

        # Start UI updates
        self.update_display()

        # Show window after everything is set up
        self.root.deiconify()

    def setup_minimal_ui(self):
        """Setup minimal UI as fallback"""
        try:
            # Simple label
            label = tk.Label(self.root, text="SmartClip CZ - Live Confidence",
                           font=('Arial', 14), fg='white', bg='#1a1a1a')
            label.pack(pady=20)

            # Basic confidence displays
            self.basic_label = tk.Label(self.root, text="Basic Emotion: 0.00",
                                      font=('Arial', 12), fg='#ff6b6b', bg='#1a1a1a')
            self.basic_label.pack(pady=5)

            self.opensmile_label = tk.Label(self.root, text="OpenSMILE: 0.00",
                                          font=('Arial', 12), fg='#4ecdc4', bg='#1a1a1a')
            self.opensmile_label.pack(pady=5)

            self.vosk_label = tk.Label(self.root, text="Vosk: 0.00",
                                     font=('Arial', 12), fg='#45b7d1', bg='#1a1a1a')
            self.vosk_label.pack(pady=5)

            # Status
            self.emotion_label = tk.Label(self.root, text="Last Emotion: neutral",
                                        font=('Arial', 10), fg='#cccccc', bg='#1a1a1a')
            self.emotion_label.pack(pady=5)

            self.phrase_label = tk.Label(self.root, text="Last Phrase: -",
                                       font=('Arial', 10), fg='#cccccc', bg='#1a1a1a')
            self.phrase_label.pack(pady=5)

            print("Minimal UI created successfully")

        except Exception as e:
            print(f"Error creating minimal UI: {e}")

    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="🎭 SmartClip CZ - Live Confidence",
            font=('Arial', 16, 'bold'),
            fg='#ffffff',
            bg='#1a1a1a'
        )
        title_label.pack(pady=(0, 10))
        
        # Current values frame
        values_frame = tk.Frame(main_frame, bg='#1a1a1a')
        values_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Basic Emotion
        self.basic_label = tk.Label(
            values_frame,
            text="🎭 Basic Emotion: 0.00",
            font=('Arial', 12, 'bold'),
            fg='#ff6b6b',
            bg='#1a1a1a'
        )
        self.basic_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # OpenSMILE
        self.opensmile_label = tk.Label(
            values_frame,
            text="🤖 OpenSMILE: 0.00",
            font=('Arial', 12, 'bold'),
            fg='#4ecdc4',
            bg='#1a1a1a'
        )
        self.opensmile_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Vosk
        self.vosk_label = tk.Label(
            values_frame,
            text="🗣️ Vosk: 0.00",
            font=('Arial', 12, 'bold'),
            fg='#45b7d1',
            bg='#1a1a1a'
        )
        self.vosk_label.pack(side=tk.LEFT)
        
        # Status frame
        status_frame = tk.Frame(main_frame, bg='#1a1a1a')
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Last emotion
        self.emotion_label = tk.Label(
            status_frame,
            text="Last Emotion: neutral",
            font=('Arial', 10),
            fg='#cccccc',
            bg='#1a1a1a'
        )
        self.emotion_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Last phrase
        self.phrase_label = tk.Label(
            status_frame,
            text="Last Phrase: -",
            font=('Arial', 10),
            fg='#cccccc',
            bg='#1a1a1a'
        )
        self.phrase_label.pack(side=tk.LEFT)
        
        # Visualization frame
        viz_frame = tk.Frame(main_frame, bg='#1a1a1a')
        viz_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Progress bars for confidence levels
        progress_frame = tk.Frame(viz_frame, bg='#1a1a1a')
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        # Basic Emotion Progress Bar
        tk.Label(progress_frame, text="🎭 Basic Emotion", font=('Arial', 10, 'bold'),
                fg='#ff6b6b', bg='#1a1a1a').pack(anchor=tk.W)
        self.basic_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.basic_progress.pack(fill=tk.X, pady=(2, 8))

        # OpenSMILE Progress Bar
        tk.Label(progress_frame, text="🤖 OpenSMILE", font=('Arial', 10, 'bold'),
                fg='#4ecdc4', bg='#1a1a1a').pack(anchor=tk.W)
        self.opensmile_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.opensmile_progress.pack(fill=tk.X, pady=(2, 8))

        # Vosk Progress Bar
        tk.Label(progress_frame, text="🗣️ Vosk", font=('Arial', 10, 'bold'),
                fg='#45b7d1', bg='#1a1a1a').pack(anchor=tk.W)
        self.vosk_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.vosk_progress.pack(fill=tk.X, pady=(2, 8))

        # History display
        history_frame = tk.Frame(viz_frame, bg='#1a1a1a')
        history_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(history_frame, text="Recent Activity:", font=('Arial', 12, 'bold'),
                fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(0, 5))

        # Text widget for history
        self.history_text = tk.Text(history_frame, height=8, bg='#2d2d2d', fg='#ffffff',
                                   font=('Consolas', 9), wrap=tk.WORD)
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # Scrollbar for history
        scrollbar = tk.Scrollbar(history_frame, command=self.history_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_text.config(yscrollcommand=scrollbar.set)
        
        # Control buttons
        control_frame = tk.Frame(main_frame, bg='#1a1a1a')
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Clear button
        clear_btn = tk.Button(
            control_frame,
            text="Clear History",
            command=self.clear_history,
            bg='#4a4a4a',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Always on top toggle
        self.always_on_top = tk.BooleanVar(value=True)
        self.root.attributes('-topmost', True)
        
        topmost_cb = tk.Checkbutton(
            control_frame,
            text="Always on Top",
            variable=self.always_on_top,
            command=self.toggle_topmost,
            bg='#1a1a1a',
            fg='white',
            selectcolor='#4a4a4a',
            font=('Arial', 10)
        )
        topmost_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        # Transparency slider
        tk.Label(control_frame, text="Opacity:", bg='#1a1a1a', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.opacity_var = tk.DoubleVar(value=0.9)
        opacity_scale = tk.Scale(
            control_frame,
            from_=0.3,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var,
            command=self.update_opacity,
            bg='#1a1a1a',
            fg='white',
            highlightthickness=0,
            length=100
        )
        opacity_scale.pack(side=tk.LEFT)
        
        # Set initial opacity
        self.root.attributes('-alpha', 0.9)
    
    def toggle_topmost(self):
        """Toggle always on top"""
        self.root.attributes('-topmost', self.always_on_top.get())
    
    def update_opacity(self, value):
        """Update window opacity"""
        self.root.attributes('-alpha', float(value))
    
    def clear_history(self):
        """Clear all history data"""
        with self.data_lock:
            self.basic_emotion_data.clear()
            self.opensmile_data.clear()
            self.vosk_data.clear()
            self.timestamps.clear()
    
    def monitor_data(self):
        """Monitor for new detection data"""
        data_file = "confidence_data.json"
        last_modified = 0
        
        while self.monitoring:
            try:
                # Check if data file exists and was modified
                try:
                    import os
                    if os.path.exists(data_file):
                        modified = os.path.getmtime(data_file)
                        if modified > last_modified:
                            last_modified = modified
                            self.load_data(data_file)
                except Exception:
                    pass
                
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"Error monitoring data: {e}")
                time.sleep(1)
    
    def load_data(self, filename):
        """Load detection data from file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Update current values
            self.current_basic = data.get('basic_emotion', 0.0)
            self.current_opensmile = data.get('opensmile', 0.0)
            self.current_vosk = data.get('vosk', 0.0)
            self.last_emotion = data.get('last_emotion', 'neutral')
            self.last_phrase = data.get('last_phrase', '')
            
            # Add to history
            with self.data_lock:
                now = datetime.now()
                self.timestamps.append(now)
                self.basic_emotion_data.append(self.current_basic)
                self.opensmile_data.append(self.current_opensmile)
                self.vosk_data.append(self.current_vosk)
                
                # Keep only recent data
                if len(self.timestamps) > self.max_history:
                    self.timestamps.pop(0)
                    self.basic_emotion_data.pop(0)
                    self.opensmile_data.pop(0)
                    self.vosk_data.pop(0)
            
            # Update labels
            self.root.after(0, self.update_labels)
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def update_labels(self):
        """Update the current value labels"""
        self.basic_label.config(text=f"🎭 Basic Emotion: {self.current_basic:.2f}")
        self.opensmile_label.config(text=f"🤖 OpenSMILE: {self.current_opensmile:.2f}")
        self.vosk_label.config(text=f"🗣️ Vosk: {self.current_vosk:.2f}")
        self.emotion_label.config(text=f"Last Emotion: {self.last_emotion}")
        self.phrase_label.config(text=f"Last Phrase: {self.last_phrase}")

        # Update progress bars
        self.basic_progress['value'] = self.current_basic * 100
        self.opensmile_progress['value'] = self.current_opensmile * 100
        self.vosk_progress['value'] = self.current_vosk * 100

        # Add to history if there's activity
        if self.current_basic > 0.1 or self.current_opensmile > 0.1 or self.current_vosk > 0.1:
            timestamp = datetime.now().strftime("%H:%M:%S")
            activity = f"[{timestamp}] "

            if self.current_basic > 0.1:
                activity += f"Basic: {self.current_basic:.2f} "
            if self.current_opensmile > 0.1:
                activity += f"OpenSMILE: {self.current_opensmile:.2f} "
            if self.current_vosk > 0.1:
                activity += f"Vosk: {self.current_vosk:.2f} "

            if self.last_emotion != 'neutral':
                activity += f"({self.last_emotion})"
            if self.last_phrase:
                activity += f" '{self.last_phrase}'"

            activity += "\n"

            self.history_text.insert(tk.END, activity)
            self.history_text.see(tk.END)

            # Keep history manageable
            lines = self.history_text.get("1.0", tk.END).split('\n')
            if len(lines) > 50:
                self.history_text.delete("1.0", "2.0")

    def update_display(self):
        """Update the display periodically"""
        try:
            # Schedule next update
            self.root.after(100, self.update_display)  # Update every 100ms
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def run(self):
        """Start the widget"""
        try:
            self.root.mainloop()
        finally:
            self.monitoring = False
    
    def close(self):
        """Close the widget"""
        self.monitoring = False
        self.root.quit()

def main():
    """Main function"""
    print("Starting SmartClip CZ Confidence Widget...")
    print("This widget shows real-time confidence levels for streaming.")
    print("Add this window as a 'Window Capture' source in OBS.")
    print("Press Ctrl+C to exit.")
    
    try:
        widget = ConfidenceWidget()
        widget.run()
    except KeyboardInterrupt:
        print("\nShutting down widget...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
