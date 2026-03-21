import os
os.environ["PATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ.get("PATH", "")

from tkinterdnd2 import TkinterDnD, DND_FILES
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, Menu
import mpv
import time
import os

class EzGolfAnnotator(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("EzGolf - Swing Analyzer")
        self.geometry("1280x800")

        # Layout Containers
        self.side_panel = tk.Frame(self, width=340, bg="#2c2c2c")
        self.side_panel.pack(side=tk.RIGHT, fill=tk.Y)

        self.main_frame = tk.Frame(self, bg="black")
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Progress Frame (Bottom of Main Frame)
        self.progress_frame = tk.Frame(self.main_frame)
        self.progress_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=8)

        # Video container
        self.video_container = tk.Frame(self.main_frame, bg="black")
        self.video_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # mpv is embedded in the video container. The canvas will be in a separate overlay window.
        self.player = mpv.MPV(wid=str(int(self.video_container.winfo_id())),
                              gpu_api="d3d11",  # try "auto" or "vulkan" if black
                              input_default_bindings=False,
                              input_vo_keyboard=False)
        self.player.loop = False
        self.player['keep-open'] = 'yes'
        self.player.speed = 1.0
        self.playing = False
        self.current_video_name = "No video loaded"

        # The canvas for drawing will be created in a separate, transparent overlay window.
        self.canvas = None
        self.overlay_window = None
        self.input_window = None

        self.layers = []
        self.next_layer_id = 1
        self.tool = tk.StringVar(value="draw")
        self.drawing = False
        self.start_x = self.start_y = -1
        self.is_scrubbing = False

        self.setup_ui()
        self.after_idle(self.create_overlay)
        self.after(100, self.update_loop)

    def setup_ui(self):
        # Menu
        menubar = Menu(self)
        self.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Video...", command=self.open_video_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

        # Sidebar content
        tk.Button(self.side_panel, text="<< Hide Sidebar", command=lambda: self.toggle_sidebar()).pack(fill=tk.X, pady=5)

        # Video details in sidebar
        self.video_title_label = tk.Label(self.side_panel, text="No video loaded", bg="#2c2c2c", fg="white",
                                          font=("Arial", 12, "bold"), wraplength=300)
        self.video_title_label.pack(pady=10, padx=15, fill=tk.X)

        self.video_details_label = tk.Label(self.side_panel, text="Resolution: -\nFPS: -\nDuration: -\nPath: -",
                                            bg="#2c2c2c", fg="#aaa", font=("Arial", 10), justify="left", anchor="w", wraplength=300)
        self.video_details_label.pack(pady=5, padx=15, fill=tk.X)

        tk.Button(self.side_panel, text="Open Video", command=lambda: self.open_video_dialog()).pack(pady=10, padx=15, fill=tk.X)

        tk.Label(self.side_panel, text="Playback Speed", bg="#2c2c2c", fg="white").pack(pady=8)
        self.speed_scale = ttk.Scale(self.side_panel, from_=0.25, to=4.0, value=1.0, orient=tk.HORIZONTAL,
                                     command=self.update_speed)
        self.speed_scale.pack(padx=15, fill=tk.X)
        self.speed_label = tk.Label(self.side_panel, text="1.0×", bg="#2c2c2c", fg="white")
        self.speed_label.pack(pady=5)

        tk.Label(self.side_panel, text="Line Layers", bg="#2c2c2c", fg="white", font=("Arial", 12, "bold")).pack(pady=(15,5))

        self.layers_canvas = tk.Canvas(self.side_panel, bg="#2c2c2c", highlightthickness=0)
        self.layers_canvas.pack(fill=tk.BOTH, expand=True)
        self.layers_frame = tk.Frame(self.layers_canvas, bg="#2c2c2c")
        self.layers_canvas.create_window((0,0), window=self.layers_frame, anchor="nw")

        scrollbar = ttk.Scrollbar(self.side_panel, orient="vertical", command=self.layers_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.layers_canvas.configure(yscrollcommand=scrollbar.set)
        self.layers_frame.bind("<Configure>", lambda e: self.layers_canvas.configure(scrollregion=self.layers_canvas.bbox("all")))

        # Progress + Play controls
        self.time_label = tk.Label(self.progress_frame, text="0:00 / 0:00", width=14, anchor="w")
        self.time_label.pack(side=tk.LEFT)

        self.prev_frame_btn = tk.Button(self.progress_frame, text="<", command=self.frame_back)
        self.prev_frame_btn.pack(side=tk.LEFT, padx=2)

        self.next_frame_btn = tk.Button(self.progress_frame, text=">", command=self.frame_forward)
        self.next_frame_btn.pack(side=tk.LEFT, padx=2)

        self.progress_scale = ttk.Scale(self.progress_frame, orient="horizontal", from_=0, to=100, command=self.on_scale_scrub)
        self.progress_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,5))
        self.progress_scale.bind("<ButtonPress-1>", self.on_scrub_start)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_scrub_end)

        self.play_btn = tk.Button(self.progress_frame, text="Play", command=lambda: self.toggle_play())
        self.play_btn.pack(side=tk.RIGHT, padx=5)

        # Bindings
        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Left>", lambda e: self.frame_back())
        self.bind("<Right>", lambda e: self.frame_forward())
        self.bind("<Map>", self.on_map)
        self.bind("<Unmap>", self.on_unmap)

    def create_overlay(self):
        # 1. Visual Layer (Lines)
        # Uses transparentcolor to make the background invisible.
        self.overlay_window = tk.Toplevel(self)
        self.overlay_window.overrideredirect(True)
        self.overlay_window.transient(self)
        self.overlay_window.attributes('-transparentcolor', '#ff00ff')
        self.overlay_window.config(bg='#ff00ff')

        # The canvas for drawing goes into this overlay window
        self.canvas = tk.Canvas(self.overlay_window, bg="#ff00ff", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 2. Input Layer (Mouse Capture)
        # Uses alpha=0.01 to be effectively invisible but still capture mouse events.
        # This fixes the click-through issue caused by transparentcolor.
        self.input_window = tk.Toplevel(self)
        self.input_window.overrideredirect(True)
        self.input_window.transient(self)
        self.input_window.attributes('-alpha', 0.01)
        self.input_window.config(bg='white')

        # Bind drawing events to the input window
        self.input_window.bind("<ButtonPress-1>", lambda e: self.on_mouse_down(e))
        self.input_window.bind("<B1-Motion>", lambda e: self.on_mouse_move(e))
        self.input_window.bind("<ButtonRelease-1>", lambda e: self.on_mouse_up(e))
        self.input_window.bind("<space>", lambda e: self.toggle_play())
        self.input_window.bind("<Left>", lambda e: self.frame_back())
        self.input_window.bind("<Right>", lambda e: self.frame_forward())

        # Bind events to keep the overlay positioned correctly
        self.bind("<Configure>", self.update_overlay_geometry)
        self.bind("<FocusIn>", lambda e: self.lift_overlays())

        # Initial placement
        self.update_overlay_geometry()

    def on_map(self, event):
        if event.widget == self:
            if self.overlay_window: self.overlay_window.deiconify()
            if self.input_window: self.input_window.deiconify()

    def on_unmap(self, event):
        if event.widget == self:
            if self.overlay_window: self.overlay_window.withdraw()
            if self.input_window: self.input_window.withdraw()

    def lift_overlays(self, event=None):
        if self.overlay_window: self.overlay_window.lift()
        if self.input_window: self.input_window.lift()

    def update_overlay_geometry(self, event=None):
        if self.overlay_window and self.video_container.winfo_ismapped():
            geom = f"{self.video_container.winfo_width()}x{self.video_container.winfo_height()}+{self.video_container.winfo_rootx()}+{self.video_container.winfo_rooty()}"
            self.overlay_window.geometry(geom)
            if self.input_window:
                self.input_window.geometry(geom)

    def _format_time(self, seconds):
        if seconds is None:
            return "0:00"
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def toggle_sidebar(self):
        if self.side_panel.winfo_ismapped():
            self.side_panel.pack_forget()
        else:
            self.main_frame.pack_forget()
            self.side_panel.pack(side=tk.RIGHT, fill=tk.Y)
            self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def open_video_dialog(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if path:
            self.load_video(path)

    def load_video(self, path):
        self.current_video_name = os.path.basename(path)
        self.title(f"EzGolf - Swing Analyzer - {self.current_video_name}")

        self.player.play(path)
        self.player.pause = True
        self.playing = False
        self.layers = []
        self.next_layer_id = 1
        for child in self.layers_frame.winfo_children():
            child.destroy()

        self.video_title_label.config(text=self.current_video_name)
        self.video_details_label.config(text=f"Resolution: Loading...\nFPS: Loading...\nDuration: Loading...\nPath: {path}")

        self.play_btn.config(text="Play")
        self.after(100, lambda: self.fetch_video_info(path))

    def fetch_video_info(self, path, retries=20):
        if self.player.width is None or self.player.duration is None:
            if retries > 0:
                self.after(100, lambda: self.fetch_video_info(path, retries - 1))
            else:
                self.video_details_label.config(text=f"Resolution: Unknown\nFPS: Unknown\nDuration: Unknown\nPath: {path}")
            return

        width = self.player.width
        height = self.player.height
        fps = self.player.container_fps or self.player.estimated_vf_fps
        duration = self.player.duration

        fps_str = f"{fps:.2f}" if fps else "Unknown"
        dur_str = self._format_time(duration)

        info_text = f"Resolution: {width}x{height}\nFPS: {fps_str}\nDuration: {dur_str}\nPath: {path}"
        self.video_details_label.config(text=info_text)

    def toggle_play(self, event=None):
        # If we reached the end of the video, restart from the beginning
        if not self.playing and self.player.duration and self.player.time_pos:
            if self.player.time_pos >= self.player.duration - 0.1:
                self.player.seek(0, "absolute")

        self.playing = not self.playing
        self.player.pause = not self.playing
        self.play_btn.config(text="Pause" if self.playing else "Play")

    def update_speed(self, val):
        self.speed = float(val)
        self.speed_label.config(text=f"{self.speed:.2f}×")
        self.player.speed = self.speed

    def on_scrub_start(self, event):
        self.is_scrubbing = True

    def on_scrub_end(self, event):
        self.is_scrubbing = False
        # Do a final seek to make sure we land exactly where the drag ends
        try:
            val = self.progress_scale.get()
            self.player.seek(val, "absolute-percent")
        except Exception:
            pass

    def on_scale_scrub(self, val):
        if self.is_scrubbing:
            try:
                self.player.seek(float(val), "absolute-percent")
            except Exception:
                pass

    def frame_forward(self):
        self.playing = False
        self.player.pause = True
        self.play_btn.config(text="Play")
        self.player.command("frame-step")

    def frame_back(self):
        self.playing = False
        self.player.pause = True
        self.play_btn.config(text="Play")
        self.player.command("frame-back-step")

    def on_mouse_down(self, event):
        print(f"Mouse down event at ({event.x}, {event.y})") # For debugging
        if self.canvas and self.tool.get() == "draw":
            self.drawing = True
            self.start_x, self.start_y = event.x, event.y

    def on_mouse_move(self, event):
        if self.drawing:
            # Live preview on canvas overlay
            self.canvas.delete("preview")
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill="lime", width=3, tags="preview")

    def on_mouse_up(self, event):
        if self.drawing:
            self.drawing = False
            self.canvas.delete("preview")
            self.add_layer((self.start_x, self.start_y), (event.x, event.y))

    def add_layer(self, start, end):
        layer_id = self.next_layer_id
        self.next_layer_id += 1
        layer = {"id": layer_id, "name": f"Line {layer_id}", "start": start, "end": end, "color": "#00ff00", "visible": True}
        self.layers.append(layer)
        self.rebuild_layer_ui(layer)

    def rebuild_layer_ui(self, layer):
        row = tk.Frame(self.layers_frame, bg="#2c2c2c")
        row.pack(fill=tk.X, pady=3)
        color_btn = tk.Button(row, text="  ", width=2, bg=layer["color"], fg=layer["color"],
                              command=lambda lid=layer["id"]: self.change_color(lid))
        color_btn.pack(side=tk.LEFT, padx=(5,3))
        name_var = tk.StringVar(value=layer["name"])
        name_entry = tk.Entry(row, textvariable=name_var, bg="#444", fg="white", relief="flat", width=18)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        name_entry.bind("<Return>", lambda e, nv=name_var, lid=layer["id"]: self.update_layer_name(lid, nv.get()))
        name_entry.bind("<FocusOut>", lambda e, nv=name_var, lid=layer["id"]: self.update_layer_name(lid, nv.get()))
        var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(row, variable=var, bg="#2c2c2c", fg="white", selectcolor="#555",
                             command=lambda lid=layer["id"]: self.set_layer_visible(lid, var.get()))
        chk.pack(side=tk.LEFT, padx=5)
        del_btn = tk.Button(row, text="×", width=2, bg="#555", fg="red", relief="flat",
                            command=lambda lid=layer["id"]: self.delete_layer(lid))
        del_btn.pack(side=tk.RIGHT, padx=3)
        layer["widgets"] = {"row": row, "color_btn": color_btn, "name_var": name_var, "var": var}

    def update_layer_name(self, layer_id, new_name):
        for layer in self.layers:
            if layer["id"] == layer_id:
                layer["name"] = new_name.strip() or f"Line {layer_id}"
                break

    def change_color(self, layer_id):
        color = colorchooser.askcolor(parent=self, title="Choose Line Color")
        if color[1]:
            for layer in self.layers:
                if layer["id"] == layer_id:
                    layer["color"] = color[1]
                    layer["widgets"]["color_btn"].config(bg=color[1], fg=color[1])
                    break

    def set_layer_visible(self, layer_id, visible):
        for layer in self.layers:
            if layer["id"] == layer_id:
                layer["visible"] = visible
                break

    def delete_layer(self, layer_id):
        for layer in self.layers:
            if layer["id"] == layer_id:
                if "widgets" in layer and "row" in layer["widgets"]:
                    layer["widgets"]["row"].destroy()
                self.layers.remove(layer)
                break

    def update_loop(self):
        # Update progress bar and time label
        if self.player and self.player.duration:
            pos = self.player.time_pos or 0
            duration = self.player.duration

            if not self.is_scrubbing:
                self.progress_scale.set((pos / duration) * 100)
            self.time_label.config(text=f"{self._format_time(pos)} / {self._format_time(duration)}")

        # Redraw canvas overlays
        if self.canvas:
            self.canvas.delete("layer")
            for layer in self.layers:
                if layer["visible"]:
                    self.canvas.create_line(layer["start"], layer["end"], fill=layer["color"], width=3, tags="layer")

        self.after(100, self.update_loop)

    def destroy(self):
        self.player.terminate()
        if self.overlay_window:
            self.overlay_window.destroy()
        if self.input_window:
            self.input_window.destroy()
        super().destroy()

if __name__ == "__main__":
    app = EzGolfAnnotator()
    app.mainloop()