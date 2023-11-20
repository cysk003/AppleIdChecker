import PySimpleGUI as sg

layout = [ [sg.Text("What's your name?")],
           [sg.Input()],
           [sg.Button('Ok')] ]

window = sg.Window('Window Title', layout)

event, values = window.read()

print('Hello', values[0], "! Thanks for trying PySimpleGUI")

window.close()