#!/usr/bin/env python3
"""
Windows 11 desktop app for Master NFC Writer.

This module keeps NFC card operations in src.master_nfc_writer and focuses on a
polished Windows desktop workflow for ACR122U business-card writing.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path


def prepare_tk_environment() -> None:
    """Point frozen builds at their bundled Tcl/Tk libraries before importing tkinter."""
    if not hasattr(sys, "_MEIPASS"):
        return
    base = Path(getattr(sys, "_MEIPASS"))
    tcl_library = base / "tcl" / "tcl8.6"
    tk_library = base / "tcl" / "tk8.6"
    if tcl_library.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl_library))
    if tk_library.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk_library))


prepare_tk_environment()

import tkinter as tk
from tkinter import messagebox, ttk

try:
    from src import master_nfc_writer as nfc
except ModuleNotFoundError:
    import master_nfc_writer as nfc  # type: ignore


APP_TITLE = "Master NFC Writer"
APP_SUBTITLE = "Windows 11 NFC business-card writer"

BG = "#f3f6fb"
PANEL = "#ffffff"
BORDER = "#d8e2f0"
TEXT = "#18233a"
MUTED = "#5f6d82"
BLUE = "#0565ff"
GREEN = "#14804a"
RED = "#b42318"


def resource_path(*parts: str) -> Path:
    """Return a repo or PyInstaller resource path."""
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).joinpath(*parts)
    return Path(__file__).resolve().parents[1].joinpath(*parts)


class Worker:
    def __init__(self) -> None:
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()

    def run(self, target, *args) -> None:
        thread = threading.Thread(target=self._run, args=(target, args), daemon=True)
        thread.start()

    def _run(self, target, args) -> None:
        try:
            self.messages.put(("success", target(*args)))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.messages.put(("error", exc))


class BatchState:
    def __init__(self) -> None:
        self.active = False
        self.success_count = 0
        self.failure_count = 0
        self.seen_uids: set[str] = set()

    def reset(self) -> None:
        self.active = True
        self.success_count = 0
        self.failure_count = 0
        self.seen_uids.clear()


class MasterNfcWriterWindows11(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1060x760")
        self.minsize(940, 660)
        self.configure(bg=BG)

        self.worker = Worker()
        self.batch = BatchState()
        self.reader_map = {}
        self.current_job = ""
        self.app_icon: tk.PhotoImage | None = None

        self.reader_var = tk.StringVar()
        self.connection_var = tk.StringVar(value="Reader not checked")
        self.uid_var = tk.StringVar(value="No card scanned")
        self.ndef_var = tk.StringVar(value="No NDEF data loaded")
        self.record_type_var = tk.StringVar(value="url")
        self.payload_var = tk.StringVar(value=nfc.CONFIG.get("default_url", ""))
        self.preset_var = tk.StringVar()

        self.business_name_var = tk.StringVar(value=nfc.CONFIG.get("business_name", ""))
        self.owner_name_var = tk.StringVar(value=nfc.CONFIG.get("owner_name", ""))
        self.default_url_var = tk.StringVar(value=nfc.CONFIG.get("default_url", ""))
        self.website_var = tk.StringVar(value=nfc.CONFIG.get("website_url", ""))
        self.phone_var = tk.StringVar(value=nfc.CONFIG.get("phone", ""))
        self.email_var = tk.StringVar(value=nfc.CONFIG.get("email", ""))

        self.batch_mode_var = tk.StringVar(value="format_write")
        self.batch_overwrite_var = tk.BooleanVar(value=False)
        self.batch_status_var = tk.StringVar(value="Not started")
        self.batch_success_var = tk.StringVar(value="0")
        self.batch_failure_var = tk.StringVar(value="0")
        self.batch_last_uid_var = tk.StringVar(value="None")

        self._load_icon()
        self._configure_styles()
        self._build_ui()
        self.refresh_readers(show_errors=False)
        self.load_presets()
        self.after(120, self.poll_worker)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _load_icon(self) -> None:
        png_path = resource_path("assets", "windows", "master-nfc-writer.png")
        ico_path = resource_path("assets", "windows", "master-nfc-writer.ico")
        try:
            if png_path.exists():
                self.app_icon = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self.app_icon)
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except tk.TclError:
            self.app_icon = None

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        for theme in ("vista", "xpnative", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        style.configure(".", font=("Segoe UI", 10), foreground=TEXT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 22, "bold"))
        style.configure("Subheader.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 12, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Value.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background=PANEL, foreground=BLUE, font=("Segoe UI", 10, "bold"))
        style.configure("Danger.TLabel", background=PANEL, foreground=RED, font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X, pady=(0, 14))

        if self.app_icon:
            logo = ttk.Label(header, image=self.app_icon, background=BG)
            logo.pack(side=tk.LEFT, padx=(0, 12))

        title_box = ttk.Frame(header)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_box, text=APP_TITLE, style="Header.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text=APP_SUBTITLE, style="Subheader.TLabel").pack(anchor=tk.W)

        self.connection_label = ttk.Label(header, textvariable=self.connection_var, style="Subheader.TLabel")
        self.connection_label.pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_writer_tab()
        self._build_batch_tab()
        self._build_settings_tab()
        self._build_activity_tab()

        self.status_bar = ttk.Label(root, text="Ready", style="Subheader.TLabel")
        self.status_bar.pack(fill=tk.X, pady=(10, 0))

    def _panel(self, parent, title: str, fill=tk.X, expand: bool = False) -> ttk.Frame:
        shell = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        shell.pack(fill=fill, expand=expand, pady=(0, 12))
        ttk.Label(shell, text=title, style="PanelTitle.TLabel").pack(anchor=tk.W, pady=(0, 10))
        return shell

    def _build_writer_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="Write Card")

        reader_panel = self._panel(tab, "Reader")
        reader_grid = ttk.Frame(reader_panel, style="Panel.TFrame")
        reader_grid.pack(fill=tk.X)
        ttk.Label(reader_grid, text="Reader", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.reader_combo = ttk.Combobox(reader_grid, textvariable=self.reader_var, state="readonly", width=70)
        self.reader_combo.grid(row=0, column=1, sticky=tk.EW, padx=(0, 8))
        ttk.Button(reader_grid, text="Refresh", command=self.refresh_readers).grid(row=0, column=2, sticky=tk.E)
        reader_grid.columnconfigure(1, weight=1)

        status_panel = self._panel(tab, "Card")
        status_grid = ttk.Frame(status_panel, style="Panel.TFrame")
        status_grid.pack(fill=tk.X)
        ttk.Label(status_grid, text="UID", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Label(status_grid, textvariable=self.uid_var, style="Value.TLabel").grid(row=0, column=1, sticky=tk.W, pady=4)
        ttk.Label(status_grid, text="NDEF", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Label(status_grid, textvariable=self.ndef_var, style="Value.TLabel", wraplength=700).grid(
            row=1, column=1, sticky=tk.W, pady=4
        )
        ttk.Button(status_grid, text="Scan / Verify", command=self.scan_card).grid(row=0, column=2, rowspan=2, padx=(12, 0))
        status_grid.columnconfigure(1, weight=1)

        write_panel = self._panel(tab, "Payload")
        form = ttk.Frame(write_panel, style="Panel.TFrame")
        form.pack(fill=tk.X)
        ttk.Label(form, text="Preset", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.preset_combo = ttk.Combobox(form, textvariable=self.preset_var, state="readonly", width=70)
        self.preset_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.apply_selected_preset)

        ttk.Label(form, text="Type", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            form,
            textvariable=self.record_type_var,
            state="readonly",
            values=["url", "phone", "email", "text"],
            width=18,
        ).grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(form, text="Value", style="Muted.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form, textvariable=self.payload_var).grid(row=2, column=1, sticky=tk.EW, pady=5)
        form.columnconfigure(1, weight=1)

        actions = ttk.Frame(write_panel, style="Panel.TFrame")
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Write Only", command=lambda: self.write_card(False)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="Format + Write",
            style="Primary.TButton",
            command=lambda: self.write_card(True),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Open Batch", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT)

    def _build_batch_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="Batch")

        settings = self._panel(tab, "Batch Setup")
        ttk.Radiobutton(
            settings,
            text="Format + Write",
            variable=self.batch_mode_var,
            value="format_write",
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(settings, text="Write Only", variable=self.batch_mode_var, value="write_only").pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(
            settings,
            text="Allow overwrite when a card already has NDEF data",
            variable=self.batch_overwrite_var,
        ).pack(anchor=tk.W, pady=(8, 0))

        status = self._panel(tab, "Progress")
        grid = ttk.Frame(status, style="Panel.TFrame")
        grid.pack(fill=tk.X)
        ttk.Label(grid, text="Status", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(grid, textvariable=self.batch_status_var, style="Status.TLabel").grid(
            row=0, column=1, columnspan=3, sticky=tk.W, pady=5
        )
        ttk.Label(grid, text="Success", style="Muted.TLabel").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(grid, textvariable=self.batch_success_var, style="Value.TLabel").grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(grid, text="Failed", style="Muted.TLabel").grid(row=1, column=2, sticky=tk.W, padx=(24, 0), pady=5)
        ttk.Label(grid, textvariable=self.batch_failure_var, style="Value.TLabel").grid(row=1, column=3, sticky=tk.W, pady=5)
        ttk.Label(grid, text="Last UID", style="Muted.TLabel").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(grid, textvariable=self.batch_last_uid_var, style="Value.TLabel").grid(
            row=2, column=1, columnspan=3, sticky=tk.W, pady=5
        )

        actions = ttk.Frame(status, style="Panel.TFrame")
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Start / Reset", command=self.start_batch).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="Write Current Card",
            style="Primary.TButton",
            command=self.batch_write_current_card,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Stop", command=self.stop_batch).pack(side=tk.LEFT)

    def _build_settings_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="Settings")

        panel = self._panel(tab, "Business Profile")
        fields = [
            ("Business", self.business_name_var),
            ("Owner", self.owner_name_var),
            ("Default URL", self.default_url_var),
            ("Website", self.website_var),
            ("Phone", self.phone_var),
            ("Email", self.email_var),
        ]
        for row, (label, var) in enumerate(fields):
            ttk.Label(panel, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Entry(panel, textvariable=var).grid(row=row, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        panel.columnconfigure(1, weight=1)

        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.grid(row=len(fields), column=1, sticky=tk.W, padx=(10, 0), pady=(12, 0))
        ttk.Button(actions, text="Save Config", command=self.save_business_profile).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Reload Presets", command=self.load_presets).pack(side=tk.LEFT)

    def _build_activity_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="Activity")

        panel = self._panel(tab, "Activity Log", fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(
            panel,
            height=20,
            wrap=tk.WORD,
            bg="#0f172a",
            fg="#e5edf7",
            insertbackground="#e5edf7",
            relief=tk.FLAT,
            padx=12,
            pady=10,
            font=("Consolas", 10),
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(panel, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(tab)
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Open Log Folder", command=self.open_log_folder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Clear Activity", command=lambda: self.log_text.delete("1.0", tk.END)).pack(side=tk.LEFT)
        self.log("Ready. Connect the ACR122U and choose a reader.")

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def set_status(self, message: str) -> None:
        self.status_bar.configure(text=message)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.configure(cursor="watch" if busy else "")
        self.set_status(message if busy and message else "Ready")

    def get_selected_reader(self):
        reader = self.reader_map.get(self.reader_var.get())
        if reader is None:
            raise nfc.NFCError("No PC/SC reader selected.")
        return reader

    def load_presets(self) -> None:
        presets = nfc.CONFIG.get("presets", [])
        names = [preset.get("name", f"Preset {idx}") for idx, preset in enumerate(presets, start=1)]
        self.preset_combo.configure(values=names)
        if names and not self.preset_var.get():
            self.preset_var.set(names[0])
            self.apply_selected_preset()
        self.log("Presets loaded.")

    def apply_selected_preset(self, _event=None) -> None:
        name = self.preset_var.get()
        for preset in nfc.CONFIG.get("presets", []):
            if preset.get("name") == name:
                self.record_type_var.set(preset.get("type", "url"))
                self.payload_var.set(preset.get("value", ""))
                return

    def refresh_readers(self, show_errors: bool = True) -> None:
        try:
            found = nfc.get_readers()
            self.reader_map = {str(reader): reader for reader in found}
            names = list(self.reader_map.keys())
            self.reader_combo.configure(values=names)
            if names:
                suggested = next((name for name in names if "ACR122" in name.upper() or "ACS" in name.upper()), names[0])
                self.reader_var.set(suggested)
                self.connection_var.set(f"Reader ready: {suggested}")
                self.log(f"Reader ready: {suggested}")
            else:
                self.reader_var.set("")
                self.connection_var.set("No reader found")
                self.log("No PC/SC readers found.")
        except Exception as exc:  # noqa: BLE001
            self.connection_var.set("Reader error")
            self.log(f"Reader error: {exc}")
            if show_errors:
                messagebox.showerror("Reader Error", str(exc))

    def poll_worker(self) -> None:
        try:
            while True:
                kind, payload = self.worker.messages.get_nowait()
                self.set_busy(False)
                if kind == "error":
                    self.handle_worker_error(payload)
                else:
                    self.handle_worker_success(payload)
        except queue.Empty:
            pass
        self.after(120, self.poll_worker)

    def handle_worker_error(self, payload) -> None:
        if self.current_job == "batch_write" and self.batch.active:
            self.batch.failure_count += 1
            self.batch_failure_var.set(str(self.batch.failure_count))
            self.batch_status_var.set(f"Failed: {payload}")
        self.log(f"ERROR: {payload}")
        messagebox.showerror("NFC Error", str(payload))
        self.current_job = ""

    def handle_worker_success(self, payload) -> None:
        action = payload.get("action")
        uid = payload.get("uid", "")
        decoded = payload.get("decoded")

        if uid:
            self.uid_var.set(uid)

        if decoded:
            self.ndef_var.set(f"{decoded.get('type')}: {decoded.get('value')}")
        elif action in {"scan", "write", "batch_write"}:
            self.ndef_var.set("No NDEF data found" if action == "scan" else "Write complete")

        if action == "scan":
            self.log(f"Scanned UID {uid}: {self.ndef_var.get()}")
        elif action == "write":
            self.log(f"Write verified for UID {uid}.")
            messagebox.showinfo("Success", "Card write verified successfully.")
        elif action == "batch_write":
            self.batch.success_count += 1
            self.batch.seen_uids.add(uid)
            self.batch_success_var.set(str(self.batch.success_count))
            self.batch_last_uid_var.set(uid)
            self.batch_status_var.set("Success. Remove card and place the next one.")
            self.log(f"Batch write verified for UID {uid}.")

        self.current_job = ""

    def open_log_folder(self) -> None:
        nfc.ensure_log_file()
        os.startfile(nfc.LOG_DIR.resolve())  # noqa: S606 - local user action

    # ------------------------------------------------------------------
    # NFC actions
    # ------------------------------------------------------------------

    def scan_card(self) -> None:
        self.current_job = "scan"
        self.log("Scanning card...")
        self.set_busy(True, "Scanning card...")
        self.worker.run(self._scan_card_worker)

    def _scan_card_worker(self):
        reader = self.get_selected_reader()
        conn = nfc.connect_card(reader)
        try:
            uid = nfc.get_uid(conn)
            decoded = nfc.read_decoded_ndef_from_conn(conn)
            return {"action": "scan", "uid": uid, "decoded": decoded}
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

    def write_card(self, force_format: bool) -> None:
        record_type = self.record_type_var.get()
        value = self.payload_var.get().strip()
        if not value:
            messagebox.showwarning("Missing Value", "Enter a payload before writing.")
            return
        title = "Format + Write" if force_format else "Write"
        if not messagebox.askyesno(title, f"{title} this owned NFC card?"):
            self.log("Write canceled.")
            return
        self.current_job = "write"
        self.log(f"{title} started: {record_type} -> {value}")
        self.set_busy(True, f"{title} in progress...")
        self.worker.run(self._write_card_worker, record_type, value, force_format)

    def _write_card_worker(self, record_type: str, value: str, force_format: bool):
        reader = self.get_selected_reader()
        conn = nfc.connect_card(reader)
        uid = "unknown"
        action = "windows11_format_write" if force_format else "windows11_write"
        try:
            uid = nfc.get_uid(conn)
            if force_format:
                nfc.format_mifare_classic_1k_as_ndef(conn)
            nfc.write_ndef_payload_to_nfc_sectors(conn, record_type, value)
            decoded = nfc.read_decoded_ndef_from_conn(conn)
            nfc.log_write(uid, action, record_type, value, "success", f"decoded={decoded}")
            return {"action": "write", "uid": uid, "decoded": decoded}
        except Exception as exc:
            nfc.log_write(uid, action, record_type, value, "failed", str(exc))
            raise
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

    def start_batch(self) -> None:
        self.batch.reset()
        self.batch_success_var.set("0")
        self.batch_failure_var.set("0")
        self.batch_last_uid_var.set("None")
        self.batch_status_var.set("Place one card, then click Write Current Card.")
        self.log("Batch started.")

    def stop_batch(self) -> None:
        self.batch.active = False
        summary = f"Batch stopped. Success={self.batch.success_count}, failed={self.batch.failure_count}."
        self.batch_status_var.set(summary)
        self.log(summary)

    def batch_write_current_card(self) -> None:
        if not self.batch.active:
            messagebox.showwarning("Batch Not Started", "Start or reset the batch first.")
            return
        record_type = self.record_type_var.get()
        value = self.payload_var.get().strip()
        if not value:
            messagebox.showwarning("Missing Value", "Choose a preset or enter a payload first.")
            return
        force_format = self.batch_mode_var.get() == "format_write"
        allow_overwrite = bool(self.batch_overwrite_var.get())
        self.current_job = "batch_write"
        self.batch_status_var.set("Writing current card...")
        self.log(f"Batch write started: {record_type} -> {value}")
        self.set_busy(True, "Batch write in progress...")
        self.worker.run(self._batch_write_card_worker, record_type, value, force_format, allow_overwrite)

    def _batch_write_card_worker(self, record_type: str, value: str, force_format: bool, allow_overwrite: bool):
        reader = self.get_selected_reader()
        conn = nfc.connect_card(reader)
        uid = "unknown"
        action = "windows11_batch_format_write" if force_format else "windows11_batch_write"
        try:
            uid = nfc.get_uid(conn)
            if uid in self.batch.seen_uids:
                raise nfc.NFCError(f"UID {uid} was already written in this batch.")
            existing = nfc.read_decoded_ndef_from_conn(conn)
            if existing and not allow_overwrite:
                raise nfc.NFCError("Card already contains NDEF data. Enable overwrite or use another card.")
            if force_format:
                nfc.format_mifare_classic_1k_as_ndef(conn)
            nfc.write_ndef_payload_to_nfc_sectors(conn, record_type, value)
            decoded = nfc.read_decoded_ndef_from_conn(conn)
            nfc.log_write(uid, action, record_type, value, "success", f"decoded={decoded}")
            return {"action": "batch_write", "uid": uid, "decoded": decoded}
        except Exception as exc:
            nfc.log_write(uid, action, record_type, value, "failed", str(exc))
            raise
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def save_business_profile(self) -> None:
        nfc.CONFIG["business_name"] = self.business_name_var.get().strip()
        nfc.CONFIG["owner_name"] = self.owner_name_var.get().strip()
        nfc.CONFIG["default_url"] = self.default_url_var.get().strip()
        nfc.CONFIG["website_url"] = self.website_var.get().strip()
        nfc.CONFIG["phone"] = self.phone_var.get().strip()
        nfc.CONFIG["email"] = self.email_var.get().strip()
        if nfc.CONFIG.get("presets"):
            nfc.CONFIG["presets"][0]["value"] = nfc.CONFIG["default_url"]
        nfc.save_config()
        self.payload_var.set(nfc.CONFIG["default_url"])
        self.load_presets()
        self.log("Config saved.")
        messagebox.showinfo("Saved", "Config saved to config.json.")


def main() -> None:
    app = MasterNfcWriterWindows11()
    app.mainloop()


if __name__ == "__main__":
    main()
