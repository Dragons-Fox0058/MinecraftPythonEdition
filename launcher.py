"""Minecraft Python Edition desktop launcher."""
from __future__ import annotations

import socket
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

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
        self.world_name = tk.StringVar(value="New World")
        self.seed = tk.StringVar(value="0")
        tk.Label(self.root, text="MINECRAFT", bg="#151923", fg="#f4f6fb",
                 font=("Segoe UI", 27, "bold")).pack(pady=(34, 0))
        tk.Label(self.root, text="PYTHON EDITION", bg="#151923", fg="#77c7ff",
                 font=("Segoe UI", 13, "bold")).pack(pady=(0, 22))
        form = tk.Frame(self.root, bg="#151923")
        form.pack(fill="x", padx=64, pady=(0, 8))
        tk.Label(form, text="WORLD NAME", bg="#151923", fg="#c7cfdd",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        saved_worlds = []
        saves_root = Path("saves")
        if saves_root.is_dir():
            saved_worlds = sorted(
                folder.name for folder in saves_root.iterdir()
                if folder.is_dir() and (folder / "level.dat").is_file()
            )
        ttk.Combobox(form, textvariable=self.world_name, values=saved_worlds).grid(
            row=1, column=0, sticky="ew", ipady=5, padx=(0, 8)
        )
        tk.Label(form, text="SEED", bg="#151923", fg="#c7cfdd",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w")
        tk.Entry(form, textvariable=self.seed, bg="#252c3a", fg="white",
                 insertbackground="white", relief="flat", width=12).grid(row=1, column=1, sticky="ew", ipady=7)
        form.columnconfigure(0, weight=1)
        self._button("PLAY SINGLEPLAYER", self.play).pack(fill="x", padx=90, pady=7)
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
        name = self.world_name.get().strip()
        if not name or name in (".", "..") or any(ch in name for ch in "/\\\\"):
            messagebox.showerror("Invalid world name", "Enter a valid world name.")
            return
        try:
            seed = int(self.seed.get().strip() or "0")
        except ValueError:
            messagebox.showerror("Invalid seed", "Seed must be an integer.")
            return
        self.root.withdraw()
        try:
            run_game(seed=seed, world_name=name)
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
