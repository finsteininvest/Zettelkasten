import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font, PhotoImage
from PIL import Image, ImageTk, ImageGrab
from natsort import natsorted
import uuid

class NoteApp:
    def __init__(self, root):
        self.edit_mode = True
        self.default_font_size = 18
        self.default_font = font.Font(family="Courier New", size=self.default_font_size)

        self.root = root
        self.root.title("Zettelkasten v1.5.2")
        self.notes = {}
        self.current_note = None
        self.image_refs = []

        self.archive_dir = "notes"
        self.image_dir = os.path.join(self.archive_dir, "images")
        os.makedirs(self.image_dir, exist_ok=True)

        paned = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(paned, bg="lightgray", width=200)
        self.right_frame = tk.Frame(paned)

        paned.add(self.left_frame)
        paned.add(self.right_frame)

        self.note_listbox = tk.Listbox(self.left_frame)
        self.note_listbox.pack(fill=tk.BOTH, expand=True)
        self.note_listbox.bind('<<ListboxSelect>>', self.load_note)


        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(self.right_frame, textvariable=self.title_var, font=("Helvetica", 14, "bold"))
        self.title_entry.pack(fill=tk.X, padx=5, pady=5)
        self.title_entry.bind("<FocusOut>", self.handle_title_focus_out)

        toolbar = tk.Frame(self.right_frame)
        toolbar.pack(fill=tk.X)

        tk.Button(toolbar, text="Bold", command=lambda: self.insert_md("**", "**")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Underline", command=lambda: self.insert_md("_", "_")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Italic", command=lambda: self.insert_md("*", "*")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="H1", command=lambda: self.insert_heading(1)).pack(side=tk.LEFT)
        tk.Button(toolbar, text="H2", command=lambda: self.insert_heading(2)).pack(side=tk.LEFT)
        tk.Button(toolbar, text="H3", command=lambda: self.insert_heading(3)).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Insert Image", command=self.insert_image).pack(side=tk.LEFT)
        self.toggle_button = tk.Button(toolbar, text="Switch to Preview", command=self.toggle_edit_mode)
        self.toggle_button.pack(side=tk.LEFT)

        self.text_area = tk.Text(self.right_frame, wrap=tk.WORD)
        self.text_area.configure(font=self.default_font)
        self.title_entry.configure(font=self.default_font)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_area.bind("<Double-Button-1>", self.handle_image_double_click)

        self.root.bind('<Control-s>', self.save_note)
        self.root.bind('<Command-s>', self.save_note)
        self.root.bind('<Control-n>', self.new_note)
        self.root.bind('<Command-n>', self.new_note)

        self.root.bind('<Control-d>', self.delete_note)
        self.root.bind('<Command-d>', self.delete_note)


        italic_font = self.default_font.copy()
        italic_font.configure(slant="italic")
        self.text_area.tag_configure("italic", font=italic_font)
        bold_font = self.default_font.copy()
        bold_font.configure(weight="bold")
        self.text_area.tag_configure("bold", font=bold_font)
        underline_font = self.default_font.copy()
        underline_font.configure(underline=True)
        self.text_area.tag_configure("underline", font=underline_font)

        search_frame = tk.Frame(self.right_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(search_frame, text="Search", command=self.search_notes).pack(side=tk.LEFT)
        self.search_entry.bind("<Return>", lambda event: self.search_notes())

        self.text_area.tag_configure("h1", font=("Helvetica", self.default_font_size + 6, "bold"))
        self.text_area.tag_configure("h2", font=("Helvetica", self.default_font_size + 4, "bold"))
        self.text_area.tag_configure("h3", font=("Helvetica", self.default_font_size + 2, "bold"))
        self.text_area.tag_configure("hidden", elide=True)

        self.text_area.bind("<Control-v>", self.paste_clipboard_image)


        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Note\tCtrl+N", command=self.new_note)
        filemenu.add_command(label="Delete Note\tCtrl+D", command=self.delete_note)
        filemenu.add_command(label="Save Note\tCtrl+S", command=self.save_note)
        filemenu.add_separator()
        filemenu.add_command(label="Switch Archive…", command=self.switch_archive)
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        for widget in [self.note_listbox, self.title_entry, self.text_area]:
            widget.bind("<Control-Tab>", self.cycle_focus)

        self.load_all_notes()

    def cycle_focus(self, event=None):
        widgets = [self.note_listbox, self.title_entry, self.text_area]
        current = self.root.focus_get()

        try:
            idx = widgets.index(current)
            next_widget = widgets[(idx + 1) % len(widgets)]
        except ValueError:
            next_widget = self.note_listbox

        print(next_widget)
        next_widget.focus_set()
        return "break"  # verhindert z.B. Einrückung im Text



    def new_note(self, event=None):
        title = simpledialog.askstring("New Note", "Enter note title:")
        if title:
            title = title.strip()
            if title not in self.notes:
                self.notes[title] = ""
                self.note_listbox.insert(tk.END, title)

            self.current_note = title
            self.title_var.set(title)
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete(1.0, tk.END)

            # Sort the listbox
            titles = list(self.notes.keys())
            self.note_listbox.delete(0, tk.END)
            for t in natsorted(titles):
                self.note_listbox.insert(tk.END, t)
            
            # Select the new note
            idx = self.note_listbox.get(0, tk.END).index(title)
            self.note_listbox.selection_set(idx)
            self.note_listbox.see(idx)


    def delete_note(self, event=None):
        selection = self.note_listbox.curselection()
        if selection:
            title = self.note_listbox.get(selection[0])
            if messagebox.askyesno("Delete", f"Delete note '{title}'?"):
                self.notes.pop(title, None)
                path = os.path.join(self.archive_dir, f"{title}.md")
                if os.path.exists(path):
                    os.remove(path)
                self.note_listbox.delete(selection[0])
                self.title_var.set("")
                self.text_area.delete(1.0, tk.END)
                self.current_note = None

    def handle_title_focus_out(self, event):
        new_title = self.title_var.get().strip()
        old_title = self.current_note

        if not new_title:
            return

        if new_title == old_title:
            return  # No change

        content = self.text_area.get(1.0, tk.END).strip()

        # Rename note if title changed
        if old_title and old_title in self.notes:
            self.notes.pop(old_title)
            old_path = os.path.join(self.archive_dir, f"{old_title}.md")
            if os.path.exists(old_path):
                os.remove(old_path)

        # Update or create new
        self.notes[new_title] = content
        self.current_note = new_title

        # Update listbox
        titles = list(self.notes.keys())
        self.note_listbox.delete(0, tk.END)
        for title in sorted(titles):
            self.note_listbox.insert(tk.END, title)
        self.title_var.set(new_title)

        # Re-select the renamed note
        idx = titles.index(new_title)
        self.note_listbox.selection_set(idx)


    def insert_md(self, prefix, suffix):
        try:
            start = self.text_area.index("sel.first")
            end = self.text_area.index("sel.last")
            text = self.text_area.get(start, end)
            self.text_area.delete(start, end)
            self.text_area.insert(start, f"{prefix}{text}{suffix}")
        except tk.TclError:
            pass

    def insert_heading(self, level):
        self.text_area.insert(tk.INSERT, "\n" + "#" * level + " ")

    def insert_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.gif")])
        if filepath:
            filename = os.path.basename(filepath)
            new_path = os.path.join(self.image_dir, filename)
            if not os.path.exists(new_path):
                Image.open(filepath).save(new_path)

            # Insert real markdown text
            self.text_area.insert(tk.INSERT, f"\n![{filename}]\n")
            # Replace it immediately with image preview
            self.insert_with_preview(self.text_area.get(1.0, tk.END))

    def handle_image_double_click(self, event):
        index = self.text_area.index(f"@{event.x},{event.y}")
        line = index.split(".")[0]

        if hasattr(self, "image_positions") and line in self.image_positions:
            path = self.image_positions[line]
            if os.path.exists(path):
                try:
                    Image.open(path).show()  # opens in default viewer
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open image:\n{e}")

    def paste_clipboard_image(self, event=None):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                filename = f"{uuid.uuid4().hex[:8]}.png"
                path = os.path.join(self.image_dir, filename)
                img.save(path)
                self.text_area.insert(tk.INSERT, f"\n![{filename}]\n")
        except Exception as e:
            messagebox.showerror("Paste Error", str(e))

    def save_note(self, event=None):
        title = self.title_var.get().strip()
        if title:
            # First: convert current preview to markdown (reverse preview if needed — optional step)
            content = self.text_area.get(1.0, tk.END).strip()
            self.notes[title] = content
            with open(os.path.join(self.archive_dir, f"{title}.md"), "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Note '{title}' saved.")
            self.insert_with_preview(content)  # re-render with formatting

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode

        if self.edit_mode:
            # Switch to EDIT mode
            self.text_area.config(state=tk.NORMAL)
            raw_text = self.text_area.get(1.0, tk.END)
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, self.notes.get(self.current_note, raw_text))
            self.toggle_button.config(text="Switch to Preview")
        else:
            # Switch to PREVIEW mode
            self.text_area.config(state=tk.NORMAL)
            raw_text = self.text_area.get(1.0, tk.END)
            self.insert_with_preview(raw_text)
            self.text_area.config(state=tk.DISABLED)
            self.toggle_button.config(text="Switch to Edit")

    def search_notes(self):
        query = self.search_var.get().lower().strip()

        for i in range(self.note_listbox.size()):
             # If search field is empty → reset background
            if not query:
                self.note_listbox.itemconfig(i, bg="white")
                continue
            title = self.note_listbox.get(i)
            path = os.path.join(self.archive_dir, f"{title}.md")
            match = False

            if query in title.lower():
                match = True
            elif os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if query in content:
                        match = True

            if match:
                self.note_listbox.itemconfig(i, bg="yellow")
            else:
                self.note_listbox.itemconfig(i, bg="white")


    def load_all_notes(self):
        titles = [file[:-3] for file in os.listdir(self.archive_dir) if file.endswith(".md")]
        for title in natsorted(titles):
            print(title)
            path = os.path.join(self.archive_dir, f"{title}.md")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.notes[title] = content
                self.note_listbox.insert(tk.END, title)


    def switch_archive(self):
        new_dir = filedialog.askdirectory(title="Choose archive folder")
        print(new_dir)
        if new_dir:
            self.archive_dir = new_dir
            self.image_dir = os.path.join(self.archive_dir, "images")
            os.makedirs(self.image_dir, exist_ok=True)
            self.notes.clear()
            self.note_listbox.delete(0, tk.END)
            self.current_note = None
            self.title_var.set("")
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete(1.0, tk.END)
            print('Image dir now:', self.image_dir)
            self.load_all_notes()

    def load_note(self, event):
        selection = self.note_listbox.curselection()
        if selection:
            title = self.note_listbox.get(selection[0])
            self.current_note = title
            self.title_var.set(title)
            path = os.path.join(self.archive_dir, f"{title}.md")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.notes[title] = content
                if self.edit_mode:
                    self.text_area.config(state=tk.NORMAL)
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, content)
                else:
                    self.text_area.config(state=tk.NORMAL)
                    self.insert_with_preview(content)
                    self.text_area.config(state=tk.DISABLED)

    def insert_with_preview(self, content):
        self.text_area.delete(1.0, tk.END)
        self.image_refs.clear()
        self.image_positions = {}

        for line in content.splitlines():
            stripped = line.strip()
            #print('Checking for images')
            #print(line, stripped)
            # Headings
            if stripped.startswith("### "):
                self.text_area.insert(tk.END, stripped[4:] + "\n", "h3")
            elif stripped.startswith("## "):
                self.text_area.insert(tk.END, stripped[3:] + "\n", "h2")
            elif stripped.startswith("# "):
                self.text_area.insert(tk.END, stripped[2:] + "\n", "h1")

            # Images

            elif stripped.startswith("![") and stripped.endswith("]"):
                filename = stripped[2:-1]
                path = os.path.join(self.image_dir, filename)
                print('Preview', path)
                if os.path.exists(path):
                    try:
                        img = Image.open(path)
                        img.thumbnail((300, 300))
                        tk_img = ImageTk.PhotoImage(img)


                        # Insert hidden markdown text
                        self.text_area.insert(tk.END, f"![{filename}]\n", ("hidden",))

                        # Insert image preview
                        self.text_area.image_create(tk.END, image=tk_img)

                        # Capture the line number *after* image is placed
                        image_line = self.text_area.index(tk.INSERT).split(".")[0]
                        self.text_area.insert(tk.END, "\n")

                        # Track references
                        self.image_refs.append(tk_img)
                        self.image_positions[image_line] = path

                    except Exception as e:
                        self.text_area.insert(tk.END, f"[Image error: {e}]\n")
                else:
                    self.text_area.insert(tk.END, f"[Missing image: {filename}]\n")

            # Formatted text
            else:
                i = 0
                while i < len(line):
                    if line[i:i+2] == "**":
                        end = line.find("**", i+2)
                        if end != -1:
                            self.text_area.insert(tk.END, line[i+2:end], "bold")
                            i = end + 2
                            continue
                    elif line[i] == "*" and (i == 0 or line[i-1] != "*"):
                        end = line.find("*", i+1)
                        if end != -1 and (line[end-1] != "*"):
                            self.text_area.insert(tk.END, line[i+1:end], "italic")
                            i = end + 1
                            continue
                    elif line[i] == "_":
                        end = line.find("_", i+1)
                        if end != -1:
                            self.text_area.insert(tk.END, line[i+1:end], "underline")
                            i = end + 1
                            continue
                    self.text_area.insert(tk.END, line[i])
                    i += 1
                self.text_area.insert(tk.END, "\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = NoteApp(root)
    root.mainloop()