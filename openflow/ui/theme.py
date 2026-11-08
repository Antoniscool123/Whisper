STYLE = """
* { font-family: 'Segoe UI', 'Inter', 'DejaVu Sans', sans-serif; font-size: 13px; color: #E8EFF7; }
QMainWindow, QWidget#Root { background: #0B111B; }
QWidget#Sidebar { background: #0E1622; border-right: 1px solid #1D2A3A; }
QLabel { background: transparent; border: none; }
QLabel#Brand { font-size: 23px; font-weight: 700; letter-spacing: -0.5px; }
QLabel#Eyebrow { color: #6F879E; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; }
QLabel#Title { font-size: 29px; font-weight: 700; color: #F3F7FB; }
QLabel#PageTitle { font-size: 25px; font-weight: 700; }
QLabel#Subtitle { color: #8FA3B8; font-size: 13px; }
QLabel#HeroTitle { font-size: 21px; font-weight: 600; }
QLabel#SectionTitle { font-size: 16px; font-weight: 600; }
QLabel#Muted { color: #8FA3B8; }
QLabel#Small { color: #7F94AA; font-size: 11px; }
QLabel#Accent { color: #5EEAD4; font-weight: 600; }
QLabel#StatValue { font-size: 25px; font-weight: 700; color: #F2F7FC; }
QLabel#Warning { color: #FBBF24; }
QLabel#Error { color: #FCA5A5; }
QFrame#Card { background: #121D2B; border: 1px solid #223144; border-radius: 14px; }
QFrame#Hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #142B35,stop:0.55 #132230,stop:1 #152033); border: 1px solid #294451; border-radius: 18px; }
QFrame#Privacy { background: #111F29; border: 1px solid #213643; border-radius: 12px; }
QFrame#Setup { background: #172432; border: 1px solid #30465A; border-radius: 12px; }
QPushButton { background: #1C2B3D; border: 1px solid #304258; border-radius: 8px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #26394E; border-color: #49627B; }
QPushButton:pressed { background: #142131; }
QPushButton:disabled { color: #53677C; background: #14202D; border-color: #223144; }
QPushButton#Primary { background: #5EEAD4; color: #08251F; border: 1px solid #5EEAD4; }
QPushButton#Primary:hover { background: #99F6E4; border-color: #99F6E4; }
QPushButton#Primary:disabled { background: #244A47; color: #688E88; border-color: #2B5550; }
QPushButton#Ghost { background: transparent; border-color: transparent; color: #91A6BB; }
QPushButton#Ghost:hover { background: #1B2A3B; color: #E8EFF7; }
QPushButton#Danger { color: #FCA5A5; background: #2B1D27; border-color: #53303C; }
QPushButton#Nav { text-align: left; padding: 12px 16px; border: none; background: transparent; color: #91A6BB; font-size: 14px; border-radius: 9px; }
QPushButton#Nav:hover { background: #172434; color: #DCE8F4; }
QPushButton#Nav:checked { background: #193536; color: #7EF0DB; font-weight: 700; }
QPushButton#MicButton { border-radius: 43px; background: #5EEAD4; border: 6px solid #244D4C; padding: 0; }
QPushButton#MicButton:hover { background: #99F6E4; border-color: #32635E; }
QPushButton#MicButton:disabled { background: #315451; border-color: #203C3E; }
QPushButton#MicButton[state="recording"] { background: #F87171; border-color: #633A43; }
QComboBox { background: #172536; border: 1px solid #304258; border-radius: 8px; padding: 8px 12px; min-height: 20px; }
QComboBox:hover { border-color: #4B687F; }
QComboBox:disabled { color: #60768B; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView { background: #172536; border: 1px solid #304258; selection-background-color: #24504E; selection-color: #B9FFF0; outline: none; padding: 5px; }
QTextEdit, QLineEdit { background: #0E1824; border: 1px solid #28394D; border-radius: 9px; padding: 10px; selection-background-color: #245C56; font-size: 14px; }
QTextEdit:focus, QLineEdit:focus { border-color: #4DB6A8; }
QTextEdit#Rules { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; }
QCheckBox { spacing: 10px; color: #D5E1ED; padding: 4px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 4px; border: 1px solid #435970; background: #111D2B; }
QCheckBox::indicator:checked { background: #5EEAD4; border-color: #5EEAD4; }
QCheckBox::indicator:disabled { border-color: #28394D; background: #172331; }
QProgressBar { background: #0E1824; border: 1px solid #2A3E50; border-radius: 6px; height: 12px; text-align: center; color: #B5C8D9; font-size: 10px; }
QProgressBar::chunk { background: #45CDB7; border-radius: 5px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #304257; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #466078; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip { background: #203247; color: #E8EFF7; border: 1px solid #405972; padding: 7px; }
QStatusBar { background: #0B111B; color: #7F94AA; border-top: 1px solid #1D2A3A; }
"""
