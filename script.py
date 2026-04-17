import sys
import os
import shutil
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTextEdit,
    QProgressBar, QTabWidget, QRadioButton, QGroupBox, QLineEdit,
    QCheckBox, QScrollArea, QFrame
)
# Добавляем QSpacerItem для корректной очистки лайаута
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt

CONFIG_FILE = "config.json"

DEFAULT_RULES = {
    "Images": ".jpg, .jpeg, .png, .gif, .bmp, .svg, .webp",
    "Documents": ".pdf, .docx, .doc, .txt, .xlsx, .pptx, .csv",
    "Videos": ".mp4, .avi, .mov, .mkv",
    "Music": ".mp3, .wav, .flac, .m4a",
    "Archives": ".zip, .rar, .7z, .tar",
    "Executables": ".exe, .msi, .bat"
}


class RuleRow(QFrame):
    def __init__(self, name="", extensions="", checked=True):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Название папки")
        self.name_edit.setFixedWidth(120)

        self.ext_edit = QLineEdit(extensions)
        self.ext_edit.setPlaceholderText("Расширения (через запятую)")

        self.btn_delete = QPushButton("✕")
        self.btn_delete.setFixedWidth(30)
        self.btn_delete.setStyleSheet("background-color: #cf6679; padding: 5px;")
        self.btn_delete.clicked.connect(self.deleteLater)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.ext_edit)
        layout.addWidget(self.btn_delete)


class FileSorterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.folder = ""
        self.rules = {}
        self.init_ui()
        self.load_settings()  # Загружаем настройки после инициализации UI

    def init_ui(self):
        self.setWindowTitle("Smart File Sorter")
        self.setMinimumSize(750, 600)
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; font-family: 'Segoe UI'; }
            QTabWidget::pane { border: 1px solid #333; background-color: #121212; }
            QTabBar::tab { background: #1c2128; color: #adbac7; padding: 10px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #1f6feb; color: white; }
            QPushButton { background-color: #1f6feb; border-radius: 6px; padding: 10px; font-weight: bold; }
            QPushButton:hover { background-color: #388bfd; }
            QLineEdit { background-color: #1c2128; border: 1px solid #30363d; padding: 5px; border-radius: 4px; color: #adbac7; }
            QTextEdit { background-color: #1e1e1e; color: #00ff00; font-family: 'Consolas', monospace; }
            QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #1f6feb; }
        """)
        #СОРТИРОВКА
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        sort_tab = QWidget()
        sort_layout = QVBoxLayout(sort_tab)

        self.label_folder = QLabel("Папка: Не выбрана")
        btn_choose = QPushButton("Выбрать папку")
        btn_choose.clicked.connect(self.choose_folder)

        mode_box = QGroupBox("Режим сортировки")
        mode_layout = QHBoxLayout(mode_box)
        self.radio_type = QRadioButton("По правилам (типам)")
        self.radio_date = QRadioButton("По дате изменения")
        self.radio_type.setChecked(True)
        mode_layout.addWidget(self.radio_type)
        mode_layout.addWidget(self.radio_date)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.progress = QProgressBar()

        self.btn_start = QPushButton("Запустить сортировку")
        self.btn_start.clicked.connect(self.start_sorting)

        sort_layout.addWidget(btn_choose)
        sort_layout.addWidget(self.label_folder)
        sort_layout.addWidget(mode_box)
        sort_layout.addWidget(self.log)
        sort_layout.addWidget(self.progress)
        sort_layout.addWidget(self.btn_start)

        #ПРАВИЛА
        rules_tab = QWidget()
        rules_main_layout = QVBoxLayout(rules_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.rules_container = QWidget()
        self.rules_list_layout = QVBoxLayout(self.rules_container)
        self.rules_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.rules_container)

        btn_add = QPushButton("+ Добавить новое правило")
        btn_add.setStyleSheet("background-color: #238636;")
        btn_add.clicked.connect(lambda: self.add_rule_row())

        btn_save = QPushButton("Сохранить настройки")
        btn_save.clicked.connect(self.save_rules)

        rules_main_layout.addWidget(QLabel("Настройте категории (автоматически сохраняются):"))
        rules_main_layout.addWidget(scroll)
        rules_main_layout.addWidget(btn_add)
        rules_main_layout.addWidget(btn_save)

        self.tabs.addTab(sort_tab, "Сортировка")
        self.tabs.addTab(rules_tab, "Правила")
        main_layout.addWidget(self.tabs)

    def add_rule_row(self, name="", exts="", checked=True):
        row = RuleRow(name, exts, checked)
        self.rules_list_layout.addWidget(row)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выбор папки")
        if folder:
            self.folder = folder
            self.label_folder.setText(f"Папка: {folder}")
            self.save_rules(silent=True)  # Сохраняем путь к папке

    def save_rules(self, silent=False):
        """Собирает данные и сохраняет в JSON файл"""
        self.rules = {}
        all_rules_to_save = []  # Список для сохранения состояния (даже неактивных)

        for i in range(self.rules_list_layout.count()):
            item = self.rules_list_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, RuleRow):
                    name = widget.name_edit.text().strip()
                    exts = widget.ext_edit.text().strip()
                    is_checked = widget.checkbox.isChecked()

                    if name and exts:
                        all_rules_to_save.append({
                            "name": name,
                            "exts": exts,
                            "active": is_checked
                        })
                        if is_checked:
                            self.rules[name] = exts

        config_data = {
            "last_folder": self.folder,
            "rules": all_rules_to_save
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

        if not silent:
            QMessageBox.information(self, "Успех", "Настройки сохранены в config.json!")

    def load_settings(self):

        if not os.path.exists(CONFIG_FILE):
            # Закгрузка базовых правил
            for name, exts in DEFAULT_RULES.items():
                self.add_rule_row(name, exts)
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Восстанавливаем папку
                self.folder = data.get("last_folder", "")
                if self.folder:
                    self.label_folder.setText(f"Папка: {self.folder}")

                # Восстанавливаем правила
                saved_rules = data.get("rules", [])
                if saved_rules:
                    for r in saved_rules:
                        self.add_rule_row(r["name"], r["exts"], r["active"])
                else:
                    # Если в JSON пустой список правил, грузим дефолтные
                    for name, exts in DEFAULT_RULES.items():
                        self.add_rule_row(name, exts)


            self.save_rules(silent=True)
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")


    def start_sorting(self):
        self.save_rules(silent=True)
        if not self.folder:
            QMessageBox.warning(self, "Ошибка", "Выберите папку!")
            return
        files = [os.path.join(self.folder, f) for f in os.listdir(self.folder)
                 if os.path.isfile(os.path.join(self.folder, f))]
        if not files:
            QMessageBox.information(self, "Инфо", "В папке нет файлов для сортировки")
            return
        self.btn_start.setEnabled(False)
        self.log.clear()
        mode = 'type' if self.radio_type.isChecked() else 'date'
        for i, path in enumerate(files, start=1):
            QApplication.processEvents()
            name = os.path.basename(path)
            try:
                if mode == 'type':
                    category = self.get_category(name)
                else:
                    t = os.path.getmtime(path)
                    category = datetime.fromtimestamp(t).strftime('%Y-%m (Дата)')
                new_folder = os.path.join(self.folder, category)
                os.makedirs(new_folder, exist_ok=True)
                self.move_file(path, new_folder)
                self.log.append(f"✓ {name} → {category}")
            except Exception as e:
                self.log.append(f"✗ Ошибка: {name} ({e})")
            self.progress.setValue(int((i / len(files)) * 100))
        self.btn_start.setEnabled(True)
        QMessageBox.information(self, "Готово", "Сортировка завершена!")

    def get_category(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        for category_name, extensions in self.rules.items():
            ext_list = [e.strip().lower() for e in extensions.split(',')]
            if ext in ext_list or ext.replace('.', '') in ext_list:
                return category_name
        return "Others"

    def move_file(self, src, dst_folder):
        name = os.path.basename(src)
        base, ext = os.path.splitext(name)
        dst = os.path.join(dst_folder, name)
        i = 1
        while os.path.exists(dst):
            dst = os.path.join(dst_folder, f"{base}_{i}{ext}")
            i += 1
        shutil.move(src, dst)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileSorterApp()
    window.show()
    sys.exit(app.exec())