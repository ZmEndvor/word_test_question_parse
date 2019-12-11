# -*- coding: UTF-8 -*-
# @Author ：Jerrmy_Z
# @Time ：2019/11/18 14:29

import re
import unittest
from tray import *
import sys
import pyperclip


class TrayIcon(TrayIcon):
    """
    重写init方法
    """
    def __init__(self):
        self.prScrnLib = self.loadLibrary()
        self.rubbish_list = []


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.word_path = '2.docx'
        self.parse_word_json = {
            'identifier': 'venus',  # 固定取值 venus。云平台只认识此格式
            'format': 'question',  # 格式类型，可以是question 或 plain，亦或 latex
            'text': '',  # 格式为plain或者latext时有定义
            'question': {  # 格式为question时有定义
                'sourceText': "",  # 来源。题目开头，圆括号，方括号等标明出处的文本
                'content': "",  # 题干
                'type': '',  # 单选、多选、非选择、题组
                'answer': "",  # 正确答案. 多选答案用 : 分割。如A:B
                'analysis': "",  # 解析
                'options': [{
                    'option': 'A',  # 选项
                    'content': ""  # 选项正文
                }],
                'children': []  # 包含题组时有定义。内容为question相同格式。但不可再包含children
            },
            'origin': ''  # 解析前的原始内容
        }
        self.result = self.parse_word()

    def parse_word(self):
        """
        解析word
        :return:
        """
        ti = TrayIcon()
        word_converter = WordConverter()
        try:
            result = word_converter.to_latex(
                self.word_path,
                ti.save_word_picture()
            )
        except Exception as exc:
            raise Exception('解析文件错误!')

        ti.parse_questions("\n".join(result), self.parse_word_json)

        return self.parse_word_json

    def test_is_result(self):
        """
        测试是否有返回结果
        :return:
        """
        self.assertTrue(self.result, "没有返回结果")
        print("\n'{}'返回结果的测试完成".format(self.test_is_result.__name__))

    def test_result_is_filed_name(self):
        """
        测试返回结果的格式是否完整
        :return:
        """
        for i in self.result.keys():
            self.assertTrue(i in self.parse_word_json.keys(), "{}不存在".format(i))
            if i == 'question':
                for j in self.result[i].keys():
                    self.assertTrue(j in self.parse_word_json['question'].keys(), "question{}不存在".format(j))
        print("\n'{}'返回结果格式的测试完成".format(self.test_result_is_filed_name.__name__))

    def test_question_type_question_group(self):
        """
        测试题组主要key的值是否为空
        :return:
        """
        r_type = self.result['question']['type']
        r_children = self.result['question']['children']
        if r_type == "题组":
            self.assertTrue(r_children, "题组children为空")
            for i in r_children:
                self.assertTrue(i['content'], "children['content']为空")
                if i['type'] in ['选择题', '单选', '多选']:
                    self.assertTrue(i['options'], "children['option']为空")
                    for option in i['options']:
                        self.assertTrue(option['option'], "children选项为空")
                        self.assertTrue(option['content'], "children选项正文为空")
            print("\n'{}'题组主要key值的测试完成".format(self.test_question_type_question_group.__name__))

    def test_question_type_true_or_false(self):
        """
        测试非选择题主要key的值是否为空
        :return:
        """
        r_type = self.result['question']['type']
        if r_type == "非选择题":
            self.assertTrue(self.result['question']['content'], "非选择题content为空")
            print("\n'{}'非选择题主要key值的测试完成".format(self.test_question_type_true_or_false.__name__))

    def test_question_type_option(self):
        """
        测试选择题主要key的值是否为空
        :return:
        """
        r_type = self.result['question']['type']
        r_content = self.result['question']['content']
        r_options = self.result['question']['options']
        if r_type in ['选择题', '单选', '多选']:
            self.assertTrue(r_options, "选择题选项为空")
            self.assertTrue(r_content, '选择题content为空')
            print("\n'{}'选择题主要key值的测试完成".format(self.test_question_type_option.__name__))

    def test_choice_answer(self):
        """
        测试选择题答案存在时，结果中的选择题答案是否为空
        :return:
        """
        r_type = self.result['question']['type']
        if r_type in ['单选', '多选']:
            if "答案" in self.result['origin']:
                self.assertTrue(self.result['question']['answer'], "{}答案为空".format(r_type))
                print("\n'{}'选择题答案的测试完成".format(self.test_choice_answer.__name__))

    def test_mutiple_choice_answer_style(self):
        """
        测试多选的答案格式是否正确
        :return:
        """
        r_type = self.result['question']['type']
        if r_type == "多选":
            self.assertTrue(":" in self.result['question']['answer'], "多选答案格式不正确")
            print("\n'{}'多选答案格式的测试完成".format(self.test_mutiple_choice_answer_style.__name__))

    def test_analysis(self):
        """
        测试解析是否为空
        :return:
        """
        if "解析" in self.result['origin']:
            self.assertTrue(self.result['question']['analysis'], "解析为空")
            print("\n'{}'解析是否为空的测试完成".format(self.test_analysis.__name__))

    def test_sourceText(self):
        """
        测试来源是否为空
        :return:
        """
        sourceText = re.compile(r'\d+[\.|．]\s([\[|\(|\（|】]\S+[\]|\)|\）|】])').findall(self.result['origin'])
        if sourceText:
            self.assertTrue(self.result['question']['sourceText'], '来源为空')
            print("\n'{}'来源是否为空的测试完成".format(self.test_sourceText.__name__))

    def test_choice_one_line(self):
        """
        测试选择题选项为一行时的返回结果是否正确
        :return:
        """
        r_type = self.result['question']['type']
        if r_type in ['选择题', '单选', '多选']:
            options = re.compile(r'[A-F][\.|．].*[^A-F]').findall(self.result['origin'])
            opts = re.compile(r'[A-F][\.|．]').findall(self.result['origin'])
            if len(options) == 1:
                self.assertEqual(len(self.result['question']['options']), len(opts))
                print("\n'{}'选择题选项为一行的测试完成".format(self.test_choice_one_line.__name__))

    def test_choice_irregular(self):
        """
        测试选择题选项不规则相连时的返回结果是否正确
        :return:
        """
        r_type = self.result['question']['type']
        if r_type in ['选择题', '单选', '多选']:
            options = re.compile(r'[A-F][\.|．].*[^A-F]').findall(self.result['origin'])
            opts = re.compile(r'[A-F][\.|．]').findall(self.result['origin'])
            if len(options) != 1:
                self.assertEqual(len(self.result['question']['options']), len(opts))
                print("\n'{}'选择题选项不规则相连的测试完成".format(self.test_choice_irregular.__name__))

    def test_blanks_format(self):
        """
        测试填空题格式是否正确
        :return:
        """
        pass

    def test_question_answer_format(self):
        """
        测试问答题格式是否正确
        :return:
        """
        pass

    def test_multiple_choice_format(self):
        """
        测试选择题格式是否正确
        :return:
        """
        pass

    def test_question_group_format(self):
        """
        测试题组格式是否正确
        :return:
        """
        pass

    def test_judgment_format(self):
        """
        测试判断题格式是否正确
        :return:
        """
        pass

    def test_cloze_format(self):
        """
        测试完形填空格式是否正确
        :return:
        """
        pass

    def test_reading_format(self):
        """
        测试阅读理解格式是否正确
        :return:
        """
        pass

    def test_option_content_is_jpg(self):
        """
        测试选项为图片的是否解析正确
        :return:
        """
        pass

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()

