import tkinter as tk
from tkinter import filedialog

root = tk.Tk()  # 创建主窗口
root.title("File Uploader")   # 设置窗口标题
root.geometry("400x200")    # 设置窗口大小

file_path_label = tk.Label(root, text="No file selected")  # 创建标签
file_path_label.pack()    # 将标签添加到主窗口

upload_button = tk.Button(root, text="Upload File", command=lambda: upload_file())  # 创建按钮
upload_button.pack()   # 将按钮添加到主窗口

def upload_file():
    file_path = filedialog.askopenfilename()  # 获取文件路径
    file_path_label.config(text=file_path)    # 更新标签显示的内容

root.mainloop() # 进入消息循环，等待用户操作