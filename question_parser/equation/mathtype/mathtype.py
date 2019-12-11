import logging
import struct

import binascii

from .chars import chars as CHAR_MAP
from olefile import OleFileIO

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
AUTO_DETECT_SLOTS = -1
logger.setLevel(logging.DEBUG)


class MathTypeParser(object):
    """
    MathType转换工具

    将MathType OleData转换为LateX格式
    转换时，将忽略里边的格式代码，只保留公式本身
    参考资料:http://rtf2latex2e.sourceforge.net/MTEF5.html

    目前不支持字体、颜色、大小等修饰性内容

    数据构成:
        MTEF Header
        公式属性定义
        SIZE记录
        PILE或LINE记录
            PILE或LINE内容
        END记录

    版本:1.0
    """

    # # 选项
    mtefOPT_NUDGE = 0x08
    mtefOPT_CHAR_EMBELL = 0x1
    mtefOPT_CHAR_FUNC_START = 0x2
    mtefOPT_CHAR_ENC_CHAR_8 = 0x4
    mtefOPT_CHAR_ENC_CHAR_16 = 0x10
    mtefOPT_CHAR_ENC_NO_MTCODE = 0x20
    mtefOPT_LINE_NULL = 0x1
    mtefOPT_LINE_LSPACE = 0x4
    mtefOPT_LP_RULER = 0x2

    # 颜色
    mtefCOLOR_CMYK = 0x01
    mtefCOLOR_SPOT = 0x02
    mtefCOLOR_NAME = 0x04

    # #  Template
    # 括号
    tmANGLE = 0  # angle brackets <>
    tmPAREN = 1  # parentheses ()
    tmBRACE = 2  # braces (curly brackets) {}
    tmBRACK = 3  # square brackets []
    tmBAR = 4  # vertical bars |
    tmDBAR = 5  # double vertical bars ||
    tmFLOOR = 6  # floor brackets  https://en.wikipedia.org/wiki/Floor_and_ceiling_functions
    tmCEILING = 7  # ceiling brackets  https://en.wikipedia.org/wiki/Floor_and_ceiling_functions
    tmOBRACK = 8  # open (white) brackets
    tvFENCE_L = 0x001  # left fence is present 左(各种)括号
    tvFENCE_R = 0x002  # right fence is present 右(各种)括号

    # 间隔
    tmINTERVAL = 9  # unmatched brackets and parentheses 不成对括号
    tvINTV_LEFT_LP = 0x0000  # left fence is left parenthesis (...
    tvINTV_LEFT_RP = 0x0001  # left fence is right parenthesis )...
    tvINTV_LEFT_LB = 0x0002  # #left fence is left bracket {(?)...
    tvINTV_LEFT_RB = 0x0003  # left fence is right bracket }(?)...
    tvINTV_RIGHT_LP = 0x0000  # right fence is left parenthesis ...(
    tvINTV_RIGHT_RP = 0x0010  # right fence is right parenthesis ...)
    tvINTV_RIGHT_LB = 0x0020  # right fence is left bracket ....{(?)
    tvINTV_RIGHT_RB = 0x0030  # right fence is right bracket ...}(?)

    # 根数
    tmROOT = 10
    tvROOT_SQ = 0  # square root 平方根
    tvROOT_NTH = 1  # nth root n次方根

    # 分数
    tmFRACT = 11
    tvFR_SMALL = 0x0001  # subscript-size slots (piece fraction) small大小
    tvFR_SLASH = 0x0002  # fraction bar is a slash 分号是斜线/
    tvFR_BASE = 0x0004  # num. and denom. are baseline aligned 基线对齐

    # 上下（划线？）
    tmUBAR = 12
    tmOBAR = 13
    tvBAR_DOUBLE = 0x0001  # bar is doubled, else single

    # 箭头
    tmARROW = 14

    tvAR_SINGLE = 0x0000  # single arrow 单箭头
    tvAR_DOUBLE = 0x0001  # double arrow 双箭头
    tvAR_HARPOON = 0x0002  # harpoon 鱼叉
    tvAR_TOP = 0x0004  # top slot is present  在字符上边
    tvAR_BOTTOM = 0x0008  # bottom slot is present 在字符下边
    tvAR_LEFT = 0x0010  # if single, arrow points left 单箭头向左
    tvAR_RIGHT = 0x0020  # if single, arrow points right 单箭头向右
    tvAR_LOS = 0x0010  # if double or harpoon, large over small 双箭头或鱼叉箭头，大到小？
    tvAR_SOL = 0x0020  # if double or harpoon, small over large 双箭头或鱼叉箭头，小到大？

    # 积分
    tmINTEG = 15
    tvINT_1 = 0x0001  # single integral sign 单积分
    tvINT_2 = 0x0002  # double integral sign 双积分
    tvINT_3 = 0x0003  # triple integral sign 三重积分
    tvINT_LOOP = 0x0004  # has loop w/o arrows 包含循环 w/o 箭头 	\oint
    tvINT_CW_LOOP = 0x0008  # has clockwise loop 顺时针循环
    tvINT_CCW_LOOP = 0x000C  # has counter-clockwise loop 逆时针循环
    tvINT_EXPAND = 0x10  # integral signs expand 扩大积分符号

    # 大操作符
    tmSUM = 16  # sum 求和
    tmPROD = 17  # Product 乘积
    tmCOPROD = 18  # coproduct
    tmUNION = 19  # union 并集
    tmINTER = 20  # intersection 交集
    tmINTOP = 21  # integral-style big operator积分式大操作符
    tmSUMOP = 22  # summation-style big operator 求和式大操作符

    # 极限
    tmLIM = 23
    tvSUBAR = 0  # single underbar
    tvDUBAR = 1  # double underbar

    # 文档中是0x01，实际可能是0x10
    tvBO_LOWER = 0x10
    tvBO_UPPER = 0x20
    tvBO_SUM = 0x40

    # 水平(上下？)括号
    tmHBRACE = 24  # horizontal brace
    tmHBRACK = 25  # horizontal bracket

    tvHB_TOP = 0x0001  # slot is on the top, else on the bottom 顶部，其他值是底部

    tmLDIV = 26  # long division  长除法
    tvLD_UPPER = 0x0001  # upper slot is present 上部分存在

    # 上下角标
    tmSUB = 27  # subscript 下标
    tmSUP = 28  # superscript 上标
    tmSUBSUP = 29  # subscript and superscript 下标和上标
    tvSU_PRECEDES = 0x0001  # script precedes scripted item,else follows 角标在在前，否则在后

    # 狄拉克符号 常用语量子力学
    #  https://zh.wikipedia.org/wiki/%E7%8B%84%E6%8B%89%E5%85%8B%E7%AC%A6%E5%8F%B7
    tmDIRAC = 30
    tvDI_LEFT = 0x0001  # left part is present 左矢
    tvDI_RIGHT = 0x0002  # right part is present 右矢

    # 向量
    tmVEC = 31
    tvVE_LEFT = 0x0001  # arrow points left 箭头向左
    tvVE_RIGHT = 0x0002  # arrow points right 箭头向右
    tvVE_UNDER = 0x0004  # arrow under slot, else over slot 箭头在slot下，否则在上
    tvVE_HARPOON = 0x0008  # harpoon 鱼叉箭头

    # Hats, arcs, tilde, joint status
    tmTILDE = 32  # tilde over characters 波浪线在字符上
    tmHAT = 33  # hat over characters hat在字符上
    tmARC = 34  # arc over characters弧线在字符上
    tmJSTATUS = 35  # joint status construct 连接状态构建

    # 删除线
    tmSTRIKE = 36
    tvST_HORIZ = 0x0001  # line is horizontal, else slashes 水平横线，否则斜线
    tvST_UP = 0x0002  # if slashes, slash from lower-left to upper-right is present 左下到右上的斜线
    tvST_DOWN = 0x0004  # if slashes, slash from upper-left to lower-right is present 左上到右下的斜线

    # 盒
    tmBOX = 37
    tvBX_ROUND = 0x0001  # corners are round, else square 圆角，其他直角
    tvBX_LEFT = 0x0002  # 左
    tvBX_RIGHT = 0x0004  # 右
    tvBX_TOP = 0x0008  # 上
    tvBX_BOTTOM = 0x0010  # 下

    # TypeFace
    fnFUNCTION = 2

    def __init__(self):
        self._data = None  # 数据流 bytes
        self._position = 28  # OleData嵌入的公式，包含一个28字节的头部
        self._env = ''
        self._debug = False
        self._intend = -1  # 缩进级别
        self._stack = []  # 堆栈消息
        self._last_typeface = None  # 上一个Char的TypeFace
        self._function_started = False
        # record 解析器
        self._parses = {
            0: self._parse_end,
            1: self._parse_line,
            2: self._parse_char,
            3: self._parse_tmpl,
            4: self._parse_pile,
            5: self._parse_matrix,
            6: self._parse_embell,
            7: self._parse_ruler,
            8: self._parse_font_style_def,
            9: self._parse_size,
            10: self._parse_full,
            11: self._parse_sub,
            12: self._parse_sub2,
            13: self._parse_sym,
            14: self._parse_subsym,
            15: self._parse_color,
            16: self._parse_color_def,
            17: self._parse_font_def,
            18: self._parse_equation_prefs,
            19: self._parse_encoding_def
        }

    def parse_eqn(self, ole_data):
        self._data = ole_data
        # skip ole header
        self._position = 28

        # skip header
        mtef_version = self._data[self._position]
        self._position += 1

        # skip platform and mathtype
        self._position += 2

        mt_major_version = self._data[self._position]
        self._position += 1

        mt_minor_version = self._data[self._position]
        self._position += 1
        if mtef_version != 0x05 and mt_major_version != 0x06:
            logger.error("UNSUPPORTED VERSION:{} {}.{}".format(mtef_version, mt_major_version, mt_minor_version))
            return ''

        # skip DSMT4
        self._position += 6

        option = self._data[self._position]
        self._position += 1

        r = ''.join(self._parse_records())
        return r.replace(r'\asin', r'\operatorname{asin}')

    def parse(self, ole_data: bytes) -> str:
        """
        转换公式
        :param ole_data:
        :return: 转换好的LateX
        """

        if self._debug:
            logger.setLevel(logging.DEBUG)
        self._stack.clear()

        f = OleFileIO(ole_data)
        stream = f.openstream("Equation Native")
        self._data = stream.read()
        stream.close()
        f.close()
        return self.parse_eqn(self._data)

    def _parse_records(self, record_count=AUTO_DETECT_SLOTS):
        """
        解析记录
        :param record_count: 需要解析的一级记录数。默认自动检测

        :return:
        """
        record_type = self._data[self._position]
        length = len(self._data)
        result = []
        self._intend += 1

        # 检测到0(end record) 且 未获得期待的记录数
        while record_type != 0 and (record_count == AUTO_DETECT_SLOTS or len(result) < record_count):  # end record
            if record_type not in self._parses:
                logger.error(
                    "CAN NOT FOUND RECORD TYPE: {}, Position: {}\r\n {}".format(
                        record_type, self._position, binascii.hexlify(self._data)
                    )
                )
                logger.error('\r\n'.join(self._stack))
            if self._debug:
                self._stack.append(
                    "    " * self._intend + "Position: {} Record Type:{}".format(self._position, record_type))

            func = self._parses[record_type]

            r = func()
            if self._debug:
                self._stack.append("    " * self._intend + "::Value:{}".format(r))
            if r:  # 跳过空值
                result.append(r)
            # 01 01 线占位符，
            elif record_type == 1 and self._data[self._position - 1] == 0x01:
                result.append(r)

            if length <= self._position:
                break
            record_type = self._data[self._position]

        if (
                # 拿到了期望的记录数
                (record_count != AUTO_DETECT_SLOTS and record_count == len(result)) or
                # 最后一个记录是占位
                (self._data[self._position - 2] == 0x01 and self._data[self._position - 1] == 0x01)
        ):
            pass
        else:
            self._position += 1

        self._intend -= 1
        return result

    def _parse_nudge(self):
        """
        解析NUDGE数据
        包含2个或者六个字节数据
        :return:
        """

        small_dx = self._data[self._position]
        self._position += 1

        small_dy = self._data[self._position]
        self._position += 1

        # 6个字节
        if small_dx == -128 and small_dy == -128:
            self._position += 4

    def _get_signed_int(self):
        """
        解析有符号数
        :return:
        """
        if self._data[self._position] < 0xFF:
            val = self._data[self._position] - 128
            self._position += 1
            return val
        else:
            vals = struct.unpack_from('h', self._data, self._position + 1)  # skip 0xFF
            self._position += 3
            return vals[0]

    def _get_unsigned_int(self):
        """
        解析无符号数
        :return:
        """
        if self._data[self._position] < 0xFF:
            val = self._data[self._position]
            self._position += 1
            return val
        else:
            vals = struct.unpack_from('h', self._data, self._position + 1)  # skip 0xFF
            self._position += 3
            return vals[0]

    def _skip_to_end(self):
        """
        寻找结束符
        :return:
        """
        length = len(self._data)
        while self._position < length and self._data[self._position] != 0:
            self._position += 1

    def _parse_end(self):
        """
        解析end
        :return:
        """
        self._position += 1
        return ""

    def _parse_char(self):
        """
        解析CHAR
        :return:
        """
        val = ''
        # skip record type
        self._position += 1

        # option
        option = self._data[self._position]
        self._position += 1

        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()
        # typeface value
        typeface = self._get_signed_int()
        mapped_mt_code = False

        # char values
        # 除非指定了NO_MTCODE，否则，必然包含MT_CODE；并且根据选项，可知后续可能包含CHAR_8或CHAR_16
        if option & self.mtefOPT_CHAR_ENC_NO_MTCODE == 0:
            vals = bytes([self._data[self._position], self._data[self._position + 1]])
            self._position += 2

            # TODO: 有些字符， 可能解析会失败
            # if vals[1] == 0:
            #     val = chr(vals[0])
            # else:
            #     val = vals.decode('utf-16')
            val = vals.decode('utf-16')
            val = CHAR_MAP.get(int.from_bytes(vals, 'little'), val)
            mapped_mt_code = int.from_bytes(vals, 'little') in CHAR_MAP.keys()
            if mapped_mt_code:
                val = CHAR_MAP.get(int.from_bytes(vals, 'little'), val)

        if option & self.mtefOPT_CHAR_ENC_CHAR_8 > 0:
            vals = struct.unpack_from('c', self._data, self._position)
            # if not mapped_mt_code:
            #     val = vals[0].decode('latin-1')
            self._position += 1
        elif option & self.mtefOPT_CHAR_ENC_CHAR_16 > 0:
            vals = bytes([self._data[self._position], self._data[self._position] + 1])
            # if not mapped_mt_code:
            #     val = vals.decode('utf-16')
            self._position += 2

        # 跟随字体修饰
        if option & self.mtefOPT_CHAR_EMBELL > 0:
            embell = ''.join(self._parse_records(1))
            if not embell:
                embell = '%s'
        else:
            embell = '%s'

        if option & self.mtefOPT_CHAR_FUNC_START > 0:
            self._function_started = True
            val = '\\' + val
        else:
            val = embell % val
        if self._function_started and typeface != self.fnFUNCTION:
            val = ' ' + val
            self._function_started = False
        self._last_typeface = typeface
        return val

    def _parse_line(self):
        """
        解析LINE
        :return:
        """
        # skip record type
        self._position += 1
        val = ''
        # option
        option = self._data[self._position]
        self._position += 1

        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()
        elif option & self.mtefOPT_LINE_NULL > 0:
            return ''

        if option & self.mtefOPT_LINE_LSPACE > 0:
            self._position += 2  # 跳过spacing
        elif option & self.mtefOPT_LP_RULER > 0:
            val += self._parse_ruler()

        val += ''.join(self._parse_records())
        return val

    def _parse_tmpl(self):
        """
        解析TMPL
        :return:
        """
        # skip record type
        self._position += 1
        # option
        option = self._data[self._position]
        self._position += 1

        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()

        # selector
        selector_key = self._data[self._position]
        if self._debug:
            self._stack.append('    ' * self._intend + "  tmpl:{}".format(selector_key))
        self._position += 1

        selector_parser = self._tmpl_selector_parsers[selector_key]
        val = selector_parser()
        self._position += 1  # skip end
        return val

    def _parse_pile(self):
        """
        解析PILE
        :return:
        """
        # skip record type
        self._position += 1
        val = ''
        option = self._data[self._position]
        self._position += 1
        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()

        halign = self._data[self._position]
        self._position += 1
        valign = self._data[self._position]
        self._position += 1

        if option & self.mtefOPT_LP_RULER > 0:
            val += self._parse_ruler()
        elif option & self.mtefOPT_LINE_LSPACE > 0:
            self._position += 2  # 跳过spacing
        elif option & self.mtefOPT_LP_RULER > 0:
            val += self._parse_ruler()
        elif option & self.mtefOPT_LINE_NULL > 0:
            return ''
        obj_list = self._parse_records()
        obj_val = obj_list[0]
        for i in range(1, len(obj_list)):
            obj_val = r'{%s} \atop {%s}' % (obj_val, obj_list[i])
        r = val + obj_val
        if self._env and self._env.startswith("in_fences:"):
            v = r'\begin{matrix}' + r + r'\end{matrix}'
        else:
            v = r
        return v

    def _parse_matrix(self):
        """
        解析MATRIX
        设置环境变量 _env为 is_matrix
        :return:
        """
        # skip record type
        # self._env = 'is_matrix'
        self._position += 1
        option = self._data[self._position]
        self._position += 1
        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()

        valign = self._data[self._position]
        self._position += 1

        hjust = self._data[self._position]
        self._position += 1

        vjust = self._data[self._position]
        self._position += 1

        rows = self._data[self._position]
        self._position += 1

        columns = self._data[self._position]
        self._position += 1

        # row_parts
        self._position += int(rows / 4) + 1

        # col_parts
        self._position += int(columns / 4) + 1

        v = self._parse_records()
        r = []
        for i in range(0, len(v)):
            if i > 0 and i % columns == 0:
                r.append(r" \\ ")
            elif i % columns > 0:
                r.append(" & ")
            r.append(v[i])
        r = ''.join(r)
        # if self._env and self._env.startswith("in_fences:"):
        #     type = int(self._env[self._env.rindex(":") + 1:])
        #     if type == self.tmPAREN:  # 小括号
        #         v = r'\begin{pmatrix}' + r + r'\end{pmatrix}'
        #     elif type == self.tmBRACE:  # 花括号
        #         v = r'\begin{Bmatrix}' + r + r'\end{Bmatrix}'
        #     elif type == self.tmBRACK:  # 方括号
        #         v = r'\begin{bmatrix}' + r + r'\end{bmatrix}'
        #     elif type == self.tmBAR:  # 数线
        #         v = r'\begin{vmatrix}' + r + r'\end{vmatrix}'
        #     elif type == self.tmDBAR:  # 双竖线
        #         v = r'\begin{Vmatrix}' + r + r'\end{Vmatrix}'
        #     else:
        #         v = r'\begin{matrix}' + r + r'\end{matrix}'
        # else:
        #     v = r'\begin{matrix}' + r + r'\end{matrix}'
        v = r'\begin{matrix}' + r + r'\end{matrix}'
        return v

    embel_map = {
        2: r'\dot{%s}',  # over single dot
        3: r'\ddot{%s}',  # over double dot
        4: r'\dddot{%s}',  # over triple dot
        5: r"%s'",  # single prime
        6: r"%s''",  # double prime
        7: r"'%s",  # backwards prime (left of character)
        8: r"\tilde{%s}",  # tilde
        9: r"\hat{%s}",  # hat (circumflex)
        10: r"\xcancel{%s}",  # diagonal slash through character 可能不对。mathJax需要xcancel包
        11: r"\overrightarrow{%s}",  # over right arrow
        12: r"\overleftarrow{%s}",  # over left arrow
        13: r"\overleftrightarrow{%s}",  # over both arrow
        14: r"\overrightharpoon{%s}",  # over right single-barbed arrow
        15: r"\overleftharpoon{%s}",  # over left single-barbed arrow
        16: r"\overline{%s}",  # mid-height horizontal bar
        17: r"\overline{%s}",  # over-bar
        18: r"%s'''",  # triple prime
        19: r"\hat{%s}",  # over-arc, concave downward 可能不对
        20: r"\breve{%s}",  # over-arc, concave upward
        21: r"\dot{%s}",  # double diagonal bars 不支持。用点替代
        22: r"\dot{%s}",  # bottom-left to top-right diagonal bar  不支持。用点替代
        23: r"\dot{%s}",  # top-left to bottom-right diagonal bar 不支持。用点替代
        24: r"\ddddot{%s}",  # over quad dot
        25: r"%s",  # embU_1DOT
        26: r"%s",  # embU_2DOT
        27: r"%s",  # embU_3DOT
        28: r"%s",  # embU_4DOT
        29: r"\underline{%s}",  # under bar
        30: r"\utilde{%s}",  # under tilde bar
        31: r"\underline{%s}",  # under arc (ends point down)
        32: r"\underline{%s}",  # under arc (ends point down)
        33: r"\underrightarrow{%s}",  # under right arrow
        34: r"\underleftarrow{%s}",  # under left arrow
        35: r"\\underleftrightarrow{%s}",  # under both arrow (left and right)
        36: r"%s",  # under right arrow (1 barb)
        37: r"%s",  # under left arrow (1 barb)
    }

    def _parse_embell(self):
        """
        解析EMBELL
        :return:
        """
        self._position += 1
        option = self._data[self._position]
        self._position += 1
        if option & self.mtefOPT_NUDGE > 0:
            self._parse_nudge()

        embell_type = self._data[self._position]
        self._position += 1

        self._position += 1 # skip end

        return self.embel_map[embell_type]

    def _parse_ruler(self):
        """
        解析RULE
        :return:
        """
        self._position += 1
        tab_num = self._data[self._position]
        self._position += 1

        self._position += 3 * tab_num  # tab_type, 16-bit integer

        return ''

    def _parse_font_style_def(self):
        """
        解析FONT_STYLE_DEF
        :return:
        """
        self._position += 1

        font_def_index = self._data[self._position]
        self._position += 1

        char_style = self._data[self._position]
        self._position += 1

        return ''

    def _parse_size(self):
        """
        解析SIZE
        :return:
        """
        self._position += 1

        option = self._data[self._position]
        self._position += 1

        if option == 101:
            self._position += 2
        elif option == 100:
            self._position += 3
        else:
            self._position += 3
        return ''

    def _parse_full(self):
        """
        解析FULL

        简单跳过
        :return:
        """

        self._position += 1

        return ''

    def _parse_sub(self):
        """
        解析SUB SIZE

        简单跳过
        :return:
        """
        self._position += 1

        return ''

    def _parse_sub2(self):
        """
        解析SUB2

        简单跳过
        :return:
        """

        self._position += 1

        return ''

    def _parse_sym(self):
        """
        解析SYM symbol size
        直接返回子容器内容
        :return:
        """
        self._position += 1

        # r = self._parse_records()

        return ''

    def _parse_subsym(self):
        """
        解析SUBSYM symbol size
        :return:
        """
        self._position += 1
        # r = self._parse_records()
        return ''

    def _parse_color(self):
        """
        解析COLOR
        :return:
        """
        self._position += 1

        color_index = self._get_unsigned_int()

        return ''

    def _parse_color_def(self):
        """
        解析COLOR_DEF
        :return:
        """
        self._position += 1

        option = self._data[self._position]
        self._position += 1

        if option & self.mtefCOLOR_CMYK > 0:
            self._position += 4 * 2
        else:
            self._position += 3 * 2

        if option & self.mtefCOLOR_SPOT > 0:
            pass  # self._position += 4
        if option & self.mtefCOLOR_NAME > 0:
            self._skip_to_end()
            self._position += 1

        return ''

    def _parse_font_def(self):
        """
        解析FONT_DEF
        :return:
        """

        self._position += 1

        enc_def_index = self._get_unsigned_int()
        self._skip_to_end()
        self._position += 1
        return ''

    def _parse_equation_prefs(self):
        """
        解析EQN_PREFS equation preferences(sizes, styles, spacing)
        :return:
        """
        self._position += 1

        option = self._data[self._position]
        self._position += 1

        size_array_count = self._data[self._position]
        self._position += 1

        # skip size
        counter = 0
        odd = True
        while counter < size_array_count:
            if odd:
                flag = (self._data[self._position] & 0xF0) >> 4
            else:
                flag = self._data[self._position] & 0x0F
            if not odd:  # 读完一个字节
                self._position += 1
            if flag == 0xF:
                counter += 1
            odd = not odd

        space_array_count = self._data[self._position]
        self._position += 1

        # skip space_array_count
        counter = 0
        odd = True
        while counter < space_array_count:
            if odd:
                flag = (self._data[self._position] & 0xF0) >> 4
            else:
                flag = self._data[self._position] & 0x0F
            if not odd:  # 读完一个字节
                self._position += 1
            if flag == 0xF:
                counter += 1
            odd = not odd

        styles_count = self._data[self._position]
        self._position += 1
        counter = 0
        while counter < styles_count:
            if self._data[self._position] == 0:
                counter += 1
                self._position += 1
            else:
                counter += 1
                self._position += 2

    def _parse_encoding_def(self):
        """
        解析ENCODING_DEF
        :return:
        """
        self._position += 1

        self._skip_to_end()

        self._position += 1

    def _parse_future(self):
        """
        解析FUTURE
        :return:
        """

    # # template selector parsers
    #  每个解析器返回 (前导字符，子对象容器格式化字符串，子对象分割容器字符串)

    def _tmpl_variation(self, ):
        var = self._data[self._position]
        if var & 0x80 > 0:
            var = (self._data[self._position] & 0x7f) | (self._data[self._position + 1] << 8)
            self._position += 2
        else:
            self._position += 1
        return var

    def _tmpl_general_parse(self, slot_count=AUTO_DETECT_SLOTS):
        """
        分析模板数据
        :param slot_count: 槽数量。默认自动检测
        :return:
        """
        # var
        var = self._tmpl_variation()

        template_options = self._data[self._position]
        self._position += 1

        slots = self._parse_records(slot_count)
        return var, template_options, slots

    def _tmpl_fences(self):
        """
        括号解析

        支持0-8类型的选择符解析
        :return:
        """
        symbols = ((r'\langle ', r'\rangle '),  # <>  angle
                   ('(', ')'),  # () pare
                   (r'\{', r'\}'),  # {}
                   ('[', ']'),  # []
                   ('|', '|'),  # | |
                   (r'\|', r'\|'),  # || ||
                   (r'\lfloor ', r'\rfloor '),
                   (r'\lceil ', r'\rceil '),
                   (r'(', ')')  # TODO: 未找到对应物
                   )
        type = self._data[self._position - 1]
        var = self._data[self._position]
        slots_count = 1
        if var & self.tvFENCE_L > 0:
            slots_count += 1
        if var & self.tvFENCE_R > 0:
            slots_count += 1

        # 矩阵结构：公式模板 括号 line 矩阵 括号左符号，括号右符号
        # +2 跳过 本身的选项和template option
        # BUG: option可能是多个字节
        has_matrix = False
        if struct.unpack_from('i', self._data, self._position + 2)[0] == 0x50001:  # 0x01000500:
            has_matrix = True
        has_pile = False
        # 数组结构： 公式模板 括号 pile
        if self._data[self._position + 2] == 0x4:
            has_pile = True

        # 设置进入 括号区域
        if not self._env:
            self._env = 'in_fences:%s' % type
        var, template_options, slots = self._tmpl_general_parse(slots_count)
        self._env = None

        # # 括号..>矩阵，需要修改装饰符号
        # if has_pile:
        #     v = r'\begin{pmatrix}' + slots[0] + r'\end{pmatrix}'
        # elif has_matrix:
        #     if type == self.tmPAREN:  # 小括号
        #         v = r'\begin{pmatrix}' + slots[0] + r'\end{pmatrix}'
        #     elif type == self.tmBRACE:  # 花括号
        #         v = r'\begin{Bmatrix}' + slots[0] + r'\end{Bmatrix}'
        #     elif type == self.tmBRACK:  # 方括号
        #         v = r'\begin{bmatrix}' + slots[0] + r'\end{bmatrix}'
        #     elif type == self.tmBAR:  # 数线
        #         v = r'\begin{vmatrix}' + slots[0] + r'\end{vmatrix}'
        #     elif type == self.tmDBAR:  # 双竖线
        #         v = r'\begin{Vmatrix}' + slots[0] + r'\end{Vmatrix}'
        #     else:
        #         v = r'\begin{matrix}' + slots[0] + r'\end{matrix}'
        # # if self._env == 'is_matrix':
        # #     v = r'\begin{pmatrix}' + slots[0] + r'\end{pmatrix}'
        # #     self._env = ''  # 清空环境变量
        # else:
        if var & self.tvFENCE_L > 0:  # 左括号
            v = r'\left%s' % symbols[type][0]
        else:
            v = '\left.'
        v += slots[0]
        if var & self.tvFENCE_R > 0:  # 右括号
            v += r'\right%s' % symbols[type][1]
        else:
            v += r'\right.'
        return v

    def _tmpl_intervals(self):
        """
        不对称的括号

        类型9解析
        :return:
        """
        var = self._data[self._position]
        slots_count = 3

        var, template_options, slots = self._tmpl_general_parse(slots_count)
        left = var & 0x0F
        right = var & 0xF0
        val = ''
        if left == self.tvINTV_LEFT_LP:
            val = '('
        elif left == self.tvINTV_LEFT_RP:
            val = ')'
        elif left == self.tvINTV_LEFT_LB:
            val = '['
        elif left == self.tvINTV_LEFT_RB:
            val = ']'
        val += slots[0]
        if right == self.tvINTV_RIGHT_LP:
            val += '('
        elif right == self.tvINTV_RIGHT_RP:
            val += ')'
        elif right == self.tvINTV_RIGHT_LB:
            val += '['
        elif right == self.tvINTV_RIGHT_RB:
            val += ']'
        return val

    def _tmpl_radicals(self):
        """
        根式

        类型10
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(slot_count=2)

        if var == self.tvROOT_SQ:
            return r'\sqrt{%s}' % slots[0]
        elif var == self.tvROOT_NTH:
            return r'\sqrt[%s]{%s}' % (slots[1], slots[0])
        else:
            logger.error("radicals: unsupported options: " + var)
        return ''

    def _tmpl_fraction(self):
        """
        分式

        分子，分母包含在两个LINE中

        类型11
        :return:
        """

        var, template_options, slots = self._tmpl_general_parse(slot_count=2)

        if var == self.tvFR_SMALL:
            return r'\tfrac{%s}{%s}' % (slots[0], slots[1])
        elif var == self.tvFR_SLASH:
            return '{%s}/{%s}' % (slots[0], slots[1])
        elif var == self.tvFR_BASE:
            logger.warning("frac. unsupported tvFR_BASE")
        return r'\frac{%s}{%s}' % (slots[0], slots[1])

    def _tmpl_over_underbars(self):
        """

        上下划线
        类型12、13
        :return:
        """
        type = self._data[self._position - 1]
        var, template_options, slots = self._tmpl_general_parse(1)
        formater = r'\underline{%s}' if type == self.tmUBAR else r'\overline{%s}'
        if var == self.tvBAR_DOUBLE:
            formater = r'\underline{\underline{%s}}' if type == self.tmUBAR else r'\overline{\overline{%s}}'
        return formater % slots[0]

    def _tmpl_arrows(self):
        """
        箭头

        类型14
        :return:
        """
        # main slots 不确定，要跟踪到end
        var, template_options, slots = self._tmpl_general_parse()
        arrow_type = var & 0x0F
        arrow_option = var & 0xF0
        top_str = ''
        bottom_str = ''

        if arrow_type & self.tvAR_TOP > 0 and arrow_type & self.tvAR_BOTTOM > 0:
            bottom_str = '{%s}' % slots[0]
            top_str = '[%s]' % slots[1]
        elif arrow_type & self.tvAR_TOP > 0:  # 箭头上包含文字
            top_str = '{%s}' % slots[0]
        elif arrow_type & self.tvAR_BOTTOM > 0:  # 箭头下包含文字
            top_str = '[%s]' % slots[1]
            bottom_str = '{}'

        if arrow_type & self.tvAR_DOUBLE > 0:
            logger.warning("tmpl 14: 不支持上下不一致的箭头形式. ")
            if arrow_option & self.tvAR_LOS > 0:  # 上大下小
                pass
            elif arrow_option & self.tvAR_SOL > 0:  # 上小下大
                pass
            else:  # 一般大
                pass
            formatter = r'\xtofrom'
        elif arrow_type & self.tvAR_HARPOON > 0:
            logger.warning("tmpl 14: 不支持上下不一致的箭头形式. ")
            if arrow_option & self.tvAR_LOS > 0:  # 上大下小
                pass
            elif arrow_option & self.tvAR_SOL > 0:  # 上小下大
                pass
            else:  # 一般大
                pass
            formatter = r'\xrightleftharpoons'
        else:
            if arrow_option & self.tvAR_LEFT > 0 and arrow_option & self.tvAR_RIGHT > 0:
                formatter = r'\xleftrightarrow'
            else:
                if arrow_option & self.tvAR_LEFT > 0:
                    formatter = r'\xleftarrow'
                else:  # arrow_option & self.tvAR_RIGHT > 0:
                    formatter = r'\xrightarrow'
        return formatter + top_str + bottom_str

    def _tmpl_integrals(self):
        """
        积分

        类型15
        :return:
        """

        var, template_options, slots = self._tmpl_general_parse(slot_count=4)

        # 不止一个符号，直接把后续符号跳过
        if var & self.tvINT_EXPAND > 0:
            while self._data[self._position] == 0x02:
                slots[3] += ''.join(self._parse_records(1))
        operator = ''
        op_type = var & 0x03  # 最后两位表示积分符号（几重积分）
        if op_type == self.tvINT_1:
            operator = r'\int'
            if var & self.tvINT_LOOP > 0:  # 单积分符号上包含圆圈
                operator = r'\oint'
            if var & 0xF0 == 0x70:  # 数值在积分符号上，下
                operator = r'\intop'
        elif op_type == self.tvINT_2:
            operator = r'\iint'
            if var & 0xFD > 0:
                logger.warning("双积分，不支持任何附加符号")
        elif op_type == self.tvINT_3:
            operator = r'\iiint'
            if var & 0xFD > 0:
                logger.warning("三积分，不支持任何附加符号")
        if var & self.tvBO_LOWER > 0 and var & self.tvBO_UPPER > 0:
            r = '%s_{%s}^{%s}{%s}' % (operator, slots[1], slots[2], slots[0])
        elif var & self.tvBO_LOWER > 0:
            r = '%s_{%s}{%s}' % (operator, slots[1], slots[0])
        elif var & self.tvBO_UPPER > 0:
            r = '%s^{%s}{%s}' % (operator, slots[2], slots[0])
        else:
            r = operator + '{%s}' % slots[0]

        # if var & 0x10 > 0:  # 主，上，下
        #     if len(slots) <= 2:
        #         r = '%s_{%s}{%s}' % (operator, slots[1], slots[0])
        #     else:
        #         r = '%s_{%s}^{%s}{%s}' % (operator, slots[1], slots[2], slots[0])
        # else:
        #     r = operator + '{%s}' % slots[0]
        return r

    def __slots_clear_empty(self, slots):
        """
        清除空字段
        :param slots:
        :return:
        """
        while "" in slots:
            slots.remove("")

    def _tmpl_sum_prod_unprod_set(self):
        """
        求和、乘积、交叉并集等

        类型16-22
        :return:
        """
        type = self._data[self._position - 1]
        var, template_options, slots = self._tmpl_general_parse(slot_count=4)

        operator = ''
        if type == self.tmSUM:
            operator = r'\sum'
        elif type == self.tmPROD:
            operator = r'\prod'
        elif type == self.tmCOPROD:
            operator = r'\coprod'
        elif type == self.tmUNION:
            operator = r'\bigcup'
        elif type == self.tmINTER:
            operator = r'\bigcap'
        elif type == self.tmINTOP:
            operator = slots[3]
        elif type == self.tmSUMOP:
            operator = slots[3]
        upper = ''
        lower = ''
        main_ = ''
        if var & self.tvSU_PRECEDES > 0:  # 符号在主内容前
            logger.warning("tvSU_PRECEDES: {}{}{}{}".format(slots[0], slots[1], slots[2], slots[3]))
            if var & self.tvBO_UPPER > 0:
                upper = '^{%s}' % slots[1]
            if var & self.tvBO_LOWER > 0:
                lower = '_{%s}' % slots[0]
            if slots[2]:
                main_ = '{%s}' % slots[2]
        else:  # 主内容，符号
            if var & self.tvBO_UPPER > 0:
                upper = '^{%s}' % slots[2]
            if var & self.tvBO_LOWER > 0:
                lower = '_{%s}' % slots[1]
            if slots[0]:
                main_ = '{%s}' % slots[0]
        v = '%s%s%s' % (lower, upper, main_)
        return operator + v

    def _tmpl_limits(self):
        """
        极限

        类型23
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(4)
        opeartor = r'\lim\limits'
        if slots[1]:
            limits = '_{%s}' % slots[1]
        else:
            limits = ''
        return opeartor + limits

    def _tmpl_horizontal_braces(self):
        """
        上下括号

        类型24
        :return:
        """
        type = self._data[self._position - 1]
        var, template_options, slots = self._tmpl_general_parse(3)
        if type == self.tmHBRACK:
            logger.warning("不支持上下方括号，改为花括号")
        if var == self.tvHB_TOP:
            return r'\overbrace{%s}^{%s}' % (slots[0], slots[1])
        else:
            return r'\underbrace{%s}_{%s}' % (slots[0], slots[1])

    def _tmpl_long_division(self):
        """
        长除

        类型25
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(4)
        self.__slots_clear_empty(slots)
        if len(slots) == 1:
            return r'\overline{\left)%s\right.}' % slots[0]
        else:
            return r'\overset{%s}{\overline{\left)%s\right.}}' % (slots[1], slots[0])

    def _tmpl_subscript_superscript(self):
        """
        上下角标

        类型27-29
        :return:
        """
        type = self._data[self._position - 1]
        var, template_options, slots = self._tmpl_general_parse(2)
        if type == self.tmSUB:
            return r'_{%s}' % slots[0]
        elif type == self.tmSUP:
            return r'^{%s}' % slots[1]
        else:
            return r'_{%s}^{%s}' % (slots[0], slots[1])

    def _tmpl_dirac_notation(self):
        """
        迪科尔符号

        类型30
        :return:
        """
        slots_count = 3
        var = self._data[self._position]
        if var & self.tvDI_LEFT > 0:
            slots_count += 1
        if var & self.tvDI_RIGHT > 0:
            slots_count += 1
        var, template_options, slots = self._tmpl_general_parse(slots_count)
        v = ''
        if var & self.tvDI_LEFT > 0:
            v += r'\langle{%s}' % slots[0]
        v += '|'
        if var & self.tvDI_RIGHT > 0:
            v += r'{%s}\rangle' % slots[1]
        return v

    def _tmpl_vector(self):
        """
        向量

        类型31
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(2)

        if var & self.tvVE_LEFT > 0 and var & self.tvVE_RIGHT:
            if var & self.tvVE_HARPOON > 0:
                logger.warning("VECTOR not support tvVE_HARPOON")
            if var & self.tvVE_UNDER:
                return r'\underleftrightarrow{%s}' % slots[0]
            else:
                return r'\overleftrightarrow{%s}' % slots[0]

        if var & self.tvVE_UNDER > 0:
            if var & self.tvVE_HARPOON > 0:
                logger.warning("VECTOR not support tvVE_HARPOON")
            if var & self.tvVE_LEFT:
                return r'\underleftarrow{%s}' % slots[0]
            else:
                return r'\underrightarrow{%s}' % slots[0]
        else:
            if var & self.tvVE_LEFT:
                if var & self.tvVE_HARPOON > 0:
                    return r'\overleftharpoon{%s}' % slots[0]
                else:
                    return r'\overleftarrow{%s}' % slots[0]
            else:
                if var & self.tvVE_HARPOON > 0:
                    return r'\overrightharpoon{%s}' % slots[0]
                else:
                    return r'\overrightarrow{%s}' % slots[0]

    def _tmpl_hats(self):
        """
        装饰符号

        类型32-35
        :return:
        """
        type = self._data[self._position - 1]
        var, template_options, slots = self._tmpl_general_parse(2)
        if type == self.tmTILDE:
            op = r'\widetilde{%s}'
        elif type == self.tmHAT:
            op = r'\widehat{%s}'
        elif type == self.tmARC:
            op = r'\overgroup{%s}'
        elif type == self.tmJSTATUS:
            op = r'\overlinesegment{%s}'
        else:
            op = ''
        return op % slots[0]

    def _tmpl_cross_out(self):
        """
        删除线

        类型36
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(1)
        if var & self.tvST_HORIZ > 0:
            return r'sout{%s}' % slots[0]
        else:
            if var & self.tvST_UP > 0 and var & self.tvST_DOWN > 0:
                return r'\xcancel{%s}' % slots[0]
            elif var & self.tvST_UP > 0:
                return r'\bcancel{%s}' % slots[0]
            else:
                return r'\cancel{%s}' % slots[0]

    def _tmpl_box(self):
        """
        盒

        类型37
        :return:
        """
        var, template_options, slots = self._tmpl_general_parse(1)
        return r'\boxed{%s}' % slots[0]

    @property
    def _tmpl_selector_parsers(self):
        """
        公式模板解析器
        :return:
        """
        name = '__tmpl_selector_parsers'
        if hasattr(self, name):
            return getattr(self, name)
        parsers = {
            0: self._tmpl_fences,
            1: self._tmpl_fences,
            2: self._tmpl_fences,
            3: self._tmpl_fences,
            4: self._tmpl_fences,
            5: self._tmpl_fences,
            6: self._tmpl_fences,
            7: self._tmpl_fences,
            8: self._tmpl_fences,

            9: self._tmpl_intervals,

            10: self._tmpl_radicals,

            11: self._tmpl_fraction,

            12: self._tmpl_over_underbars,
            13: self._tmpl_over_underbars,

            14: self._tmpl_arrows,

            15: self._tmpl_integrals,

            16: self._tmpl_sum_prod_unprod_set,
            17: self._tmpl_sum_prod_unprod_set,
            18: self._tmpl_sum_prod_unprod_set,
            19: self._tmpl_sum_prod_unprod_set,
            20: self._tmpl_sum_prod_unprod_set,
            21: self._tmpl_sum_prod_unprod_set,
            22: self._tmpl_sum_prod_unprod_set,

            23: self._tmpl_limits,

            24: self._tmpl_horizontal_braces,
            25: self._tmpl_horizontal_braces,

            26: self._tmpl_long_division,

            27: self._tmpl_subscript_superscript,
            28: self._tmpl_subscript_superscript,
            29: self._tmpl_subscript_superscript,

            30: self._tmpl_dirac_notation,

            31: self._tmpl_vector,

            32: self._tmpl_hats,
            33: self._tmpl_hats,
            34: self._tmpl_hats,
            35: self._tmpl_hats,

            36: self._tmpl_cross_out,

            37: self._tmpl_box
        }
        setattr(self, name, parsers)
        return parsers
