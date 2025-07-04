import os
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QToolBar,
    QMessageBox, QWidget, QPlainTextEdit, QVBoxLayout, QTextEdit,
    QMenuBar, QInputDialog, QStatusBar, QSplitter, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QDialog, QDialogButtonBox,
    QCheckBox, QSpinBox, QFormLayout, QComboBox, QTreeView, QFileSystemModel,QMenu,QLineEdit
)
from PySide6.QtGui import (
    QColor, QPainter, QFont, QSyntaxHighlighter, QTextCharFormat,
    QAction, QKeySequence, QShortcut, QPixmap, QIcon,QTextDocument,QTextCursor
)
from PySide6.QtCore import Qt, QRect, QRegularExpression, QThread, Signal, QTimer, QSettings,QDir,QSize


# ---------- Compilation Thread ----------
class CompilationThread(QThread):
    compilation_finished = Signal(int, str, str)  # return_code, stdout, stderr
    
    def __init__(self, compile_cmd, run_cmd=None):
        super().__init__()
        self.compile_cmd = compile_cmd
        self.run_cmd = run_cmd
    
    def run(self):
        # Compile
        result = subprocess.run(self.compile_cmd, shell=True, capture_output=True, text=True)
        self.compilation_finished.emit(result.returncode, result.stdout, result.stderr)


# ---------- Settings Dialog ----------
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor Settings")
        self.setModal(True)
        self.resize(400, 300)
        

        tabs = QTabWidget()

        # -------- Editor Settings Tab --------
        editor_layout = QFormLayout()

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 40)
        editor_layout.addRow("Font Size:", self.font_size_spin)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(["Consolas", "Courier New", "Monaco", "Fira Code", "Source Code Pro"])
        editor_layout.addRow("Font Family:", self.font_family_combo)

        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(2, 8)
        editor_layout.addRow("Tab Size:", self.tab_size_spin)

        self.line_wrap_check = QCheckBox()
        editor_layout.addRow("Line Wrap:", self.line_wrap_check)

        self.auto_indent_check = QCheckBox()
        self.auto_indent_check.setChecked(True)
        editor_layout.addRow("Auto Indent:", self.auto_indent_check)

        editor_tab = QWidget()
        editor_tab.setLayout(editor_layout)
        tabs.addTab(editor_tab, "📝 Editor")

        # -------- Build Settings Tab --------
        build_layout = QFormLayout()

        self.compiler_combo = QComboBox()
        self.compiler_combo.addItems(["g++", "clang++", "cl"])
        build_layout.addRow("Compiler:", self.compiler_combo)

        self.flags_edit = QLineEdit()
        self.flags_edit.setPlaceholderText("-std=c++17 -Wall -Wextra")
        build_layout.addRow("Extra Flags:", self.flags_edit)

        self.run_in_cmd_check = QCheckBox("Run in CMD after build")
        self.run_in_cmd_check.setChecked(True)
        build_layout.addRow(self.run_in_cmd_check)

        build_tab = QWidget()
        build_tab.setLayout(build_layout)
        tabs.addTab(build_tab, "🔨 Build")

        # -------- Buttons --------
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addWidget(tabs)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

# ---------- Find/Replace Dialog ----------
class FindReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find & Replace")
        self.setModal(False)
        self.resize(400, 200)
        
        layout = QFormLayout()
        
        # Find field
        self.find_edit = QPlainTextEdit()
        self.find_edit.setMaximumHeight(30)
        layout.addRow("Find:", self.find_edit)
        
        # Replace field
        self.replace_edit = QPlainTextEdit()
        self.replace_edit.setMaximumHeight(30)
        layout.addRow("Replace:", self.replace_edit)
        
        # Options
        self.case_sensitive_check = QCheckBox("Case Sensitive")
        self.whole_word_check = QCheckBox("Whole Word")
        
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.whole_word_check)
        layout.addRow("Options:", options_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.find_button = QPushButton("Find Next")
        self.replace_button = QPushButton("Replace")
        self.replace_all_button = QPushButton("Replace All")
        
        button_layout.addWidget(self.find_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(self.replace_all_button)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)


# ---------- Line Number Area ----------
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return self.code_editor.lineNumberAreaSize()

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


# ---------- Enhanced Code Editor Widget ----------
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 12))
        self.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc;")
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))
        
        # Editor settings
        self.auto_indent_enabled = True
        self.tab_size = 4
        
        # Line number area
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # Auto-save every 30 seconds
        
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Track modifications
        self.is_modified = False
        self.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        self.is_modified = True

    def auto_save(self):
        if hasattr(self.parent(), 'auto_save_current_file'):
            self.parent().auto_save_current_file()

    def keyPressEvent(self, event):
        # Auto-indent on Enter
        if event.key() == Qt.Key_Return and self.auto_indent_enabled:
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            
            # Count leading spaces/tabs
            indent = len(text) - len(text.lstrip())
            
            # Add extra indent after opening braces
            if text.rstrip().endswith('{'):
                indent += self.tab_size
            
            super().keyPressEvent(event)
            
            # Insert the indentation
            cursor = self.textCursor()
            cursor.insertText(' ' * indent)
            return
        
        # Handle tab key
        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                # Indent selected lines
                self.indent_selection()
            else:
                # Insert tab
                cursor.insertText(' ' * self.tab_size)
            return
        
        # Handle Shift+Tab for unindent
        if event.key() == Qt.Key_Backtab:
            self.unindent_selection()
            return
        
        super().keyPressEvent(event)

    def indent_selection(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)
        
        while cursor.position() < end:
            cursor.insertText(' ' * self.tab_size)
            cursor.movePosition(QTextCursor.NextBlock)
            if cursor.position() == 0:
                break

    def unindent_selection(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfBlock)
        
        while cursor.position() < end:
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            text = cursor.selectedText()
            
            # Remove leading spaces (up to tab_size)
            spaces_to_remove = 0
            for char in text:
                if char == ' ' and spaces_to_remove < self.tab_size:
                    spaces_to_remove += 1
                else:
                    break
            
            if spaces_to_remove > 0:
                cursor.movePosition(QTextCursor.StartOfBlock)
                for _ in range(spaces_to_remove):
                    cursor.deleteChar()
            
            cursor.movePosition(QTextCursor.NextBlock)
            if cursor.position() == 0:
                break

    def lineNumberAreaWidth(self):
        digits = len(str(self.blockCount()))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def lineNumberAreaPaintEvent(self, event):
        if not self.line_number_area.isVisible():
            return

        painter = QPainter(self.line_number_area)
        if not painter.isActive():
            return

        painter.fillRect(event.rect(), QColor("#2d2d2d"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#888"))
                painter.drawText(
                    0, int(top),
                    self.line_number_area.width(),
                    int(self.fontMetrics().height()),
                    Qt.AlignRight,
                    number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )
            
    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def highlightCurrentLine(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#2a2d2e"))
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)


# ---------- Enhanced Syntax Highlighter ----------
class CppHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.highlightingRules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
            "bool", "break", "case", "catch", "char", "char8_t", "char16_t", "char32_t",
            "class", "compl", "concept", "const", "consteval", "constexpr", "constinit",
            "const_cast", "continue", "co_await", "co_return", "co_yield", "decltype",
            "default", "delete", "do", "double", "dynamic_cast", "else", "enum",
            "explicit", "export", "extern", "false", "float", "for", "friend", "goto",
            "if", "inline", "int", "long", "mutable", "namespace", "new", "noexcept",
            "not", "not_eq", "nullptr", "operator", "or", "or_eq", "private", "protected",
            "public", "register", "reinterpret_cast", "requires", "return", "short",
            "signed", "sizeof", "static", "static_assert", "static_cast", "struct",
            "switch", "template", "this", "thread_local", "throw", "true", "try",
            "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual",
            "void", "volatile", "wchar_t", "while", "xor", "xor_eq"
        ]
        
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.highlightingRules.append((pattern, keyword_format))

        # Preprocessor directives
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(QColor("#9B9B9B"))
        self.highlightingRules.append((QRegularExpression(r"#\w+"), preprocessor_format))

        # String literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.highlightingRules.append((QRegularExpression(r"\"([^\"\\]|\\.)*\""), string_format))
        self.highlightingRules.append((QRegularExpression(r"'([^'\\]|\\.)*'"), string_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.highlightingRules.append((QRegularExpression(r"\b\d+\.?\d*[fFlL]?\b"), number_format))
        self.highlightingRules.append((QRegularExpression(r"\b0[xX][0-9A-Fa-f]+\b"), number_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        comment_format.setFontItalic(True)
        self.highlightingRules.append((QRegularExpression(r"//[^\n]*"), comment_format))
        
        # Multi-line comments
        self.multiline_comment_format = QTextCharFormat()
        self.multiline_comment_format.setForeground(QColor("#6A9955"))
        self.multiline_comment_format.setFontItalic(True)
        
        # Function names
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))
        self.highlightingRules.append((QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"), function_format))

    def highlightBlock(self, text):
        # Apply regular highlighting rules
        for pattern, fmt in self.highlightingRules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, fmt)

        # Handle multi-line comments
        self.setCurrentBlockState(0)
        comment_start = QRegularExpression(r"/\*")
        comment_end = QRegularExpression(r"\*/")
        
        if self.previousBlockState() != 1:
            start_index = comment_start.match(text).capturedStart()
        else:
            start_index = 0
            
        while start_index >= 0:
            match = comment_end.match(text, start_index)
            end_index = match.capturedStart()
            
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + match.capturedLength()
                
            self.setFormat(start_index, comment_length, self.multiline_comment_format)
            start_index = comment_start.match(text, start_index + comment_length).capturedStart()


# ---------- Enhanced Main Window ----------
class CppEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("C++ Editor")
        self.setGeometry(100, 100, 1200, 800)
        icon_path = os.path.join(os.path.dirname(__file__), "logo.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.settings = QSettings("CppEditor", "Settings")
        self.load_settings()

        self.init_ui()
        # Restore working directory
        last_dir = self.settings.value("last_working_directory")
        if last_dir and os.path.isdir(last_dir):
            QDir.setCurrent(last_dir)
            self.set_working_directory(last_dir)  # if you have a function to handle file tree

        # Restore open files
        open_files = self.settings.value("open_files", [])
        if open_files:
            self.tab_widget.clear()  # remove the default blank tab
            for file in open_files:
                if os.path.isfile(file):
                    self.create_new_tab(file)

        self.init_menus()
        self.init_toolbar()
        self.init_statusbar()
        self.init_shortcuts()

        self.current_file = ""
        self.recent_files = self.settings.value("recent_files", [])
        self.update_recent_files_menu()

        self.compilation_thread = None
        self.find_replace_dialog = None

    def init_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.create_new_tab()

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(500)

        # Apply font from settings
        font_family = self.settings.value("font_family", "Consolas")
        font_size = int(self.settings.value("font_size", 12))
        self.log_box.setFont(QFont(font_family, font_size))

        self.log_box.setStyleSheet("""
            QTextEdit {
                background-color: #252526;
                color: #CCCCCC;
                border: 1px solid #3E3E3E;
            }
        """)


        vertical_splitter = QSplitter(Qt.Vertical)
        vertical_splitter.addWidget(self.tab_widget)
        vertical_splitter.addWidget(self.log_box)
        vertical_splitter.setSizes([600, 150])

        # Add file tree
        self.file_model = QFileSystemModel()

        # Working directory path
        root_path = QDir.currentPath()
        root_index = self.file_model.setRootPath(root_path)

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)

        # ✅ Show the working folder as the only root
        self.file_tree.setRootIndex(root_index)  # This limits the view to just this folder

        # ✅ Appearance settings
        self.file_tree.setRootIsDecorated(True)
        self.file_tree.setItemsExpandable(True)
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)

        # ✅ Expand + highlight root
        self.file_tree.expand(root_index)
        self.file_tree.scrollTo(root_index)
        self.file_tree.setCurrentIndex(root_index)

        # ✅ Context menu + file opening
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.file_tree.doubleClicked.connect(self.open_file_from_tree)


        # Combine tree and editor
        horizontal_splitter = QSplitter(Qt.Horizontal)
        horizontal_splitter.addWidget(self.file_tree)
        horizontal_splitter.addWidget(vertical_splitter)
        horizontal_splitter.setSizes([250, 950])

        self.setCentralWidget(horizontal_splitter)

    def show_tree_context_menu(self, position):
        index = self.file_tree.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()

        menu.addAction("📄 New File", lambda: self.create_new_file(index))
        menu.addAction("📁 New Folder", lambda: self.create_new_folder(index))
        menu.addSeparator()
        menu.addAction("✏️ Rename", lambda: self.rename_item(index))
        menu.addAction("🗑️ Delete", lambda: self.delete_item(index))

        menu.exec(self.file_tree.viewport().mapToGlobal(position))

    def create_new_file(self, index):
        dir_path = self.file_model.filePath(index)
        if not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)

        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name:
            file_path = os.path.join(dir_path, name)
            try:
                with open(file_path, 'w') as f:
                    pass
                self.log(f"📄 Created file: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file:\n{str(e)}")

    def create_new_folder(self, index):
        dir_path = self.file_model.filePath(index)
        if not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)

        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            folder_path = os.path.join(dir_path, name)
            try:
                os.makedirs(folder_path)
                self.log(f"📁 Created folder: {folder_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{str(e)}")

    def rename_item(self, index):
        old_path = self.file_model.filePath(index)
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=os.path.basename(old_path))
        if ok and name:
            new_path = os.path.join(os.path.dirname(old_path), name)
            try:
                os.rename(old_path, new_path)
                self.log(f"✏️ Renamed: {old_path} → {new_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename:\n{str(e)}")

    def delete_item(self, index):
        path = self.file_model.filePath(index)
        reply = QMessageBox.question(self, "Delete", f"Delete:\n{path}?", 
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.log(f"🗑️ Deleted: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete:\n{str(e)}")


    def set_working_directory(self, path=None):
        if not path:
            path = QFileDialog.getExistingDirectory(self, "Select Working Directory", QDir.currentPath())
        if path:
            QDir.setCurrent(path)
            self.file_model.setRootPath(path)
            self.file_tree.setRootIndex(self.file_model.index(path))
            self.log(f"📁 Working directory set to: {path}")

    
    def open_file_from_tree(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabToolTip(i) == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return
            editor = self.create_new_tab(file_path)
            if editor:
                self.add_to_recent_files(file_path)
                self.log(f"📂 Opened from tree: {os.path.basename(file_path)}")
    
    def create_new_tab(self, file_path=""):
        editor = CodeEditor()
        highlighter = CppHighlighter(editor.document())
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                editor.setPlainText(content)
                editor.is_modified = False
                tab_name = os.path.basename(file_path)
            except Exception as e:
                self.log(f"❌ Error opening file: {str(e)}")
                return None
        else:
            tab_name = "Untitled"
        
        tab_index = self.tab_widget.addTab(editor, tab_name)
        self.tab_widget.setCurrentIndex(tab_index)
        
        # Store file path in tab
        self.tab_widget.setTabToolTip(tab_index, file_path)
        font_family = self.settings.value("font_family", "Consolas")
        font_size = int(self.settings.value("font_size", 12))
        editor.setFont(QFont(font_family, font_size))
        
        tab_size = int(self.settings.value("tab_size", 4))
        editor.tab_size = tab_size
        editor.setTabStopDistance(tab_size * editor.fontMetrics().horizontalAdvance(' '))

        editor.auto_indent_enabled = self.settings.value("auto_indent", True, type=bool)
        wrap = self.settings.value("line_wrap", False, type=bool)
        editor.setLineWrapMode(QPlainTextEdit.WidgetWidth if wrap else QPlainTextEdit.NoWrap)

        return editor

    def get_current_editor(self):
        return self.tab_widget.currentWidget()

    def close_tab(self, index):
        editor = self.tab_widget.widget(index)
        if editor and editor.is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes", 
                "File has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        
        self.tab_widget.removeTab(index)
        
        if self.tab_widget.count() == 0:
            self.create_new_tab()

    def init_menus(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Recent files submenu
        self.recent_files_menu = file_menu.addMenu("Recent Files")
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("Find & Replace", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.show_find_replace)
        edit_menu.addAction(find_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # Build menu
        build_menu = menubar.addMenu("Build")
        
        compile_action = QAction("Compile", self)
        compile_action.setShortcut(QKeySequence("F7"))
        compile_action.triggered.connect(self.compile_only)
        build_menu.addAction(compile_action)
        
        run_action = QAction("Compile & Run", self)
        run_action.setShortcut(QKeySequence("F5"))
        run_action.triggered.connect(self.compile_and_run)
        build_menu.addAction(run_action)

        # Help/About Menu (optional)
        about_action = QAction("About Developer", self)
        about_action.triggered.connect(self.show_about_me)
        menubar.addAction(about_action)  # Or use: help_menu.addAction(about_action)
   
    def show_about_me(self):
        QMessageBox.about(self, "About the Developer", """
        <h3>C++ Editor - Built with ❤️ by Anshul Wycliffe</h3>
        <p><b>Version:</b> 2.0</p>
        <p><b>Developer:</b> Anshul Wycliffe<br>
        A passionate software developer with expertise in:</p>
        <ul>
            <li>💻 Python Desktop App</li>
            <li>🎨 Android Development</li>
        </ul>
        <p>Visit: <a href='https://github.com/anshulwycliffe'>GitHub</a></p>
        <p>Contact: service.anshul@gmail.com</p>
        """)

    def init_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)

        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3c3c3c;
                spacing: 6px;
                padding: 4px;
            }
            QToolButton {
                background-color: #2d2d2d;
                border: 1px solid #444;
                color: white;
                padding: 6px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
                border: 1px solid #5a5a5a;
            }
            QToolButton:pressed {
                background-color: #007acc;
                border: 1px solid #007acc;
            }
        """)
        self.addToolBar(toolbar)

        # Toolbar actions with emojis
        toolbar.addAction("🆕 New", self.new_file)
        toolbar.addAction("📂 Open File", self.open_file)
        toolbar.addAction("📁 Set Folder", self.set_working_directory)
        toolbar.addAction("💾 Save", self.save_file)
        toolbar.addSeparator()

        toolbar.addAction("🛠️ Compile", self.compile_only)
        toolbar.addAction("🚀 Run", self.compile_and_run)
        toolbar.addSeparator()

        toolbar.addAction("🔍 Find", self.show_find_replace)
        toolbar.addAction("⚙️ Settings", self.show_settings)



    def init_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Line/Column indicator
        self.line_col_label = QLabel("Line: 1, Col: 1")
        self.statusbar.addPermanentWidget(self.line_col_label)
        
        # File encoding
        self.encoding_label = QLabel("UTF-8")
        self.statusbar.addPermanentWidget(self.encoding_label)
        
        # Update line/col on cursor change
        if self.get_current_editor():
            self.get_current_editor().cursorPositionChanged.connect(self.update_cursor_position)

    def update_cursor_position(self):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.line_col_label.setText(f"Line: {line}, Col: {col}")

    def init_shortcuts(self):
        # Additional shortcuts
        QShortcut(QKeySequence("Ctrl+T"), self, self.new_file)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close_current_tab)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)

    def load_settings(self):
        self.resize(
            self.settings.value("window_width", 1200),
            self.settings.value("window_height", 800)
        )
        self.move(
            self.settings.value("window_x", 100),
            self.settings.value("window_y", 100)
        )

    def save_settings(self):
        self.settings.setValue("window_width", self.width())
        self.settings.setValue("window_height", self.height())
        self.settings.setValue("window_x", self.x())
        self.settings.setValue("window_y", self.y())
        self.settings.setValue("recent_files", self.recent_files)

    def closeEvent(self, event):
        # Check for unsaved changes
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor and editor.is_modified:
                reply = QMessageBox.question(
                    self, "Unsaved Changes", 
                    "Some files have unsaved changes. Exit anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    event.ignore()
                    return
                break
        
        self.save_settings()
        
        event.accept()

    def log(self, message: str):
        from datetime import datetime
        time_str = datetime.now().strftime("[%H:%M:%S]")
        self.log_box.appendPlainText(f"{time_str} {message}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def new_file(self):
        self.create_new_tab()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", 
            "C++ Files (*.cpp *.cxx *.cc *.c *.h *.hpp *.hxx);;All Files (*)"
        )
        if file_path:
            # Check if file is already open
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabToolTip(i) == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return
            
            editor = self.create_new_tab(file_path)
            if editor:
                self.add_to_recent_files(file_path)
                self.log(f"📂 Opened: {os.path.basename(file_path)}")

    def save_file(self):
        editor = self.get_current_editor()
        if not editor:
            return
        
        current_index = self.tab_widget.currentIndex()
        file_path = self.tab_widget.tabToolTip(current_index)
        
        if not file_path:
            self.save_file_as()
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            editor.is_modified = False
            self.log(f"💾 Saved: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def save_file_as(self):
        editor = self.get_current_editor()
        if not editor:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", 
            "C++ Files (*.cpp *.cxx *.cc *.c *.h *.hpp *.hxx);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                editor.is_modified = False
                
                # Update tab
                current_index = self.tab_widget.currentIndex()
                self.tab_widget.setTabText(current_index, os.path.basename(file_path))
                self.tab_widget.setTabToolTip(current_index, file_path)
                
                self.add_to_recent_files(file_path)
                self.log(f"💾 Saved as: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def auto_save_current_file(self):
        editor = self.get_current_editor()
        if not editor or not editor.is_modified:
            return
        
        current_index = self.tab_widget.currentIndex()
        file_path = self.tab_widget.tabToolTip(current_index)
        
        if file_path:
            try:
                with open(file_path + ".autosave", 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                self.log("💾 Auto-saved backup")
            except Exception as e:
                self.log(f"❌ Auto-save failed: {str(e)}")

    def add_to_recent_files(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # Keep only 10 recent files
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        self.recent_files_menu.clear()
        for file_path in self.recent_files:
            if os.path.exists(file_path):
                action = QAction(os.path.basename(file_path), self)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self.open_recent_file(path))
                self.recent_files_menu.addAction(action)

    def open_recent_file(self, file_path):
        if os.path.exists(file_path):
            # Check if already open
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabToolTip(i) == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return
            
            editor = self.create_new_tab(file_path)
            if editor:
                self.log(f"📂 Opened recent: {os.path.basename(file_path)}")
        else:
            self.recent_files.remove(file_path)
            self.update_recent_files_menu()
            QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")

    def close_current_tab(self):
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def undo(self):
        editor = self.get_current_editor()
        if editor:
            editor.undo()

    def redo(self):
        editor = self.get_current_editor()
        if editor:
            editor.redo()

    def show_find_replace(self):
        if not self.find_replace_dialog:
            self.find_replace_dialog = FindReplaceDialog(self)
            self.find_replace_dialog.find_button.clicked.connect(self.find_next)
            self.find_replace_dialog.replace_button.clicked.connect(self.replace_current)
            self.find_replace_dialog.replace_all_button.clicked.connect(self.replace_all)
        
        self.find_replace_dialog.show()
        self.find_replace_dialog.raise_()
        self.find_replace_dialog.activateWindow()

    def find_next(self):
        editor = self.get_current_editor()
        if not editor or not self.find_replace_dialog:
            return

        find_text = self.find_replace_dialog.find_edit.toPlainText()
        if not find_text:
            return

        flags = QTextDocument.FindFlag(0)
        if self.find_replace_dialog.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.find_replace_dialog.whole_word_check.isChecked():
            flags |= QTextDocument.FindWholeWords

        found = editor.find(find_text, flags)
        if not found:
            # Start from beginning
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            found = editor.find(find_text, flags)

        if not found:
            QMessageBox.information(self, "Find", "Text not found.")

    def replace_current(self):
        editor = self.get_current_editor()
        if not editor or not self.find_replace_dialog:
            return
        
        cursor = editor.textCursor()
        if cursor.hasSelection():
            find_text = self.find_replace_dialog.find_edit.toPlainText()
            replace_text = self.find_replace_dialog.replace_edit.toPlainText()
            
            selected_text = cursor.selectedText()
            if (self.find_replace_dialog.case_sensitive_check.isChecked() and 
                selected_text == find_text) or (
                not self.find_replace_dialog.case_sensitive_check.isChecked() and 
                selected_text.lower() == find_text.lower()):
                cursor.insertText(replace_text)
        
        self.find_next()

    def replace_all(self):
        editor = self.get_current_editor()
        if not editor or not self.find_replace_dialog:
            return
        
        find_text = self.find_replace_dialog.find_edit.toPlainText()
        replace_text = self.find_replace_dialog.replace_edit.toPlainText()
        
        if not find_text:
            return
        
        content = editor.toPlainText()
        if self.find_replace_dialog.case_sensitive_check.isChecked():
            new_content = content.replace(find_text, replace_text)
        else:
            # Case-insensitive replace
            import re
            pattern = re.escape(find_text)
            new_content = re.sub(pattern, replace_text, content, flags=re.IGNORECASE)
        
        if new_content != content:
            editor.setPlainText(new_content)
            count = content.count(find_text) if self.find_replace_dialog.case_sensitive_check.isChecked() else len(re.findall(pattern, content, re.IGNORECASE))
            QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences")
        else:
            QMessageBox.information(self, "Replace All", "No occurrences found")

    def show_settings(self):
        dialog = SettingsDialog(self)
        
        # Load current settings
        editor = self.get_current_editor()
        if editor:
            current_font = editor.font()
            dialog.font_family_combo.setCurrentText(self.settings.value("font_family", "Consolas"))
            dialog.font_size_spin.setValue(int(self.settings.value("font_size", 12)))
            dialog.tab_size_spin.setValue(int(self.settings.value("tab_size", 4)))
            dialog.auto_indent_check.setChecked(self.settings.value("auto_indent", True, type=bool))
            dialog.line_wrap_check.setChecked(self.settings.value("line_wrap", False, type=bool))

            dialog.compiler_combo.setCurrentText(self.settings.value("compiler", "g++"))
            dialog.flags_edit.setText(self.settings.value("build_flags", "-std=c++17 -Wall -Wextra"))
            dialog.run_in_cmd_check.setChecked(self.settings.value("run_in_cmd", True, type=bool))


        
        if dialog.exec() == QDialog.Accepted:
            self.apply_settings(dialog)

    def apply_settings(self, dialog):
        font_family = dialog.font_family_combo.currentText()
        font_size = dialog.font_size_spin.value()

        # Store to QSettings
        self.settings.setValue("font_family", font_family)
        self.settings.setValue("font_size", font_size)
        self.settings.setValue("tab_size", dialog.tab_size_spin.value())
        self.settings.setValue("auto_indent", dialog.auto_indent_check.isChecked())
        self.settings.setValue("line_wrap", dialog.line_wrap_check.isChecked())
        self.settings.setValue("compiler", dialog.compiler_combo.currentText())
        self.settings.setValue("build_flags", dialog.flags_edit.text())
        self.settings.setValue("run_in_cmd", dialog.run_in_cmd_check.isChecked())


        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor:
                new_font = QFont(font_family, font_size)
                editor.setFont(new_font)
                editor.tab_size = dialog.tab_size_spin.value()
                editor.setTabStopDistance(editor.tab_size * editor.fontMetrics().horizontalAdvance(' '))
                editor.auto_indent_enabled = dialog.auto_indent_check.isChecked()
                wrap = dialog.line_wrap_check.isChecked()
                editor.setLineWrapMode(QPlainTextEdit.WidgetWidth if wrap else QPlainTextEdit.NoWrap)

        # Apply to log box
        log_font = QFont(font_family, font_size)
        self.log_box.setFont(log_font)

        self.log(f"🔧 Settings applied")

    def save_settings(self):
        self.settings.setValue("window_width", self.width())
        self.settings.setValue("window_height", self.height())
        self.settings.setValue("window_x", self.x())
        self.settings.setValue("window_y", self.y())
        self.settings.setValue("recent_files", self.recent_files)

        # ✅ Save open tabs
        open_files = []
        for i in range(self.tab_widget.count()):
            path = self.tab_widget.tabToolTip(i)
            if path:
                open_files.append(path)
        self.settings.setValue("open_files", open_files)

        # ✅ Save current working directory
        self.settings.setValue("last_working_directory", QDir.currentPath())


    def get_current_file_path(self):
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            return self.tab_widget.tabToolTip(current_index)
        return ""

    def compile_only(self):
        file_path = self.get_current_file_path()
        if not file_path:
            QMessageBox.warning(self, "No File", "Please save your file first.")
            return
        
        # Save current file
        self.save_file()
        
        # Determine output file
        output_path = os.path.splitext(file_path)[0]
        if sys.platform == "win32":
            output_path += ".exe"
        
        # Compile command
        compiler = self.settings.value("compiler", "g++")
        flags = self.settings.value("build_flags", "-std=c++17 -Wall -Wextra")
        compile_cmd = f'{compiler} "{file_path}" -o "{output_path}" {flags}'

        self.log(f"🔨 Compiling: {os.path.basename(file_path)}")
        self.log(f"Command: {compile_cmd}")
        
        if self.compilation_thread and self.compilation_thread.isRunning():
            self.compilation_thread.terminate()
            self.compilation_thread.wait()
        
        self.compilation_thread = CompilationThread(compile_cmd)
        self.compilation_thread.compilation_finished.connect(self.on_compilation_finished)
        self.compilation_thread.start()

    def compile_and_run(self):
        file_path = self.get_current_file_path()
        if not file_path:
            QMessageBox.warning(self, "No File", "Please save your file first.")
            return
        
        # Save current file
        self.save_file()
        
        # Determine output file
        output_path = os.path.splitext(file_path)[0]
        if sys.platform == "win32":
            output_path += ".exe"
        
        # Compile command
        compiler = self.settings.value("compiler", "g++")
        flags = self.settings.value("build_flags", "-std=c++17 -Wall -Wextra")
        compile_cmd = f'{compiler} "{file_path}" -o "{output_path}" {flags}'

        run_in_cmd = self.settings.value("run_in_cmd", True, type=bool)
        

        self.log(f"🔨 Compiling and running: {os.path.basename(file_path)}")
        self.log(f"Command: {compile_cmd}")
        
        if self.compilation_thread and self.compilation_thread.isRunning():
            self.compilation_thread.terminate()
            self.compilation_thread.wait()
        
        self.compilation_thread = CompilationThread(compile_cmd, output_path)
        self.compilation_thread.compilation_finished.connect(
            lambda rc, stdout, stderr: self.on_compilation_finished(rc, stdout, stderr, run_in_cmd)
        )
        self.compilation_thread.start()

    def on_compilation_finished(self, return_code, stdout, stderr, run_after=False):
        if return_code == 0:
            self.log("✅ Compilation successful!")
            if stdout:
                self.log(f"Output: {stdout}")
            
            if run_after:
                file_path = self.get_current_file_path()
                output_path = os.path.splitext(file_path)[0]
                if sys.platform == "win32":
                    output_path += ".exe"
                    # Run in new command prompt window
                    subprocess.Popen(f'start cmd /k "{output_path}"', shell=True)
                else:
                    # Run in terminal (Linux/Mac)
                    subprocess.Popen(['gnome-terminal', '--', output_path])
                
                self.log(f"🚀 Running: {os.path.basename(output_path)}")
        else:
            self.log("❌ Compilation failed!")
            if stderr:
                self.log(f"Errors:\n{stderr}")
            QMessageBox.critical(self, "Compilation Error", 
                               f"Compilation failed with return code {return_code}:\n{stderr}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx')):
                self.create_new_tab(file_path)
                self.add_to_recent_files(file_path)
                self.log(f"📂 Opened (drag & drop): {os.path.basename(file_path)}")


# ---------- Application Entry Point ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("C++ Editor")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Anshul Wycliffe")
    
    # Apply dark theme
    app.setStyle('Fusion')

    app.setWindowIcon(QIcon("logo.ico"))
    
    # Dark palette
    from PySide6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # Create and show main window
    window = CppEditorWindow()
    window.showMaximized()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isfile(arg):
                window.create_new_tab(arg)
                window.add_to_recent_files(arg)
                window.log(f"📂 Opened (command line): {os.path.basename(arg)}")
    
    sys.exit(app.exec())