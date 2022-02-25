#%%
import sys
import os
import datetime
from PySide2 import QtXml
from PySide2 import QtUiTools, QtGui
from PySide2.QtWidgets import QApplication, QMainWindow, QHeaderView, QFileDialog, QTableWidgetItem


class MainView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUI()
        self.setButtons()

 

    def setupUI(self):
        global UI_MAIN, UI_REPLACE, UI_FRONT, UI_BACK

 

        # 메인 화면
        UI_MAIN = QtUiTools.QUiLoader().load(resource_path("filenamechange.ui"))

        # 문자열 바꾸기 화면
        UI_REPLACE = QtUiTools.QUiLoader().load(resource_path("filenamechange_replace.ui"))
        UI_REPLACE.setWindowTitle("문자열 변경")
        # 앞문자 추가 화면
        UI_FRONT = QtUiTools.QUiLoader().load(resource_path("filenamechange_front.ui"))
        UI_FRONT.setWindowTitle("앞에 문자 추가")
        # 뒷문자 추가 화면
        UI_BACK = QtUiTools.QUiLoader().load(resource_path("filenamechange_back.ui"))
        UI_BACK.setWindowTitle("뒤에 문자 추가")

 

        # 테이블 위젯 컬럼 이름 설정
        UI_MAIN.TW_list.setHorizontalHeaderLabels(['현재이름','변경이름','파일경로','파일크기','변경시각'])

        # 테이블 헤더 사이즈 늘리기

        UI_MAIN.TW_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

 

        self.setCentralWidget(UI_MAIN)
        self.setWindowTitle("파일 이름 변경 프로그램")
        self.resize(800, 600)
        self.show()

 

    def setButtons(self):
        UI_MAIN.BTN_list.clicked.connect(self.FilesOpen)

 

        # 문자열 바꾸기 버튼 클릭
        UI_MAIN.BTN_replace.clicked.connect(self.NameReplaceFormOn)
        # 문자열 변경 창의 취소 버튼
        UI_REPLACE.BTN_cancel.clicked.connect(self.NameReplaceFormOff)
        # 문자열 변경 창의 확인 버튼
        UI_REPLACE.BTN_confirm.clicked.connect(NameReplace)

 

        # 앞문자 추가
        UI_MAIN.BTN_frontadd.clicked.connect(self.FrontaddFormOn)
        # 앞문자 추가 창의 취소 버튼
        UI_FRONT.BTN_cancel.clicked.connect(self.FrontaddFormOff)
        # 앞문자 추가 창의 확인 버튼
        UI_FRONT.BTN_confirm.clicked.connect(Frontadd)

 

        # 뒷문자 추가
        UI_MAIN.BTN_backadd.clicked.connect(self.BackaddFormOn)
        # 뒷문자 추가 창의 취소 버튼
        UI_BACK.BTN_cancel.clicked.connect(self.BackaddFormOff)
        # 뒷문자 추가 창의 확인 버튼
        UI_BACK.BTN_confirm.clicked.connect(Backadd)

        # 변경 적용 버튼 눌렀을 때
        UI_MAIN.BTN_excute.clicked.connect(RenameExcute)

 

        # 변경 취소 버튼 눌렀을 때
        UI_MAIN.BTN_cancel.clicked.connect(RenameReset)


    # Non static function 다중 파일
    def FilesOpen(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter(self.tr("Images (*.png *.xpm *.jpg *.gif);; All Files(*.*)"))
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            fileNames = dialog.selectedFiles()
            # 파일 목록을 테이블 위젯에 넣기 위해 setList 함수 호출
            setList(fileNames)

 

    # 문자열 바꾸기 버튼 클릭, 문자열 변경 창을 보여준다.
    def NameReplaceFormOn(self):
        UI_REPLACE.show()

        UI_REPLACE.activateWindow()

    # 문자열 변경 창에서 취소 클릭, 문자열 변경 창을 사라지게 한다.
    def NameReplaceFormOff(self):
        UI_REPLACE.close()


    # 앞문자 추가 클릭, 앞문자 추가 창을 보여준다.
    def FrontaddFormOn(self):
        UI_FRONT.show()

        UI_FRONT.activateWindow()

    # 앞문자 추가 창에서 취소 클릭, 앞문자 추가 창을 사라지게 한다.
    def FrontaddFormOff(self):
        UI_FRONT.close()

 

    # 뒷문자 추가 클릭, 뒷문자 추가 창을 보여준다.
    def BackaddFormOn(self):
        UI_BACK.show()

        UI_BACK.activateWindow()

    # 뒷문자 추가 창에서 취소 클릭, 뒷문자 추가 창을 사라지게 한다.
    def BackaddFormOff(self):
        UI_BACK.close()
 


def RenameReset():
    # 테이블 위젯의 row count
    rowcount = UI_MAIN.TW_list.rowCount()
    for i in range(rowcount):
        # 변경할 이름을 현재 파일 이름으로 모두 변경한다.
        # 현재 이름
        cname = UI_MAIN.TW_list.item(i, 0).text()
        # 변경이름을 현재이름으로 바꾸어 준다.
        UI_MAIN.TW_list.item(i, 1).setText(cname)

 

def RenameExcute():
    # 테이블 위젯의 row count
    rowcount = UI_MAIN.TW_list.rowCount()
    for i in range(rowcount):
        # 파일 이름과 경로를 받아온다.
        # 경로
        dir = UI_MAIN.TW_list.item(i, 2).text()
        # 현재 이름
        cname = UI_MAIN.TW_list.item(i, 0).text()
        # 변경할 이름
        newname = UI_MAIN.TW_list.item(i, 1).text()

 

        # 현재 이름과 변경할 이름이 다르면 이름을 변경한다.
        if cname != newname:
            result = os.rename(dir + "/" + cname, dir + "/" + newname)
            # 변경 후 원래 이름을 변경 이름으로 바꾸어 준다.
            UI_MAIN.TW_list.item(i, 0).setText(newname)

def Backadd():
    # 파일 이름 뒤에 추가할 문자열
    str_new = UI_BACK.LE_str.text()

 

    # 테이블 위젯의 row count 만큼 반복하며 변경 이름의 텍스트를 변경하여 다시 저장한다.
    # 테이블 위젯의 row count
    rowcount = UI_MAIN.TW_list.rowCount()
    # 테이블 row 수만큼 반복
    for i in range(rowcount):
        # 변경이름의 값을 받아온다.
        prevname = UI_MAIN.TW_list.item(i, 1).text()

 

        # 파일 이름과 확장자를 구분한다.
        tempname = prevname.split(".")
        # 변경이름에서 변경할 문자열을 변경한다.
        newname = tempname[0] + str_new + "." + tempname[1]

 

        # 변경이름에 다시 입력한다.
        UI_MAIN.TW_list.item(i, 1).setText(newname)

 

    # 작업을 마치고 창을 닫는다.
    UI_BACK.close()

 

def Frontadd():
    # 파일 이름 앞에 추가할 문자열
    str_new = UI_FRONT.LE_str.text()

 

    # 테이블 위젯의 row count 만큼 반복하며 변경 이름의 텍스트를 변경하여 다시 저장한다.
    # 테이블 위젯의 row count
    rowcount = UI_MAIN.TW_list.rowCount()
    # 테이블 row 수만큼 반복
    for i in range(rowcount):
        # 변경이름의 값을 받아온다.
        prevname = UI_MAIN.TW_list.item(i, 1).text()
        # 변경이름에서 변경할 문자열을 변경한다.
        newname = str_new + prevname

 

        # 변경이름에 다시 입력한다.
        UI_MAIN.TW_list.item(i, 1).setText(newname)

 

    # 작업을 마치고 창을 닫는다.
    UI_FRONT.close()

 

def NameReplace():
    # 문자열 변경창에서 확인 버튼이 눌렸을 때
    # 변경될 문자열
    str_prev = UI_REPLACE.LE_prev.text()
    # 변경할 문자열
    str_new = UI_REPLACE.LE_new.text()

 

    # 테이블 위젯의 row count 만큼 반복하며 변경 이름의 텍스트를 변경하여 다시 저장한다.
    # 테이블 위젯의 row count
    rowcount = UI_MAIN.TW_list.rowCount()
    # 테이블 row 수만큼 반복
    for i in range(rowcount):
        # 변경이름의 값을 받아온다.
        prevname = UI_MAIN.TW_list.item(i, 1).text()
        # 변경이름에서 변경할 문자열을 변경한다.
        newname = prevname.replace(str_prev, str_new)

        # 변경이름에 다시 입력한다.
        UI_MAIN.TW_list.item(i, 1).setText(newname)

    

    # 작업을 마치고 창을 닫는다.

    UI_REPLACE.close()


def setList(fileNames):
    # 파일 목록 갯수 저장
    count = len(fileNames)
    # 파일 목록 갯수만큼 row 생성
    UI_MAIN.TW_list.setRowCount(count)

 

    # 파일 정보를 테이블 위젯에 삽입

    for i in range(count):
        # 파일 경로와 파일 이름
        dir, file = os.path.split(fileNames[i])
        # 파일 크기
        fsize = os.path.getsize(fileNames[i])

        # 변경 시각 - 유닉스 타임으로 반환
        mtime = os.path.getmtime(fileNames[i])

        # 유닉스 타임을 년월일시분초 형태로 변환 (1580628774 -> 2020-02-02 00:32:54)
        mtimestamp = datetime.datetime.fromtimestamp(int(mtime))
  

        # 테이블 아이템 입력
        UI_MAIN.TW_list.setItem(i, 0, QTableWidgetItem(file))
        UI_MAIN.TW_list.setItem(i, 1, QTableWidgetItem(file))
        UI_MAIN.TW_list.setItem(i, 2, QTableWidgetItem(dir))
        UI_MAIN.TW_list.setItem(i, 3, QTableWidgetItem(str(fsize)))
        UI_MAIN.TW_list.setItem(i, 4, QTableWidgetItem(str(mtimestamp)))


# 파일 경로
# pyinstaller로 원파일로 압축할때 경로 필요함
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainView()
    # main.show()
    sys.exit(app.exec_())
# %%
