#!/usr/bin/env python3
"""
SmartClip CZ - Simple Confidence Visualization Widget
A fallback streamable widget using only basic tkinter
"""

import sys
import json
import time
import threading
import os
from datetime import datetime

# Suppress all warnings
import warnings
warnings.filterwarnings("ignore")

try:
    import tkinter as tk
    # Set locale to avoid locale errors
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'C')
    except:
        pass  # Ignore locale errors
except ImportError as e:
    print(f"Missing tkinter: {e}")
    sys.exit(1)

class SimpleConfidenceWidget:
    """Simple real-time confidence visualization widget for streaming"""
    
    def __init__(self):
        try:
            self.root = tk.Tk()
            self.root.title("SmartClip CZ - Live Confidence")
            self.root.geometry("600x400")
            self.root.configure(bg='#1a1a1a')  # Dark theme for streaming
            
            # Handle window close event
            self.root.protocol("WM_DELETE_WINDOW", self.close)
            
            # Current values
            self.current_basic = 0.0
            self.current_opensmile = 0.0
            self.current_vosk = 0.0
            self.last_emotion = "neutral"
            self.last_phrase = ""
            
            # Setup UI
            self.setup_ui()
            
            # Start data monitoring
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_data, daemon=True)
            self.monitor_thread.start()
            
            # Start UI updates
            self.update_display()
            
        except Exception as e:
            print(f"Error initializing simple widget: {e}")
            raise
    
    def setup_ui(self):
        """Setup the simple user interface"""
        try:
            # Main frame
            main_frame = tk.Frame(self.root, bg='#1a1a1a')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = tk.Label(
                main_frame, 
                text="🎭 SmartClip CZ - Live Confidence",
                font=('Arial', 16, 'bold'),
                fg='#ffffff',
                bg='#1a1a1a'
            )
            title_label.pack(pady=(0, 20))
            
            # Current values frame
            values_frame = tk.Frame(main_frame, bg='#1a1a1a')
            values_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Basic Emotion
            self.basic_label = tk.Label(
                values_frame,
                text="🎭 Basic Emotion: 0.00",
                font=('Arial', 14, 'bold'),
                fg='#ff6b6b',
                bg='#1a1a1a'
            )
            self.basic_label.pack(pady=5)
            
            # Basic emotion bar (using Canvas)
            self.basic_canvas = tk.Canvas(values_frame, height=20, bg='#2d2d2d', highlightthickness=0)
            self.basic_canvas.pack(fill=tk.X, pady=(0, 10))
            
            # OpenSMILE
            self.opensmile_label = tk.Label(
                values_frame,
                text="🤖 OpenSMILE: 0.00",
                font=('Arial', 14, 'bold'),
                fg='#4ecdc4',
                bg='#1a1a1a'
            )
            self.opensmile_label.pack(pady=5)
            
            # OpenSMILE bar
            self.opensmile_canvas = tk.Canvas(values_frame, height=20, bg='#2d2d2d', highlightthickness=0)
            self.opensmile_canvas.pack(fill=tk.X, pady=(0, 10))
            
            # Vosk
            self.vosk_label = tk.Label(
                values_frame,
                text="🗣️ Vosk: 0.00",
                font=('Arial', 14, 'bold'),
                fg='#45b7d1',
                bg='#1a1a1a'
            )
            self.vosk_label.pack(pady=5)
            
            # Vosk bar
            self.vosk_canvas = tk.Canvas(values_frame, height=20, bg='#2d2d2d', highlightthickness=0)
            self.vosk_canvas.pack(fill=tk.X, pady=(0, 10))
            
            # Status frame
            status_frame = tk.Frame(main_frame, bg='#1a1a1a')
            status_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Last emotion
            self.emotion_label = tk.Label(
                status_frame,
                text="Last Emotion: neutral",
                font=('Arial', 12),
                fg='#cccccc',
                bg='#1a1a1a'
            )
            self.emotion_label.pack(pady=2)
            
            # Last phrase
            self.phrase_label = tk.Label(
                status_frame,
                text="Last Phrase: -",
                font=('Arial', 12),
                fg='#cccccc',
                bg='#1a1a1a'
            )
            self.phrase_label.pack(pady=2)
            
            # Activity log
            log_frame = tk.Frame(main_frame, bg='#1a1a1a')
            log_frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(log_frame, text="Recent Activity:", font=('Arial', 12, 'bold'), 
                    fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W, pady=(0, 5))
            
            # Text widget for activity log
            self.log_text = tk.Text(log_frame, height=6, bg='#2d2d2d', fg='#ffffff', 
                                   font=('Consolas', 9), wrap=tk.WORD)
            self.log_text.pack(fill=tk.BOTH, expand=True)
            
            # Control buttons
            control_frame = tk.Frame(main_frame, bg='#1a1a1a')
            control_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Clear button
            clear_btn = tk.Button(
                control_frame,
                text="Clear Log",
                command=self.clear_log,
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
            topmost_cb.pack(side=tk.LEFT)
            
        except Exception as e:
            print(f"Error setting up UI: {e}")
            raise
    
    def draw_progress_bar(self, canvas, value, color):
        """Draw a progress bar on canvas"""
        try:
            canvas.delete("all")
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            
            if width > 1:  # Only draw if canvas is visible
                # Background
                canvas.create_rectangle(0, 0, width, height, fill='#2d2d2d', outline='')
                
                # Progress
                progress_width = int(width * value)
                if progress_width > 0:
                    canvas.create_rectangle(0, 0, progress_width, height, fill=color, outline='')
                
                # Text
                percentage = f"{value*100:.0f}%"
                canvas.create_text(width//2, height//2, text=percentage, fill='white', font=('Arial', 8))
        except Exception as e:
            print(f"Error drawing progress bar: {e}")
    
    def toggle_topmost(self):
        """Toggle always on top"""
        try:
            self.root.attributes('-topmost', self.always_on_top.get())
        except Exception as e:
            print(f"Error toggling topmost: {e}")
    
    def clear_log(self):
        """Clear activity log"""
        try:
            self.log_text.delete("1.0", tk.END)
        except Exception as e:
            print(f"Error clearing log: {e}")
    
    def monitor_data(self):
        """Monitor for new detection data"""
        data_file = os.path.join(os.path.dirname(__file__), "confidence_data.json")
        last_modified = 0
        
        while self.monitoring:
            try:
                if os.path.exists(data_file):
                    modified = os.path.getmtime(data_file)
                    if modified > last_modified:
                        last_modified = modified
                        self.load_data(data_file)
                
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
            
            # Update UI
            self.root.after(0, self.update_labels)
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def update_labels(self):
        """Update the current value labels"""
        try:
            self.basic_label.config(text=f"🎭 Basic Emotion: {self.current_basic:.2f}")
            self.opensmile_label.config(text=f"🤖 OpenSMILE: {self.current_opensmile:.2f}")
            self.vosk_label.config(text=f"🗣️ Vosk: {self.current_vosk:.2f}")
            self.emotion_label.config(text=f"Last Emotion: {self.last_emotion}")
            self.phrase_label.config(text=f"Last Phrase: {self.last_phrase}")
            
            # Update progress bars
            self.draw_progress_bar(self.basic_canvas, self.current_basic, '#ff6b6b')
            self.draw_progress_bar(self.opensmile_canvas, self.current_opensmile, '#4ecdc4')
            self.draw_progress_bar(self.vosk_canvas, self.current_vosk, '#45b7d1')
            
            # Add to activity log if there's significant activity
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
                
                self.log_text.insert(tk.END, activity)
                self.log_text.see(tk.END)
                
                # Keep log manageable
                lines = self.log_text.get("1.0", tk.END).split('\n')
                if len(lines) > 30:
                    self.log_text.delete("1.0", "2.0")
                    
        except Exception as e:
            print(f"Error updating labels: {e}")
    
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
            print("Simple confidence widget started successfully")
            self.root.mainloop()
        except Exception as e:
            print(f"Error running widget: {e}")
        finally:
            self.monitoring = False
    
    def close(self):
        """Close the widget"""
        try:
            self.monitoring = False
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error closing widget: {e}")

def main():
    """Main function"""
    print("Starting SmartClip CZ Simple Confidence Widget...")
    print("This widget shows real-time confidence levels for streaming.")
    print("Add this window as a 'Window Capture' source in OBS.")
    
    try:
        widget = SimpleConfidenceWidget()
        widget.run()
    except KeyboardInterrupt:
        print("\nShutting down widget...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
