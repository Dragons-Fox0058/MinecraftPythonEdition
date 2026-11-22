"""Minecraft Python Edition desktop launcher."""
from __future__ import annotations

import socket
import tkinter as tk
from tkinter import messagebox

from engine.app.client import main as run_game
from engine.server.local import PythonEditionServer, ServerConfig


class Launcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Minecraft Python Edition")
        self.root.geometry("520x390")
        self.root.minsize(480, 350)
        self.root.configure(bg="#151923")
        self.server = None
        self.status = tk.StringVar(value="Ready")
        tk.Label(self.root, text="MINECRAFT", bg="#151923", fg="#f4f6fb",
                 font=("Segoe UI", 27, "bold")).pack(pady=(34, 0))
        tk.Label(self.root, text="PYTHON EDITION", bg="#151923", fg="#77c7ff",
                 font=("Segoe UI", 13, "bold")).pack(pady=(0, 22))
        self._button("PLAY", self.play).pack(fill="x", padx=90, pady=7)
        self._button("HOST PYTHON EDITION SERVER", self.host).pack(fill="x", padx=90, pady=7)
        self._button("STOP SERVER", self.stop_server).pack(fill="x", padx=90, pady=7)
        tk.Label(self.root, textvariable=self.status, bg="#151923", fg="#c7cfdd",
                 font=("Segoe UI", 9), wraplength=430).pack(pady=18)
        tk.Label(self.root, text="Python Edition clients only • Java Edition is not supported",
                 bg="#151923", fg="#8993a5", font=("Segoe UI", 8)).pack(side="bottom", pady=15)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _button(self, label, command):
        return tk.Button(self.root, text=label, command=command, bg="#2b75bd", fg="white",
                         activebackground="#398bd8", activeforeground="white",
                         relief="flat", bd=0, padx=12, pady=12,
                         font=("Segoe UI", 10, "bold"), cursor="hand2")

    def play(self):
        self.root.withdraw()
        try:
            run_game()
        except Exception as exc:
            messagebox.showerror("Minecraft Python Edition", str(exc), parent=self.root)
        finally:
            self.root.deiconify()

    def host(self):
        if self.server is not None and self.server.running:
            messagebox.showinfo("Server", f"Server already running at {self.server.address[0]}:{self.server.address[1]}")
            return
        try:
            self.server = PythonEditionServer(ServerConfig(host="0.0.0.0", port=25575))
            host, port = self.server.start()
            self.status.set(f"Python Edition server running on port {port}. Share your LAN IP with Python Edition players.")
            messagebox.showinfo("Server started", f"LAN server listening on port {port}.\nOnly Python Edition clients can join.")
        except Exception as exc:
            self.server = None
            messagebox.showerror("Server error", str(exc))

    def stop_server(self):
        if self.server is not None:
            self.server.stop()
            self.server = None
        self.status.set("Server stopped")

    def close(self):
        self.stop_server()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Launcher().run()
