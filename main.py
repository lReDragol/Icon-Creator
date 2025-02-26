import os
import urllib
import io
import tkinter as tk
from tkinter import colorchooser, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageGrab
import subprocess
import numpy as np
import cv2

def convert_to_png_bytes(path):
    ext = os.path.splitext(path)[1].lower()
    img = Image.open(path)
    img.load()
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        return output.getvalue()

class ImageEditorApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Icon Creator")
        self.geometry("960x640")
        self.resizable(False, False)
        self.original_image = None
        self.processed_image = None
        self.tk_image = None
        self.pipette_mode = False
        self.gradient_color = "#000000"
        self.gradient_enabled = tk.BooleanVar(value=True)
        self.gradient_height_var = tk.IntVar(value=360)
        self.gradient_opacity_var = tk.IntVar(value=100)
        self.gradient_intensity_var = tk.IntVar(value=110)
        self.text_color = "#ffffff"
        self.text_var = tk.StringVar()
        self.font_size_var = tk.IntVar(value=90)
        self.bold_var = tk.BooleanVar(value=False)
        self.text_dragging = False
        self.text_drag_offset = [0, 0]
        self.x_offset_var = tk.IntVar(value=25)
        self.y_offset_var = tk.IntVar(value=30)
        self.logo_var = tk.BooleanVar(value=False)
        self.logo_base_image = None
        self.dragging_logo = False
        self.drag_offset = [0, 0]
        self.logo_size_var = tk.IntVar(value=128)
        self.logo_preview_image = None
        self.logo_x_offset_var = tk.IntVar(value=0)
        self.logo_y_offset_var = tk.IntVar(value=0)
        self.logo_outline_var = tk.BooleanVar(value=False)
        self.crop_offset_x = 0
        self.crop_offset_y = 0
        self.bind_all("<Left>", self.on_arrow_key)
        self.bind_all("<Right>", self.on_arrow_key)
        self.bind_all("<Up>", self.on_arrow_key)
        self.bind_all("<Down>", self.on_arrow_key)
        self.init_ui()
        self.text_var.trace("w", lambda *args: self.update_preview())
        self.font_size_var.trace("w", lambda *args: self.update_preview())
        self.logo_size_var.trace("w", lambda *args: self.update_preview())
        self.logo_x_offset_var.trace("w", lambda *args: self.update_preview())
        self.logo_y_offset_var.trace("w", lambda *args: self.update_preview())
        self.canvas.bind("<Button-1>", self.on_preview_click)
        self.canvas.bind("<B1-Motion>", self.on_preview_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_preview_release)

    def init_ui(self):
        self.preview_frame = tk.Frame(self, width=640, height=640)
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        self.canvas = tk.Canvas(self.preview_frame, bg="#dddddd", width=640, height=640, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self.drop_image)

        self.tools_frame = tk.Frame(self, width=320, height=640, bg="#f0f0f0")
        self.tools_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.text_frame = tk.LabelFrame(self.tools_frame, text="Текст", bg="#f0f0f0")
        self.text_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(self.text_frame, text="Текст:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(self.text_frame, textvariable=self.text_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        tk.Label(self.text_frame, text="Размер:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Spinbox(self.text_frame, from_=8, to=200, textvariable=self.font_size_var, width=5).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        tk.Checkbutton(self.text_frame, text="Жирный", variable=self.bold_var, onvalue=True, offvalue=False, bg="#f0f0f0", command=self.update_preview).grid(row=1, column=2, padx=5, pady=5, sticky="w")

        tk.Button(self.text_frame, text="Цвет", command=self.choose_text_color).grid(row=2, column=0, padx=5, pady=5, sticky="w")

        tk.Label(self.text_frame, text="X:", bg="#f0f0f0").grid(row=2, column=1, padx=2, pady=5, sticky="e")
        tk.Spinbox(self.text_frame, from_=0, to=1000, textvariable=self.x_offset_var, width=5, command=self.update_preview).grid(row=2, column=2, padx=2, pady=5, sticky="w")
        tk.Label(self.text_frame, text="Y:", bg="#f0f0f0").grid(row=2, column=3, padx=2, pady=5, sticky="e")
        tk.Spinbox(self.text_frame, from_=0, to=1000, textvariable=self.y_offset_var, width=5, command=self.update_preview).grid(row=2, column=4, padx=2, pady=5, sticky="w")

        self.text_frame.columnconfigure(1, weight=1)
        self.text_frame.columnconfigure(2, weight=1)
        self.text_frame.columnconfigure(3, weight=1)
        self.text_frame.columnconfigure(4, weight=1)

        self.gradient_frame = tk.LabelFrame(self.tools_frame, text="Градиент", bg="#f0f0f0")
        self.gradient_frame.pack(fill=tk.X, padx=5, pady=5)
        for i in range(4):
            self.gradient_frame.columnconfigure(i, weight=1)

        tk.Checkbutton(self.gradient_frame, text="Градиент", variable=self.gradient_enabled, onvalue=True, offvalue=False, bg="#f0f0f0", command=self.update_preview).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(self.gradient_frame, text="Цвет", command=self.choose_gradient_color).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(self.gradient_frame, text="Пипетка", command=self.toggle_pipette_mode).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        tk.Button(self.gradient_frame, text="Средний цвет", command=self.set_average_color).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        tk.Label(self.gradient_frame, text="Высота (px):", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        tk.Scale(self.gradient_frame, from_=0, to=512, orient=tk.HORIZONTAL, variable=self.gradient_height_var, command=lambda x: self.update_preview(), length=130).grid(row=1, column=1, padx=5, pady=5, sticky="w", columnspan=3)

        tk.Label(self.gradient_frame, text="Прозрачность (%):", bg="#f0f0f0").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        tk.Scale(self.gradient_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.gradient_opacity_var, command=lambda x: self.update_preview(), length=130).grid(row=2, column=1, padx=5, pady=5, sticky="w", columnspan=3)

        tk.Label(self.gradient_frame, text="Интенсивность (%):", bg="#f0f0f0").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        tk.Scale(self.gradient_frame, from_=0, to=200, orient=tk.HORIZONTAL, variable=self.gradient_intensity_var, command=lambda x: self.update_preview(), length=130).grid(row=3, column=1, padx=5, pady=5, sticky="w", columnspan=3)

        self.logo_frame = tk.LabelFrame(self.tools_frame, text="Логотип", bg="#f0f0f0")
        self.logo_frame.pack(fill=tk.X, padx=5, pady=5)

        logo_top_frame = tk.Frame(self.logo_frame, bg="#f0f0f0")
        logo_top_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Checkbutton(logo_top_frame, text="Logo", variable=self.logo_var, onvalue=True, offvalue=False, bg="#f0f0f0", command=self.update_preview).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Checkbutton(logo_top_frame, text="Обводка", variable=self.logo_outline_var, onvalue=True, offvalue=False, bg="#f0f0f0", command=self.update_preview).pack(side=tk.LEFT, padx=5, pady=5)

        self.logo_canvas = tk.Canvas(logo_top_frame, bg="#ffffff", width=48, height=48, highlightthickness=1, highlightbackground="#888888")
        self.logo_canvas.pack(side=tk.LEFT, padx=5, pady=5)
        self.logo_canvas.drop_target_register(DND_FILES)
        self.logo_canvas.dnd_bind("<<Drop>>", self.drop_logo)
        self.logo_canvas.bind("<Double-Button-1>", self.on_logo_canvas_double_click)

        logo_bottom_frame = tk.Frame(self.logo_frame, bg="#f0f0f0")
        logo_bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(logo_bottom_frame, text="Размер:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        tk.Spinbox(logo_bottom_frame, from_=16, to=256, textvariable=self.logo_size_var, width=5).pack(side=tk.LEFT, padx=5)

        tk.Label(logo_bottom_frame, text="X:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        tk.Spinbox(logo_bottom_frame, from_=0, to=256, textvariable=self.logo_x_offset_var, width=5, command=self.update_preview).pack(side=tk.LEFT, padx=5)
        tk.Label(logo_bottom_frame, text="Y:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        tk.Spinbox(logo_bottom_frame, from_=0, to=256, textvariable=self.logo_y_offset_var, width=5, command=self.update_preview).pack(side=tk.LEFT, padx=5)

        self.tiles_frame = tk.LabelFrame(self.tools_frame, text="Плитки", bg="#f0f0f0")
        self.tiles_frame.pack(fill=tk.X, padx=5, pady=5)

        self.freeze_move_button = tk.Button(self.tiles_frame, text="Frize перемещение", command=self.toggle_freeze_move)
        self.freeze_move_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.freeze_change_button = tk.Button(self.tiles_frame, text="Frize изменение", command=self.freeze_change)
        self.freeze_change_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.save_frame = tk.Frame(self.tools_frame, bg="#f0f0f0")
        self.save_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(self.save_frame, text="Сохранить (ICO)", command=self.save_image).pack(fill=tk.X, padx=5, pady=0)

    def set_average_color(self):
        if self.processed_image:
            px = list(self.processed_image.getdata())
            r_sum, g_sum, b_sum, c = 0, 0, 0, 0
            for p in px:
                r_sum += p[0]
                g_sum += p[1]
                b_sum += p[2]
                c += 1
            if c > 0:
                r_avg = r_sum // c
                g_avg = g_sum // c
                b_avg = b_sum // c
                self.gradient_color = f"#{r_avg:02x}{g_avg:02x}{b_avg:02x}"
                self.update_preview()

    def drop_image(self, event):
        path = event.data.strip("{}")
        if path.lower().startswith("file://"):
            path = path.replace("file:///", "")
            path = path.replace("file://", "")
            path = urllib.parse.unquote(path)
        if os.path.isfile(path):
            try:
                self.original_image = Image.open(path).convert("RGBA")
                self.crop_offset_x = 0
                self.crop_offset_y = 0
                self.update_preview()
            except Exception as e:
                print("Ошибка загрузки изображения:", e)

    def drop_logo(self, event):
        path = event.data.strip("{}")
        if path.lower().startswith("file://"):
            path = path.replace("file:///", "")
            path = path.replace("file://", "")
            path = urllib.parse.unquote(path)
        if os.path.isfile(path):
            try:
                png_data = convert_to_png_bytes(path)
                temp_img = Image.open(io.BytesIO(png_data)).convert("RGBA")
                self.logo_base_image = self.crop_and_scale_to_square(temp_img)
                self.logo_x_offset_var.set(0)
                self.logo_y_offset_var.set(0)
                self.show_logo_preview()
                self.update_preview()
            except Exception as e:
                print("Ошибка загрузки логотипа:", e)

    def on_logo_canvas_double_click(self, event):
        try:
            clip_data = ImageGrab.grabclipboard()
            if isinstance(clip_data, list):
                for item in clip_data:
                    if hasattr(item, "save"):
                        clip_img = item.convert("RGBA")
                        self.logo_base_image = self.crop_and_scale_to_square(clip_img)
                        self.logo_x_offset_var.set(0)
                        self.logo_y_offset_var.set(0)
                        self.show_logo_preview()
                        self.update_preview()
                        break
            elif hasattr(clip_data, "save"):
                clip_img = clip_data.convert("RGBA")
                self.logo_base_image = self.crop_and_scale_to_square(clip_img)
                self.logo_x_offset_var.set(0)
                self.logo_y_offset_var.set(0)
                self.show_logo_preview()
                self.update_preview()
        except Exception as e:
            print("Ошибка вставки из буфера:", e)

    def crop_and_scale_to_square(self, img):
        w, h = img.size
        if w != h:
            if w > h:
                left = (w - h) // 2
                img = img.crop((left, 0, left + h, h))
            else:
                top = (h - w) // 2
                img = img.crop((0, top, w, top + w))
        return img.resize((64, 64), Image.Resampling.LANCZOS)

    def show_logo_preview(self):
        if not self.logo_base_image:
            self.logo_canvas.delete("all")
            return
        preview_50 = self.logo_base_image.resize((52, 52), Image.Resampling.NEAREST)
        self.logo_preview_image = ImageTk.PhotoImage(preview_50)
        self.logo_canvas.delete("all")
        self.logo_canvas.create_image(0, 0, anchor=tk.NW, image=self.logo_preview_image)

    def get_preview_crop(self):
        if not self.original_image:
            return None
        w, h = self.original_image.size
        side = min(w, h)
        if side <= 0:
            return None
        x = self.crop_offset_x
        y = self.crop_offset_y
        if w > h:
            if x < 0:
                x = 0
            if x + side > w:
                x = w - side
            box = (x, 0, x + side, side)
        else:
            if y < 0:
                y = 0
            if y + side > h:
                y = h - side
            box = (0, y, side, y + side)
        img = self.original_image.crop(box)
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        return img

    def build_pipeline(self, img):
        if img is None:
            return None
        img = img.copy()
        if self.gradient_enabled.get():
            img = self.apply_gradient(img)
        t = self.text_var.get().strip()
        if t:
            img = self.draw_text(img, t)
        if self.logo_var.get() and self.logo_base_image:
            try:
                s = int(self.logo_size_var.get())
            except:
                s = 64
            logo = self.logo_base_image.resize((s, s), Image.Resampling.LANCZOS)
            if self.logo_outline_var.get():
                oc = (255, 255, 255, 255)
                ot = 6
                op = 1
                sr = 0.05
                logo = logo.convert("RGBA")
                alpha = np.array(logo.split()[-1])
                tv = int((1 - sr) * 255)
                _, binary = cv2.threshold(alpha, tv, 255, cv2.THRESH_BINARY)
                if op > 0:
                    ek = np.ones((op * 2 + 1, op * 2 + 1), np.uint8)
                    sh = cv2.erode(binary, ek, iterations=1)
                else:
                    sh = binary.copy()
                dk = np.ones((ot * 2 + 1, ot * 2 + 1), np.uint8)
                dl = cv2.dilate(sh, dk, iterations=1)
                om = cv2.subtract(dl, sh)
                oi = Image.new("RGBA", logo.size, oc)
                oa = Image.fromarray(om).convert("L")
                oi.putalpha(oa)
                logo = Image.alpha_composite(oi, logo)
            lx = self.logo_x_offset_var.get()
            ly = self.logo_y_offset_var.get()
            mx = 512 - s
            my = 512 - s
            if lx > mx:
                lx = mx
            if ly > my:
                ly = my
            tmp = img.copy()
            tmp.alpha_composite(logo, dest=(lx, ly))
            img = tmp
        return img

    def update_preview(self):
        pc = self.get_preview_crop()
        if pc is None:
            self.canvas.delete("all")
            self.processed_image = None
            return
        final = self.build_pipeline(pc)
        if not final:
            self.canvas.delete("all")
            self.processed_image = None
            return
        self.processed_image = final
        preview_img = final.resize((640, 640), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(preview_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def apply_gradient(self, base):
        w, h = base.size
        gh = self.gradient_height_var.get()
        if gh > h:
            gh = h
        op = self.gradient_opacity_var.get()
        mo = int(255 * (op / 100.0))
        it = self.gradient_intensity_var.get()
        intensity_factor = it / 100.0
        r = int(self.gradient_color[1:3], 16)
        g = int(self.gradient_color[3:5], 16)
        b = int(self.gradient_color[5:7], 16)
        ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        for i in range(gh):
            ratio = i / float(gh)
            alpha = int(mo * (1 - ratio) * intensity_factor)
            if alpha > 255:
                alpha = 255
            y = (h - 1) - i
            dr.line([(0, y), (w, y)], fill=(r, g, b, alpha))
        return Image.alpha_composite(base, ov)

    def draw_text(self, img, text):
        tmp = img.copy()
        dr = ImageDraw.Draw(tmp)
        fnt = self.get_font()
        bbox = dr.textbbox((0, 0), text, font=fnt)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        xo = self.x_offset_var.get()
        yo = self.y_offset_var.get()
        iw, ih = img.size
        if lw + xo * 2 <= iw:
            x = xo
            y = ih - lh - yo
            dr.text((x, y), text, font=fnt, fill=self.text_color)
        else:
            words = text.split()
            if len(words) < 2:
                x = xo
                y = ih - lh - yo
                dr.text((x, y), text, font=fnt, fill=self.text_color)
            else:
                l1 = " ".join(words[:-1])
                l2 = words[-1]
                b1 = dr.textbbox((0, 0), l1, font=fnt)
                w1 = b1[2] - b1[0]
                h1 = b1[3] - b1[1]
                b2 = dr.textbbox((0, 0), l2, font=fnt)
                w2 = b2[2] - b2[0]
                h2 = b2[3] - b2[1]
                y2 = ih - h2 - yo
                y1 = y2 - h1
                x1 = xo
                x2 = xo
                dr.text((x1, y1), l1, font=fnt, fill=self.text_color)
                dr.text((x2, y2), l2, font=fnt, fill=self.text_color)
        return tmp

    def get_font(self):
        s = self.font_size_var.get()
        b = self.bold_var.get()
        if b:
            try:
                return ImageFont.truetype("arialbd.ttf", s)
            except:
                try:
                    return ImageFont.truetype("Arial Rounded MT Bold.ttf", s)
                except:
                    return ImageFont.load_default()
        else:
            try:
                return ImageFont.truetype("arial.ttf", s)
            except:
                try:
                    return ImageFont.truetype("Arial.ttf", s)
                except:
                    return ImageFont.load_default()

    def on_preview_click(self, event):
        if self.pipette_mode and self.processed_image:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            ix = int(event.x * sx)
            iy = int(event.y * sy)
            if 0 <= ix < iw and 0 <= iy < ih:
                c = self.processed_image.getpixel((ix, iy))
                r, g, b, a = c
                self.gradient_color = f"#{r:02x}{g:02x}{b:02x}"
            self.toggle_pipette_mode()
            self.update_preview()
            return
        if self.check_text_hit(event.x, event.y):
            self.text_dragging = True
            return
        if self.logo_var.get() and self.logo_base_image:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if not self.processed_image:
                return
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            cx = int(event.x * sx)
            cy = int(event.y * sy)
            try:
                s = int(self.logo_size_var.get())
            except:
                s = 64
            lx = self.logo_x_offset_var.get()
            ly = self.logo_y_offset_var.get()
            if lx <= cx < lx + s and ly <= cy < ly + s:
                self.dragging_logo = True
                self.drag_offset = [cx - lx, cy - ly]

    def check_text_hit(self, cx, cy):
        t = self.text_var.get().strip()
        if not t:
            return False
        if not self.processed_image:
            return False
        f = self.get_font()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.processed_image.size
        sx = iw / cw
        sy = ih / ch
        ix = int(cx * sx)
        iy = int(cy * sy)
        dr = ImageDraw.Draw(self.processed_image.copy())
        bb = dr.textbbox((0, 0), t, font=f)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        xo = self.x_offset_var.get()
        yo = self.y_offset_var.get()
        by = ih - lh - yo
        if lw + xo * 2 <= iw:
            if (xo <= ix < xo + lw) and (by <= iy < by + lh):
                self.text_drag_offset = [ix - xo, iy - by]
                return True
            return False
        else:
            words = t.split()
            if len(words) < 2:
                if (xo <= ix < xo + lw) and (by <= iy < by + lh):
                    self.text_drag_offset = [ix - xo, iy - by]
                    return True
                return False
            else:
                l1 = " ".join(words[:-1])
                l2 = words[-1]
                b1 = dr.textbbox((0, 0), l1, font=f)
                w1 = b1[2] - b1[0]
                h1 = b1[3] - b1[1]
                b2 = dr.textbbox((0, 0), l2, font=f)
                w2 = b2[2] - b2[0]
                h2 = b2[3] - b2[1]
                y2 = ih - h2 - yo
                y1 = y2 - h1
                tw = max(w1, w2)
                th = h1 + h2
                if (xo <= ix < xo + tw) and (y1 <= iy < y1 + th):
                    self.text_drag_offset = [ix - xo, iy - y1]
                    return True
                return False

    def on_preview_drag(self, event):
        if self.text_dragging:
            self.drag_text(event.x, event.y)
            return
        if self.dragging_logo and self.logo_var.get() and self.logo_base_image:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if not self.processed_image:
                return
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            dx = int(event.x * sx)
            dy = int(event.y * sy)
            try:
                s = int(self.logo_size_var.get())
            except:
                s = 64
            nlx = dx - self.drag_offset[0]
            nly = dy - self.drag_offset[1]
            mx = iw - s
            my = ih - s
            if nlx < 0:
                nlx = 0
            elif nlx > mx:
                nlx = mx
            if nly < 0:
                nly = 0
            elif nly > my:
                nly = my
            self.logo_x_offset_var.set(nlx)
            self.logo_y_offset_var.set(nly)
            self.update_preview()

    def drag_text(self, cx, cy):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if not self.processed_image:
            return
        iw, ih = self.processed_image.size
        sx = iw / cw
        sy = ih / ch
        dx = int(cx * sx)
        dy = int(cy * sy)
        ox = dx - self.text_drag_offset[0]
        oy = dy - self.text_drag_offset[1]
        if ox < 0:
            ox = 0
        if oy < 0:
            oy = 0
        f = self.get_font()
        ts = self.text_var.get().strip()
        if ts:
            d = ImageDraw.Draw(self.processed_image.copy())
            bb = d.textbbox((0, 0), ts, font=f)
            w = bb[2] - bb[0]
            h = bb[3] - bb[1]
            if ox + w > iw:
                ox = iw - w
            if oy + h > ih:
                oy = ih - h
            ny = ih - oy - h
            if ny < 0:
                ny = 0
            self.y_offset_var.set(ny)
        self.x_offset_var.set(ox)
        self.update_preview()

    def on_preview_release(self, event):
        if self.dragging_logo:
            self.dragging_logo = False
        if self.text_dragging:
            self.text_dragging = False

    def toggle_pipette_mode(self):
        self.pipette_mode = not self.pipette_mode

    def choose_gradient_color(self):
        c = colorchooser.askcolor(title="Цвет градиента", initialcolor=self.gradient_color)
        if c and c[1]:
            self.gradient_color = c[1]
            self.update_preview()

    def choose_text_color(self):
        c = colorchooser.askcolor(title="Цвет текста", initialcolor=self.text_color)
        if c and c[1]:
            self.text_color = c[1]
            self.update_preview()

    def save_image(self):
        if not self.original_image:
            return
        w, h = self.original_image.size
        side = min(w, h)
        x = self.crop_offset_x
        y = self.crop_offset_y
        if w > h:
            if x < 0:
                x = 0
            if x + side > w:
                x = w - side
            box = (x, 0, x + side, side)
        else:
            if y < 0:
                y = 0
            if y + side > h:
                y = h - side
            box = (0, y, side, y + side)
        img = self.original_image.crop(box)
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        final_img = self.build_pipeline(img)
        if not final_img:
            return
        default_name = self.text_var.get().strip()
        if not default_name:
            default_name = "icon"
        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".ico",
            filetypes=[("ICO files", "*.ico"), ("All files", "*.*")]
        )
        if path:
            try:
                final_img.save(path, format="ICO")
                with open(path, "ab") as f:
                    f.write(b"\nhttps://github.com/lReDragol")
            except Exception as e:
                print("Ошибка сохранения:", e)

    def is_blocked(self):
        r = subprocess.run(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "/v", "NoChangeStartMenu"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return r.returncode == 0 and ("0x1" in r.stdout or "1" in r.stdout)

    def block_tiles(self):
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        subprocess.run(["reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                        "/v", "NoChangeStartMenu", "/t", "REG_DWORD", "/d", "1", "/f"])
        subprocess.run("start explorer.exe", shell=True)

    def unblock_tiles(self):
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        subprocess.run(["reg", "delete", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                        "/v", "NoChangeStartMenu", "/f"])
        subprocess.run("start explorer.exe", shell=True)

    def toggle_freeze_move(self):
        if self.is_blocked():
            self.unblock_tiles()
            self.freeze_move_button.config(text="Frize перемещение")
        else:
            self.block_tiles()
            self.freeze_move_button.config(text="UnFrize перемещение")

    def freeze_change(self):
        if self.is_update_blocked():
            self.unblock_tile_updates()
            self.freeze_change_button.config(text="Frize изменение")
        else:
            self.block_tile_updates()
            self.freeze_change_button.config(text="UnFrize изменение")

    def is_update_blocked(self):
        r = subprocess.run(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "/v", "NoUpdateStartMenu"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return r.returncode == 0 and ("0x1" in r.stdout or "1" in r.stdout)

    def block_tile_updates(self):
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        subprocess.run(["reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                        "/v", "NoUpdateStartMenu", "/t", "REG_DWORD", "/d", "1", "/f"])
        subprocess.run("start explorer.exe", shell=True)

    def unblock_tile_updates(self):
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        subprocess.run(["reg", "delete", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
                        "/v", "NoUpdateStartMenu", "/f"])
        subprocess.run("start explorer.exe", shell=True)

    def on_arrow_key(self, event):
        s = 10
        if event.keysym == "Left":
            self.crop_offset_x -= s
        elif event.keysym == "Right":
            self.crop_offset_x += s
        elif event.keysym == "Up":
            self.crop_offset_y -= s
        elif event.keysym == "Down":
            self.crop_offset_y += s
        self.update_preview()

if __name__ == "__main__":
    app = ImageEditorApp()
    app.mainloop()
