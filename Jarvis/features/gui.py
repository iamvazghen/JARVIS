# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets

from Jarvis.features.matrix import MatrixRainWidget


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("JIVAN")
        MainWindow.resize(1500, 920)
        MainWindow.setStyleSheet("QMainWindow{background-color: rgb(6, 12, 24);}")

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self._stack = QtWidgets.QStackedLayout(self.centralwidget)
        self._stack.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self.centralwidget.setLayout(self._stack)

        self.matrix = MatrixRainWidget(self.centralwidget)
        self.matrix.setObjectName("matrix")
        self.matrix.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._stack.addWidget(self.matrix)

        self.overlay = QtWidgets.QWidget(self.centralwidget)
        self.overlay.setObjectName("overlay")
        self.overlay.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.overlay.setStyleSheet(
            "QWidget#overlay{"
            "background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(4,10,20,95), stop:0.6 rgba(6,16,30,65), stop:1 rgba(8,22,40,85));"
            "}"
        )
        self._stack.addWidget(self.overlay)

        primary_font = "Segoe UI Variable Text"
        if not QtGui.QFont(primary_font).exactMatch():
            primary_font = "Segoe UI"
        mono = "Cascadia Mono"
        if not QtGui.QFont(mono).exactMatch():
            mono = "Consolas"

        panel_qss = (
            "QFrame{"
            "background-color: rgba(10, 18, 34, 190);"
            "border: 1px solid rgba(58, 170, 255, 130);"
            "border-radius: 18px;"
            "}"
        )
        soft_panel_qss = (
            "QFrame{"
            "background-color: rgba(11, 22, 40, 170);"
            "border: 1px solid rgba(52, 132, 201, 140);"
            "border-radius: 18px;"
            "}"
        )
        scrollbars_qss = (
            "QScrollBar:vertical{background:transparent;width:10px;margin:6px 3px 6px 0px;}"
            "QScrollBar::handle:vertical{background:rgba(58,170,255,95);border-radius:5px;min-height:28px;}"
            "QScrollBar::handle:vertical:hover{background:rgba(58,170,255,145);}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}"
        )

        outer = QtWidgets.QVBoxLayout(self.overlay)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)

        outer_row = QtWidgets.QHBoxLayout()
        outer_row.setContentsMargins(0, 0, 0, 0)
        outer_row.setSpacing(0)
        outer_row.addStretch(1)

        self.centerContainer = QtWidgets.QWidget(self.overlay)
        self.centerContainer.setObjectName("centerContainer")
        self.centerContainer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.centerContainer.setMaximumWidth(1360)
        self.centerContainer.setMaximumHeight(860)
        outer_row.addWidget(self.centerContainer, 0)
        outer_row.addStretch(1)

        outer.addLayout(outer_row, 0)
        outer.addStretch(1)

        root = QtWidgets.QGridLayout(self.centerContainer)
        root.setContentsMargins(36, 28, 36, 28)
        root.setHorizontalSpacing(22)
        root.setVerticalSpacing(18)
        root.setRowStretch(0, 0)
        root.setRowStretch(1, 1)
        root.setRowStretch(2, 0)
        root.setColumnStretch(0, 0)
        root.setColumnStretch(1, 1)

        self.hudFrame = QtWidgets.QFrame(self.overlay)
        self.hudFrame.setStyleSheet(panel_qss)
        self.hudFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.hudFrame.setObjectName("hudFrame")
        self.hudFrame.setMinimumWidth(520)
        self.hudFrame.setMaximumWidth(560)

        hud_layout = QtWidgets.QVBoxLayout(self.hudFrame)
        hud_layout.setContentsMargins(22, 18, 22, 18)
        hud_layout.setSpacing(10)

        self.titleLabel = QtWidgets.QLabel(self.hudFrame)
        self.titleLabel.setStyleSheet(
            "color: rgb(232, 244, 255);"
            f"font: 700 28pt \"{primary_font}\";"
            "letter-spacing: 1px;"
        )
        self.titleLabel.setObjectName("titleLabel")

        self.subtitleLabel = QtWidgets.QLabel(self.hudFrame)
        self.subtitleLabel.setStyleSheet(
            "color: rgba(116, 196, 255, 225);"
            f"font: 11pt \"{primary_font}\";"
        )
        self.subtitleLabel.setObjectName("subtitleLabel")

        self.statusChip = QtWidgets.QLabel(self.hudFrame)
        self.statusChip.setStyleSheet(
            "color: rgb(227, 241, 255);"
            "background-color: rgba(56, 161, 255, 24);"
            "border: 1px solid rgba(56, 161, 255, 160);"
            "border-radius: 10px;"
            "padding: 6px 10px;"
            f"font: 700 10pt \"{primary_font}\";"
        )
        self.statusChip.setObjectName("statusChip")
        self.statusChip.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)

        self.hintLabel = QtWidgets.QLabel(self.hudFrame)
        self.hintLabel.setStyleSheet(
            "color: rgba(184, 214, 239, 195);"
            f"font: 10pt \"{primary_font}\";"
        )
        self.hintLabel.setWordWrap(True)
        self.hintLabel.setObjectName("hintLabel")

        self.hudDivider = QtWidgets.QFrame(self.hudFrame)
        self.hudDivider.setStyleSheet("background-color: rgba(58, 170, 255, 110);")
        self.hudDivider.setFrameShape(QtWidgets.QFrame.HLine)
        self.hudDivider.setObjectName("hudDivider")

        self.hudConsoleTitle = QtWidgets.QLabel(self.hudFrame)
        self.hudConsoleTitle.setStyleSheet(
            "color: rgba(203, 230, 251, 205);"
            f"font: 700 10pt \"{primary_font}\";"
            "letter-spacing: 1px;"
        )
        self.hudConsoleTitle.setObjectName("hudConsoleTitle")

        self.hudConsole = QtWidgets.QTextBrowser(self.hudFrame)
        self.hudConsole.setStyleSheet(
            "QTextBrowser{"
            "background-color: rgba(8, 16, 29, 175);"
            "border: 1px solid rgba(58, 170, 255, 110);"
            "border-radius: 14px;"
            "padding: 12px;"
            "color: rgba(214, 236, 255, 228);"
            f"font: 10pt \"{primary_font}\";"
            "}"
            + scrollbars_qss
        )
        self.hudConsole.setOpenExternalLinks(True)
        self.hudConsole.setObjectName("hudConsole")

        hud_layout.addWidget(self.titleLabel)
        hud_layout.addWidget(self.subtitleLabel)
        hud_layout.addWidget(self.statusChip)
        hud_layout.addWidget(self.hintLabel)
        hud_layout.addWidget(self.hudDivider)
        hud_layout.addWidget(self.hudConsoleTitle)
        hud_layout.addWidget(self.hudConsole, 1)

        self.clockFrame = QtWidgets.QFrame(self.overlay)
        self.clockFrame.setStyleSheet(soft_panel_qss)
        self.clockFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.clockFrame.setObjectName("clockFrame")
        self.clockFrame.setMinimumHeight(84)

        clock_layout = QtWidgets.QHBoxLayout(self.clockFrame)
        clock_layout.setContentsMargins(18, 10, 18, 10)
        clock_layout.setSpacing(12)

        self.textBrowser = QtWidgets.QTextBrowser(self.clockFrame)
        self.textBrowser.setStyleSheet(
            "QTextBrowser{"
            "background: transparent;"
            "border: none;"
            f"font: 700 14pt \"{primary_font}\";"
            "color: rgba(214, 236, 255, 220);"
            "}"
        )
        self.textBrowser.setObjectName("textBrowser")

        divider = QtWidgets.QFrame(self.clockFrame)
        divider.setFrameShape(QtWidgets.QFrame.VLine)
        divider.setStyleSheet("background-color: rgba(58, 170, 255, 80);")
        divider.setFixedWidth(1)

        self.textBrowser_2 = QtWidgets.QTextBrowser(self.clockFrame)
        self.textBrowser_2.setStyleSheet(
            "QTextBrowser{"
            "background: transparent;"
            "border: none;"
            f"font: 700 16pt \"{primary_font}\";"
            "color: rgba(223, 242, 255, 235);"
            "}"
        )
        self.textBrowser_2.setObjectName("textBrowser_2")

        clock_layout.addWidget(self.textBrowser, 1)
        clock_layout.addWidget(divider)
        clock_layout.addWidget(self.textBrowser_2, 1)

        self.rightFrame = QtWidgets.QFrame(self.overlay)
        self.rightFrame.setStyleSheet(panel_qss)
        self.rightFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.rightFrame.setObjectName("rightFrame")

        right_layout = QtWidgets.QVBoxLayout(self.rightFrame)
        right_layout.setContentsMargins(22, 18, 22, 18)
        right_layout.setSpacing(10)

        self.rightTitle = QtWidgets.QLabel(self.rightFrame)
        self.rightTitle.setStyleSheet(
            "color: rgba(203, 230, 251, 205);"
            f"font: 700 10pt \"{primary_font}\";"
            "letter-spacing: 1px;"
        )
        self.rightTitle.setObjectName("rightTitle")

        self.textBrowser_3 = QtWidgets.QTextBrowser(self.rightFrame)
        self.textBrowser_3.setStyleSheet(
            "QTextBrowser{"
            "background-color: rgba(8, 16, 29, 175);"
            "border: 1px solid rgba(58, 170, 255, 105);"
            "border-radius: 14px;"
            "padding: 14px;"
            f"font: 10pt \"{primary_font}\";"
            "color: rgba(214, 236, 255, 228);"
            "}"
            + scrollbars_qss
        )
        self.textBrowser_3.setOpenExternalLinks(True)
        self.textBrowser_3.setObjectName("textBrowser_3")

        right_layout.addWidget(self.rightTitle)
        right_layout.addWidget(self.textBrowser_3, 1)

        self.bottomBar = QtWidgets.QFrame(self.overlay)
        self.bottomBar.setStyleSheet(soft_panel_qss)
        self.bottomBar.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.bottomBar.setObjectName("bottomBar")
        self.bottomBar.setMinimumHeight(76)

        bottom_layout = QtWidgets.QHBoxLayout(self.bottomBar)
        bottom_layout.setContentsMargins(18, 10, 18, 10)
        bottom_layout.setSpacing(12)

        self.bottomHint = QtWidgets.QLabel(self.bottomBar)
        self.bottomHint.setStyleSheet(
            "color: rgba(191, 218, 243, 170);"
            f"font: 9pt \"{primary_font}\";"
        )
        self.bottomHint.setObjectName("bottomHint")
        self.bottomHint.setWordWrap(True)

        self.pushButton = QtWidgets.QPushButton(self.bottomBar)
        self.pushButton.setMinimumSize(QtCore.QSize(132, 48))
        self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton.setStyleSheet(
            "QPushButton{"
            "background-color: rgba(58, 170, 255, 220);"
            "color: rgb(8, 22, 40);"
            f"font: 700 13pt \"{primary_font}\";"
            "border-radius: 14px;"
            "border: 1px solid rgba(211, 235, 255, 185);"
            "padding: 8px 18px;"
            "}"
            "QPushButton:hover{background-color: rgba(96, 189, 255, 240);}"
            "QPushButton:pressed{background-color: rgba(36, 142, 230, 230);}"
            "QPushButton:disabled{background-color: rgba(58, 170, 255, 70); color: rgba(5,16,28,120);}"
        )
        self.pushButton.setObjectName("pushButton")

        bottom_layout.addWidget(self.bottomHint, 1)
        bottom_layout.addWidget(
            self.pushButton,
            0,
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,  # type: ignore[arg-type]
        )

        root.addWidget(self.hudFrame, 0, 0, 3, 1)
        root.addWidget(self.clockFrame, 0, 1)
        root.addWidget(self.rightFrame, 1, 1)
        root.addWidget(self.bottomBar, 2, 1)

        self._shadows = []
        for widget in (self.hudFrame, self.clockFrame, self.rightFrame, self.bottomBar):
            shadow = QtWidgets.QGraphicsDropShadowEffect(self.overlay)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 0)
            shadow.setColor(QtGui.QColor(58, 170, 255, 65))
            widget.setGraphicsEffect(shadow)
            self._shadows.append(shadow)

        self.centralwidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1500, 26))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "JIVAN"))
        self.titleLabel.setText(_translate("MainWindow", "JIVAN"))
        self.subtitleLabel.setText(_translate("MainWindow", "Just Intelligent Versatile, Autonomous Nexus"))
        self.statusChip.setText(_translate("MainWindow", "SYSTEM READY"))
        self.hintLabel.setText(
            _translate("MainWindow", "Natural voice control + deterministic tools + protocol automation.")
        )
        self.hudConsoleTitle.setText(_translate("MainWindow", "MISSION BRIEF"))
        self.rightTitle.setText(_translate("MainWindow", "LIVE OPERATIONS"))
        self.pushButton.setText(_translate("MainWindow", "RUN"))
        self.bottomHint.setText(
            _translate(
                "MainWindow",
                "Try: telegram send hello, open excel, weather in yerevan, run protocol monday.",
            )
        )

        self.hudConsole.setHtml(
            "<div style='line-height:1.45'>"
            "<span style='color:#E8F4FF'><b>JIVAN</b></span> // command center online<br/>"
            "Press <b>RUN</b> to start listening.<br/>"
            "Examples: <i>telegram send hello</i>, <i>open excel</i>, <i>tell me about Ada Lovelace</i>."
            "</div>"
        )
        self.textBrowser_3.setHtml(
            "<div style='line-height:1.55'>"
            "<span style='color:#E8F4FF'><b>JIVAN</b></span> // ACTIVE<br/>"
            "MODE: <span style='color:#3AAAFF'>OPERATOR</span><br/><br/>"
            "<span style='color:#3AAAFF'>POLICY</span>: Tool-first execution for deterministic results."
            "</div>"
        )
        self.matrix.lower()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main_window = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(main_window)
    main_window.show()
    sys.exit(app.exec_())
