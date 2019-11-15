from psyhive.qt import QtCore, QtGui, QtWidgets, QtUiTools


class UICollapseForm(QtWidgets.QWidget):
    def __init__(self):
        super(UICollapseForm, self).__init__()
        collapse_form = self
        collapse_form.setObjectName("collapseForm")
        collapse_form.resize(1009, 162)

        self.formGLayout = QtWidgets.QGridLayout(collapse_form)
        self.formGLayout.setContentsMargins(0, 0, 0, 0)
        self.formGLayout.setSpacing(0)
        self.formGLayout.setObjectName("formGLayout")

        # Setup Frame ---------------------------------------------------------------------
        self.collapseFrame = QtWidgets.QFrame(collapse_form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.collapseFrame.sizePolicy().hasHeightForWidth())
        self.collapseFrame.setSizePolicy(sizePolicy)
        self.collapseFrame.setMinimumSize(QtCore.QSize(0, 0))
        self.collapseFrame.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.collapseFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.collapseFrame.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.collapseFrame.setLineWidth(2)
        self.collapseFrame.setObjectName("collapseFrame")

        self.frameGLayout = QtWidgets.QGridLayout(self.collapseFrame)
        self.frameGLayout.setContentsMargins(2, 0, 2, 0)
        self.frameGLayout.setHorizontalSpacing(0)
        self.frameGLayout.setVerticalSpacing(2)
        self.frameGLayout.setObjectName("frameGLayout")

        #  Setup ToolButton ----------------------------------------------------------------------
        self.toolBtn = QtWidgets.QToolButton(self.collapseFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolBtn.sizePolicy().hasHeightForWidth())
        self.toolBtn.setSizePolicy(sizePolicy)
        self.toolBtn.setMinimumSize(QtCore.QSize(0, 25))
        # self.set_toolbtn_font()

        self.toolBtn.setCheckable(True)
        self.toolBtn.setChecked(False)
        self.toolBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolBtn.setAutoRaise(True)
        self.toolBtn.setArrowType(QtCore.Qt.RightArrow)
        self.toolBtn.setObjectName("collapseToolBtn")
        self.frameGLayout.addWidget(self.toolBtn, 1, 0, 1, 2)

        # Setup Group Box ----------------------------------------------------------------------
        self.grp = QtWidgets.QGroupBox(self.collapseFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grp.sizePolicy().hasHeightForWidth())
        self.grp.setSizePolicy(sizePolicy)
        self.grp.setTitle("")
        self.grp.setObjectName("collapseGrp")
        self.grpGLayout = QtWidgets.QGridLayout(self.grp)
        self.grpGLayout.setContentsMargins(0, 0, 0, 0)
        self.grpGLayout.setSpacing(0)
        self.grpGLayout.setObjectName("grpGLayout")
        self.frameGLayout.addWidget(self.grp, 2, 0, 1, 2)
        self.formGLayout.addWidget(self.collapseFrame, 0, 0, 1, 1)

        # Connect button
        self.toolBtn.toggled.connect(self.grp.setVisible)

    def set_toolbtn_font(self):
        font = QtGui.QFont()
        font.setFamily("Meiryo")
        font.setPointSize(10)
        font.setWeight(75)
        font.setBold(True)

        self.toolBtn.setFont(font)

    def set_style(self, color=None):
        style = {'raised_style': """QToolButton {{ background-color:rgb({tint}, 90);
                     color: rgb(200, 200, 200);
                     border-bottom: 1px solid rgb(30,30,30);
                     border-right: 1px solid rgb(30,30,30);
                     border-top: 1px solid rgb(97, 97, 97);
                     border-left: 1px solid rgb(97, 97, 97);  }}

                     QToolButton:checked {{    background-color: rgba({tint}, 120);
                     color: rgb(200, 200, 200);
                     border-top: 1px solid rgb(30,30,30);
                     border-left: 1px solid rgb(30,30,30);
                     border-bottom: 1px solid rgb(97, 97, 97);
                     border-right: 1px solid rgb(97, 97, 97);  }}

                     QToolButton:hover:!checked {{background-color: rgba({tint}, 120);
                     color: rgb(200, 200, 200);
                     border-bottom: 1px solid rgb(30,30,30);
                     border-right: 1px solid rgb(30,30,30);
                     border-top: 1px solid rgb(97, 97, 97);
                     border-left: 1px solid rgb(97, 97, 97);  }}

                     QToolButton:hover:checked {{background-color: rgba({tint}, 190);
                     color: rgb(200, 200, 200);
                     border-top: 1px solid rgb(30,30,30);
                     border-left: 1px solid rgb(30,30,30);
                     border-bottom: 1px solid rgb(97, 97, 97);
                     border-right: 1px solid rgb(97, 97, 97);  }}
                     """,
                 'default': """QToolButton {{background-color:rgb({tint}, 90); color: rgb(200, 200, 200);}}
                     QToolButton:checked {{background-color: rgba({tint}, 120); color: rgb(200, 200, 200);}}
                     QToolButton:hover:!checked {{background-color: rgba({tint}, 120); color: rgb(200, 200, 200);}}
                     QToolButton:hover:checked {{background-color: rgba({tint}, 190); color: rgb(200, 200, 200); }}
                     """,
                 'grp_border_style': """ QGroupBox{{
                                    border: 1px solid rgba({tint}, 120);
                                    border-radius: 0px;
                                    margin-top: 0ex;
                                    margin-bottom: 0ex;
                                    padding: 2 2px;}}

                             QGroupBox:title {{
                                    border: 1px solid rgba({tint}, 120);
                                    subcontrol-origin: margin;
                                    subcontrol-position: top center;
                                    padding: 10 0px;}}"""
                 }
        default_style = """QToolButton {{
                                background-color:rgb({tint}, 90);
                                color: rgb(200, 200, 200);}}
                            QToolButton:checked {{
                                background-color: rgba({tint}, 120);
                                color: rgb(200, 200, 200);}}
                            QToolButton:hover:!checked {{
                                background-color: rgba({tint}, 120);
                                color: rgb(200, 200, 200);}}
                            QToolButton:hover:checked {{
                                background-color: rgba({tint}, 190);
                                color: rgb(200, 200, 200); }}
                            """
        default_grp_style = """ QGroupBox{{
                                            border: 1px solid rgba({tint}, 120);
                                            border-radius: 0px;
                                            margin-top: 0ex;
                                            margin-bottom: 0ex;
                                            padding: 2 2px;}}

                                     QGroupBox:title {{
                                            border: 1px solid rgba({tint}, 120);
                                            subcontrol-origin: margin;
                                            subcontrol-position: top center;
                                            padding: 10 0px;}}"""

        self.grp.setStyleSheet(style.get('grp_border_style', default_grp_style).format(tint=self.color))
        self.toolBtn.setStyleSheet(style.get('default_style', default_style).format(tint=self.color))


class MayaFrameWidget(UICollapseForm):
    __class_name__ = "MayaCFrame"

    def __init__(self, parent=None, name=None, state=False, color='160, 160, 170', toolname="tul", win=None, ui=None):
        super(MayaFrameWidget, self).__init__()
        # self.parent = parent
        self.main_tool_window = win
        self.name = name
        self.toolname = toolname
        self.color = color

        self.toolBtn = self.findChildren(QtWidgets.QToolButton, 'collapseToolBtn')[-1]
        self.grp = self.findChildren(QtWidgets.QGroupBox, 'collapseGrp')[-1]
        self.layout = self.grp.findChildren(QtWidgets.QLayout, 'grpGLayout')[-1]

        self.toolBtn.setText(name)
        self.toolBtn.setChecked(state)
        self.toggle_arrow(self.toolBtn)
        self.toolBtn.setWindowState(state)

        self.grp.setVisible(state)
        self.toolBtn.clicked.connect(lambda: self.toggle_arrow(self.toolBtn))
        self.set_style()
        self.ui = None
        if ui:
            self.load_ui(ui_file=ui)

    def toggle_arrow(self, *args):
        self.arrow_update(args[0], args[0].isChecked())
        main_window = self.main_tool_window
        hint = main_window.minimumSizeHint()
        current_size = main_window.size()
        w = current_size.width()
        h = hint.height()
        # size = QtCore.QSize(w, h)
        # pos = main_window.pos()
        g = main_window.geometry()
        main_window.setGeometry(g.x(), g.y(), w, h)
        # main_window.resize(size)

    def arrow_update(self, widget, *args):
        if args[0]:
            widget.setArrowType(QtCore.Qt.DownArrow)
        else:
            widget.setArrowType(QtCore.Qt.RightArrow)

    def load_ui(self, ui_file=None):
        self.ui = QtUiTools.QUiLoader().load(ui_file)
        self.layout.addWidget(self.ui)
