import tkinter as tk
from tkinter import ttk

root = tk.Tk()  # 创建主窗口
root.title("Text Transformer")   # 设置窗口标题
root.geometry("400x200")    # 设置窗口大小

# 创建一个输入框
input_label = tk.Label(root, text="Enter your text:")  # 创建标签
input_label.pack()    # 将标签添加到主窗口
input_text = tk.Entry(root, width=50)  # 创建输入框
input_text.pack()    # 将输入框添加到主窗口

# 创建一个下拉菜单选择器
optins_label = tk.Label(root, text="Choose an action:")  # 创建标签
optins_label.pack()    # 将标签添加到主窗口
options = ["Uppercase", "Lowercase", "Reverse"]
action = ttk.Combobox(root, values=options)  # 创建下拉菜单
action.pack()   # 将下拉菜单添加到主窗口
action.set("Uppercase")  # 设置默认选项

# 创建一个输出标签
output_label = tk.Label(root, text="Result:")  # 创建标签
output_label.pack()    # 将标签添加到主窗口
result = tk.Label(root, text="", bg="light grey", width=50)  # 创建标签
result.pack()    # 将标签添加到主窗口

# 定义按钮点击事件处理函数
def transformer_text():
    text = input_text.get()  # 获取输入框的内容
    selected_action = action.get()  # 获取下拉菜单的选项
    if selected_action == "Uppercase":
        transformed = text.upper()
    elif selected_action == "Lowercase":
        transformed = text.lower()
    elif selected_action == "Reverse":
        transformed = text[::-1]
    result.config(text=transformed)  # 更新输出标签的内容

transform_button = tk.Button(root, text="Transform", command=transformer_text)  # 创建按钮, 并绑定事件处理函数
transform_button.pack()   # 将按钮添加到主窗口

root.mainloop() # 进入消息循环，等待用户操作