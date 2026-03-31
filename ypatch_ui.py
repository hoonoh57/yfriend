#!/usr/bin/env python3
"""
yPatch UI v2 - yFriend Development Editor
Paste -> Preview -> Validate -> Apply -> Run -> See Results
All in one GUI window.

Run: python ypatch_ui.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


# ============================================================
#  Data Models
# ============================================================

@dataclass
class FileOp:
    action: str
    path: str
    content: str = ""
    range_start: int = 0
    range_end: int = 0
    rename_to: str = ""


@dataclass
class GitOp:
    message: str
    push: bool = True


@dataclass
class PatchPlan:
    file_ops: list[FileOp] = field(default_factory=list)
    git_op: Optional[GitOp] = None


@dataclass
class ValidationError:
    op_index: int
    action: str
    path: str
    message: str
    severity: str = "ERROR"


# ============================================================
#  Parser
# ============================================================

class PatchParser:
    BLOCK_RE = re.compile(r'===FILE:(\w+)===\s*\n(.*?)---END---', re.DOTALL)
    GIT_RE = re.compile(r'===GIT===\s*\n(.*?)---END---', re.DOTALL)

    def parse(self, text: str) -> PatchPlan:
        plan = PatchPlan()

        for match in self.BLOCK_RE.finditer(text):
            action = match.group(1).upper()
            body = match.group(2)
            op = FileOp(action=action, path="")
            content_lines = []
            in_content = False

            for line in body.split("\n"):
                if not in_content:
                    if line.strip() == "---":
                        in_content = True
                        continue
                    s = line.strip()
                    if s.startswith("path:"):
                        op.path = s.split(":", 1)[1].strip()
                    elif s.startswith("range:"):
                        r = s.split(":", 1)[1].strip()
                        parts = r.split("-")
                        op.range_start = int(parts[0])
                        op.range_end = int(parts[1]) if len(parts) > 1 else int(parts[0])
                    elif s.startswith("to:"):
                        op.rename_to = s.split(":", 1)[1].strip()
                else:
                    content_lines.append(line)

            while content_lines and content_lines[-1] == "":
                content_lines.pop()
            op.content = "\n".join(content_lines)
            if op.path:
                plan.file_ops.append(op)

        git_match = self.GIT_RE.search(text)
        if git_match:
            for line in git_match.group(1).split("\n"):
                if line.strip().startswith("message:"):
                    msg = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if msg:
                        plan.git_op = GitOp(message=msg)
        return plan


# ============================================================
#  Validator
# ============================================================

class PatchValidator:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def validate(self, plan: PatchPlan) -> list[ValidationError]:
        errors = []
        for i, op in enumerate(plan.file_ops):
            target = self.base_dir / op.path

            if not op.path:
                errors.append(ValidationError(i, op.action, op.path, "path is empty", "ERROR"))
                continue

            try:
                resolved = (self.base_dir / op.path).resolve()
                if not str(resolved).startswith(str(self.base_dir.resolve())):
                    errors.append(ValidationError(i, op.action, op.path, "path outside project", "ERROR"))
                    continue
            except Exception as e:
                errors.append(ValidationError(i, op.action, op.path, "path error: " + str(e), "ERROR"))
                continue

            if op.action == "CREATE":
                if target.exists() and len(op.content.strip()) == 0:
                    old_size = target.stat().st_size
                    if old_size > 0:
                        errors.append(ValidationError(i, op.action, op.path,
                            "Blocking overwrite of " + str(old_size) + "B file with empty content", "ERROR"))

                if target.exists() and len(op.content.strip()) > 0:
                    old_size = target.stat().st_size
                    new_size = len(op.content.encode("utf-8"))
                    if old_size > 100 and new_size < old_size * 0.1:
                        errors.append(ValidationError(i, op.action, op.path,
                            "Size drop warning: " + str(old_size) + "B -> " + str(new_size) + "B", "WARNING"))

            elif op.action == "PATCH":
                if not target.exists():
                    errors.append(ValidationError(i, op.action, op.path, "File not found", "ERROR"))
                else:
                    total = len(target.read_text(encoding="utf-8").split("\n"))
                    if op.range_start < 1:
                        errors.append(ValidationError(i, op.action, op.path,
                            "range_start " + str(op.range_start) + " < 1", "ERROR"))
                    if op.range_end > total:
                        errors.append(ValidationError(i, op.action, op.path,
                            "range_end " + str(op.range_end) + " > total lines " + str(total), "ERROR"))
                    if op.range_start > op.range_end:
                        errors.append(ValidationError(i, op.action, op.path,
                            "range reversed", "ERROR"))
                    if len(op.content.strip()) == 0:
                        errors.append(ValidationError(i, op.action, op.path,
                            "PATCH content is empty", "ERROR"))

            elif op.action == "DELETE":
                if not target.exists():
                    errors.append(ValidationError(i, op.action, op.path, "File already gone", "WARNING"))

            elif op.action == "RENAME":
                if not target.exists():
                    errors.append(ValidationError(i, op.action, op.path, "Source not found", "ERROR"))
                if not op.rename_to:
                    errors.append(ValidationError(i, op.action, op.path, "to: is empty", "ERROR"))
        return errors


# ============================================================
#  Backup
# ============================================================

class BackupManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = base_dir / ".ypatch_backup" / self.timestamp
        self.manifest = []

    def snapshot(self, plan: PatchPlan) -> int:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        for op in plan.file_ops:
            target = self.base_dir / op.path
            if target.exists():
                safe = op.path.replace("/", "__").replace("\\", "__")
                bp = self.backup_dir / safe
                shutil.copy2(target, bp)
                self.manifest.append({
                    "original_path": op.path,
                    "backup_path": str(bp),
                    "size": target.stat().st_size,
                })
        with open(self.backup_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({"timestamp": self.timestamp, "files": self.manifest}, f, indent=2, ensure_ascii=False)
        return len(self.manifest)

    def rollback(self) -> int:
        restored = 0
        for entry in self.manifest:
            bp = Path(entry["backup_path"])
            orig = self.base_dir / entry["original_path"]
            if bp.exists():
                orig.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bp, orig)
                restored += 1
        return restored


# ============================================================
#  Executor (BUG FIXED)
# ============================================================

class PatchExecutor:
    def __init__(self, base_dir: Path, log_fn=None):
        self.base_dir = base_dir.resolve()  # FIXED: always use absolute path
        self.log_fn = log_fn or print

    def log(self, msg: str):
        self.log_fn(msg)

    def execute(self, plan: PatchPlan) -> tuple[bool, list[str]]:
        logs = []

        # Backup
        backup = BackupManager(self.base_dir)
        backed = backup.snapshot(plan)
        msg = "Backup: " + str(backed) + " files -> " + backup.backup_dir.name
        logs.append(msg)
        self.log(msg)

        # Execute each op
        for op in plan.file_ops:
            try:
                if op.action == "CREATE":
                    r = self._create(op)
                elif op.action == "PATCH":
                    r = self._patch(op)
                elif op.action == "APPEND":
                    r = self._append(op)
                elif op.action == "DELETE":
                    r = self._delete(op)
                elif op.action == "RENAME":
                    r = self._rename(op)
                else:
                    r = "Unknown action: " + op.action
                logs.append(r)
                self.log(r)
            except Exception as e:
                r = "FAIL " + op.action + " " + op.path + ": " + str(e)
                logs.append(r)
                self.log(r)
                self.log("Rolling back...")
                restored = backup.rollback()
                logs.append("Rolled back: " + str(restored) + " files")
                self.log("Rolled back: " + str(restored) + " files")
                return False, logs

        # Git
        if plan.git_op:
            git_logs = self._git(plan.git_op)
            logs.extend(git_logs)

        return True, logs

    def _create(self, op: FileOp) -> str:
        target = self.base_dir / op.path
        is_overwrite = target.exists()
        tag = "OVERWRITE" if is_overwrite else "CREATE"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(op.content, encoding="utf-8")

        # VERIFY write
        actual_size = target.stat().st_size
        lines = len(op.content.split("\n"))
        return "[OK] " + tag + ": " + op.path + " (" + str(lines) + " lines, " + str(actual_size) + "B)"

    def _patch(self, op: FileOp) -> str:
        target = self.base_dir / op.path
        original = target.read_text(encoding="utf-8")
        lines = original.split("\n")

        old_count = op.range_end - op.range_start + 1
        new_lines = op.content.split("\n")

        # Replace lines (1-based range)
        lines[op.range_start - 1 : op.range_end] = new_lines

        target.write_text("\n".join(lines), encoding="utf-8")

        # VERIFY
        verify = target.read_text(encoding="utf-8")
        return "[OK] PATCH: " + op.path + " L" + str(op.range_start) + "-" + str(op.range_end) + " (" + str(old_count) + " -> " + str(len(new_lines)) + " lines)"

    def _append(self, op: FileOp) -> str:
        target = self.base_dir / op.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n" + op.content)
        return "[OK] APPEND: " + op.path

    def _delete(self, op: FileOp) -> str:
        target = self.base_dir / op.path
        if target.exists():
            target.unlink()
            return "[OK] DELETE: " + op.path
        return "[WARN] DELETE: " + op.path + " (already gone)"

    def _rename(self, op: FileOp) -> str:
        source = self.base_dir / op.path
        dest = self.base_dir / op.rename_to
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        return "[OK] RENAME: " + op.path + " -> " + op.rename_to

    def _git(self, git_op: GitOp) -> list[str]:
        logs = []
        try:
            subprocess.run(["git", "add", "."], cwd=str(self.base_dir), check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", git_op.message], cwd=str(self.base_dir), check=True, capture_output=True)
            logs.append("[OK] GIT commit: " + git_op.message)
            self.log("[OK] GIT commit: " + git_op.message)
            if git_op.push:
                r = subprocess.run(["git", "push"], cwd=str(self.base_dir), capture_output=True, text=True)
                if r.returncode == 0:
                    logs.append("[OK] GIT push done")
                    self.log("[OK] GIT push done")
                else:
                    logs.append("[WARN] GIT push failed: " + r.stderr[:200])
                    self.log("[WARN] GIT push failed")
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode()[:200] if e.stderr else str(e)
            logs.append("[WARN] GIT: " + err)
            self.log("[WARN] GIT: " + err)
        return logs


# ============================================================
#  GUI Application
# ============================================================

class YPatchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("yPatch UI v2 - yFriend Dev Editor")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e2e")

        # FIXED: base_dir is always the directory containing ypatch_ui.py
        self.base_dir = Path(__file__).parent.resolve()
        self.plan: Optional[PatchPlan] = None

        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_statusbar()
        self._update_file_tree()

    # ──────── Menu ────────

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Folder...", command=self._open_folder, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="Rollback (latest backup)", command=self._rollback)
        menubar.add_cascade(label="Tools", menu=tool_menu)

        self.root.config(menu=menubar)
        self.root.bind("<Control-o>", lambda e: self._open_folder())

    # ──────── Toolbar ────────

    def _build_toolbar(self):
        tb = ttk.Frame(self.root)
        tb.pack(fill=tk.X, padx=5, pady=3)

        ttk.Button(tb, text="Open", command=self._open_folder).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(tb, text="Paste+Parse", command=self._paste_and_parse).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Validate", command=self._validate).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Apply", command=self._apply).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(tb, text="Run", command=self._run_code).pack(side=tk.LEFT, padx=2)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(tb, text="Rollback", command=self._rollback).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="Refresh", command=self._update_file_tree).pack(side=tk.LEFT, padx=2)

        ttk.Label(tb, text="  Cmd:").pack(side=tk.LEFT, padx=(15, 2))
        self.run_cmd_var = tk.StringVar(value='python main.py "test topic"')
        cmd_entry = ttk.Entry(tb, textvariable=self.run_cmd_var, width=55)
        cmd_entry.pack(side=tk.LEFT, padx=2)
        cmd_entry.bind("<Return>", lambda e: self._run_code())

    # ──────── Main Layout ────────

    def _build_main(self):
        main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pw.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Left: file tree
        left = ttk.LabelFrame(main_pw, text="Project Files")
        main_pw.add(left, weight=1)

        self.file_tree = ttk.Treeview(left, show="tree")
        tree_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.file_tree.bind("<Double-1>", self._on_tree_double_click)

        # Center: input + file view (vertical split)
        center = ttk.PanedWindow(main_pw, orient=tk.VERTICAL)
        main_pw.add(center, weight=3)

        input_frame = ttk.LabelFrame(center, text="Patch Instructions (paste here)")
        center.add(input_frame, weight=2)

        self.input_text = scrolledtext.ScrolledText(
            input_frame, wrap=tk.NONE, font=("Consolas", 11),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
            selectbackground="#264f78", undo=True,
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)

        file_view_frame = ttk.LabelFrame(center, text="File Content (read-only)")
        center.add(file_view_frame, weight=1)

        self.file_view_text = scrolledtext.ScrolledText(
            file_view_frame, wrap=tk.NONE, font=("Consolas", 11),
            bg="#1e1e2e", fg="#cdd6f4", insertbackground="white",
            state=tk.DISABLED,
        )
        self.file_view_text.pack(fill=tk.BOTH, expand=True)

        # Right: logs + run output (vertical split)
        right = ttk.PanedWindow(main_pw, orient=tk.VERTICAL)
        main_pw.add(right, weight=2)

        log_frame = ttk.LabelFrame(right, text="Validate / Apply Log")
        right.add(log_frame, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#0d1117", fg="#58a6ff", insertbackground="white",
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        run_frame = ttk.LabelFrame(right, text="Run Output (stdout / stderr)")
        right.add(run_frame, weight=1)

        self.run_text = scrolledtext.ScrolledText(
            run_frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#0d1117", fg="#7ee787", insertbackground="white",
            state=tk.DISABLED,
        )
        self.run_text.pack(fill=tk.BOTH, expand=True)
        self.run_text.tag_configure("stdout", foreground="#7ee787")
        self.run_text.tag_configure("stderr", foreground="#f85149")
        self.run_text.tag_configure("info", foreground="#58a6ff")

    # ──────── Statusbar ────────

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Project: " + str(self.base_dir))
        sb = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        sb.pack(fill=tk.X, side=tk.BOTTOM)

    # ──────── File Tree ────────

    def _update_file_tree(self):
        self.file_tree.delete(*self.file_tree.get_children())
        self._populate_tree("", self.base_dir)
        self.status_var.set("Project: " + str(self.base_dir))

    def _populate_tree(self, parent: str, path: Path):
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return
        for item in items:
            if item.name.startswith("."):
                continue
            if item.name == "__pycache__":
                continue
            display = item.name
            node = self.file_tree.insert(parent, tk.END, text=display, values=(str(item),))
            if item.is_dir():
                self._populate_tree(node, item)

    def _on_tree_select(self, event):
        sel = self.file_tree.selection()
        if not sel:
            return
        vals = self.file_tree.item(sel[0], "values")
        if vals:
            path = Path(vals[0])
            if path.is_file():
                self._show_file_content(path)

    def _on_tree_double_click(self, event):
        sel = self.file_tree.selection()
        if not sel:
            return
        vals = self.file_tree.item(sel[0], "values")
        if vals:
            path = Path(vals[0])
            if path.is_file() and path.suffix == ".py":
                try:
                    rel = path.relative_to(self.base_dir)
                    self.run_cmd_var.set("python " + str(rel))
                except ValueError:
                    self.run_cmd_var.set("python " + str(path))

    def _show_file_content(self, path: Path):
        self.file_view_text.config(state=tk.NORMAL)
        self.file_view_text.delete("1.0", tk.END)
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.split("\n")
            numbered = "\n".join(str(i + 1).rjust(4) + " | " + line for i, line in enumerate(lines))
            self.file_view_text.insert("1.0", numbered)
        except Exception as e:
            self.file_view_text.insert("1.0", "Read error: " + str(e))
        self.file_view_text.config(state=tk.DISABLED)

    # ──────── Log Helpers ────────

    def _log(self, msg: str):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _log_clear(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _run_output(self, msg: str, tag: str = "stdout"):
        self.run_text.config(state=tk.NORMAL)
        self.run_text.insert(tk.END, msg + "\n", tag)
        self.run_text.see(tk.END)
        self.run_text.config(state=tk.DISABLED)

    def _run_clear(self):
        self.run_text.config(state=tk.NORMAL)
        self.run_text.delete("1.0", tk.END)
        self.run_text.config(state=tk.DISABLED)

    # ──────── Actions ────────

    def _open_folder(self):
        d = filedialog.askdirectory(title="Select project folder")
        if d:
            self.base_dir = Path(d).resolve()
            self._update_file_tree()

    def _paste_and_parse(self):
        self._log_clear()

        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            self._log("[ERROR] Clipboard is empty!")
            messagebox.showerror("Error", "Clipboard is empty.")
            return

        if not text or len(text.strip()) < 20:
            self._log("[ERROR] Clipboard content too short (" + str(len(text.strip())) + " chars)")
            messagebox.showerror("Error", "Clipboard too short (min 20 chars)")
            return

        if "===FILE:" not in text and "===GIT===" not in text:
            self._log("[ERROR] No valid YPATCH instructions found")
            messagebox.showerror("Error", "No ===FILE: found in clipboard")
            return

        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)

        self.plan = PatchParser().parse(text)

        create_count = sum(1 for o in self.plan.file_ops if o.action == "CREATE")
        patch_count = sum(1 for o in self.plan.file_ops if o.action == "PATCH")
        delete_count = sum(1 for o in self.plan.file_ops if o.action == "DELETE")

        self._log("Parsed: " + str(len(self.plan.file_ops)) + " operations")
        self._log("  CREATE=" + str(create_count) + " PATCH=" + str(patch_count) + " DELETE=" + str(delete_count))
        if self.plan.git_op:
            self._log("  GIT: " + self.plan.git_op.message)
        self._log("")

        for i, op in enumerate(self.plan.file_ops):
            target = self.base_dir / op.path
            exists = target.exists()
            if op.action == "CREATE":
                tag = "overwrite" if exists else "new"
                lines = len(op.content.split("\n"))
                self._log("  " + str(i + 1) + ". CREATE [" + tag + "] " + op.path + " (" + str(lines) + " lines)")
            elif op.action == "PATCH":
                self._log("  " + str(i + 1) + ". PATCH " + op.path + " L" + str(op.range_start) + "-" + str(op.range_end))
            elif op.action == "DELETE":
                self._log("  " + str(i + 1) + ". DELETE " + op.path)
            elif op.action == "RENAME":
                self._log("  " + str(i + 1) + ". RENAME " + op.path + " -> " + op.rename_to)
            elif op.action == "APPEND":
                self._log("  " + str(i + 1) + ". APPEND " + op.path)

        self._log("")
        self._log("Parsed OK - click Validate")
        self._log("Base dir: " + str(self.base_dir))

    def _validate(self):
        if not self.plan:
            text = self.input_text.get("1.0", tk.END)
            if "===FILE:" in text:
                self.plan = PatchParser().parse(text)
            else:
                self._log("[ERROR] No instructions to validate")
                return

        self._log("--- Validating ---")

        validator = PatchValidator(self.base_dir)
        errors = validator.validate(self.plan)

        if not errors:
            self._log("[OK] Validation passed!")
            self._log("Click Apply to proceed")
            self.status_var.set("Validated OK")
        else:
            error_count = sum(1 for e in errors if e.severity == "ERROR")
            warn_count = sum(1 for e in errors if e.severity == "WARNING")
            for e in errors:
                icon = "[ERROR]" if e.severity == "ERROR" else "[WARN]"
                self._log("  " + icon + " " + e.path + ": " + e.message)
            if error_count > 0:
                self._log("[BLOCKED] " + str(error_count) + " errors - cannot apply")
            else:
                self._log("[OK] " + str(warn_count) + " warnings - can still apply")

    def _apply(self):
        if not self.plan:
            self._log("[ERROR] Nothing to apply")
            return

        validator = PatchValidator(self.base_dir)
        errors = validator.validate(self.plan)
        if any(e.severity == "ERROR" for e in errors):
            self._log("[BLOCKED] Fix errors first")
            messagebox.showerror("Blocked", "Fix validation errors first")
            return

        count = len(self.plan.file_ops)
        if not messagebox.askyesno("Confirm", "Apply " + str(count) + " file operations?\n(backup will be created)"):
            self._log("Cancelled by user")
            return

        self._log("--- Applying ---")
        self._log("Base dir: " + str(self.base_dir))

        executor = PatchExecutor(self.base_dir, log_fn=self._log)
        success, logs = executor.execute(self.plan)

        if success:
            self._log("")
            self._log("[OK] All operations completed!")
            self.status_var.set("Applied OK")
        else:
            self._log("")
            self._log("[FAIL] Error occurred - rolled back")
            self.status_var.set("Failed - rolled back")

        self._update_file_tree()

    def _run_code(self):
        cmd = self.run_cmd_var.get().strip()
        if not cmd:
            self._run_output("[ERROR] No command", "stderr")
            return

        self._run_clear()
        self._run_output(">>> " + cmd, "info")
        self._run_output("    dir: " + str(self.base_dir), "info")
        self._run_output("-" * 50, "info")

        thread = threading.Thread(target=self._run_in_thread, args=(cmd,), daemon=True)
        thread.start()

    def _run_in_thread(self, cmd: str):
        try:
            process = subprocess.Popen(
                cmd, shell=True, cwd=str(self.base_dir),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            def read_stdout():
                for line in iter(process.stdout.readline, ""):
                    self.root.after(0, self._run_output, line.rstrip(), "stdout")
                process.stdout.close()

            def read_stderr():
                for line in iter(process.stderr.readline, ""):
                    self.root.after(0, self._run_output, line.rstrip(), "stderr")
                process.stderr.close()

            t1 = threading.Thread(target=read_stdout, daemon=True)
            t2 = threading.Thread(target=read_stderr, daemon=True)
            t1.start()
            t2.start()

            process.wait()
            t1.join(timeout=3)
            t2.join(timeout=3)

            code = process.returncode
            if code == 0:
                self.root.after(0, self._run_output, "\n[OK] Exit code: " + str(code), "info")
            else:
                self.root.after(0, self._run_output, "\n[FAIL] Exit code: " + str(code), "stderr")

            self.root.after(100, self._update_file_tree)

        except Exception as e:
            self.root.after(0, self._run_output, "[ERROR] " + str(e), "stderr")
            self.root.after(0, self._run_output, traceback.format_exc(), "stderr")

    def _rollback(self):
        backup_root = self.base_dir / ".ypatch_backup"
        if not backup_root.exists():
            messagebox.showinfo("Rollback", "No backups found.")
            return

        dirs = sorted([d for d in backup_root.iterdir() if d.is_dir()], reverse=True)
        if not dirs:
            messagebox.showinfo("Rollback", "No backups found.")
            return

        latest = dirs[0]
        manifest_path = latest / "manifest.json"
        if not manifest_path.exists():
            messagebox.showinfo("Rollback", "No manifest in " + latest.name)
            return

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_list = "\n".join("  " + e["original_path"] for e in data["files"])
        if not messagebox.askyesno("Rollback", "Restore " + str(len(data["files"])) + " files from " + latest.name + "?\n\n" + file_list):
            return

        restored = 0
        for entry in data["files"]:
            bp = Path(entry["backup_path"])
            orig = self.base_dir / entry["original_path"]
            if bp.exists():
                orig.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bp, orig)
                restored += 1

        self._log("Rolled back: " + str(restored) + " files from " + latest.name)
        self._update_file_tree()
        messagebox.showinfo("Rollback", str(restored) + " files restored")


# ============================================================
#  Entry Point
# ============================================================

def main():
    root = tk.Tk()
    style = ttk.Style()
    for t in ("clam", "alt", "default"):
        if t in style.theme_names():
            style.theme_use(t)
            break
    app = YPatchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
