#!/usr/bin/env python3
"""
SmartClip CZ - Standalone Confidence Visualization Widget
A completely standalone widget that works from any directory
"""

# Set environment variables before any imports to prevent locale errors
import os
import sys

# Suppress all possible locale and encoding errors
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'
os.environ['LC_CTYPE'] = 'C'

# Redirect stderr to suppress error dialogs
import io
original_stderr = sys.stderr
sys.stderr = io.StringIO()

try:
    # Suppress warnings
    import warnings
    warnings.filterwarnings("ignore")
    
    # Set locale safely
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'C')
    except:
        pass
    
    # Import tkinter
    import tkinter as tk
    from tkinter import messagebox
    
    # Restore stderr after successful import
    sys.stderr = original_stderr
    
except Exception as e:
    # Restore stderr and show error
    sys.stderr = original_stderr
    print(f"Import error: {e}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        messagebox.showerror("Import Error", f"Failed to import required modules: {e}")
    except:
        print("Critical error: Cannot import tkinter")
    sys.exit(1)

import json
import time
import threading
from datetime import datetime

class StandaloneConfidenceWidget:
    """Standalone confidence widget that works from any directory"""
    
    def __init__(self):
        try:
            # Create main window
            self.root = tk.Tk()
            self.root.withdraw()  # Hide initially
            
            # Window setup
            self.root.title("SmartClip CZ - Live Confidence")
            self.root.geometry("500x350")
            self.root.configure(bg='#1a1a1a')
            
            # Handle close event
            self.root.protocol("WM_DELETE_WINDOW", self.close)
            
            # Data variables
            self.current_basic = 0.0
            self.current_opensmile = 0.0
            self.current_vosk = 0.0
            self.last_emotion = "neutral"
            self.last_phrase = ""
            
            # Find data file in multiple possible locations
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
            self.root.focus_force()
            
            print("Standalone confidence widget started successfully")
            
        except Exception as e:
            print(f"Error initializing widget: {e}")
            try:
                messagebox.showerror("Widget Error", f"Failed to initialize widget: {e}")
            except:
                pass
            raise
    
    def find_data_file(self):
        """Find the confidence data file in various locations"""
        possible_paths = [
            # Same directory as this script
            os.path.join(os.path.dirname(__file__), "confidence_data.json"),
            # Parent directory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "confidence_data.json"),
            # SmartClip directory
            os.path.join(os.path.dirname(__file__), "..", "smartclip_cz_python", "confidence_data.json"),
            # Current working directory
            os.path.join(os.getcwd(), "confidence_data.json"),
            # Temp directory
            os.path.join(os.path.expanduser("~"), "smartclip_confidence_data.json"),
        ]
        
        # Check existing files first
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    print(f"Found existing data file: {path}")
                    return path
            except:
                continue
        
        # Use first writable location
        for path in possible_paths:
            try:
                # Test if we can write to this location
                test_data = {"test": True}
                with open(path, 'w') as f:
                    json.dump(test_data, f)
                os.remove(path)  # Clean up test file
                print(f"Using data file location: {path}")
                return path
            except:
                continue
        
        # Fallback to temp file
        fallback = os.path.join(os.path.expanduser("~"), "smartclip_confidence_data.json")
        print(f"Using fallback data file: {fallback}")
        return fallback
    
    def setup_ui(self):
        """Setup the user interface"""
        try:
            # Main frame
            main_frame = tk.Frame(self.root, bg='#1a1a1a')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text="🎭 SmartClip CZ - Live Confidence",
                font=('Arial', 14, 'bold'),
                fg='#ffffff',
                bg='#1a1a1a'
            )
            title_label.pack(pady=(0, 15))
            
            # Status info
            status_frame = tk.Frame(main_frame, bg='#1a1a1a')
            status_frame.pack(fill=tk.X, pady=(0, 10))
            
            status_label = tk.Label(
                status_frame,
                text=f"Data file: {os.path.basename(self.data_file)}",
                font=('Arial', 8),
                fg='#888888',
                bg='#1a1a1a'
            )
            status_label.pack()
            
            # Confidence displays
            conf_frame = tk.Frame(main_frame, bg='#1a1a1a')
            conf_frame.pack(fill=tk.X, pady=(0, 15))
            
            # Basic Emotion
            self.basic_label = tk.Label(
                conf_frame,
                text="🎭 Basic Emotion: 0.00",
                font=('Arial', 12, 'bold'),
                fg='#ff6b6b',
                bg='#1a1a1a'
            )
            self.basic_label.pack(pady=3)
            
            self.basic_canvas = tk.Canvas(conf_frame, height=15, bg='#2d2d2d', highlightthickness=0)
            self.basic_canvas.pack(fill=tk.X, pady=(2, 8))
            
            # OpenSMILE
            self.opensmile_label = tk.Label(
                conf_frame,
                text="🤖 OpenSMILE: 0.00",
                font=('Arial', 12, 'bold'),
                fg='#4ecdc4',
                bg='#1a1a1a'
            )
            self.opensmile_label.pack(pady=3)
            
            self.opensmile_canvas = tk.Canvas(conf_frame, height=15, bg='#2d2d2d', highlightthickness=0)
            self.opensmile_canvas.pack(fill=tk.X, pady=(2, 8))
            
            # Vosk
            self.vosk_label = tk.Label(
                conf_frame,
                text="🗣️ Vosk: 0.00",
                font=('Arial', 12, 'bold'),
                fg='#45b7d1',
                bg='#1a1a1a'
            )
            self.vosk_label.pack(pady=3)
            
            self.vosk_canvas = tk.Canvas(conf_frame, height=15, bg='#2d2d2d', highlightthickness=0)
            self.vosk_canvas.pack(fill=tk.X, pady=(2, 8))
            
            # Last detection info
            info_frame = tk.Frame(main_frame, bg='#1a1a1a')
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            self.emotion_label = tk.Label(
                info_frame,
                text="Last Emotion: neutral",
                font=('Arial', 10),
                fg='#cccccc',
                bg='#1a1a1a'
            )
            self.emotion_label.pack(pady=2)
            
            self.phrase_label = tk.Label(
                info_frame,
                text="Last Phrase: -",
                font=('Arial', 10),
                fg='#cccccc',
                bg='#1a1a1a'
            )
            self.phrase_label.pack(pady=2)
            
            # Activity log
            log_frame = tk.Frame(main_frame, bg='#1a1a1a')
            log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            tk.Label(log_frame, text="Recent Activity:", font=('Arial', 10, 'bold'),
                    fg='#ffffff', bg='#1a1a1a').pack(anchor=tk.W)
            
            self.log_text = tk.Text(log_frame, height=4, bg='#2d2d2d', fg='#ffffff',
                                   font=('Consolas', 8), wrap=tk.WORD)
            self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            
            # Controls
            control_frame = tk.Frame(main_frame, bg='#1a1a1a')
            control_frame.pack(fill=tk.X)
            
            clear_btn = tk.Button(
                control_frame,
                text="Clear Log",
                command=self.clear_log,
                bg='#4a4a4a',
                fg='white',
                font=('Arial', 9),
                relief=tk.FLAT
            )
            clear_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # Always on top
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
                font=('Arial', 9)
            )
            topmost_cb.pack(side=tk.LEFT)
            
            print("UI setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up UI: {e}")
            # Create minimal fallback UI
            label = tk.Label(self.root, text="SmartClip CZ - Live Confidence\n(Minimal Mode)",
                           font=('Arial', 12), fg='white', bg='#1a1a1a')
            label.pack(expand=True)
    
    def draw_progress_bar(self, canvas, value, color):
        """Draw a progress bar"""
        try:
            canvas.delete("all")
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            
            if width > 1:
                # Background
                canvas.create_rectangle(0, 0, width, height, fill='#2d2d2d', outline='')
                
                # Progress
                progress_width = int(width * value)
                if progress_width > 0:
                    canvas.create_rectangle(0, 0, progress_width, height, fill=color, outline='')
                
                # Text
                percentage = f"{value*100:.0f}%"
                canvas.create_text(width//2, height//2, text=percentage, fill='white', font=('Arial', 7))
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
        """Monitor for data file changes"""
        last_modified = 0
        
        while self.monitoring:
            try:
                if os.path.exists(self.data_file):
                    modified = os.path.getmtime(self.data_file)
                    if modified > last_modified:
                        last_modified = modified
                        self.load_data()
                else:
                    # Create empty data file if it doesn't exist
                    try:
                        with open(self.data_file, 'w') as f:
                            json.dump({
                                'basic_emotion': 0.0,
                                'opensmile': 0.0,
                                'vosk': 0.0,
                                'last_emotion': 'neutral',
                                'last_phrase': ''
                            }, f)
                    except:
                        pass
                
                time.sleep(0.2)  # Check every 200ms
                
            except Exception as e:
                print(f"Error monitoring data: {e}")
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
            
            # Update UI in main thread
            self.root.after(0, self.update_labels)
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def update_labels(self):
        """Update UI labels and progress bars"""
        try:
            # Update labels
            self.basic_label.config(text=f"🎭 Basic Emotion: {self.current_basic:.2f}")
            self.opensmile_label.config(text=f"🤖 OpenSMILE: {self.current_opensmile:.2f}")
            self.vosk_label.config(text=f"🗣️ Vosk: {self.current_vosk:.2f}")
            self.emotion_label.config(text=f"Last Emotion: {self.last_emotion}")
            self.phrase_label.config(text=f"Last Phrase: {self.last_phrase}")
            
            # Update progress bars
            self.draw_progress_bar(self.basic_canvas, self.current_basic, '#ff6b6b')
            self.draw_progress_bar(self.opensmile_canvas, self.current_opensmile, '#4ecdc4')
            self.draw_progress_bar(self.vosk_canvas, self.current_vosk, '#45b7d1')
            
            # Add to activity log if significant activity
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
                if len(lines) > 20:
                    self.log_text.delete("1.0", "2.0")
                    
        except Exception as e:
            print(f"Error updating labels: {e}")
    
    def update_display(self):
        """Update display periodically"""
        try:
            self.root.after(100, self.update_display)
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
    
    def close(self):
        """Close the widget"""
        try:
            self.monitoring = False
            self.root.quit()
            self.root.destroy()
        except:
            pass

def main():
    """Main function"""
    print("Starting SmartClip CZ Standalone Confidence Widget...")
    print("This widget works independently and finds data automatically.")
    
    try:
        widget = StandaloneConfidenceWidget()
        widget.run()
    except KeyboardInterrupt:
        print("\nWidget closed by user")
    except Exception as e:
        print(f"Widget error: {e}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Widget Error", f"Failed to start widget:\n{e}")
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()
