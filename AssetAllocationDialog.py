import tkinter as tk
from tkinter import ttk, messagebox

class AssetAllocationDialog:
    def __init__(self, parent, tickers):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("资产配置")
        self.tickers = tickers
        self.allocations = {}
        self.result = None
        self.create_widgets()

    def create_widgets(self):
        for i, ticker in enumerate(self.tickers):
            ttk.Label(self.dialog, text=f"{ticker}:").grid(row=i, column=0, padx=5, pady=5)
            entry = ttk.Entry(self.dialog, width=10)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entry.insert(0, "0")
            self.allocations[ticker] = entry

        ttk.Button(self.dialog, text="确认", command=self.validate_and_close).grid(row=len(self.tickers), column=0, columnspan=2, pady=10)

    def validate_and_close(self):
        try:
            total = sum(float(entry.get()) for entry in self.allocations.values())
            if abs(total - 100) > 0.01:  # Allow for small floating point errors
                messagebox.showerror("错误", "所有占比之和必须为100%")
                return
            self.result = {ticker: float(entry.get()) / 100 for ticker, entry in self.allocations.items()}
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def show(self):
        self.dialog.grab_set()  # 模态对话框
        self.parent.wait_window(self.dialog)
        return self.result