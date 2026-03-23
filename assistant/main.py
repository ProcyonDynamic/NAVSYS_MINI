import tkinter as tk

root = tk.Tk()
root.title("Portalis Assistant")
root.geometry("320x320")
root.attributes("-topmost", True)

label = tk.Label(root, text="Assistant launch OK")
label.pack(pady=20)

btn = tk.Button(root, text= "Close", command=root.destroy)
btn.pack()

root.mainloop()