#!/usr/bin/env python3
"""
Master NFC Writer GUI v0.2.1.

Windows Tkinter GUI for the proven ACR122U + MIFARE Classic 1K NFC writer.

v0.2.1 adds guided batch writing:
- Write one card at a time from the GUI
- Success/failure counters
- Duplicate UID detection
- Existing NDEF warning/overwrite control
- Format + Write or Write Only mode

Run from repo root:
    python -m src.master_nfc_writer_gui

Or:
    run_gui.bat
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from src import master_nfc_writer as nfc
except ModuleNotFoundError:
    # Allows running this file directly from src/ during development.
    import master_nfc_writer as nfc  # type: ignore


class Worker:
    """Small background worker helper so NFC operations do not freeze the UI."""

    def __init__(self, app: "MasterNfcWriterGui") -> None:
        self.app = app
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()

    def run(self, target, *args, **kwargs) -> None:
        thread = threading.Thread(target=self._run, args=(target, args, kwargs), daemon=True)
        thread.start()

    def _run(self, target, args, kwargs) -> None:
        try:
            result = target(*args, **kwargs)
            self.messages.put(("success", result))
        except Exception as exc:  # noqa: BLE001 - user-facing NFC/tool errors
            self.messages.put(("error", exc))


class BatchState:
    def __init__(self) -> None:
        self.seen_uids: set[str] = set()
        self.success_count = 0
        self.failure_count = 0
        self.active = False

    def reset(self) -> None:
        self.seen_uids.clear()
        self.success_count = 0
        self.failure_count = 0
        self.active = True


class MasterNfcWriterGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Master NFC Writer")
        self.geometry("920x700")
        self.minsize(820, 600)

        self.worker = Worker(self)
        self.batch = BatchState()
        self.batch_window: tk.Toplevel | None = None

        self.reader_var = tk.StringVar()
        self.uid_var = tk.StringVar(value="No card scanned")
        self.ndef_var = tk.StringVar(value="No NDEF data loaded")
        self.record_type_var = tk.StringVar(value="url")
        self.payload_var = tk.StringVar(value=nfc.CONFIG.get("default_url", ""))
        self.preset_var = tk.StringVar()

        self.batch_status_var = tk.StringVar(value="Batch mode not started")
        self.batch_success_var = tk.StringVar(value="0")
        self.batch_failure_var = tk.StringVar(value="0")
        self.batch_last_uid_var = tk.StringVar(value="None")
        self.batch_mode_var = tk.StringVar(value="format_write")
        self.batch_overwrite_var = tk.BooleanVar(value=False)

        self.reader_map = {}

        self._build_ui()
        self.refresh_readers()
        self.load_presets()
        self.after(150, self.poll_worker)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(outer, text="Master NFC Writer", font=("Segoe UI", 18, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            outer,
            text="ACR122U + MIFARE Classic 1K phone-readable NFC business-card writer",
        )
        subtitle.pack(anchor=tk.W, pady=(0, 12))

        reader_frame = ttk.LabelFrame(outer, text="Reader")
        reader_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(reader_frame, text="Reader:").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        self.reader_combo = ttk.Combobox(reader_frame, textvariable=self.reader_var, state="readonly", width=65)
        self.reader_combo.grid(row=0, column=1, padx=8, pady=8, sticky=tk.EW)
        ttk.Button(reader_frame, text="Refresh", command=self.refresh_readers).grid(row=0, column=2, padx=8, pady=8)
        reader_frame.columnconfigure(1, weight=1)

        card_frame = ttk.LabelFrame(outer, text="Card Status")
        card_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(card_frame, text="UID:").grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(card_frame, textvariable=self.uid_var).grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)

        ttk.Label(card_frame, text="NDEF:").grid(row=1, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(card_frame, textvariable=self.ndef_var, wraplength=700).grid(row=1, column=1, padx=8, pady=6, sticky=tk.W)

        btns = ttk.Frame(card_frame)
        btns.grid(row=0, column=2, rowspan=2, padx=8, pady=8, sticky=tk.E)
        ttk.Button(btns, text="Scan / Read", command=self.scan_card).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Verify NDEF", command=self.scan_card).pack(fill=tk.X, pady=2)
        card_frame.columnconfigure(1, weight=1)

        write_frame = ttk.LabelFrame(outer, text="Write")
        write_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(write_frame, text="Preset:").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        self.preset_combo = ttk.Combobox(write_frame, textvariable=self.preset_var, state="readonly", width=65)
        self.preset_combo.grid(row=0, column=1, padx=8, pady=8, sticky=tk.EW)
        self.preset_combo.bind("<<ComboboxSelected>>", self.apply_selected_preset)

        ttk.Label(write_frame, text="Type:").grid(row=1, column=0, padx=8, pady=8, sticky=tk.W)
        type_combo = ttk.Combobox(
            write_frame,
            textvariable=self.record_type_var,
            state="readonly",
            values=["url", "phone", "email", "text"],
            width=16,
        )
        type_combo.grid(row=1, column=1, padx=8, pady=8, sticky=tk.W)

        ttk.Label(write_frame, text="Payload:").grid(row=2, column=0, padx=8, pady=8, sticky=tk.W)
        payload_entry = ttk.Entry(write_frame, textvariable=self.payload_var)
        payload_entry.grid(row=2, column=1, padx=8, pady=8, sticky=tk.EW)

        write_buttons = ttk.Frame(write_frame)
        write_buttons.grid(row=3, column=1, padx=8, pady=(4, 10), sticky=tk.W)
        ttk.Button(write_buttons, text="Write Only", command=lambda: self.write_card(force_format=False)).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(write_buttons, text="Format + Write", command=lambda: self.write_card(force_format=True)).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(write_buttons, text="Guided Batch Mode", command=self.open_batch_window).pack(side=tk.LEFT)

        write_frame.columnconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(outer, text="Activity")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=14, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log("Ready. Plug in the ACR122U, place a card, then scan.")

    def open_batch_window(self) -> None:
        if self.batch_window and self.batch_window.winfo_exists():
            self.batch_window.focus()
            return

        win = tk.Toplevel(self)
        win.title("Guided Batch Mode")
        win.geometry("760x520")
        win.minsize(700, 480)
        self.batch_window = win

        outer = ttk.Frame(win, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Guided Batch Writing", font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="Write one owned NFC business card at a time. Place a card, click Write Current Card, then remove it.",
        ).pack(anchor=tk.W, pady=(0, 12))

        settings = ttk.LabelFrame(outer, text="Batch Settings")
        settings.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(settings, text="Mode:").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        ttk.Radiobutton(settings, text="Format + Write fresh cards", variable=self.batch_mode_var, value="format_write").grid(
            row=0, column=1, padx=8, pady=8, sticky=tk.W
        )
        ttk.Radiobutton(settings, text="Write only already-formatted cards", variable=self.batch_mode_var, value="write_only").grid(
            row=0, column=2, padx=8, pady=8, sticky=tk.W
        )

        ttk.Checkbutton(
            settings,
            text="Allow overwriting cards that already contain NDEF data",
            variable=self.batch_overwrite_var,
        ).grid(row=1, column=1, columnspan=2, padx=8, pady=8, sticky=tk.W)

        status = ttk.LabelFrame(outer, text="Batch Status")
        status.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status, text="Status:").grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(status, textvariable=self.batch_status_var, wraplength=600).grid(row=0, column=1, columnspan=3, padx=8, pady=6, sticky=tk.W)

        ttk.Label(status, text="Success:").grid(row=1, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(status, textvariable=self.batch_success_var).grid(row=1, column=1, padx=8, pady=6, sticky=tk.W)

        ttk.Label(status, text="Failed:").grid(row=1, column=2, padx=8, pady=6, sticky=tk.W)
        ttk.Label(status, textvariable=self.batch_failure_var).grid(row=1, column=3, padx=8, pady=6, sticky=tk.W)

        ttk.Label(status, text="Last UID:").grid(row=2, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(status, textvariable=self.batch_last_uid_var).grid(row=2, column=1, columnspan=3, padx=8, pady=6, sticky=tk.W)

        buttons = ttk.Frame(outer)
        buttons.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(buttons, text="Start / Reset Batch", command=self.start_batch).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Write Current Card", command=self.batch_write_current_card).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Stop Batch", command=self.stop_batch).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Close", command=win.destroy).pack(side=tk.RIGHT)

        help_box = ttk.LabelFrame(outer, text="Workflow")
        help_box.pack(fill=tk.BOTH, expand=True)
        help_text = tk.Text(help_box, height=9, wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True)
        help_text.insert(
            tk.END,
            "1. Choose Format + Write for fresh blank cards, or Write Only for already-formatted cards.\n"
            "2. Click Start / Reset Batch.\n"
            "3. Place one card on the ACR122U.\n"
            "4. Click Write Current Card.\n"
            "5. Wait for success, remove the card, then place the next one.\n\n"
            "Safety: use this only on blank cards or cards you own. Do not use this on access badges, hotel cards, transit cards, employee cards, or anything that controls access.\n",
        )
        help_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def set_busy(self, busy: bool) -> None:
        self.configure(cursor="watch" if busy else "")
        if self.batch_window and self.batch_window.winfo_exists():
            self.batch_window.configure(cursor="watch" if busy else "")

    def get_selected_reader(self):
        name = self.reader_var.get()
        reader = self.reader_map.get(name)
        if reader is None:
            raise nfc.NFCError("No ACR122U/PCSC reader selected.")
        return reader

    def load_presets(self) -> None:
        presets = nfc.CONFIG.get("presets", [])
        names = [preset.get("name", f"Preset {idx}") for idx, preset in enumerate(presets, start=1)]
        self.preset_combo.configure(values=names)

        if presets:
            self.preset_combo.current(0)
            self.apply_selected_preset()

    def apply_selected_preset(self, _event=None) -> None:
        name = self.preset_var.get()
        for preset in nfc.CONFIG.get("presets", []):
            if preset.get("name") == name:
                self.record_type_var.set(preset.get("type", "url"))
                self.payload_var.set(preset.get("value", ""))
                return

    def refresh_readers(self) -> None:
        try:
            found = nfc.get_readers()
            self.reader_map = {str(reader): reader for reader in found}
            names = list(self.reader_map.keys())
            self.reader_combo.configure(values=names)

            if names:
                suggested = next((name for name in names if "ACR122" in name.upper() or "ACS" in name.upper()), names[0])
                self.reader_var.set(suggested)
                self.log(f"Reader found: {suggested}")
            else:
                self.reader_var.set("")
                self.log("No PC/SC readers found.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Reader Error", str(exc))
            self.log(f"Reader error: {exc}")

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

        self.after(150, self.poll_worker)

    def handle_worker_error(self, payload) -> None:
        self.log(f"ERROR: {payload}")
        if self.batch.active:
            self.batch.failure_count += 1
            self.batch_failure_var.set(str(self.batch.failure_count))
            self.batch_status_var.set(f"Failed: {payload}")
        messagebox.showerror("NFC Error", str(payload))

    def handle_worker_success(self, payload) -> None:
        action = payload.get("action")

        if action == "scan":
            uid = payload.get("uid", "")
            decoded = payload.get("decoded")
            self.uid_var.set(uid)

            if decoded:
                value = decoded.get("value")
                record_type = decoded.get("type")
                self.ndef_var.set(f"{record_type}: {value}")
                self.log(f"Scanned UID {uid}; NDEF {record_type}: {value}")
            else:
                self.ndef_var.set("No NDEF data found")
                self.log(f"Scanned UID {uid}; no NDEF found.")

        elif action == "write":
            uid = payload.get("uid", "")
            decoded = payload.get("decoded")
            self.uid_var.set(uid)

            if decoded:
                self.ndef_var.set(f"{decoded.get('type')}: {decoded.get('value')}")
                self.log(f"Write complete for UID {uid}: {decoded.get('value')}")
            else:
                self.ndef_var.set("Write complete; decode not available")
                self.log(f"Write complete for UID {uid}.")

            messagebox.showinfo("Success", "Card write verified successfully.")

        elif action == "batch_write":
            uid = payload.get("uid", "")
            decoded = payload.get("decoded")
            self.batch.success_count += 1
            self.batch.seen_uids.add(uid)
            self.batch_success_var.set(str(self.batch.success_count))
            self.batch_last_uid_var.set(uid)

            if decoded:
                self.batch_status_var.set(f"Success. Remove card. Last wrote: {decoded.get('value')}")
                self.ndef_var.set(f"{decoded.get('type')}: {decoded.get('value')}")
                self.log(f"Batch success UID {uid}: {decoded.get('value')}")
            else:
                self.batch_status_var.set("Success. Remove card and place the next one.")
                self.log(f"Batch success UID {uid}.")

    # ------------------------------------------------------------------
    # NFC actions
    # ------------------------------------------------------------------

    def scan_card(self) -> None:
        self.set_busy(True)
        self.log("Scanning card...")
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
            messagebox.showwarning("Missing Payload", "Enter a URL, phone number, email, or text payload.")
            return

        if force_format:
            ok = messagebox.askyesno(
                "Confirm Format + Write",
                "This will format the card as MIFARE Classic NDEF/MAD1 and write the payload.\n\n"
                "Use only on blank cards or cards you own.\n\nContinue?",
            )
        else:
            ok = messagebox.askyesno(
                "Confirm Write",
                "This will write the payload to the current card.\n\n"
                "Use only on blank cards or cards you own.\n\nContinue?",
            )

        if not ok:
            self.log("Write canceled by user.")
            return

        self.set_busy(True)
        self.log(("Format + write" if force_format else "Write") + f" started: {record_type} -> {value}")
        self.worker.run(self._write_card_worker, record_type, value, force_format)

    def _write_card_worker(self, record_type: str, value: str, force_format: bool):
        reader = self.get_selected_reader()
        conn = nfc.connect_card(reader)
        uid = "unknown"

        try:
            uid = nfc.get_uid(conn)

            if force_format:
                nfc.format_mifare_classic_1k_as_ndef(conn)

            nfc.write_ndef_payload_to_nfc_sectors(conn, record_type, value)
            decoded = nfc.read_decoded_ndef_from_conn(conn)
            nfc.log_write(
                uid,
                "gui_format_write" if force_format else "gui_write",
                record_type,
                value,
                "success",
                f"decoded={decoded}",
            )
            return {"action": "write", "uid": uid, "decoded": decoded}
        except Exception as exc:
            nfc.log_write(
                uid,
                "gui_format_write" if force_format else "gui_write",
                record_type,
                value,
                "failed",
                str(exc),
            )
            raise
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Guided batch writing
    # ------------------------------------------------------------------

    def start_batch(self) -> None:
        self.batch.reset()
        self.batch_success_var.set("0")
        self.batch_failure_var.set("0")
        self.batch_last_uid_var.set("None")
        self.batch_status_var.set("Batch started. Place one card on the reader, then click Write Current Card.")
        self.log("Guided batch mode started.")

    def stop_batch(self) -> None:
        self.batch.active = False
        self.batch_status_var.set(
            f"Batch stopped. Final totals: success={self.batch.success_count}, failed={self.batch.failure_count}"
        )
        self.log(self.batch_status_var.get())

    def batch_write_current_card(self) -> None:
        if not self.batch.active:
            messagebox.showwarning("Batch Not Started", "Click Start / Reset Batch first.")
            return

        record_type = self.record_type_var.get()
        value = self.payload_var.get().strip()
        if not value:
            messagebox.showwarning("Missing Payload", "Enter a payload or choose a preset first.")
            return

        force_format = self.batch_mode_var.get() == "format_write"
        allow_overwrite = bool(self.batch_overwrite_var.get())

        self.set_busy(True)
        self.batch_status_var.set("Writing current card...")
        self.log(
            f"Batch write started: {'Format + Write' if force_format else 'Write Only'} | "
            f"{record_type} -> {value}"
        )
        self.worker.run(self._batch_write_card_worker, record_type, value, force_format, allow_overwrite)

    def _batch_write_card_worker(self, record_type: str, value: str, force_format: bool, allow_overwrite: bool):
        reader = self.get_selected_reader()
        conn = nfc.connect_card(reader)
        uid = "unknown"

        try:
            uid = nfc.get_uid(conn)

            if uid in self.batch.seen_uids:
                raise nfc.NFCError(f"UID {uid} was already written in this batch. Remove it and place a new card.")

            existing = nfc.read_decoded_ndef_from_conn(conn)
            if existing and not allow_overwrite:
                raise nfc.NFCError(
                    "This card already contains NDEF data. Enable overwrite in Batch Settings, "
                    "or use a blank card."
                )

            if force_format:
                nfc.format_mifare_classic_1k_as_ndef(conn)

            nfc.write_ndef_payload_to_nfc_sectors(conn, record_type, value)
            decoded = nfc.read_decoded_ndef_from_conn(conn)
            nfc.log_write(
                uid,
                "gui_batch_format_write" if force_format else "gui_batch_write",
                record_type,
                value,
                "success",
                f"decoded={decoded}",
            )
            return {"action": "batch_write", "uid": uid, "decoded": decoded}
        except Exception as exc:
            nfc.log_write(
                uid,
                "gui_batch_format_write" if force_format else "gui_batch_write",
                record_type,
                value,
                "failed",
                str(exc),
            )
            raise
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass


def main() -> None:
    app = MasterNfcWriterGui()
    app.mainloop()


if __name__ == "__main__":
    main()
