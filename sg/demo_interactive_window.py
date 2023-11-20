import PySimpleGUI as sg

layout = [[sg.Text("What's your name?")],
          [sg.Input(key='-IN-')],
          [sg.Text(size=(40, 1), key='-OUT-')],
          [sg.Button('Ok'), sg.Button('Quit')]
          ]

window = sg.Window('Window Title', layout)

while True:  # Event Loop
    event, values = window.read()
    print(event, values)
    if event == sg.WIN_CLOSED or event == 'Quit':
        break
        # Update the "output" text element to be the value of "input" element
    window['-OUT-'].update('Hello ' + values['-IN-'] + "! Thanks for trying PySimpleGUI",
                           text_color='red')

window.close()