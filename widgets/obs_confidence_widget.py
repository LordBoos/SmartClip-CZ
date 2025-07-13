#!/usr/bin/env python3
"""
SmartClip CZ - OBS-Compatible Confidence Widget
Specifically designed to work when launched from OBS subprocess
"""

# Comprehensive error suppression for OBS environment
import sys
import os

# Set environment before any other imports
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'
os.environ['LC_CTYPE'] = 'C'

# Suppress all warnings and errors
import warnings
warnings.filterwarnings("ignore")

# Redirect stderr to suppress error dialogs completely
import io
sys.stderr = io.StringIO()

try:
    import tkinter as tk
    # Restore stderr after successful import
    sys.stderr = sys.__stderr__
except Exception as e:
    # If tkinter fails, try to show error and exit gracefully
    sys.stderr = sys.__stderr__
    print(f"Tkinter import failed: {e}")
    try:
        # Try to create a simple message box
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Widget Error", f"Failed to start confidence widget:\n{e}")
        root.destroy()
    except:
        pass
    sys.exit(1)

import json
import time
import threading
from datetime import datetime

class OBSConfidenceWidget:
    """OBS-compatible confidence widget"""
    
    def __init__(self):
        try:
            # Create root window with error handling
            self.root = tk.Tk()
            self.root.title("SmartClip CZ - Live Confidence")
            self.root.geometry("450x300")
            self.root.configure(bg='#1a1a1a')
            
            # Prevent window from being destroyed accidentally
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Data variables
            self.current_basic = 0.0
            self.current_opensmile = 0.0
            self.current_vosk = 0.0
            self.last_emotion = "neutral"
            self.last_phrase = ""
            
            # Find data file
            self.data_file = self.find_data_file()
            
            # Setup UI
            self.setup_ui()
            
            # Start monitoring
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_data, daemon=True)
            self.monitor_thread.start()
            
            # Start updates
            self.update_display()
            
            # Show window
            self.root.deiconify()
            self.root.lift()
            
            print("OBS confidence widget started successfully")
            
        except Exception as e:
            print(f"Error initializing OBS widget: {e}")
            sys.exit(1)
    
    def find_data_file(self):
        """Find confidence data file"""
        possible_paths = [
            "confidence_data.json",
            os.path.join(os.path.dirname(__file__), "confidence_data.json"),
            os.path.join(os.path.expanduser("~"), "smartclip_confidence_data.json"),
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    return path
            except:
                continue
        
        # Use first writable location
        for path in possible_paths:
            try:
                with open(path, 'w') as f:
                    json.dump({"test": True}, f)
                os.remove(path)
                return path
            except:
                continue
        
        return "confidence_data.json"  # Fallback
    
    def setup_ui(self):
        """Setup simple, robust UI"""
        try:
            # Main frame
            main_frame = tk.Frame(self.root, bg='#1a1a1a')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Title
            title = tk.Label(main_frame, text="🎭 SmartClip CZ - Live Confidence",
                           font=('Arial', 12, 'bold'), fg='white', bg='#1a1a1a')
            title.pack(pady=(0, 10))
            
            # Confidence displays
            self.basic_label = tk.Label(main_frame, text="🎭 Basic Emotion: 0.00",
                                      font=('Arial', 10, 'bold'), fg='#ff6b6b', bg='#1a1a1a')
            self.basic_label.pack(pady=2)
            
            self.basic_bar = tk.Frame(main_frame, height=8, bg='#2d2d2d')
            self.basic_bar.pack(fill=tk.X, pady=(2, 8))
            
            self.opensmile_label = tk.Label(main_frame, text="🤖 OpenSMILE: 0.00",
                                          font=('Arial', 10, 'bold'), fg='#4ecdc4', bg='#1a1a1a')
            self.opensmile_label.pack(pady=2)
            
            self.opensmile_bar = tk.Frame(main_frame, height=8, bg='#2d2d2d')
            self.opensmile_bar.pack(fill=tk.X, pady=(2, 8))
            
            self.vosk_label = tk.Label(main_frame, text="🗣️ Vosk: 0.00",
                                     font=('Arial', 10, 'bold'), fg='#45b7d1', bg='#1a1a1a')
            self.vosk_label.pack(pady=2)
            
            self.vosk_bar = tk.Frame(main_frame, height=8, bg='#2d2d2d')
            self.vosk_bar.pack(fill=tk.X, pady=(2, 8))
            
            # Status
            self.emotion_label = tk.Label(main_frame, text="Last Emotion: neutral",
                                        font=('Arial', 9), fg='#cccccc', bg='#1a1a1a')
            self.emotion_label.pack(pady=2)
            
            self.phrase_label = tk.Label(main_frame, text="Last Phrase: -",
                                       font=('Arial', 9), fg='#cccccc', bg='#1a1a1a')
            self.phrase_label.pack(pady=2)
            
            # Activity log
            log_frame = tk.Frame(main_frame, bg='#1a1a1a')
            log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            
            tk.Label(log_frame, text="Recent Activity:", font=('Arial', 9, 'bold'),
                    fg='white', bg='#1a1a1a').pack(anchor=tk.W)
            
            self.log_text = tk.Text(log_frame, height=3, bg='#2d2d2d', fg='white',
                                   font=('Consolas', 8), wrap=tk.WORD)
            self.log_text.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
            
            # Controls
            control_frame = tk.Frame(main_frame, bg='#1a1a1a')
            control_frame.pack(fill=tk.X, pady=(5, 0))
            
            clear_btn = tk.Button(control_frame, text="Clear", command=self.clear_log,
                                bg='#4a4a4a', fg='white', font=('Arial', 8), relief=tk.FLAT)
            clear_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Always on top
            self.always_on_top = tk.BooleanVar(value=True)
            self.root.attributes('-topmost', True)
            
            topmost_cb = tk.Checkbutton(control_frame, text="Always on Top",
                                      variable=self.always_on_top, command=self.toggle_topmost,
                                      bg='#1a1a1a', fg='white', selectcolor='#4a4a4a',
                                      font=('Arial', 8))
            topmost_cb.pack(side=tk.LEFT)
            
        except Exception as e:
            print(f"Error setting up UI: {e}")
            # Create minimal fallback
            label = tk.Label(self.root, text="SmartClip CZ\nLive Confidence",
                           font=('Arial', 10), fg='white', bg='#1a1a1a')
            label.pack(expand=True)
    
    def update_progress_bar(self, bar_frame, value, color):
        """Update progress bar using frame width"""
        try:
            # Clear existing progress
            for widget in bar_frame.winfo_children():
                widget.destroy()
            
            # Create progress indicator
            if value > 0:
                progress_width = max(1, int(bar_frame.winfo_width() * value))
                progress = tk.Frame(bar_frame, bg=color, height=8)
                progress.place(x=0, y=0, width=progress_width, height=8)
        except:
            pass
    
    def toggle_topmost(self):
        """Toggle always on top"""
        try:
            self.root.attributes('-topmost', self.always_on_top.get())
        except:
            pass
    
    def clear_log(self):
        """Clear activity log"""
        try:
            self.log_text.delete("1.0", tk.END)
        except:
            pass
    
    def monitor_data(self):
        """Monitor data file"""
        last_modified = 0
        
        while self.monitoring:
            try:
                if os.path.exists(self.data_file):
                    modified = os.path.getmtime(self.data_file)
                    if modified > last_modified:
                        last_modified = modified
                        self.load_data()
                
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error monitoring: {e}")
                time.sleep(1)
    
    def load_data(self):
        """Load data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            self.current_basic = data.get('basic_emotion', 0.0)
            self.current_opensmile = data.get('opensmile', 0.0)
            self.current_vosk = data.get('vosk', 0.0)
            self.last_emotion = data.get('last_emotion', 'neutral')
            self.last_phrase = data.get('last_phrase', '')
            
            self.root.after(0, self.update_labels)
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def update_labels(self):
        """Update UI labels"""
        try:
            self.basic_label.config(text=f"🎭 Basic Emotion: {self.current_basic:.2f}")
            self.opensmile_label.config(text=f"🤖 OpenSMILE: {self.current_opensmile:.2f}")
            self.vosk_label.config(text=f"🗣️ Vosk: {self.current_vosk:.2f}")
            self.emotion_label.config(text=f"Last Emotion: {self.last_emotion}")
            self.phrase_label.config(text=f"Last Phrase: {self.last_phrase}")
            
            # Update progress bars
            self.update_progress_bar(self.basic_bar, self.current_basic, '#ff6b6b')
            self.update_progress_bar(self.opensmile_bar, self.current_opensmile, '#4ecdc4')
            self.update_progress_bar(self.vosk_bar, self.current_vosk, '#45b7d1')
            
            # Add to activity log
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
                if len(lines) > 15:
                    self.log_text.delete("1.0", "2.0")
                    
        except Exception as e:
            print(f"Error updating labels: {e}")
    
    def update_display(self):
        """Update display periodically"""
        try:
            self.root.after(100, self.update_display)
        except:
            pass
    
    def on_closing(self):
        """Handle window close"""
        try:
            self.monitoring = False
            self.root.quit()
            self.root.destroy()
        except:
            pass
    
    def run(self):
        """Run the widget"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error running widget: {e}")
        finally:
            self.monitoring = False

def main():
    """Main function"""
    try:
        print("Starting OBS-compatible confidence widget...")
        widget = OBSConfidenceWidget()
        widget.run()
        print("Widget closed")
    except Exception as e:
        print(f"Widget error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
