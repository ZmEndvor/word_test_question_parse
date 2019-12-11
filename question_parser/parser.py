import copy
import datetime
import os
import re
import string
import subprocess

from extension.equation.wordconverter import WordConverter
from extension.utils.misc import get_short_uuid


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
    MEDIA_URL = ''
    MEDIA_ROOT = ''

class Question(object):
    pass


class Answer(object):
    pass


class WordQuestionEntity(object):
    """
    提取 word 中question 数据
    """

    def __init__(self, word, **kwargs):
        self.word = os.path.join(settings.MEDIA_ROOT, word)

        if not os.path.exists(self.word):
            raise Exception('上传的word不存在!')

        self.kwargs = kwargs
        self.rubbish_list = []

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

        def save_picture(blob: bytes, content_type: string):

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

    def parse_word(self):
        word_converter = WordConverter()

        try:
            result = word_converter.to_latex(
                self.word,
                self.save_word_picture()
            )
        except Exception as exc:
            raise Exception('解析文件错误!')
        parser = WordQuestionParser(result, **self.kwargs)
        parser.parse_questions()

        return parser

    def clear_rubbish_list(self):
        """清空上传的文件"""
        for file_name in self.rubbish_list:
            if os.path.exists(file_name):
                os.remove(file_name)

    def clear_word(self):
        """ 清空word文件 """
        if os.path.exists(self.word):
            os.remove(self.word)


class WordQuestionParser(object):
    """
    解析word中的题目
    """

    full_structure = ['【题文】', '【答案】', '【解析】', '【结束】']
    next_line = '<br>'
    safe_dot_pair = {
        'U.S.': 'U##.S##.',
        'U．S．': 'U##．S##．',
        'U.K.': 'U##.K##.',
        'U．K．': 'U##．K##．',
        'D.C': 'D##.C##',
        'D．C': 'D##．C##',
    }

    def __init__(self, word_data_list=None, site=None, user=None, subject_id=None, chapters=None, nodes=None):
        self.word_data_list = word_data_list

        self.site = site
        self.user = user
        self.subject_id = subject_id
        self.chapters = chapters
        self.nodes = nodes

        self.created_question_count = 0
        self.pre_err_question_info = None
        self.sub_question_nums = set()
        self.current_question_info = []

        # 成功导入的题目id
        # 因使用read commited 事务隔离界别。因此导入的题目，不能够马上被索引服务所引导。故导入成功后，重新通知索引服务索引之
        self._imported_questions = []

    def clear_tag(self, content):
        """
        清理标签内的html内容
        :param content:
        :return:
        """
        if re.search(r'<.*?>', content):
            reduce_content = re.sub(r'<.*?>', '', content)

            # 标签解析
            if re.findall(r'【(题文|答案|解析|分值\d+|小题\d+|结束)】', reduce_content):
                infant_content = ''
                for item in re.split(r'(【.*?】)', content):
                    if re.match(r'【.*?】', item):
                        open_tags = []
                        close_tags = []
                        comm_cnt = ''
                        for tag_cont in filter(None, re.split(r'(<\/?.*?>)|(\w+)', item)):
                            if tag_cont.startswith('<'):
                                tag_name = re.sub(r'<(\/?.*?)>', r'\1', tag_cont)
                                if tag_name.startswith('/'):
                                    if tag_name[1:] in open_tags:
                                        open_tags.remove(tag_name[1:])
                                    else:
                                        close_tags.append(tag_name)
                                else:
                                    if '/' + tag_name in close_tags:
                                        close_tags.remove('/' + tag_name)
                                    else:
                                        open_tags.append(tag_name)

                            else:
                                comm_cnt += tag_cont

                        infant_content += ''.join('<{}>'.format(i) for i in close_tags)
                        infant_content += comm_cnt
                        infant_content += ''.join('<{}>'.format(i) for i in open_tags)
                    else:
                        infant_content += item

                return infant_content

        return content

    def parse_questions(self):
        """
        单个提取 word题目
        结尾处检查完整性
        :return:
        """
        errors = []
        self.current_question_info = []

        for item in self.word_data_list:

            item = self.clear_tag(item)

            if '【题文】' in item:
                self.current_question_info.append(item)
            elif '【答案】' in item:
                self.current_question_info.append(item)
            elif '【解析】' in item:
                self.current_question_info.append(item)
            elif '【结束】' in item:
                try:
                    self._check_integrity()
                    self._create_question()
                except Exception as exc:
                    # import traceback
                    # traceback.print_exc()
                    if self.pre_err_question_info == self.current_question_info[0]:
                        errors.pop()

                    errors.append(exc)
                    self.pre_err_question_info = self.current_question_info[0]

                finally:
                    self.current_question_info.clear()
                    self.sub_question_nums.clear()

            elif self.current_question_info:
                self.current_question_info.append(item)

        if self.current_question_info:
            self.raise_exception(msg='缺少【结束】标签!')

        if errors:
            raise Exception(self.next_line.join([i.args[0] for i in errors]))

    def _check_integrity(self, end_item=3):
        """
        检查数据完整性
        :param end_item: 验证结束位置
        :return:
        """
        # 要检查的标签
        tags = self.full_structure[:end_item]

        # 检查结果
        add_tags = []

        for item in self.current_question_info:
            if '【题文】' in tags and '【题文】' in item:
                add_tags.append('【题文】')

            if '【答案】' in tags and '【答案】' in item:
                add_tags.append('【答案】')

            if '【解析】' in tags and '【解析】' in item:
                add_tags.append('【解析】')

        # 重复标签
        if len(add_tags) > len(set(add_tags)):
            errors = []
            for item in set(add_tags):
                if add_tags.count(item) > 1:
                    errors.append(item)

            self.raise_exception(msg='重复标签: {}'.format(', '.join(errors)))

        # 检查缺失标签
        lack_tags = set(tags) - set(add_tags) - {'【解析】'}
        if lack_tags:
            self.raise_exception(lack_tags, action='缺失')

    def raise_exception(self, tags: [string] = None, action='缺失', msg=''):
        """
        组织 抛出错误
        1. 找到题号 抛出错误
        2. 找到验证的上下文 抛出错误
        :param tags:
        :param action:
        :param msg:
        :return:
        """
        num_group = re.match(r'(?P<num>\d+)[\.\．].*?【题文】', self.current_question_info[0])

        if not msg:
            msg = '{} {}标签'.format(action, ', '.join(tags or ''))

        if num_group and num_group.groupdict().get('num'):
            num = num_group.groupdict().get('num')
            raise Exception('第{}题: {}'.format(num, msg))
        else:
            item = self.current_question_info[-1]
            current_index = self.word_data_list.index(item)
            pre_content = self.word_data_list[current_index - 1 or 0]
            after_content = self.word_data_list[current_index + 1 or len(self.word_data_list)]

            raise Exception(
                '位置: {} {} 错误: {}'.format(
                    self.next_line.join([pre_content, item, after_content]),
                    self.next_line,
                    msg
                )
            )

    def _create_question(self):
        """
        创建题目, 按题干, 答案, 解析顺序保存, 遇到一个 标志位时(题干, 答案, 解析) 保存上一个标志位的属性
        :return:
        """
        self.question = Question(
            user=self.user,
            site=self.site,
            subject_id=self.subject_id
        )

        current_position = '【题文】'
        field_type_pair = {
            '【题文】': [],
            '【答案】': [],
            '【解析】': []
        }

        for item in self.current_question_info:

            if '【答案】' in item:
                current_position = '【答案】'
            if '【解析】' in item:
                current_position = '【解析】'

            if item:
                field_type_pair[current_position].append(item)

        # 保存题干
        sub_questions = self._save_content(field_type_pair['【题文】'])

        # 保存答案
        self._parse_save_answer(field_type_pair['【答案】'], sub_questions)

        # 保存解析
        self._parse_save_analysis(field_type_pair['【解析】'], sub_questions)

        self.created_question_count += 1

        self._imported_questions.append(self.question.id)

    def _construct_field(self, field_list):
        """
        包裹数学公式为 <span class="mathquill-rendered-math" data-latex="\\frac{1}{2}"></span>
        :param field_list:
        :return:
        """
        content = self.next_line.join(field_list)
        content = self._escape_character(content)
        return re.sub(
            r'\$([^\$]+)\$', r'<span class="mathquill-rendered-math" data-latex="\1"></span>',
            self.sub_br(content)
        )

    def _escape_character(self, content):
        tags = {value: f'$$~~{i}~~$$' for i, value in enumerate(re.findall(r'<[^<]*?>', content))}
        for key, value in tags.items():
            content = content.replace(key, value)

        content = content.replace('<', '&lt;')

        for key, value in tags.items():
            content = content.replace(value, key)

        return content

    def sub_br(self, content):
        return re.sub(r'^(<br>)+|(<br>)+$', '', content).strip()

    def _save_content(self, content_list):
        """
        保存题干
            主观题: 题目内容逐个解析, 最后组成题干
            选择题: 题目内容逐个解析, 最后组成题干, 选项放到choice_answer_list, 保存 正确答案 时用于保存
            题组: 题目内容逐个解析, 最后组成题干, 小题保存到sub_question_list, 选择题选项保存到小题的answer_list中, 保存 正确答案 时用

        :param content_list: 题干里的内容 包括: 选择题选项, 题组小题题干
        :return:
        """

        temp_list = []
        self.choice_answer_list = []

        sub_question_list = []  # 题组中的子题目

        for content in content_list:
            content = re.sub(r'【题文】', '', content)
            sub_question_info = re.split(r'【小题(\d+)】', content)

            safe_content = self.wrap_safe_answer(content.strip())

            # 暂时剔除无用的标签
            temp_safe_content = re.sub(r'<\/?.*?>', '', safe_content)

            # 提取选项符号：A B C
            choice_tag = re.search(r'(?P<tag>[A-N])[\.\．]', temp_safe_content)

            if (
                    choice_tag
                    and not sub_question_list
                    and len(sub_question_info) == 1
            ):
                tag = choice_tag.groupdict().get('tag') or ''
                content = self.unwrap_safe_answer(safe_content)

                # 删除选项符号
                content = content.replace(tag, '', 1)
                content, _ = re.subn(r'[\.\．]', '', content, 1)

                # 选项符号放到选项最前面
                self.choice_answer_list.append(tag + '.' + content)

            elif len(sub_question_info) > 1:  # 题组
                left_cnt, num, sub_question_content = sub_question_info

                if int(num) in self.sub_question_nums:
                    self.raise_exception(msg='小题题干{}已存在!'.format(num))

                self.sub_question_nums.add(int(num))

                sub_question = copy.deepcopy(self.question)
                sub_question.num = num
                sub_question.parent = self.question
                sub_question.answer_list = []

                self.parse_sub_question_content(sub_question, left_cnt + sub_question_content)

                sub_question_list.append(sub_question)

            elif sub_question_list:  # 题组内容
                self.parse_sub_question_content(sub_question_list[-1], content)

            else:  # 题干
                temp_list.append(content)

        score = self.fetch_score(temp_list, sub_question_list)

        quesiton_content = self._construct_field(temp_list)

        if not quesiton_content:
            self.raise_exception(msg='题干内容为空!')

        self.question.content = re.sub(r'^\s*\d+[\.\．]', '', quesiton_content)  # 去除题目前的序号
        self.question.score = score

        return sub_question_list

    def fetch_score(self, question_content_list, sub_question_list):
        """
        解析题目分值
        :param question_content_list:
        :param sub_question:
        :return:
        """
        score = 0
        for idx, content in enumerate(question_content_list):
            content_list = re.split(r'【分值(\d+\.?\d*)】', content)
            if len(content_list) == 3:
                score = float(content_list[1])

                if score > 99 or score < 1:
                    self.raise_exception(msg='分值信息错误')

                question_content_list[idx] = '{}{}'.format(content_list[0], ''.join(content_list[2:]))
                break

        sum_sub_question_score = 0
        illegality_score_nu = []
        for idx, sub_question in enumerate(sub_question_list, 1):
            content_list = re.split(r'【分值(\d+\.?\d*)】', sub_question.content)
            if len(content_list) == 3:
                sub_question.score = float(content_list[1])

                if sub_question.score > 99 or sub_question.score < 1:
                    illegality_score_nu.append(idx)

                sum_sub_question_score += sub_question.score
                content = '{}{}'.format(content_list[0], ''.join(content_list[2:]))

                sub_question.content = re.sub(r'^\s*\d+[\.\．]', '', content)  # 去除题目前的序号
            else:
                illegality_score_nu.append(idx)

        if illegality_score_nu:
            self.raise_exception(msg='小题{}分值信息错误'.format(','.join(str(i) for i in illegality_score_nu)))

        question_score = sum_sub_question_score or score
        if not question_score:
            self.raise_exception(msg='分值信息错误')

        return question_score

    def parse_sub_question_content(self, sub_question: Question, content: string):
        """
        解析小题题干
        :param content:
        :return:
        """
        if content and re.findall(r'[A-N][\.\．]', self.wrap_safe_answer(content.strip())):  # 小题为选择题暂存到题目里
            content_list = re.split(r'([A-N][\.\．])', self.wrap_safe_answer(content))

            if content_list[0].strip():
                content = (self.next_line + self.unwrap_safe_answer(content_list[0])).strip()
                sub_question.content += re.sub(r'^<br>', '', content)

            sub_question.answer_list.append(''.join(self.unwrap_safe_answer(content_list[1:])))

        else:
            content = (self.next_line + content).strip()
            sub_question.content += re.sub(r'^<br>', '', content)

    def _parse_save_answer(self, right_answer_list: [string], sub_question_list: [Question] = None):
        """
        保存 正确答案
        题组: 小题正确答案保存在 sub_question_right_answers 并验证
        其它: 正确答案保存在 question_answer 并验证
        :param right_answer_list:
        :param sub_question_list:
        :return:
        """

        is_stem = False  # 是否为题组
        sub_question_right_answers = []
        sub_question_answer_num_list = []
        question_answer = []

        for right_answer in right_answer_list:
            right_answer = re.sub(r'【答案】', '', right_answer)

            # 题组小题答案
            answer_tuple = re.split(r'【小题(\d+)】', right_answer)
            if len(answer_tuple) > 1:
                sub_question_answer_num_list.append(int(answer_tuple[1]))

                sub_question_right_answers.append([answer_tuple[0] + answer_tuple[2]])
                is_stem = True

            elif is_stem and sub_question_right_answers:
                sub_question_right_answers[-1].append(right_answer)

            # 其它题目答案
            else:
                question_answer.append(right_answer)

        # 检查题组小题数量
        if is_stem:
            self._check_sub_question_num(sub_question_answer_num_list, '答案')

        # 保存主观题, 选择题答案
        try:
            self._save_answer(question_answer, self.choice_answer_list, is_stem=is_stem)
        except Exception as exc:
            self.raise_exception(msg=exc.args[0])

        # 保存题组中的小题答案
        errors = dict()
        for idx, right_answer in enumerate(sub_question_right_answers):
            sub_question = sub_question_list[idx]

            try:
                self._save_answer(right_answer, sub_question.answer_list, sub_question)
            except Exception as exc:
                errors.setdefault(exc.args[0], []).append(sub_question.num)

        if errors:
            self.raise_exception(msg='{}'.format(
                self.next_line.join(
                    '{}: 【小题】{}'.format(k, ', '.join(v)) for k, v in errors.items()
                )
            ))

    def _save_answer(
            self,
            right_answer_list: [string],
            choice_answer_list=None,
            question=None,
            is_stem=False,
    ):
        """
        保存正确答案, 选择题 保存选项答案
        多选: A:B
        :param answers:
        :return:
        """
        if not question:
            question = self.question

        question.save()

        # 题组保存答案
        if is_stem:
            question.model = Question.QUESTION_MODEL_STEM
            question.no_choice_answer = self._construct_field(right_answer_list)
            return

        answers = right_answer_list[-1]
        is_choice = True
        answers = self.safe_choice_answer(answers)
        item_answers = answers.split(':')

        # 答案每一项都是选择题, 认为是选择题
        for answer in item_answers:
            if not answer or answer not in string.ascii_uppercase:
                is_choice = False

        if is_choice:
            if len(item_answers) > 1:
                question.model = Question.QUESTION_MODEL_MULTI_CHOICE  # 多选
            else:
                question.model = Question.QUESTION_MODEL_SINGLE_CHOICE  # 单选

            if not answers:
                raise Exception('正确答案为空!')

            question.proper = answers

            # 保存选项
            answer_list = []
            for answer in choice_answer_list:

                answer = self.wrap_safe_answer(answer)
                answers = re.split(r'([A-N])[\.\．]', answer)[1:]

                for item in zip(answers[::2], answers[1::2]):
                    answer_list.append(
                        Answer.objects.create(
                            question=question,
                            answer=item[0].strip(),
                            content=self._construct_field([
                                self.unwrap_safe_answer(item[1].strip())
                            ])
                        )
                    )

            if not answer_list:
                raise Exception('选择题未提供选项!')

            lack_answer = set(question.proper.split(':')) - set([i.answer for i in answer_list])
            if lack_answer:
                raise Exception('正确答案和选项不符!')

        # 主观题答案
        else:
            question.model = Question.QUESTION_MODEL_SUBJECTIVE
            no_choice_answer = self._construct_field(right_answer_list)

            if not no_choice_answer:
                raise Exception('正确答案为空!')

            question.no_choice_answer = no_choice_answer

    def _parse_save_analysis(self, analysis_list: [string], sub_question_list: [Question] = None):
        """
        保存题目解析
        题组: 小题解析放到sub_question_analysis_list, 逐个保存
        :param analysis_list: 是目解析的列表
        :param sub_question_list:
        :return:
        """
        question_analysis = []
        sub_question_analysis_dict = dict()
        sub_question_analysis_num_list = []

        is_stem = self.question.model == Question.QUESTION_MODEL_STEM

        for analysis in analysis_list:
            analysis = re.sub(r'【解析】', '', analysis)
            analysis_tuple = re.split(r'【小题(\d+)】', analysis)

            if len(analysis_tuple) > 1:
                left_analy, num, analy = analysis_tuple
                num = int(num)
                sub_question_analysis_num_list.append(num)

                sub_question_analysis_dict[num] = [left_analy + analy]

            elif is_stem and sub_question_analysis_dict:
                sub_question_analysis_dict[sub_question_analysis_num_list[-1]].append(analysis)

            else:
                question_analysis.append(analysis)

        if is_stem:
            self._check_sub_question_num(sub_question_analysis_num_list, '解析')

        # 保存选择, 主观题解析
        try:
            self._save_analysis(question_analysis)
        except Exception as exc:
            self.raise_exception(msg=exc.args[0])

        # 保存题组 小题解析
        errors = dict()
        for sub_question in sub_question_list:
            analysis_data = ''
            if int(sub_question.num) in sub_question_analysis_num_list:
                analysis_data = sub_question_analysis_dict.get(int(sub_question.num), '')

            try:
                self._save_analysis(analysis_data, sub_question)
            except Exception as exc:
                errors.setdefault(exc.args[0], []).append(sub_question.num)

        if errors:
            self.raise_exception(msg='{}'.format(
                self.next_line.join(
                    '{}: 【小题】{}'.format(k, ', '.join(v)) for k, v in errors.items()
                )
            ))

    def _check_sub_question_num(
            self,
            current_sub_question_nums: [int],
            error_type: string = ''
    ):
        """
        检测小题题号, 数量
        """

        # 检测题号重复
        repeat_num = set()
        if len(set(current_sub_question_nums)) != len(current_sub_question_nums):
            for num in current_sub_question_nums:
                if current_sub_question_nums.count(num) > 1:
                    repeat_num.add(str(num))

        if repeat_num:
            self.raise_exception(msg='【小题】{}{} 重复'.format(', '.join(repeat_num), error_type))

        # 检测缺少题号
        if error_type != '解析':
            lack_set = self.sub_question_nums - set(current_sub_question_nums)
            if lack_set:
                self.raise_exception(
                    msg='【小题】{}{}缺失'.format(
                        ', '.join(str(i) for i in lack_set),
                        error_type,
                    )
                )

        # 检测多于题号
        overflow_set = set(current_sub_question_nums) - self.sub_question_nums
        if overflow_set:
            self.raise_exception(
                msg='【小题】{}{}过多'.format(
                    ', '.join(str(i) for i in overflow_set),
                    error_type,
                )
            )

    def _save_analysis(self, analysis_list, question=None):
        """
        保存题目解析
        :param question:
        :param analysis_list:
        :param sub_question_list:
        :return:
        """
        if not question:
            question = self.question

        analysis = self._construct_field(analysis_list)

        question.analysis = analysis

        if question.parent:
            question.parent_id = question.parent.id

        if self.nodes:
            question.nodes.add(*self.nodes)

        if self.chapters:
            question.knowledges.add(*self.chapters)

        question.save()

    def safe_choice_answer(self, answer: string):
        """
        去除 干扰 选择题的正确答案
        :param answer:
        :return:
        """
        return re.sub(r'\u3000|\xa0|\s|<.*?>', '', answer)

    def wrap_safe_answer(self, answer):
        """
        临时修改选项预留字符
        :param answer:
        :return:
        """

        for key, value in self.safe_dot_pair.items():
            answer = answer.replace(key, value)

        return answer

    def unwrap_safe_answer(self, answer):
        """
        恢复修改选项预留字符
        :param answer:
        :return:
        """
        list_span_tag = '!~!~!'

        if isinstance(answer, list):
            answer = list_span_tag.join(answer)

        for key, value in self.safe_dot_pair.items():
            answer = answer.replace(value, key)

        if list_span_tag in answer:
            return answer.split(list_span_tag)

        return answer

