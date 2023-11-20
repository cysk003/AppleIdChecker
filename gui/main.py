import PySimpleGUI as sg

# Define the window's contents
# 定义第一行和第二行的布局


row1 = [sg.Text("总数", size=(8, 1), justification="center"), sg.Text("正确", size=(6, 1), justification="center"),
        sg.Text("双重", size=(8, 1), justification="center"), sg.Text("被锁", size=(6, 1), justification="center"),
        sg.Text("错误", size=(8, 1), justification="center")]
row2 = [sg.Text("", size=(8, 1), key="-COUNT-"),
        sg.Text("", size=(8, 1), key="-CORRECT-"),
        sg.Text(size=(8, 1), key="-2FA-"),
        sg.Text(size=(8, 1), key="-LOCKED-"),
        sg.Text(size=(8, 1), key="-ERROR-")]
row3 = [[sg.Text("输入文件：", size=(8, 1)), sg.InputText(key="-APPLEIDFILE-", size=(25, 1)),
         sg.FileBrowse(button_text="选择文件", file_types=(("文本文件", "*.txt"),))],
        [sg.Text("代理接口：", size=(8, 1)), sg.Input(
            key='-PROXYURL-')],
        [sg.Text("线程数量：", size=(8, 1)), sg.Input(
            key='-THREAD-')],
        [sg.Text("检测进度：", size=(8, 1)), sg.ProgressBar(1, orientation='h', size=(
            25, 15), key='progress', bar_color=('green', 'white'))]]
row4 = [sg.Button('Start'), sg.Button('Stop'), sg.Button('View')]

# 使用 sg.Column 并设置元素居中
layout = [[sg.Column([
    [sg.Frame('检测结果：', [row1, row2], size=(300, 60))],
    [sg.Frame('检测设置：', row3, size=(300, 120))],
    [sg.Frame('检测控制：', [row4], size=(300, 50))]
])]]


# Create the window
window = sg.Window('Apple ID 检存工具', layout)

# progress_bar = window['progress']
# 通常会做一些有用的循环
# for i in range(10000):
#     # check to see if the cancel button was clicked and exit loop if clicked
#     event, values = window.read(timeout=0)
#     if event == 'Cancel' or event == None:
#         break
#     # 检查是否单击了取消按钮，如果单击则退出循环
#     progress_bar.update_bar(i+1, 10000)
# 循环完成...需要销毁窗口，因为它仍然打开


# Display and interact with the Window using an Event Loop
while True:
    event, values = window.read()
    # 如果用户点击“Start”，处理文件
    if event == 'Start':
        file_path = values["-APPLEIDFILE-"]
        print(f"选择的文件路径是: {file_path}")
        # 在这里，您可以添加处理文件的代码
    # See if user wants to quit or window was closed
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break
    # Output a message to the window


# Finish up by removing from the screen
window.close()
