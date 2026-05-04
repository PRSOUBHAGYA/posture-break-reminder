"""
Tkinter window for the bad posture correction overlay.
"""

import tkinter as tk

class PostureCorrectionOverlay:
    def __init__(self):
        """Initialize the black correction overlay window."""
        self.root = None
        self.window = None

    def show(self):
        """
        Display a full-screen black overlay.
        The window stays open until close() is called by the AlertManager.
        """
        try:
            self.root = tk.Tk()

            # Remove window decorations
            self.root.overrideredirect(True)

            # Make it full screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

            # Set color to black and make it topmost
            self.root.configure(bg="black")
            self.root.attributes("-topmost", True)

            # Warning text
            label = tk.Label(
                self.root,
                text="⚠️\n\nCorrect your posture to return to your screen!",
                font=("Arial", 32, "bold"),
                fg="white",
                bg="black",
                justify="center"
            )
            label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

            # Use a separate thread for mainloop if called from background,
            # but since we'll trigger this via the main app's main thread
            # (or a safe mechanism), we just call mainloop.
            self.root.mainloop()
        except Exception as e:
            print(f"Correction overlay failed to launch: {e}")

    def close(self):
        """Close the overlay window."""
        if self.root:
            # Use after(0) to ensure destruction happens on the main loop
            self.root.after(0, self.root.destroy)
            self.root = None
