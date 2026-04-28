"""
Tkinter window for the 5-minute walk break reminder.
"""

import tkinter as tk
from tkinter import messagebox

class WalkReminderWindow:
    def __init__(self, on_resume_callback):
        """
        Initialize the walk reminder window.

        Args:
            on_resume_callback (callable): Callback to run when the user clicks Resume.
        """
        self.on_resume_callback = on_resume_callback
        self.root = None
        self.remaining_seconds = 5 * 60  # 5 minutes
        self.is_break_over = False

    def show(self):
        """Display the walk reminder window with a countdown."""
        self.root = tk.Tk()
        self.root.title("Walk Break!")

        # Window setup
        window_width = 500
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Center the window
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Force topmost and remove standard window closing (X button)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close_attempt)

        # UI Elements
        self.message_label = tk.Label(
            self.root,
            text="🚶 You've been sitting for 30 minutes.\nTime for a 5-minute walk!",
            font=("Arial", 16, "bold"),
            pady=20,
            justify="center"
        )
        self.message_label.pack(pady=20)

        self.timer_label = tk.Label(
            self.root,
            text="05:00",
            font=("Arial", 48, "bold"),
            fg="blue"
        )
        self.timer_label.pack(pady=10)

        self.resume_btn = tk.Button(
            self.root,
            text="Welcome back! Click to Resume",
            command=self._on_resume_clicked,
            font=("Arial", 14),
            state=tk.DISABLED, # Disabled until timer reaches 0
            padx=20,
            pady=10
        )
        self.resume_btn.pack(pady=20)

        # Start the countdown loop
        self._update_timer()
        self.root.mainloop()

    def _update_timer(self):
        """Update the countdown timer every second."""
        if self.remaining_seconds > 0:
            # Calculate MM:SS
            mins, secs = divmod(self.remaining_seconds, 60)
            self.timer_label.config(text=f"{mins:02d}:{secs:02d}")

            self.remaining_seconds -= 1
            self.root.after(1000, self._update_timer)
        else:
            # Timer reached zero
            self.timer_label.config(text="00:00", fg="green")
            self.message_label.config(text="Walk break complete!")
            self.resume_btn.config(state=tk.NORMAL)
            self.is_break_over = True

    def _handle_close_attempt(self):
        """Prevent the user from closing the window via the X button."""
        if not self.is_break_over:
            messagebox.showwarning(
                "Break in Progress",
                "Please complete your 5-minute walk before resuming!"
            )

    def _on_resume_clicked(self):
        """Handle the resume button click."""
        self.on_resume_callback()
        self.root.destroy()
