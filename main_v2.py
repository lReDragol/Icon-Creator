import os
import urllib
import io
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageQt, ImageDraw, ImageFont, ImageGrab

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QGroupBox, QVBoxLayout,
    QHBoxLayout, QGridLayout, QPushButton, QLineEdit, QSpinBox, QSlider,
    QCheckBox, QFileDialog, QColorDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QMouseEvent

def convert_to_png_bytes(path):
    ext = os.path.splitext(path)[1].lower()
    img = Image.open(path)
    img.load()
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        return output.getvalue()

class PreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.app = parent

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.app.load_image(path)

    def mousePressEvent(self, event: QMouseEvent):
        self.app.on_preview_click(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.app.on_preview_drag(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.app.on_preview_release(event)

class LogoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.app = parent

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.app.load_logo(path)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.app.on_logo_canvas_double_click()

class ImageEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Creator")
        self.setFixedSize(980, 640)

        # Глобальный стиль приложения
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f7f7f7;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid grey;
                border-radius: 5px;
                margin-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px solid #aaa;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d1d1d1;
            }
            QLineEdit, QSpinBox, QSlider, QCheckBox {
                padding: 2px;
            }
        """)

        # Исходные данные и флаги
        self.original_image = None
        self.processed_image = None
        self.pipette_mode = False
        self.gradient_color = "#000000"
        self.gradient_enabled = True
        self.gradient_height = 360
        self.gradient_opacity = 100
        self.gradient_intensity = 110
        self.text_color = "#ffffff"
        self.text_str = ""
        self.font_size = 150
        self.bold = False
        self.text_spacing = 10
        self.x_offset = 50
        self.y_offset = 90
        self.logo_enabled = False
        self.logo_base_image = None
        self.logo_size = 128
        self.logo_x_offset = 0
        self.logo_y_offset = 0
        self.logo_outline = False
        self.crop_offset_x = 0
        self.crop_offset_y = 0

        # Флаги перетаскивания
        self.text_dragging = False
        self.text_drag_offset = (0, 0)
        self.dragging_logo = False
        self.drag_offset = (0, 0)

        # Итоговый размер изображения (по умолчанию 1024x1024)
        self.final_width = 1024
        self.final_height = 1024

        self.init_ui()

    def init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Левая часть – область предпросмотра
        self.preview_label = PreviewLabel(self)
        self.preview_label.setFixedSize(640, 640)
        self.preview_label.setStyleSheet("background-color: #dddddd; border: 1px solid grey;")
        main_layout.addWidget(self.preview_label)

        # Правая часть – панель инструментов (смещена вправо на 10 пикселей)
        tools_widget = QWidget(self)
        tools_widget.setFixedWidth(320)
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setContentsMargins(10, 0, 0, 0)
        main_layout.addWidget(tools_widget)

        # Группа "Текст"
        text_group = QGroupBox("Текст")
        text_layout = QGridLayout(text_group)
        text_layout.addWidget(QLabel("Текст:"), 0, 0)
        self.text_lineedit = QLineEdit()
        text_layout.addWidget(self.text_lineedit, 0, 1, 1, 2)
        text_layout.addWidget(QLabel("Размер:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(self.font_size)
        text_layout.addWidget(self.font_size_spin, 1, 1)
        text_layout.addWidget(QLabel("Отступ:"), 1, 2)
        self.text_spacing_spin = QSpinBox()
        self.text_spacing_spin.setRange(0, 100)
        self.text_spacing_spin.setValue(self.text_spacing)
        text_layout.addWidget(self.text_spacing_spin, 1, 3)
        self.bold_checkbox = QCheckBox("Жирный")
        text_layout.addWidget(self.bold_checkbox, 1, 4)
        text_layout.addWidget(QLabel("X:"), 2, 0)
        self.x_offset_spin = QSpinBox()
        self.x_offset_spin.setRange(0, 1000)
        self.x_offset_spin.setValue(self.x_offset)
        text_layout.addWidget(self.x_offset_spin, 2, 1)
        text_layout.addWidget(QLabel("Y:"), 2, 2)
        self.y_offset_spin = QSpinBox()
        self.y_offset_spin.setRange(0, 1000)
        self.y_offset_spin.setValue(self.y_offset)
        text_layout.addWidget(self.y_offset_spin, 2, 3)
        tools_layout.addWidget(text_group)

        # Группа "Градиент"
        grad_group = QGroupBox("Градиент")
        grad_layout = QGridLayout(grad_group)
        self.gradient_checkbox = QCheckBox("Градиент")
        self.gradient_checkbox.setChecked(self.gradient_enabled)
        grad_layout.addWidget(self.gradient_checkbox, 0, 0)
        self.grad_color_button = QPushButton("Цвет")
        grad_layout.addWidget(self.grad_color_button, 0, 1)
        self.pipette_button = QPushButton("Пипетка")
        grad_layout.addWidget(self.pipette_button, 0, 2)
        self.avg_color_button = QPushButton("Средний цвет")
        grad_layout.addWidget(self.avg_color_button, 0, 3)
        grad_layout.addWidget(QLabel("Высота (px):"), 1, 0)
        self.grad_height_slider = QSlider(Qt.Horizontal)
        self.grad_height_slider.setRange(0, 1024)
        self.grad_height_slider.setValue(self.gradient_height)
        grad_layout.addWidget(self.grad_height_slider, 1, 1, 1, 3)
        grad_layout.addWidget(QLabel("Прозрачность:"), 2, 0)
        self.grad_opacity_slider = QSlider(Qt.Horizontal)
        self.grad_opacity_slider.setRange(0, 100)
        self.grad_opacity_slider.setValue(self.gradient_opacity)
        grad_layout.addWidget(self.grad_opacity_slider, 2, 1, 1, 3)
        grad_layout.addWidget(QLabel("Интенсивность:"), 3, 0)
        self.grad_intensity_slider = QSlider(Qt.Horizontal)
        self.grad_intensity_slider.setRange(0, 200)
        self.grad_intensity_slider.setValue(self.gradient_intensity)
        grad_layout.addWidget(self.grad_intensity_slider, 3, 1, 1, 3)
        tools_layout.addWidget(grad_group)

        # Группа "Логотип"
        logo_group = QGroupBox("Логотип")
        logo_layout = QVBoxLayout(logo_group)
        logo_top_layout = QHBoxLayout()
        self.logo_checkbox = QCheckBox("Logo")
        logo_top_layout.addWidget(self.logo_checkbox)
        self.logo_outline_checkbox = QCheckBox("Обводка")
        logo_top_layout.addWidget(self.logo_outline_checkbox)
        self.logo_label = LogoLabel(self)
        self.logo_label.setFixedSize(48, 48)
        self.logo_label.setStyleSheet("background-color: #ffffff; border: 1px solid #888888;")
        logo_top_layout.addWidget(self.logo_label)
        logo_layout.addLayout(logo_top_layout)
        logo_bottom_layout = QHBoxLayout()
        logo_bottom_layout.addWidget(QLabel("Размер:"))
        self.logo_size_spin = QSpinBox()
        self.logo_size_spin.setRange(16, 256)
        self.logo_size_spin.setValue(self.logo_size)
        logo_bottom_layout.addWidget(self.logo_size_spin)
        logo_bottom_layout.addWidget(QLabel("X:"))
        self.logo_x_offset_spin = QSpinBox()
        self.logo_x_offset_spin.setRange(0, 256)
        self.logo_x_offset_spin.setValue(self.logo_x_offset)
        logo_bottom_layout.addWidget(self.logo_x_offset_spin)
        logo_bottom_layout.addWidget(QLabel("Y:"))
        self.logo_y_offset_spin = QSpinBox()
        self.logo_y_offset_spin.setRange(0, 256)
        self.logo_y_offset_spin.setValue(self.logo_y_offset)
        logo_bottom_layout.addWidget(self.logo_y_offset_spin)
        logo_layout.addLayout(logo_bottom_layout)
        tools_layout.addWidget(logo_group)

        # Группа "Итоговый размер"
        final_size_group = QGroupBox("Итоговый размер")
        final_size_layout = QHBoxLayout(final_size_group)
        final_size_layout.addWidget(QLabel("Ширина:"))
        self.final_width_spin = QSpinBox()
        self.final_width_spin.setRange(256, 4096)
        self.final_width_spin.setValue(self.final_width)
        final_size_layout.addWidget(self.final_width_spin)
        final_size_layout.addWidget(QLabel("Высота:"))
        self.final_height_spin = QSpinBox()
        self.final_height_spin.setRange(256, 4096)
        self.final_height_spin.setValue(self.final_height)
        final_size_layout.addWidget(self.final_height_spin)
        tools_layout.addWidget(final_size_group)

        # Группа "Плитки"
        tiles_group = QGroupBox("Плитки")
        tiles_layout = QHBoxLayout(tiles_group)
        self.freeze_move_button = QPushButton("Frize перемещение")
        tiles_layout.addWidget(self.freeze_move_button)
        self.freeze_change_button = QPushButton("Frize изменение")
        tiles_layout.addWidget(self.freeze_change_button)
        tools_layout.addWidget(tiles_group)

        # Кнопка "Сохранить"
        save_widget = QWidget()
        save_layout = QVBoxLayout(save_widget)
        self.save_button = QPushButton("Сохранить (ICO)")
        save_layout.addWidget(self.save_button)
        tools_layout.addWidget(save_widget)

        # Связываем изменения элементов с обновлением предпросмотра
        self.text_lineedit.textChanged.connect(self.update_preview)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        self.text_spacing_spin.valueChanged.connect(self.update_preview)
        self.x_offset_spin.valueChanged.connect(self.update_preview)
        self.y_offset_spin.valueChanged.connect(self.update_preview)
        self.gradient_checkbox.stateChanged.connect(self.update_preview)
        self.grad_height_slider.valueChanged.connect(self.update_preview)
        self.grad_opacity_slider.valueChanged.connect(self.update_preview)
        self.grad_intensity_slider.valueChanged.connect(self.update_preview)
        self.logo_checkbox.stateChanged.connect(self.update_preview)
        self.logo_size_spin.valueChanged.connect(self.update_preview)
        self.logo_x_offset_spin.valueChanged.connect(self.update_preview)
        self.logo_y_offset_spin.valueChanged.connect(self.update_preview)
        self.final_width_spin.valueChanged.connect(self.update_preview)
        self.final_height_spin.valueChanged.connect(self.update_preview)

        # Связываем нажатия кнопок
        self.grad_color_button.clicked.connect(self.choose_gradient_color)
        self.pipette_button.clicked.connect(self.toggle_pipette_mode)
        self.avg_color_button.clicked.connect(self.set_average_color)
        self.save_button.clicked.connect(self.save_image)
        self.freeze_move_button.clicked.connect(self.toggle_freeze_move)
        self.freeze_change_button.clicked.connect(self.freeze_change)

    def load_image(self, path):
        try:
            self.original_image = Image.open(path).convert("RGBA")
            self.crop_offset_x = 0
            self.crop_offset_y = 0
            self.update_preview()
        except Exception as e:
            print("Ошибка загрузки изображения:", e)

    def load_logo(self, path):
        try:
            png_data = convert_to_png_bytes(path)
            temp_img = Image.open(io.BytesIO(png_data)).convert("RGBA")
            self.logo_base_image = self.crop_and_scale_to_square(temp_img)
            self.logo_x_offset = 0
            self.logo_y_offset = 0
            self.show_logo_preview()
            self.update_preview()
        except Exception as e:
            print("Ошибка загрузки логотипа:", e)

    def on_logo_canvas_double_click(self):
        try:
            clip_data = ImageGrab.grabclipboard()
            if isinstance(clip_data, list):
                for item in clip_data:
                    if hasattr(item, "save"):
                        clip_img = item.convert("RGBA")
                        self.logo_base_image = self.crop_and_scale_to_square(clip_img)
                        self.logo_x_offset = 0
                        self.logo_y_offset = 0
                        self.show_logo_preview()
                        self.update_preview()
                        break
            elif hasattr(clip_data, "save"):
                clip_img = clip_data.convert("RGBA")
                self.logo_base_image = self.crop_and_scale_to_square(clip_img)
                self.logo_x_offset = 0
                self.logo_y_offset = 0
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
            self.logo_label.clear()
            return
        preview_50 = self.logo_base_image.resize((52, 52), Image.Resampling.NEAREST)
        qimage = ImageQt.ImageQt(preview_50)
        pixmap = QPixmap.fromImage(qimage)
        self.logo_label.setPixmap(pixmap)

    def get_preview_crop(self):
        if not self.original_image:
            return None
        w, h = self.original_image.size
        # Получаем итоговый размер из SpinBox
        target_width = self.final_width_spin.value()
        target_height = self.final_height_spin.value()
        self.final_width = target_width
        self.final_height = target_height
        target_aspect = target_width / target_height
        original_aspect = w / h
        if original_aspect > target_aspect:
            # Изображение слишком широкое – обрезаем по ширине
            crop_height = h
            crop_width = int(h * target_aspect)
            x = self.crop_offset_x
            if x < 0:
                x = 0
            if x + crop_width > w:
                x = w - crop_width
            y = 0
        else:
            # Изображение слишком высокое – обрезаем по высоте
            crop_width = w
            crop_height = int(w / target_aspect)
            y = self.crop_offset_y
            if y < 0:
                y = 0
            if y + crop_height > h:
                y = h - crop_height
            x = 0
        box = (x, y, x + crop_width, y + crop_height)
        img = self.original_image.crop(box)
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        return img

    def build_pipeline(self, img):
        if img is None:
            return None
        img = img.copy()
        if self.gradient_checkbox.isChecked():
            img = self.apply_gradient(img)
        t = self.text_lineedit.text().strip()
        if t:
            img = self.draw_text(img, t)
        if self.logo_checkbox.isChecked() and self.logo_base_image:
            try:
                s = int(self.logo_size_spin.value())
            except:
                s = 64
            logo = self.logo_base_image.resize((s, s), Image.Resampling.LANCZOS)
            if self.logo_outline_checkbox.isChecked():
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
            lx = int(self.logo_x_offset_spin.value())
            ly = int(self.logo_y_offset_spin.value())
            try:
                s = int(self.logo_size_spin.value())
            except:
                s = 64
            mx = self.final_width - s
            my = self.final_height - s
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
            self.processed_image = None
            self.preview_label.clear()
            return
        final = self.build_pipeline(pc)
        if not final:
            self.processed_image = None
            self.preview_label.clear()
            return
        self.processed_image = final
        # Масштабируем итоговое изображение для предпросмотра, сохраняя пропорции
        fw, fh = final.size
        scale = min(640 / fw, 640 / fh)
        preview_size = (int(fw * scale), int(fh * scale))
        preview_img = final.resize(preview_size, Image.Resampling.NEAREST)
        qimage = ImageQt.ImageQt(preview_img)
        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap)

    def apply_gradient(self, base):
        w, h = base.size
        gh = self.grad_height_slider.value()
        if gh > h:
            gh = h
        op = self.grad_opacity_slider.value()
        mo = int(255 * (op / 100.0))
        it = self.grad_intensity_slider.value()
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
        xo = self.x_offset_spin.value()
        yo = self.y_offset_spin.value()
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
                spacing = self.text_spacing_spin.value()
                y2 = ih - h2 - yo
                y1 = y2 - h1 - spacing
                dr.text((xo, y1), l1, font=fnt, fill=self.text_color)
                dr.text((xo, y2), l2, font=fnt, fill=self.text_color)
        return tmp

    def get_font(self):
        s = self.font_size_spin.value()
        b = self.bold_checkbox.isChecked()
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

    def on_preview_click(self, event: QMouseEvent):
        if self.pipette_mode and self.processed_image:
            cw = self.preview_label.width()
            ch = self.preview_label.height()
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            pos = event.position() if hasattr(event, "position") else event.pos()
            ix = int(pos.x() * sx)
            iy = int(pos.y() * sy)
            if 0 <= ix < iw and 0 <= iy < ih:
                c = self.processed_image.getpixel((ix, iy))
                r, g, b, a = c
                self.gradient_color = f"#{r:02x}{g:02x}{b:02x}"
            self.toggle_pipette_mode()
            self.update_preview()
            return
        if self.check_text_hit(event.position().x(), event.position().y()):
            self.text_dragging = True
            return
        if self.logo_checkbox.isChecked() and self.logo_base_image:
            cw = self.preview_label.width()
            ch = self.preview_label.height()
            if not self.processed_image:
                return
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            pos = event.position() if hasattr(event, "position") else event.pos()
            cx = int(pos.x() * sx)
            cy = int(pos.y() * sy)
            try:
                s = int(self.logo_size_spin.value())
            except:
                s = 64
            lx = self.logo_x_offset
            ly = self.logo_y_offset
            if lx <= cx < lx + s and ly <= cy < ly + s:
                self.dragging_logo = True
                self.drag_offset = (cx - lx, cy - ly)

    def check_text_hit(self, cx, cy):
        t = self.text_lineedit.text().strip()
        if not t or not self.processed_image:
            return False
        f = self.get_font()
        cw = self.preview_label.width()
        ch = self.preview_label.height()
        iw, ih = self.processed_image.size
        sx = iw / cw
        sy = ih / ch
        ix = int(cx * sx)
        iy = int(cy * sy)
        dr = ImageDraw.Draw(self.processed_image.copy())
        bb = dr.textbbox((0, 0), t, font=f)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        xo = self.x_offset_spin.value()
        yo = self.y_offset_spin.value()
        by = ih - lh - yo
        if lw + xo * 2 <= iw:
            if (xo <= ix < xo + lw) and (by <= iy < by + lh):
                self.text_drag_offset = (ix - xo, iy - by)
                return True
            return False
        else:
            words = t.split()
            if len(words) < 2:
                if (xo <= ix < xo + lw) and (by <= iy < by + lh):
                    self.text_drag_offset = (ix - xo, iy - by)
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
                    self.text_drag_offset = (ix - xo, iy - y1)
                    return True
                return False

    def on_preview_drag(self, event: QMouseEvent):
        if self.text_dragging:
            self.drag_text(event.position().x(), event.position().y())
            return
        if self.dragging_logo and self.logo_checkbox.isChecked() and self.logo_base_image:
            cw = self.preview_label.width()
            ch = self.preview_label.height()
            if not self.processed_image:
                return
            iw, ih = self.processed_image.size
            sx = iw / cw
            sy = ih / ch
            pos = event.position() if hasattr(event, "position") else event.pos()
            dx = int(pos.x() * sx)
            dy = int(pos.y() * sy)
            try:
                s = int(self.logo_size_spin.value())
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
            self.logo_x_offset = nlx
            self.logo_y_offset = nly
            self.logo_x_offset_spin.setValue(nlx)
            self.logo_y_offset_spin.setValue(nly)
            self.update_preview()

    def drag_text(self, cx, cy):
        cw = self.preview_label.width()
        ch = self.preview_label.height()
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
        ts = self.text_lineedit.text().strip()
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
            self.y_offset_spin.setValue(ny)
        self.x_offset_spin.setValue(ox)
        self.update_preview()

    def on_preview_release(self, event: QMouseEvent):
        if self.dragging_logo:
            self.dragging_logo = False
        if self.text_dragging:
            self.text_dragging = False

    def toggle_pipette_mode(self):
        self.pipette_mode = not self.pipette_mode

    def choose_gradient_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.gradient_color = color.name()
            self.update_preview()

    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.text_color = color.name()
            self.update_preview()

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

    def save_image(self):
        if not self.original_image:
            return
        img = self.get_preview_crop()
        final_img = self.build_pipeline(img)
        if not final_img:
            return
        default_name = self.text_lineedit.text().strip()
        if not default_name:
            default_name = "icon"
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить (ICO)", default_name, "ICO files (*.ico);;All files (*)")
        if path:
            try:
                final_img.save(path, format="ICO")
                with open(path, "ab") as f:
                    f.write(b"\nhttps://github.com/lReDragol")
            except Exception as e:
                print("Ошибка сохранения:", e)

    def is_blocked(self):
        r = subprocess.run(
            ["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "/v", "NoChangeStartMenu"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
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
            self.freeze_move_button.setText("Frize перемещение")
        else:
            self.block_tiles()
            self.freeze_move_button.setText("UnFrize перемещение")

    def is_update_blocked(self):
        r = subprocess.run(
            ["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "/v", "NoUpdateStartMenu"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
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

    def freeze_change(self):
        if self.is_update_blocked():
            self.unblock_tile_updates()
            self.freeze_change_button.setText("Frize изменение")
        else:
            self.block_tile_updates()
            self.freeze_change_button.setText("UnFrize изменение")

    def keyPressEvent(self, event):
        s = 10
        if event.key() == Qt.Key_Left:
            self.crop_offset_x -= s
        elif event.key() == Qt.Key_Right:
            self.crop_offset_x += s
        elif event.key() == Qt.Key_Up:
            self.crop_offset_y -= s
        elif event.key() == Qt.Key_Down:
            self.crop_offset_y += s
        self.update_preview()
        super().keyPressEvent(event)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = ImageEditorApp()
    window.show()
    sys.exit(app.exec())
