import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar, DateEntry
import datetime

root = tk.Tk()  # 创建主窗口
root.title("Personal Information Manager")   # 设置窗口标题
root.geometry("500x300")    # 设置窗口大小

tab_control = ttk.Notebook(root)    # 创建选项卡控件

# 创建各个选项卡
tode_tab = ttk.Frame(tab_control)   # 待办事项选项卡
schedule_tab = ttk.Frame(tab_control)   # 日程选项卡
notes_tab = ttk.Frame(tab_control)   # 备忘录选项卡

# 将各个选项卡添加到选项卡控件中
tab_control.add(tode_tab, text="To-Do List")
tab_control.add(schedule_tab, text="Schedule")
tab_control.add(notes_tab, text="Notes")

tab_control.pack(expand=1, fill="both")    # 将选项卡控件添加到主窗口

# 待办事项选项卡
task_entry = tk.Entry(tode_tab, width=50)  # 创建输入框
task_entry.pack()    # 将输入框添加到待办事项选项卡


def add_task(task):
    if task != "":
        task_list.insert(tk.END, task)  # 将输入框中输入的内容添加到列表框中, tk.END表示将内容添加到列表框的末尾
        task_entry.delete(0, tk.END)    # 清空输入框中的内容, 0表示从第一个字符开始删除, tk.END表示删除到最后一个字符
    else:
        pass
add_task_button = tk.Button(tode_tab, text="Add task", command=lambda: add_task(task_entry.get()))  # 创建按钮
add_task_button.pack()   # 将按钮添加到待办事项选项卡

task_list = tk.Listbox(tode_tab, height=30, width=10)  # 创建列表框
task_list.pack()    # 将列表框添加到待办事项选项卡

# 日程选项卡
calender_label = tk.Label(schedule_tab, text="Select a date:")  # 创建标签
calender_label.pack(pady=10)    # 将标签添加到日程选项卡, 并设置上边距, 使其与上面的组件有一定的距离

calender = DateEntry(schedule_tab, width=30, background="darkblue", foreground="white", borderwidth=2)  # 创建日历控件
calender.pack(pady=10) # 将日历控件添加到日程选项卡

# 备忘录选项卡
def save_notes():
    notes_content = notes_text.get("1.0", tk.END)  # 获取文本框中的内容
    print("Notes Saved:", notes_content)


save_notes_button = tk.Button(notes_tab, text="Save Notes", command=save_notes)  # 创建按钮
save_notes_button.pack(pady=10)   # 将按钮添加到备忘录选项卡

notes_text = tk.Text(notes_tab, height=50, width=50)  # 创建文本框
notes_text.pack(pady=10)   # 将文本框添加到备忘录选项卡

root.mainloop() # 进入消息循环，等待用户操作