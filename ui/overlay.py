"""
Tkinter window for bad posture warning.
"""

import tkinter as tk
from typing import Optional

class PostureWarningOverlay:
    def __init__(self):
        """Initialize the red overlay window."""
        self.root = None
        self.window = None

    def show(self):
        """
        Display a full-screen semi-transparent red overlay.
        The window closes automatically after 3 seconds.
        """
        # Use a separate root to avoid interfering with the main app
        # We use a try-except block because Tkinter initialization on
        # background threads is unstable on macOS.
        try:
            self.root = tk.Tk()

            # Remove window decorations (title bar, borders)
            self.root.overrideredirect(True)

            # Make it full screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

            # Set transparency and color
            self.root.attributes("-alpha", 0.5)
            self.root.configure(bg="red")

            # Ensure it stays on top of all other windows
            self.root.attributes("-topmost", True)

            # Center the warning text
            label = tk.Label(
                self.root,
                text="⚠️ Fix your posture!",
                font=("Arial", 48, "bold"),
                fg="white",
                bg="red"
            )
            label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            # Schedule the window to close after 3000ms
            self.root.after(3000, self.close)

            # Start the loop.
            self.root.mainloop()
        except Exception as e:
            print(f"Overlay failed to launch: {e}")

    def close(self):
        """Close the overlay window."""
        if self.root:
            self.root.destroy()
            self.root = None
