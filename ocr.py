import os
from time import sleep
from tkinter import Tk, Label, RAISED, Toplevel, Canvas, PhotoImage, BOTH, YES, NW
from PIL import ImageGrab, ImageTk
import pytesseract
import pyperclip

from pytesseract import Output

from system_hotkey import SystemHotkey


def ocr(im):
    # im = ImageGrab.grabclipboard()
    if im:
        result = pytesseract.image_to_string(im, lang="chi_sim+eng+equ", output_type=Output.STRING)
        print(result)
        pyperclip.copy(result)


class MyCapture(object):
    def __init__(self, image):
        # 变量X和Y用来记录鼠标左键按下的位置
        self.X = 0
        self.Y = 0

        self.selectPosition = None
        # 屏幕尺寸
        screen_width = root.winfo_screenwidth()
        # print(screenWidth)
        screen_height = root.winfo_screenheight()
        # print(screenHeight)
        # 创建顶级组件容器
        self.top = Toplevel(root, width=screen_width, height=screen_height)

        # 不显示最大化、最小化按钮
        self.top.overrideredirect(True)
        self.canvas = Canvas(self.top, width=screen_width, height=screen_height)

        # 显示全屏截图，在全屏截图上进行区域截图
        self.image = image
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.photo, anchor=NW)

        self.canvas.pack(fill=BOTH, expand=YES)

        # 鼠标左键按下的位置
        def onLeftButtonDown(event):
            self.X = event.x
            self.Y = event.y
            # 开始截图
            self.sel = True

        self.canvas.bind('<Button-1>', onLeftButtonDown)

        # 鼠标左键移动，显示选取的区域
        def onLeftButtonMove(event):
            if not self.sel:
                return
            global lastDraw
            try:
                # 删除刚画完的图形，要不然鼠标移动的时候是黑乎乎的一片矩形
                self.canvas.delete(lastDraw)
            except Exception as e:
                pass

            lastDraw = self.canvas.create_rectangle(self.X, self.Y, event.x, event.y, outline='black')

        self.canvas.bind('<B1-Motion>', onLeftButtonMove)

        # 获取鼠标左键抬起的位置，保存区域截图
        def onLeftButtonUp(event):
            self.sel = False
            global lastDraw
            try:
                self.canvas.delete(lastDraw)
            except Exception as e:
                pass
            sleep(0.1)
            # 考虑鼠标左键从右下方按下而从左上方抬起的截图
            left, right = sorted([self.X, event.x])
            top, bottom = sorted([self.Y, event.y])
            im = self.image.crop((left, top, right, bottom))
            if im:
                ocr(im)
                im.close()

            self.top.destroy()

        self.canvas.bind('<ButtonRelease-1>', onLeftButtonUp)


def capture(event,*args,**kwargs):
    # 最小化主窗口
    # root.state('icon')
    # sleep(0.2)

    filename = 'temp.png'
    im = ImageGrab.grab()

    # im.close()
    # 显示全屏幕截图
    w = MyCapture(im)
    # im.close()

    # print(w.myleft,w.mybottom)
    # 截图结束，恢复主窗口，并删除临时的全屏幕截图文件
    # label.config(text='Hello')
    root.state('normal')
    # os.remove(filename)


# The key combination to check

# The currently active modifiers
current = set()

if __name__ == '__main__':
    root = Tk()
    label = Label(root, text="OCR识别中", cursor="plus", relief=RAISED, pady=5, wraplength=500)

    label.pack()

    hk = SystemHotkey()
    hk.register(('control', 'alt', 'w'), callback=capture)

    root.mainloop()
