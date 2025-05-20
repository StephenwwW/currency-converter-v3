# 安裝：pip install requests

import tkinter as tk
from tkinter import ttk
import requests
from threading import Timer, Thread
from decimal import Decimal, InvalidOperation, getcontext

getcontext().prec = 20  # 提高 Decimal 精度

# 幣別符號對應表
currency_symbols = {
    "AUD": "A$", "CAD": "C$", "CNY": "¥", "EUR": "€",
    "GBP": "£", "HKD": "HK$", "JPY": "¥", "KRW": "₩", "TWD": "NT$", "USD": "$"
}
def get_currency_symbol(c):
    return currency_symbols.get(c, "")

# 取得匯率（從 Google Finance 擷取）
def get_exchange_rate(frm, to, cb):
    if frm == to:
        cb(to, 1.0, None)
        return
    try:
        r = requests.get(
            f'https://www.google.com/finance/quote/{frm}-{to}',
            headers={'User-Agent': 'Mozilla/5.0'}, timeout=5
        )
        r.raise_for_status()
        rate = float(r.text.split('data-last-price="')[1].split('"')[0])
        cb(to, rate, None)
    except Exception as e:
        cb(to, None, str(e))

# 防抖機制，避免頻繁觸發換算
# 來源金額輸入防抖
debounce_from = None
# 目標金額輸入防抖
debounce_to = {}

def debounce_convert_from():
    global debounce_from
    if debounce_from:
        debounce_from.cancel()
    debounce_from = Timer(0.05, convert_from)
    debounce_from.start()

def debounce_convert_to(currency):
    if currency not in to_currencies:
        return
    t = debounce_to.get(currency)
    if t:
        t.cancel()
    t = Timer(0.05, lambda: convert_to(currency))
    debounce_to[currency] = t
    t.start()

# 來源金額 → 目標金額
def convert_from():
    try:
        amt = Decimal(amount_var_from.get().replace(",", "").strip())
    except InvalidOperation:
        clear_to()
        return

    frm = from_currency_var.get()
    for c in to_currencies:
        if c == frm:
            formatted = format_decimal(amt)
            amount_vars_to[c].set(formatted)
            formula_labels_to[c].config(text=f"1 {get_currency_symbol(frm)} = 1 {get_currency_symbol(c)}")
            continue
        amount_vars_to[c].set("載入中...")
        formula_labels_to[c].config(text="")
        Thread(target=thread_from, args=(frm, c, amt), daemon=True).start()

# 執行來源金額換算的執行緒
def thread_from(frm, to, amt):
    def cb(cur, rate, err):
        if rate is not None:
            conv = amt * Decimal(str(rate))
            formatted = format_decimal(conv)
            r = round(rate, 3)
            formula = f"1 {get_currency_symbol(frm)} * {r} = {formatted} {get_currency_symbol(cur)}"
        else:
            formatted = err or "錯誤"
            formula = ""
        root.after(0, lambda: update_single(cur, formatted, formula))
    get_exchange_rate(frm, to, cb)

# 目標金額 → 來源金額
def convert_to(cur):
    try:
        amt = Decimal(amount_vars_to[cur].get().replace(",", "").strip())
    except InvalidOperation:
        amount_var_from.set("")
        formula_label_from.config(text="")
        return

    frm = from_currency_var.get()
    if cur == frm:
        formatted = format_decimal(amt)
        amount_var_from.set(formatted)
        formula_label_from.config(text=f"1 {get_currency_symbol(cur)} = 1 {get_currency_symbol(frm)}")
        return

    formula_label_from.config(text="載入中...")
    Thread(target=thread_to, args=(cur, frm, amt), daemon=True).start()

# 執行目標金額換算的執行緒
def thread_to(cur, frm, amt):
    def cb(c, rate, err):
        if rate is not None:
            conv = amt * Decimal(str(rate))
            formatted = format_decimal(conv)
            r = round(rate, 3)
            formula = f"{amt} {get_currency_symbol(cur)} * {r} = {formatted} {get_currency_symbol(frm)}"
        else:
            formatted = err or "錯誤"
            formula = ""
        root.after(0, lambda: (
            amount_var_from.set(formatted),
            formula_label_from.config(text=formula)
        ))
    get_exchange_rate(cur, frm, cb)

# 格式化金額顯示（千分位，三位小數）
def format_decimal(val: Decimal):
    return "{:,.3f}".format(val)

# 更新單一目標欄位的金額與公式
def update_single(cur, txt, formula):
    amount_vars_to[cur].set(txt)
    formula_labels_to[cur].config(text=formula)

# 清空所有目標欄位
def clear_to():
    for c in to_currencies:
        amount_vars_to[c].set("")
        formula_labels_to[c].config(text="")

# 清空所有欄位
def clear_fields(*_):
    amount_var_from.set("")
    clear_to()
    formula_label_from.config(text="")

# GUI 介面初始化
root = tk.Tk()
root.title("多幣別匯率轉換器")
root.geometry("720x480")

# 幣別清單
currencies = ["AUD", "CAD", "CNY", "EUR", "GBP", "HKD", "JPY", "KRW", "USD", "TWD"]
to_currencies = currencies.copy()

from_currency_var = tk.StringVar(value="USD")
amount_var_from = tk.StringVar()

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# 來源金額輸入欄
entry_from = tk.Entry(frame, textvariable=amount_var_from, width=14, font=("Arial", 14))
entry_from.grid(row=0, column=0, padx=5)
entry_from.bind("<KeyRelease>", lambda e: debounce_convert_from())

ttk.Combobox(frame, textvariable=from_currency_var, values=currencies,
             width=5, font=("Arial", 12)).grid(row=0, column=1, padx=5)
from_currency_var.trace_add("write", clear_fields)

tk.Label(frame, text="↔", font=("Arial", 14)).grid(row=0, column=2, padx=10)

# 目標金額輸出欄
amount_vars_to = {}
formula_labels_to = {}
for i, c in enumerate(to_currencies):
    amount_vars_to[c] = tk.StringVar()
    e = tk.Entry(frame, textvariable=amount_vars_to[c], width=14, font=("Arial", 14))
    e.grid(row=i+2, column=3, padx=5)
    e.bind("<KeyRelease>", lambda ev, cur=c: debounce_convert_to(cur))

    ttk.Label(frame, text=c, width=5, font=("Arial", 12)).grid(row=i+2, column=4, padx=5)

    lbl = tk.Label(frame, text="", font=("Arial", 12), justify="left")
    lbl.grid(row=i+2, column=5, padx=5, sticky="w")
    formula_labels_to[c] = lbl

# 來源金額公式顯示欄
formula_label_from = tk.Label(frame, text="", font=("Arial", 12), justify="left")
formula_label_from.grid(row=1, column=0, columnspan=2, sticky="w")

# 幣別說明
info = """AUD = 澳幣
CAD = 加幣
CNY = 人民幣
EUR = 歐元
GBP = 英鎊
HKD = 港幣
JPY = 日圓
KRW = 韓圓
TWD = 新台幣
USD = 美元"""
tk.Label(root, text=info, font=("Arial", 10), justify="left", anchor="w")\
  .pack(side="bottom", padx=10, pady=5, anchor="se")

root.mainloop()
