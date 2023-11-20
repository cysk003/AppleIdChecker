import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Real-Time Progress Bar")
root.geometry("400x100")

# 创建一个进度条
progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progress.pack(pady=20)

def update_progress(current=0):
    # 更新进度条的值
    progress['value'] = current

    # 每次增加10%，直到100%
    if current < 100:
        root.after(1000, update_progress, current + 10)

# 启动进度更新
update_progress()

root.mainloop()