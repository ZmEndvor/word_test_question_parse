import ctypes
import os
import re
import copy
import pyperclip
import datetime
import operator
from functools import reduce
from collections import Counter
from PIL import ImageGrab, Image
from win32com import client as wc
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import keyboard
import shortuuid
import uuid
from pytesseract import pytesseract
import subprocess

from question_parser.equation.wordconverter import WordConverter


def get_short_uuid(length=10):
    '''
    获取短UUID
    :return:
    '''
    shortuuid.set_alphabet('1234567890abcdefghijklmnopqrstuvwxyz')
    if length > 22:  # max length is 22
        raise ValueError(u'最大长度22')
    return shortuuid.encode(uuid.uuid1())[:length]

class settings(object):
    MEDIA_URL = 'static'
    MEDIA_ROOT = 'media'


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super(TrayIcon, self).__init__(parent)
        self.setIcon(QIcon("bing.ico"))
        self.icon = self.MessageIcon()
        self.showMenu()
        self.bindHotKey()
        self.prScrnLib = self.loadLibrary()
        self.rubbish_list = []

    def loadLibrary(self):
        try:
            return ctypes.cdll.LoadLibrary('PrScrn.dll')
        except Exception:
            print("Dll load error!")
            return

    def showMenu(self):
        """
        菜单设计
        :return:
        """
        self.menu = QMenu()
        self.menuOCR = QAction("OCR", self, triggered=self.ocr)
        self.menuOCR.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_F1))

        self.menuParseWord = QAction("Word解析", self, triggered=self.parseWord)
        self.menuParseWord.setShortcut(QKeySequence(Qt.CTRL+Qt.Key_F2))

        self.menuQuit = QAction("退出", self, triggered=self.quit)

        self.menu.addAction(self.menuOCR)
        self.menu.addAction(self.menuParseWord)
        self.menu.addAction(self.menuQuit)
        self.setContextMenu(self.menu)

    def ocr(self):
        """
        启动时微信截图
        :return:
        """
        params = {
            "identifier": 'venus',  # 固定取值 venus。云平台只认识此格式
            "format": 'question',  # 格式类型，可以是question 或 plain，亦或 latex
            "text": "",
            "question": {  # 格式为question时有定义
                "sourceText": "",  # 来源。题目开头，圆括号，方括号等标明出处的文本
                "content": "",  # 题干
                "type": '',  # 单选、多选、非选择、题组
                "answer": "",  # 正确答案. 多选答案用 : 分割。如A:B
                "analysis": "",  # 解析
                "options": [],
                "children": []  # 包含题组时有定义。内容为question相同格式。但不可再包含children
            },
            'origin': ""  # 解析前的原始内容
        }

        try:
            self.prScrnLib.PrScrn(0)
        except Exception:
            self.showMessage("截图失败")
            return
        im = ImageGrab.grabclipboard()
        if im:
            # 使用Tesseract识别
            # TODO：调整角度、 去噪、二值化。目前测试看并不理想，暂不处理
            print("Will ocr")
            im.save("temp.png")
            im.close()
            result = pytesseract.image_to_string("temp.png", lang="chi_sim+eng+equ")
            print(result)

            if result:
                self.parse_questions(result, params)
                print(params)
            else:
                raise Exception("图片内容为空")

    def generate_file_name(self):
        """ 返回要保存的文件地址 """

        file_path = datetime.date.today().strftime('{}/uploads/%Y/%m%d/'.format(settings.MEDIA_ROOT))
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        return os.path.join(file_path, get_short_uuid() + '.jpg')

    def save_word_picture(self):
        """
        保存word中的图片, 并返回图片地址
        :return:
        """

        def save_picture(blob: bytes, content_type: str):

            file_name = ''
            if content_type == 'image/x-wmf':
                file_name = self.wmf_save(blob)

            elif blob:
                file_name = self.generate_file_name()

                self.rubbish_list.append(file_name)

                with open(file_name, 'wb') as f:
                    f.write(blob)

            return '<img src="{}">'.format(file_name.replace(settings.MEDIA_ROOT, settings.MEDIA_URL))

        return save_picture

    def wmf_save(self, blob: bytes):
        """ wmf 文件保存 """
        file_name = self.generate_file_name()

        proc = subprocess.Popen(['convert', '-', file_name], stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc.communicate(blob)

        return file_name

    def parseWord(self):
        """
        将尝试解析剪切板中的word片段。
        识别其中的选择题、公式、图片等。
        识别完成后，重新以内部格式存入剪切板
        :return:
        """
        params = {
            "identifier": 'venus',  # 固定取值 venus。云平台只认识此格式
            "format": 'question',  # 格式类型，可以是question 或 plain，亦或 latex
            "text": "",
            "question": {  # 格式为question时有定义
                "sourceText": "",  # 来源。题目开头，圆括号，方括号等标明出处的文本
                "content": "",  # 题干
                "type": '',  # 单选、多选、非选择、题组
                "answer": "",  # 正确答案. 多选答案用 : 分割。如A:B
                "analysis": "",  # 解析
                "options": [],
                "children": []  # 包含题组时有定义。内容为question相同格式。但不可再包含children
            },
            'origin': ""  # 解析前的原始内容
        }

        word_converter = WordConverter()

        try:
            result = word_converter.to_latex(
                self.get_new_word()
            )
        except Exception as exc:
            raise Exception('解析文件错误!')

        self.parse_questions("\n".join(result), params)

        print(params)

        return params

    def get_new_word(self):
        """
        新建一个word，将复制内容粘贴到word中保存。
        :return:
        """
        pwd = os.getcwd()
        word = wc.Dispatch("Word.Application")
        new_word = word.Documents.Add()
        word.Selection.PasteSpecial(DataType='WdPasteDataType')
        word_file = pwd + "\\1.docx"
        if os.path.exists(word_file):
            os.remove(word_file)
        new_word.SaveAs(word_file, 16)
        new_word.Close()

        return word_file

    def parse_questions(self, result, params):
        """
        单个提取 word题目
        :return:
        """
        picture_path = [(i.span(), i.group()) for i in re.finditer(r'(media.*?png)', result)]  # 提取
        for i in picture_path:
            match_span = i[0]
            match_group = i[1]
            result = result[:match_span[0]] + result[match_span[1]:]

        # 提取
        s_result = re.split(r'(\d+\.\s)|(\d+．)', result)
        s_result = self._question_connect([i for i in s_result if i])
        print(s_result)
        content = []  # 存放主体
        for i in s_result:
            if len(i) > 2:
                c = {}
                # 来源
                sourceText_re = r'([\[|\(|（|【]\S+[\]|\)|）|】]<\/?.*?>|[\[|\(|（|【]\S+[\]|\)|）|】])'
                sourceText = re.compile(sourceText_re).findall(i)
                if sourceText:
                    if sourceText[0][1:3] not in ["多选"] and sourceText[0][1] != '例':
                        sourceText_label = re.compile(r'[\]|\)|\）]<(.*?)>').findall(sourceText[0])
                        if sourceText_label:
                            sourceText[0] = '<' + sourceText_label[0].replace('/', '') + '>' + sourceText[0]
                        c['sourceText'] = sourceText[0] if len(re.compile(r'[\[|\(|（|【](.*?)[\]|\)|）|】]').findall(sourceText[0])[0]) > 1 else ''

                # 解析：通过解析字样匹配解析内容
                analysis = re.compile(r'解析(\s\S+)').findall(i)
                analysis = re.compile(r'【解析】(\s\S+)').findall(i) if not analysis else analysis
                c['analysis'] = analysis[0] if analysis else ''

                # 选项：通过A-Z以及.匹配内容多次得到选项以及内容，最后通过切片将选项与选项内容分离为option与content
                options = re.compile(r'([A-Z][．][^A-Z]+)').findall(i)
                opts = re.compile(r'[A-Z][．]').findall(i)

                # 答案
                answer = re.compile(r'答案([\s\S]+)').findall(i)  # 答案内容的匹配
                answer = re.compile(r'【答案】([\s\S]+)').findall(i) if not answer else answer
                c_answer = re.compile(r'(\s*\S+)').findall(answer[0]) if answer else ''  # 当存在多道题目的答案时，将不同题目答案拆解。

                if opts:
                    c_opts = Counter(opts)
                    options = self._options_analysis(options, c_opts)
                    for opt in options:
                        if 'options' in c:
                            c['options'].extend(opt)
                        else:
                            c['options'] = opt
                    c['type'] = self._question_type_analysis_by_options(options, c_answer)  # 题型判断
                else:
                    c['type'] = ''

                # 题目：
                c['content'] = self._question_stem_analysis(i, c['type'])

                for k in list(c.keys()):
                    if not c[k]:
                        del c[k]

                if c:
                    if c_answer:
                        if len(c_answer) > 1:
                            c['answer'] = c_answer
                            params['question']['children'] = self._question_judgment(c)
                            params['question']['type'] = "题组"
                        else:
                            c['answer'] = c_answer[0]

                    if 'type' not in c:
                        if 'answer' in c:
                            if type(c['answer']) is str and len(re.compile(r'[A-Z]').findall(c['answer'])) > 1:
                                c['type'] = '多选'
                            elif type(c['answer']) is str and len(re.compile(r'[A-Z]').findall(c['answer'])) == 1:
                                c['type'] = '单选'
                            else:
                                c['type'] = '非选择题'
                        else:
                            c['type'] = '非选择题'

                    for c_key in params['question'].keys():
                        if c_key not in c.keys() and c_key != 'children':
                            if c_key == 'options':
                                c[c_key] = []
                            else:
                                c[c_key] = ''

                    content.append(c)

        if len(content) == 1:
            params['question'].update(content[0])

        params['origin'] = result

    def _question_stem_analysis(self, content, c_type):
        c_contents = re.split(r'\d+[．|\.\s]', content)
        c_contents = [i for i in c_contents if i not in ['', '\n']]
        contents = []
        for i in c_contents:
            ct = re.compile(r'[\]|\)|）|】]<\/.*?>([\s\S]*)(?:A[\.|．])').findall(i)
            ct = re.compile(r'[\]|\)|）|】]<\/.*?>([\s\S]*)').findall(i) if not ct else ct
            ct = re.compile(r'[\]|\)|）|】]([\s\S]*)(?:A[\.|．])').findall(i) if not ct else ct
            ct = re.compile(r'[\]|\)|）|】]([\s\S]*)').findall(i) if not ct else ct
            ct = re.compile(r'([\s\S]*)(?:A[\.|．])').findall(i) if not ct else ct
            ct = re.compile(r'([\s\S]*)(?:[解析|【解析】|答案|【答案】])').findall(i) if not ct else ct
            if ct:
                ct1 = re.compile(r'([\s\S]*)(?:[解析|【解析】|答案|【答案】])').findall(ct[0])
                contents.append(ct1[0]) if ct1 else contents.append(ct[0])

            if not c_type and not contents:
                contents.append(i)
        return contents[0] if len(contents) == 1 else contents

    def _question_type_analysis_by_options(self, options, c_answer):
        if len(options) > 1:
            return "题组"
        if c_answer:
            if len(c_answer) > 1:
                return "题组"
            if len(re.compile(r'[A-Z]').findall(c_answer[0])) > 1:
                    return "多选"
            return "单选"
        return "选择题"

    def _options_analysis(self, options, count_opts):
        opts = []
        for i in range(0, len(options), len(count_opts)):
            option = []
            for opt in options[i:i + len(count_opts)]:
                if opt:
                    option.append({"option": opt[0], "content": opt[2:]})
            opts.append(option)

        return opts

    def _question_connect(self, s_result):
        question_nums = reduce(operator.add, [re.compile(r'(\d+\.)').findall(num) for num in s_result])
        invalid_nums = []
        valid_nums = []
        for i in range(len(question_nums)):
            l = i+1
            if l < len(question_nums):
                if int(question_nums[i][:-1]) + 1 != int(question_nums[l][:-1]):
                    invalid_nums.append(question_nums[i][:-1])
                else:
                    valid_nums.append(question_nums[i])

        # for i in valid_nums:
        #     print(s_result)
        #     j = s_result.index(i)
        #     s_result[j + 1] = s_result[j] + s_result[j + 1]
        #
        # for i in valid_nums:
        #     j = s_result.index(i)
        #     s_result.pop(j)

        for i in invalid_nums:
            j = s_result.index(i)
            s_result[j-1] = s_result[j-1] + s_result[j] + s_result[j+1]

        for i in invalid_nums:
            j = s_result.index(i)
            s_result.pop(j)
            s_result.pop(j)

        return s_result

    def _question_judgment(self, content):
        """
        判断题题组解析
        :param content:
        :return:
        """
        if type(content['answer']) is not list:
            return
        num = len(content['answer'])  # 判断题目的数量
        result = []
        # 将解析出来的内容分别放入样式中进行替换，最后放入返回结果中
        for i in range(num):
            content_style = copy.copy(content)
            content_style['content'] = content_style['content'][i]
            content_style['answer'] = content_style['answer'][i]
            result.append(content_style)

        return result

    def bindHotKey(self):
        keyboard.add_hotkey('ctrl+F1', self.ocr, suppress=False)  # 显示界面

        # 拦截系统的快捷键,suppress=True表示拦截,不传递到其它程序
        keyboard.add_hotkey(
            'ctrl+c', lambda: print('按下了ctrl+c'), suppress=True)


    def quit(self):
        "保险起见，为了完整的退出"
        keyboard.unhook_all_hotkeys()
        self.setVisible(False)
        qApp.quit()
        sys.exit()


class window(QWidget):
    def __init__(self, parent=None):
        super(window, self).__init__(parent)
        ti = TrayIcon(self)
        ti.show()
        ti.parseWord()

if __name__ == "__main__":
    import sys

    # im = Image.open('temp.png')
    # result = pytesseract.image_to_string("temp.png", lang="chi_sim+eng+equ")
    # print(result)
    app = QApplication(sys.argv)
    w = window()
    w.hide()

    sys.exit(app.exec_())
