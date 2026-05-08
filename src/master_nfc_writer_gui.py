#!/usr/bin/env python3
"""
Master NFC Writer GUI starter.

This is a Tkinter GUI wrapper around the working CLI core in src/master_nfc_writer.py.

Current goals:
- Keep the proven ACR122U/MIFARE Classic write logic.
- Add an easier Windows interface for scanning, verifying, formatting, writing,
  and batch-writing owned NFC business cards.
- Keep destructive actions behind confirmation dialogs.

Run:
    python .\src\master_nfc_writer_gui.py

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
        thread = threading.Thread(
            target=self._run,
            args=(target, args, kwargs),
            daemon=True,
        )
        thread.start()

    def _run(self, target, args, kwargs) -> None:
        try:
            result = target(*args, **kwargs)
            self.messages.put(("success", result))
        except Exception as exc:  # noqa: BLE001 - surface user-facing tool errors
            self.messages.put(("error", exc))


class MasterNfcWriterGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Master NFC Writer")
        self.geometry("860x620")
        self.minsize(760, 540)

        self.worker = Worker(self)

        self.reader_var = tk.StringVar()
        self.uid_var = tk.StringVar(value="No card scanned")
        self.ndef_var = tk.StringVar(value="No NDEF data loaded")
        self.record_type_var = tk.StringVar(value="url")
        self.payload_var = tk.StringVar(value=nfc.CONFIG.get("default_url", ""))
        self.preset_var = tk.StringVar()

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
        self.reader_combo = ttk.Combobox(reader_frame, textvariable=self.reader_var, state="readonly", width=55)
        self.reader_combo.grid(row=0, column=1, padx=8, pady=8, sticky=tk.EW)
        ttk.Button(reader_frame, text="Refresh", command=self.refresh_readers).grid(row=0, column=2, padx=8, pady=8)
        reader_frame.columnconfigure(1, weight=1)

        card_frame = ttk.LabelFrame(outer, text="Card Status")
        card_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(card_frame, text="UID:").grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(card_frame, textvariable=self.uid_var).grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)

        ttk.Label(card_frame, text="NDEF:").grid(row=1, column=0, padx=8, pady=6, sticky=tk.W)
        ttk.Label(card_frame, textvariable=self.ndef_var, wraplength=660).grid(row=1, column=1, padx=8, pady=6, sticky=tk.W)

        btns = ttk.Frame(card_frame)
        btns.grid(row=0, column=2, rowspan=2, padx=8, pady=8, sticky=tk.E)
        ttk.Button(btns, text="Scan / Read", command=self.scan_card).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Verify NDEF", command=self.scan_card).pack(fill=tk.X, pady=2)
        card_frame.columnconfigure(1, weight=1)

        write_frame = ttk.LabelFrame(outer, text="Write")
        write_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(write_frame, text="Preset:").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        self.preset_combo = ttk.Combobox(write_frame, textvariable=self.preset_var, state="readonly", width=55)
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
        ttk.Button(write_buttons, text="Batch Mode", command=self.batch_mode_notice).pack(side=tk.LEFT)

        write_frame.columnconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(outer, text="Activity")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log("Ready. Plug in the ACR122U, place a card, then scan.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def set_busy(self, busy: bool) -> None:
        self.configure(cursor="watch" if busy else "")

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
                    self.log(f"ERROR: {payload}")
                    messagebox.showerror("NFC Error", str(payload))
                else:
                    self.handle_worker_success(payload)
        except queue.Empty:
            pass

        self.after(150, self.poll_worker)

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
            existing = nfc.read_decoded_ndef_from_conn(conn)

            if existing and not force_format:
                # GUI has already asked for write confirmation, but surface this in logs.
                self.worker.messages.put(("success", {"action": "scan", "uid": uid, "decoded": existing}))

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

    def batch_mode_notice(self) -> None:
        messagebox.showinfo(
            "Batch Mode",
            "For this GUI starter, batch mode remains safest in the command-line app.\n\n"
            "Next GUI milestone will add guided batch writing with card remove/insert detection.",
        )


def main() -> None:
    app = MasterNfcWriterGui()
    app.mainloop()


if __name__ == "__main__":
    main()
