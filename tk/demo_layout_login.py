import tkinter as tk

root = tk.Tk()  # 创建主窗口
root.title("Login Interface")   # 设置窗口标题
root.geometry("300x200")    # 设置窗口大小

title_label = tk.Label(root, text="Login to Your Account", font=("Arial", 20))  # 创建标签
title_label.grid(row=0, column=0, columnspan=2, pady=10)    # 将标签添加到主窗口

username_label = tk.Label(root, text="Username:")  # 创建标签
username_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)    # 将标签添加到主窗口
username_entry = tk.Entry(root)  # 创建输入框
username_entry.grid(row=1, column=1, padx=5, pady=5)    # 将输入框添加到主窗口

password_label = tk.Label(root, text="Password:")  # 创建标签
password_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)    # 将标签添加到主窗口
password_entry = tk.Entry(root)  # 创建输入框
password_entry.grid(row=2, column=1, padx=5, pady=5)    # 将输入框添加到主窗口

def login():
    username = username_entry.get() # 获取输入框中的内容
    password = password_entry.get() # 获取输入框中的内容
    if username == "admin" and password == "123456":
        status_label.config(text="Login Successful")    # 更新标签显示的内容
    else:
        status_label.config(text="Login Failed")    # 更新标签显示的内容

login_button = tk.Button(root, text="Login", width=10, command=lambda: login())  # 创建按钮
login_button.grid(row=3, column=0, columnspan=2, pady=10)    # 将按钮添加到主窗口

status_label = tk.Label(root, text="")  # 创建标签
status_label.grid(row=4, column=0, columnspan=2)    # 将标签添加到主窗口

root.mainloop() # 进入消息循环，等待用户操作