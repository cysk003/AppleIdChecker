import PySimpleGUI as sg

layout = [
    [sg.Image(key="-IMAGE-")],
    [sg.Text("Image file"), sg.Input(), sg.FileBrowse()],
    [sg.Button("Load Image"), sg.Button("Exit")]
]

window = sg.Window("Image Viewer", layout)

while True:
    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    elif event == "Load Image":
        window["-IMAGE-"].update(filename=values[0])

window.close()
