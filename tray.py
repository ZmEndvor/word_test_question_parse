import ctypes
import sys
import os
import re
import copy
import pyperclip
import datetime
import operator
import pythoncom
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
            path = os.getcwd()
            return ctypes.cdll.LoadLibrary(path + '\\PrScrn.dll')
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
            self.showMessage("截图失败", "prscrn文件加载失败")
            return
        im = ImageGrab.grabclipboard()
        if im:
            # 使用Tesseract识别
            # TODO：调整角度、 去噪、二值化。目前测试看并不理想，暂不处理
            print("Will ocr")
            im.save("temp.png")
            # im.close()
            result = pytesseract.image_to_string("temp.png", lang="chi_sim+eng+equ")
            # print(result)

            if result:
                self.parse_questions(result, params)
                # print(params)
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
                self.get_new_word(),
                self.save_word_picture()
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
        pythoncom.CoInitialize()
        pwd = os.getcwd()
        word = wc.Dispatch("Word.Application")
        new_word = word.Documents.Add()
        if pyperclip.paste():
            word.Selection.PasteSpecial(DataType='WdPasteDataType')  # 复制word格式剪切板内容
        word_file = pwd + "\\1.docx"  # 生成word路径
        if os.path.exists(word_file):  # 判断文件是否存在，如果存在将其移除
            os.remove(word_file)
        new_word.SaveAs(word_file, 16)  # 将复制的内容生成word文件
        new_word.Close()  # 关闭word文件

        return word_file

    def parse_questions(self, result, params):
        """
        单个提取 word题目
        :return:
        """
        # 提取
        s_result = re.split(r'(\d+\.\s|\d+．|\d+\.)', result)
        s_result = self._png_connect(s_result)
        s_result = self._question_connect(s_result)
        content = []  # 存放主体
        stem = []
        for i in s_result:
            if not re.compile(r'(^\d+[\.|．])').findall(i) and i:
                c = {}
                # 来源
                ct_sourceText = ''
                sourceText_re = r'(^[\[|\(|\（|\【|<.*?>]\S+[\]|\)|\）|\】]<\/?.*?>|^[\[|\(|\（|\【]\S+[\]|\)|\）|\】])'
                sourceText = re.compile(sourceText_re).findall(i)
                if sourceText:
                    if sourceText[0][1:3] not in ["多选"] and sourceText[0][1] != '例':
                        ct_sourceText = sourceText[0]
                        # 当取到来源的时候有可能漏取标签，所以需要判断一下，补充标签
                        sourceText_label = re.compile(r'[\]|\)|\）|】]<(.*?)>').findall(sourceText[0])
                        if sourceText_label:
                            if not re.compile(r'^<.*?>').findall(ct_sourceText):
                                sourceText[0] = '<' + sourceText_label[0].replace('/', '') + '>' + sourceText[0]
                        c['sourceText'] = sourceText[0] if len(re.compile(r'[\[|\(|\（|【](.*?)[\]|\)|\）|】]').findall(sourceText[0])[0]) > 2 else ''

                # 解析：通过解析字样匹配解析内容
                analysis = re.compile(r'解析([\s\S]+)答案').findall(i)
                analysis = re.compile(r'【解析】([\s\S]+)【答案】').findall(i) if not analysis else analysis
                if not analysis:
                    analysis = re.compile(r'解析([\s\S]+)').findall(i)
                    analysis = re.compile(r'【解析】([\s\S]+)').findall(i) if not analysis else analysis
                analysis = self._analysis_separate(analysis) if type(analysis) is list else analysis  # 解析处理
                c['analysis'] = analysis if len(analysis) > 1 else analysis[0]

                # 选项：通过A-F以及.匹配内容多次得到选项以及内容，最后通过切片将选项与选项内容分离为option与content
                options = re.compile(r'[A-F][\.|．].*[^A-F]').findall(i)
                opts = re.compile(r'[A-F][\.|．]').findall(i)

                # 答案
                if c['analysis']:
                    answer = re.compile(r'【答案】([\s\S]+)【解析】').findall(i)  # 答案内容的匹配
                    answer = re.compile(r'答案([\s\S]+)解析').findall(i) if not answer else answer
                else:
                    answer = ''

                if not answer:
                    answer = re.compile(r'【答案】([\s\S]+)').findall(i)  # 答案内容的匹配
                    answer = re.compile(r'答案([\s\S]+)').findall(i) if not answer else answer
                answer = self._answer_separate(answer) # 答案解析
                c_answer = answer if len(answer) > 1 else answer[0]

                # 给选项计数，并整理选项
                if opts:
                    c_opts = Counter(opts)
                    options = self._options_analysis(options, c_opts) # 选项解析
                    c['options'] = options
                    c['type'] = self._question_type_analysis_by_options(options, c_answer)  # 题型判断
                else:
                    c['type'] = ''

                # 题目：
                ct = self._question_stem_analysis(i, ct_sourceText)
                c['content'] = ct[0] if ct and len(ct) == 1 else ct

                # 去除为空的字段
                for k in list(c.keys()):
                    if not c[k]:
                        del c[k]

                if c:
                    # 将有答案的题组进一步处理
                    if c_answer:
                        if type(c_answer) is list and len(c_answer) > 1:
                            c['answer'] = c_answer
                            r_result = self._question_judgment(c, params['question'])
                            params['question']['children'] = r_result[0]   # 判断题，将内容与答案分为children
                            stem.append(r_result[1]) if r_result[1] else ''
                            params['question']['type'] = "题组"
                        else:
                            c['answer'] = c_answer
                        # 多选题答案格式化为A:B:C
                        if 'type' in c and c['type'] == "多选":
                            c['answer'] = ":".join(re.compile(r'[A-F]').findall(c['answer']))
                    else:
                        if 'content' in c and type(c['content']) is list and len(c['content']) > 1:
                            c['content'] = "".join(c['content'])
                            params['question']['type'] = "非选择题"

                    # 判断题组中小题的类型
                    if 'type' not in c:
                        if 'answer' in c:
                            if type(c['answer']) is str and len(re.compile(r'[A-F]').findall(c['answer'])) > 1:
                                c['type'] = '多选'
                            elif type(c['answer']) is str and len(re.compile(r'[A-F]').findall(c['answer'])) == 1:
                                c['type'] = '单选'
                            else:
                                c['type'] = '非选择题'
                        else:
                            c['type'] = '非选择题'
                    # 补充json格式
                    for c_key in params['question'].keys():
                        if c_key not in c.keys() and c_key != 'children':
                            if c_key == 'options':
                                c[c_key] = []
                            else:
                                c[c_key] = ''
                        elif c_key not in ['children', 'options'] and type(c[c_key]) is list:
                            c[c_key] = ''
                    content.append(c)

        # 将得到的json转化为children或params
        if len(content) == 1:
            params['question'].update(content[0])
            if len(content[0]['options']) > 1 and type(content[0]['options'][0]) is list:
                new_childrens = []
                for opt in content[0]['options']:
                    new_children = copy.copy(params['question'])
                    new_children['content'] = ''
                    new_children.pop('children')
                    new_children['options'] = opt
                    new_childrens.append(new_children)
                params['question']['children'] = new_childrens
                params['question']['options'] = []
        elif len(content) > 1:
            options = [i['options'] for i in content if i['options']]
            contents = [i['content'] for i in content if i['content']]
            if len(options) == 1 and len(contents) > 1:
                new_content = copy.copy(params['question'])
                for i in content:
                    for j in i.keys():
                        if j == 'content':
                            new_content[j] = "".join(contents)
                        elif j == 'options':
                            new_content[j] = options[0]
                        elif i[j]:
                            new_content[j] = i[j]
                params['question'].update(new_content)
            else:
                q_content = []
                items = []
                for item, i in enumerate(content):
                    if len(i['content']) > 0 and len(i['options']) == 0:
                        items.append(item)
                        c_content = content[item]
                        q_content.append(c_content['content'])
                items.reverse()
                pop_content = [content.pop(i) for i in items]
                params['question']['content'] = "".join(q_content)
                params['question']['children'] = [i for i in content] if not params['question']['children'] else params['question']['children']

        if stem:
            params['question']['content'] = stem[0]

        if params['question']['children']:
            params['question']['type'] = "题组"

        params['origin'] = result

    def _analysis_separate(self, analysis):
        """
        解析进一步处理，如果解析中包含多个解析则进行小题解析分离
        :param analysis:
        :return:
        """
        if not analysis:
            return ['']

        # 判断解析是否存在有题号的多个小题并将题号匹配出来
        analysises = []
        questions_nums = re.compile(r'([\(|\（]\d+[\)|\）])').findall(analysis[0])

        if not questions_nums:
            return analysis

        # 将含有题号的内容分割开来
        anas = re.split(r'([\(|\（]\d+[\)|\）])', analysis[0])

        # 检查小题内容中是否包含与题号一样的存在，将其设置为失效题号并进行拼接
        question_tuple_nums = [(item, re.compile(r'^[\(|\（](\d+)[\)|\）]').findall(num)[0]) for item, num in enumerate(anas) if re.compile(r'^[\(|\（](\d+)[\)|\）]').findall(num)]
        question_nums = [int(i[1].encode('utf-8')) for i in question_tuple_nums]
        invalid_nums = []   # 失效题号
        for i in range(len(question_nums)):
            l = i + 1
            if l < len(question_nums):
                if int(question_nums[i]) + 1 != int(question_nums[l]) and int(question_nums[i]) - 1 != int(question_nums[i - 1]):
                    invalid_nums.append(question_tuple_nums[i])
            elif l == len(question_nums):
                if int(question_nums[i]) - 1 != int(question_nums[i - 1]):
                    invalid_nums.append(question_tuple_nums[i])

        if not invalid_nums:
            return analysis

        for invalid_num in invalid_nums:
            anas[invalid_num[0] - 1] = "".join(anas[invalid_num[0] - 1: invalid_num[0] + 2])
            anas.pop(invalid_num[0])
            anas.pop(invalid_num[0])

        # 将解析拼接后的小题重新组合为list，返回解析内容
        for item, i in enumerate(anas):
            if i and re.compile(r'^([\(|\（]\d+[\)|\）])').findall(i):
                anas[item] = "".join(anas[item:item + 2])
                analysises.append(anas[item])

        return analysises

    def _answer_separate(self, answer):
        """
        答案进一步处理，如果答案中包含多个答案则进行小题答案分离
        :param answer:
        :return:
        """
        if not answer:
            return ['']

        # 查看匹配出的答案中是否有多个小题答案存在，将其题号提取，进行小题分离组合一个新的答案list返回
        answers = []
        if type(answer) is list:
            question_nums = re.compile(r'([\(|\（]\d+[\)|\）])').findall(answer[0])
            if not question_nums:
                return answer

            ans = re.split(r'([\(|\（]\d+[\)|\）])', answer[0])
            for item, i in enumerate(ans):
                if i and re.compile(r'^([\(|\（]\d+[\)|\）])').findall(i):
                    ans[item] = "".join(ans[item:item + 2])
                    answers.append(ans[item])

            return answers

    def _png_connect(self, result):
        """
        图片拼接
        :param result:
        :return:
        """
        # 在进行题号将题目分离的情况中可能会出现图片地址包含与题号相同的存在，例如，image/1.png，这个时候会将1.判断为题号，
        # 从而使得之后得出的内容不准确，所以在进行题号分离之后将图片内容拼接，确保准确的内容执行之后的操作
        for item, i in enumerate(result):
            if re.compile(r'image$').findall(i):
                result[item] = "".join(result[item:item+3])
                result.pop(item+1)
                result.pop(item+1)
            elif re.compile(r'image$').findall(result[item - 1]):
                result[item - 1] = "".join(result[item - 1:item + 2])
                result.pop(item)
                result.pop(item)

        return result

    def _get_ct(self, s, ct):
        """
        将题干中选项之前的内容提取为题干
        :param s: 一个列表，用来存放匹配出来的结果，如果匹配到取最后一个值，如果无返回[]
        :param ct: content内容
        :return:
        """
        if type(ct) is list:
            ct = ct[0]
        ct = re.compile(r'([\s\S]*)A[\.|．]').findall(ct)
        s.append(ct) if ct else ''
        return s if not ct else self._get_ct(s, ct)

    def _recursive_find_content(self, ct):
        """
        递归查找content，过滤解析、答案
        :param ct:
        :return:
        """
        ct1 = re.compile(r'([\s\S]*)(?:[解析|【解析】|答案|【答案】])').findall(ct[0]) if ct else ct
        if not ct1:
            return ct1
        return ct1 if not re.compile(r'[解析|【解析】|答案|【答案】]').findall(ct1[0]) else self._recursive_find_content(ct1)

    def _question_stem_analysis(self, content, sourseText):
        """
        解析题干，并将内容中的来源剔除
        :param content: content内容
        :param sourseText: 来源
        :return:
        """
        # 匹配题干
        contents = []
        ct_result = []
        ct_results = self._get_ct(ct_result, content)  # 过滤选项
        ct = ct_results[-1] if ct_results else ct_results
        ct = re.compile(r'([\s\S]*)').findall(content) if not ct else ct
        ct = re.compile(r'([\s\S]*)(?:[解析|【解析】|答案|【答案】])').findall(content) if not ct else ct  # 过滤答案解析
        ct1 = self._recursive_find_content(ct) # 过滤答案解析
        ct = ct1 if ct1 else ct
        ct = [i for i in ct if i]   # 筛选非空内容
        # 匹配是否有标签，如果为单个且开头的标签，将内容变为空
        label = re.compile(r'<.*?>').findall(ct[0]) if ct else ''
        if label and len(label) == 1 and re.compile(r'^(<.*?>)').findall(ct[0]):
            return ''

        # 去除来源
        if ct:
            ct[0] = ct[0].replace(sourseText, "")  # 将题干中的来源去除
            # 匹配小题题干
            if re.compile(r'([\(|\（]\d+[\)|\）])').findall(ct[0]):
                cts = re.split(r'([\(|\（]\d+[\)|\）])', ct[0])
                for item, i in enumerate(cts):
                    if i and re.compile(r'^([\(|\（]\d+[\)|\）])').findall(i):
                        cts[item] = "".join(cts[item:item + 2])
                        contents.append(cts[item])
                    elif item == 0:
                        contents.append(cts[item])
                return contents
            contents.append(ct)

        return contents[0] if len(contents) == 1 else contents

    def _question_type_analysis_by_options(self, options, c_answer):
        """
        题型分析，根据答案以及选项结合起来判断题型
        :param options: 选项
        :param c_answer: 答案
        :return:
        """
        if len(options) > 1 and type(options[0]) is list:
            return "选择题"
        if type(c_answer) is list:
            if len(c_answer) > 1:
                return "题组"
            if len(re.compile(r'[A-F]').findall(c_answer[0])) > 1:
                return "多选"
            return "单选"
        if c_answer is not list:
            if len(re.compile(r'[A-F]').findall(c_answer)) > 1:
                return "多选"
            return "单选"
        return "选择题"

    def _options_analysis(self, options, count_opts):
        """
        选项解析
        :param options: 选项
        :param count_opts: 选项计数
        :return:
        """
        # 处理选项之间相连的情况，如果统计出来的选项与实际得到的选项不符，那么进行进一步的提取选项，并将选项进行组合
        options_opts = []
        if len(count_opts) != len(options):
            for i in options:
                old_options = [i]
                k = self._options_result(i, old_options)
                k.reverse()
                for item, j in enumerate(k):
                    if item == 0:
                        options_opts.append(j)
                    else:
                        options_opts.append(k[-1][len(k[item - 1]):len(j)])
        else:
            for i in options:
                if type(i) is list:
                    options_opts.extend(i)
        options = options_opts if options_opts else options
        opts = []
        # 将选项转化为{'options':x,'content':xxxxxx}的格式
        for i in range(0, len(options), len(count_opts)):
            option = []
            for opt in options[i:i + len(count_opts)]:
                if opt:
                    option.append({"option": opt[0], "content": opt[2:]})
            opts.append(option)

        return opts[0] if len(opts) == 1 else opts

    def _options_result(self, i, li):
        """
        递归查找选项内容
        :param i:
        :param li:
        :return:
        """
        o = re.compile(r'([A-F][\.|．][\s\S]+)[A-F][\.|．]').findall(i)
        li.extend(o)
        return li if not o else self._options_result(o[0], li)

    def _question_connect(self, s_result):
        """
        将非小题的内容拼接在一起，通过题号分离，如果小题中包含题号相似的内容可能导致误认为小题，所以将不是小题内容的
        类似题号内容拼接起来
        :param s_result:
        :return:
        """
        # 题组中小题的题号
        questions_nums = []
        for item, i in enumerate(s_result):
            question_num = re.compile(r'(^\d+[\.\s|．|\.])').findall(i)
            if question_num:
                questions_nums.append((question_num[0], item))
        if not questions_nums:
            return s_result

        # 题号没有相连的说明匹配中匹配到了内容中与题号类似的内容，将其拼接
        question_nums = reduce(operator.add, [re.compile(r'(\d+)').findall(num[0]) for num in questions_nums])
        invalid_nums = []
        for i in range(len(question_nums)):
            l = i+1
            if l < len(question_nums):
                if int(question_nums[i]) + 1 != int(question_nums[l]):
                    invalid_nums.append((questions_nums[i][1]))
            elif l == len(question_nums):
                if int(question_nums[i]) - 1 != int(question_nums[i-1]):
                    invalid_nums.append((questions_nums[i][1]))

        if not invalid_nums:
            return s_result

        invalid_nums_min = min(invalid_nums)
        invalid_nums_max = max(invalid_nums)
        s_result[invalid_nums_min-1] = "".join(s_result[invalid_nums_min-1:invalid_nums_max+2])

        min_max = [invalid_nums_min, invalid_nums_max+2]
        del s_result[min_max[0]:min_max[1]]

        ss_result = []
        for i in s_result:
            quest_nums = re.compile(r'(^\d+[\.|．])').findall(i)
            question_number = quest_nums[0] if quest_nums else quest_nums
            if question_number:
                ss_result.append(i[:len(question_number)])
                ss_result.append(i[len(question_number):])
            else:
                ss_result.append(i)
        return ss_result

    def _question_judgment(self, content, params_question):
        """
        题组解析，当题组中的小题包含多个小题时，答案、题干、解析等会形成list形式，将其格式化为children
        :param content:
        :return:
        """
        answer_num = len(content['answer'])   # 题目的数量
        content_num = len(content['content'])
        result = []
        # 将解析出来的内容分别放入样式中进行替换，最后放入返回结果中
        # 当答案数量与题干数量不符时，说明主题干也包含在content中，这个时候小题与答案对应需要将首个content排除掉
        is_content = False
        if len(content['answer']) != len(content['content']):
            is_content = True
        if answer_num:
            for i in range(answer_num):
                content_style = copy.copy(params_question)
                content_style['content'] = content['content'][i + 1] if is_content else content['content'][i]
                content_style['answer'] = content['answer'][i]
                content_style['type'] = '题组'
                del content_style['children']
                result.append(content_style)

        stem = content['content'][0] if is_content else ''

        return (result, stem)

    def bindHotKey(self):
        keyboard.add_hotkey('ctrl+F1', self.ocr, suppress=False)  # 显示界面
        # keyboard.add_hotkey('ctrl+F2', self.parseWord, suppress=False)   # 解析文档

        # 拦截系统的快捷键,suppress=True表示拦截,不传递到其它程序
        keyboard.add_hotkey('ctrl+c', self.parseWord, suppress=False)   # 捕获ctrl+c自动进行解析


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = window()
    w.hide()

    sys.exit(app.exec_())
