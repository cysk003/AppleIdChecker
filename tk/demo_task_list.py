import tkinter as tk

root = tk.Tk()  # 创建主窗口
root.title("To-Do List")   # 设置窗口标题
root.geometry("400x300")    # 设置窗口大小

# 创建一个输入框来添加新的待办事项
task_entry = tk.Entry(root, width=50)  # 创建输入框
task_entry.pack()    # 将输入框添加到主窗口

# 创建一个按钮来添加新的待办事项
add_task_button = tk.Button(root, text="Add task", command=lambda: add_task(task_entry.get()))  # 创建按钮
add_task_button.pack()   # 将按钮添加到主窗口

# 创建一个按钮来删除选中的待办事项
delete_task_button = tk.Button(root, text="Delete Selected", command=lambda: delete_task())  # 创建按钮
delete_task_button.pack()   # 将按钮添加到主窗口

# 创建一个列表框来显示所有待办事项
task_list = tk.Listbox(root, height=40, width=10)  # 创建列表框
task_list.pack()    # 将列表框添加到主窗口



# 定义一个函数来添加新的待办事项
def add_task(task):
    if task != "":
        task_list.insert(tk.END, task)  # 将输入框中输入的内容添加到列表框中
        task_entry.delete(0, tk.END)    # 清空输入框中的内容
    else:
        pass

# 定义一个函数来删除选中的待办事项
def delete_task():
    try:
        selected_task_index = task_list.curselection()[0]  # 获取当前选中的待办事项的索引
        task_list.delete(selected_task_index)    # 删除选中的待办事项
    except:
        pass

root.mainloop() # 进入消息循环，等待用户操作