import time
import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui

from trigger_matcher import TriggerMatcher
from value_resolver import ValueResolver
from confidence_engine import classify
from context_resolver import apply_context_boost


CSV_PATH = r"D:\NAVSYS_USB\data\PORTALIS\trigger_library.csv"

from excel_context_loader import build_context_from_workbook

PORTALIS_DATA = build_context_from_workbook()

matcher = TriggerMatcher(CSV_PATH)
resolver = ValueResolver(PORTALIS_DATA)


def get_conf_color(confidence):
    if confidence == "HIGH":
        return "#2e7d32"
    if confidence == "MEDIUM":
        return "#b26a00"
    if confidence == "LOW":
        return "#c62828"
    return "#616161"


class AutofillUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Portalis Autofill")
        self.root.attributes("-topmost", True)
        self.root.geometry("760x620")
        self.root.minsize(700, 540)

        self.matches = []
        self.selected_index = None

        self.delay_seconds = tk.StringVar(value="2")
        self.status_text = tk.StringVar(value="Ready")
        self.search_text = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        top_bar = tk.Frame(self.root)
        top_bar.pack(fill="x", padx=8, pady=8)

        tk.Label(top_bar, text="Field Label / Trigger").pack(anchor="w")

        self.entry = tk.Entry(top_bar, textvariable=self.search_text)
        self.entry.pack(fill="x", pady=(4, 0))
        self.entry.bind("<Return>", self.run_match)
        self.entry.focus_set()

        controls = tk.Frame(self.root)
        controls.pack(fill="x", padx=8, pady=(0, 6))

        tk.Button(controls, text="Match", command=self.run_match).pack(side="left")
        tk.Button(controls, text="Clear", command=self.clear_results).pack(side="left", padx=(6, 0))

        tk.Label(controls, text="Delay (sec)").pack(side="left", padx=(18, 4))
        self.delay_box = ttk.Combobox(
            controls,
            textvariable=self.delay_seconds,
            values=["0", "1", "2", "3", "5"],
            width=5,
            state="readonly"
        )
        self.delay_box.pack(side="left")

        tk.Button(controls, text="Copy Selected", command=self.copy_selected).pack(side="right")
        tk.Button(controls, text="Fill + Tab", command=self.fill_selected_tab).pack(side="right", padx=(0, 6))
        tk.Button(controls, text="Fill Selected", command=self.fill_selected).pack(side="right", padx=(0, 6))

        body = tk.PanedWindow(self.root, sashrelief="raised", sashwidth=6)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left_panel = tk.Frame(body)
        right_panel = tk.Frame(body)

        body.add(left_panel, minsize=250)
        body.add(right_panel, minsize=350)

        tk.Label(left_panel, text="Matches").pack(anchor="w")

        self.result_list = tk.Listbox(left_panel, exportselection=False)
        self.result_list.pack(fill="both", expand=True, pady=(4, 0))
        self.result_list.bind("<<ListboxSelect>>", self.on_select_result)

        tk.Label(right_panel, text="Selected Match Details").pack(anchor="w")

        self.detail_text = tk.Text(right_panel, wrap="word", height=20)
        self.detail_text.pack(fill="both", expand=True, pady=(4, 0))
        self.detail_text.configure(state="disabled")

        status_bar = tk.Frame(self.root, bd=1, relief="sunken")
        status_bar.pack(fill="x", side="bottom")

        tk.Label(status_bar, textvariable=self.status_text, anchor="w").pack(fill="x", padx=6, pady=4)

    def clear_results(self):
        self.matches = []
        self.selected_index = None
        self.result_list.delete(0, tk.END)
        self._set_detail("")
        self.status_text.set("Cleared")

    def run_match(self, event=None):
        user_input = self.search_text.get().strip()

        self.result_list.delete(0, tk.END)
        self.matches = []
        self.selected_index = None
        self._set_detail("")

        if not user_input:
            self.status_text.set("Enter a field label first")
            return

        matches = matcher.match(user_input)
        matches = apply_context_boost(matches, user_input)

        if not matches:
            self.status_text.set("No matches found")
            return

        self.matches = matches[:10]

        for i, item in enumerate(self.matches):
            trig = item["trigger"]
            score = item["score"]
            confidence = classify(score)
            value = resolver.resolve(trig["target_path"])

            line = f"{i + 1}. {trig['trigger_text']}  |  {confidence}  |  {value}"
            self.result_list.insert(tk.END, line)

        self.result_list.selection_set(0)
        self.result_list.event_generate("<<ListboxSelect>>")
        self.status_text.set(f"{len(self.matches)} matches found")

    def on_select_result(self, event=None):
        selection = self.result_list.curselection()
        if not selection:
            return

        self.selected_index = selection[0]
        item = self.matches[self.selected_index]
        trig = item["trigger"]
        score = item["score"]
        confidence = classify(score)
        value = resolver.resolve(trig["target_path"])
        reasons = item.get("reasons", [])

        detail = []
        detail.append(f"Trigger      : {trig.get('trigger_text', '')}")
        detail.append(f"Aliases      : {trig.get('alias_texts', trig.get('alias_text', ''))}")
        detail.append(f"Target Path  : {trig.get('target_path', '')}")
        detail.append(f"Value        : {value}")
        detail.append(f"Confidence   : {confidence} ({score})")
        detail.append(f"Context Hint : {trig.get('context_hint', '')}")
        detail.append(f"Dynamic      : {trig.get('is_dynamic', '')}")
        detail.append(f"Source Scope : {trig.get('source_scope', '')}")
        detail.append("")
        detail.append("Reasons:")
        if reasons:
            for reason in reasons:
                detail.append(f" - {reason}")
        else:
            detail.append(" - n/a")

        self._set_detail("\n".join(detail))
        self.status_text.set(f"Selected: {trig.get('trigger_text', '')}")

    def _set_detail(self, text):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _get_selected_value(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a match first.")
            return None

        item = self.matches[self.selected_index]
        trig = item["trigger"]
        value = resolver.resolve(trig["target_path"])

        if value is None:
            messagebox.showwarning("No value", "Selected trigger resolved to empty value.")
            return None

        return str(value)

    def copy_selected(self):
        value = self._get_selected_value()
        if value is None:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status_text.set(f"Copied: {value}")

    def _countdown_status(self, seconds, action_label):
        for remaining in range(seconds, 0, -1):
            self.status_text.set(f"{action_label} in {remaining}... click target field now")
            self.root.update()
            time.sleep(1)

    def _paste_value(self, value, press_tab=False):
        try:
            delay = int(self.delay_seconds.get())
        except Exception:
            delay = 2

        if delay > 0:
            self._countdown_status(delay, "Filling")

        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()

        time.sleep(0.15)

        pyautogui.hotkey("ctrl", "v")

        if press_tab:
            time.sleep(0.10)
            pyautogui.press("tab")

        self.status_text.set("Fill complete")

    def fill_selected(self):
        value = self._get_selected_value()
        if value is None:
            return

        self._paste_value(value, press_tab=False)

    def fill_selected_tab(self):
        value = self._get_selected_value()
        if value is None:
            return

        self._paste_value(value, press_tab=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = AutofillUI(root)
    root.mainloop()