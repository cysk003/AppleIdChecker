import tkinter as tk

root = tk.Tk()  # 创建主窗口
root.title("Progress Indicator")   # 设置窗口标题
root.geometry("400x200")    # 设置窗口大小

progress_label = tk.Label(root, text="Progress: 0%", font=("Helvetica", 16))  # 创建标签
progress_label.pack(pady=20)    # 将标签添加到主窗口

def update_progress(current=0):
    progress_label.config(text="Progress: " + str(current) + "%")    # 更新标签显示的内容

    if current < 100:
        root.after(100, update_progress, current + 1)

update_progress(0)

root.mainloop() # 进入消息循环，等待用户操作