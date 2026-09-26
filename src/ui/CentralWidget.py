from PyQt5.QtWidgets import QFrame, QVBoxLayout


class CentralWidget(QFrame):
    def __init__(self, parent, key_dis, mod_dis):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedSize(220, 100)
        self.setStyleSheet("""
            QFrame#Card {
                background-color: #000000;
                border: 1px solid #1f1f22;
                border-radius: 14px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.layout.addWidget(key_dis, 68)
        self.layout.addWidget(mod_dis, 32)


