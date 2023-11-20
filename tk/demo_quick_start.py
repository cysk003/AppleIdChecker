import tkinter as tk

root = tk.Tk()  # 创建主窗口
root.title("Tkinter Quick Start")   # 设置窗口标题
root.geometry("300x150")    # 设置窗口大小

label = tk.Label(root, text="Enter something:")  # 创建标签
label.pack()    # 将标签添加到主窗口

entry = tk.Entry(root)  # 创建输入框
entry.pack()    # 将输入框添加到主窗口


# 定义按钮点击事件处理函数
def on_button_click():
    # 获取输入框的内容，并更新标签显示
    label.config(text="You entred: " + entry.get())


# 创建一个按钮组件
button = tk.Button(root, text="Click me", command=on_button_click)  # 创建按钮, 并绑定事件处理函数
button.pack()   # 将按钮添加到主窗口

root.mainloop() # 进入消息循环，等待用户操作