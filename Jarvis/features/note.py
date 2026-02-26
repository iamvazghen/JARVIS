import subprocess
import datetime
import os

def note(text):
    date = datetime.datetime.now()
    file_name = str(date).replace(":", "-") + "-note.txt"
    with open(file_name, "w") as f:
        f.write(text)

    notepadpp = "C://Program Files (x86)//Notepad++//notepad++.exe"
    editor = notepadpp if os.path.exists(notepadpp) else "notepad.exe"
    subprocess.Popen([editor, file_name])

