import unittest
import struct

from ..mathtype import MathTypeParser


class MathTypeParserTests(unittest.TestCase):

    def prepare_parser(self, data):
        parser = MathTypeParser()
        data = bytes.fromhex(data)
        parser._data = data
        parser._position = 0
        return parser

    def test_parse_only_mt_char(self):
        data = bytes.fromhex('0200836200')
        parser = MathTypeParser()
        parser._data = data
        parser._position = 0
        val = parser._parse_char()
        self.assertEqual(val, 'b')

    def test_parse_mtefOPT_CHAR_ENC_CHAR_8(self):
        parser = MathTypeParser()
        data = bytes.fromhex('02048612222d')
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_char(), '-')

    def test_char_(self):
        data = bytes.fromhex('02 00 96 29 00 00')
        parser = MathTypeParser()
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_char(), ')')

    def test_char_ch_comma(self):
        data = bytes.fromhex('02 00 8C 0C ff 00')
        parser = MathTypeParser()
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_char(), '，')

    #
    # def test_parse_mtefOPT_CHAR_ENC_CHAR_16(self):
    #     parser = MathTypeParser()
    #     data = bytes.fromhex('0204861222b1')
    #     parser._data = data
    #     parser._position = 0
    #
    #     self.assertEqual(parser._parse_char(), b'\xb1'.decode())

    def test_parse_line(self):
        parser = MathTypeParser()
        data = bytes.fromhex('01 00 02 00 88 32 00 02 00 83 61 00 00 ')
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_line(), '2a')

    def test_tmpl_franc(self):
        parser = MathTypeParser()
        data = bytes.fromhex('03 00 0b 00 00 01 00 02 00 88 31 00 00 01 00 02 00 88 32 00 00 00 00')
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_tmpl(), r'\frac{1}{2}')

    def test_tmpl_franc2(self):
        parser = MathTypeParser()
        data = bytes.fromhex(
            '03 00 0b 01 00 0b 01 00 02 00 88 34 00 02 00 83 61 00 02 00 83 63 00 00 01 00 02 00 83 61 00 02 00 83 62 00 00 00 00')
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_tmpl(), r'\tfrac{4ac}{ab}')

    def test_tmpl_franc_slash(self):
        parser = MathTypeParser()
        data = bytes.fromhex('03 00 0b 02 00 01 00 02 00 88 31 00 00 01 00 02 00 88 32 00 00 00 00')
        parser._data = data
        parser._position = 0

        self.assertEqual(parser._parse_tmpl(), r'{1}/{2}')

    def test_tmpl_sqrt(self):
        parser = MathTypeParser()
        data = bytes.fromhex('03 00 0a 00 00 01 00 02 00 88 32 00 00 0b 01 01 00 00 00 00')
        parser._data = data
        parser._position = 0
        self.assertEqual(parser._parse_tmpl(), r'\sqrt{2}')

    def _test(self, data, value):
        parser = MathTypeParser()
        data = bytes.fromhex(data)
        parser._data = data
        parser._position = 0
        self.assertEqual(parser._parse_tmpl(), value)

    def test_tmp_sqrt_nth(self):
        self._test('03 00 0a 01 00 01 00 02 00 88 39 00 00 0b 01 00 02 00 88 33 00 00 00 00', r'\sqrt[3]{9}')

    def test_tmpl_long_div(self):
        self._test(
            '03 00 1a 00 00 01 00 02 00 88 38 00 00 01 01 00 00',
            r'\overline{\left)8\right.}')

    def test_tmpl_long_div2(self):
        data = '02 00 88 31 00 03 00 1a 01 00 01 00 02 00 88 32 00 00 01 00 02 00 88 31 00 00 00 00'

        parser = MathTypeParser()
        data = bytes.fromhex(data)
        parser._data = data
        parser._position = 0
        values = parser._parse_records()
        # r'\overset{3}{\overline{)3}}'
        self.assertEqual(''.join(values), r'1\overset{1}{\overline{\left)2\right.}}')

    def test_tmpl_france(self):
        data = '03 00 01 03 00 01 00 02 00 88 32 00 00 02 00 96 28 00 02 00 96 29 00 00 00'
        self._test(data, r'\left(2\right)')

    def test_tmpl_france_only_left(self):
        data = '03 00 01 01 00 01 00 02 00 88 32 00 02 00 88 30 00 00 02 00 96 28 00 00'
        self._test(data, r'\left(20\right.')

    def test_tmpl_france_angle_right(self):
        data = '03 00 00 02 00 01 00 02 00 88 35 00 00 02 00 96 2A 23 00 00'
        self._test(data, r'\left.5\right\rangle ')

    def test_tmpl_intervals(self):
        data = '03 00 09 33 00 01 00 02 00 88 35 00 00 02 00 96 5D 00 02 00 96 5D 00 00'
        self._test(data, r']5]')

    def test_tmpl_intervals2(self):
        data = '03 00 09 23 00 01 00 02 00 88 32 00 00 02 00 96 5D 00 02 00 96 5B 00 00'
        self._test(data, r']2[')

    def test_tmpl_intervals3(self):
        data = '03 00 09 12 00 01 00 02 00  88 35 00 00 02 00 96 5B 00 02 00 96 29 00 00'
        self._test(data, r'[5)')

    def test_tmpl_underbars(self):
        data = '03 00 0C 00 00 01 00 02 00  83 6A 00 02 00 83 6B 00 02 00 83 6C 00 02 00 83  6A 00 00 00 00 '
        self._test(data, r'\underline{jklj}')

    def test_tmpl_overbars(self):
        data = '03 00 0D 01 00 01 00 02 00 88 38 00 00 00 00'
        self._test(data, r'\overline{\overline{8}}')

    def test_tmpl_1f(self):
        data = '03 00 1F 02 00 01 00 02 00   88 34 00 02 00 83 6B 00 02 00 83 6A 00 02 00 83 68 00 02 00 83 73 00 00 02 00 96 D7 20 00 00'
        self._test(data, r'\overrightarrow{4kjhs}')

    def test_tmpl_1f2(self):
        data = '03 00 1F 03 00 01 00 02 00 83 6C 00 02 00 83 6C 00 02 00 83 6A 00 02 00 83 6B 00 02 00 83 6A 00 02 00 83 6B 00 00 02 00 96 E1 20 00 00'
        self._test(data, r'\overleftrightarrow{lljkjk}')

    def test_tmpl_arrow(self):
        data = '03 00 0E 3C 00 0B 01 00 02  00 88 35 00 00 01 00 02 00 83 79 00 00 0A 02 00  96 94 21 00 00'
        self._test(data, r'\xleftrightarrow[y]{5}')

    def test_tmpl_arrow2(self):
        """
        箭头下方有数字2
        :return:
        """
        data = '03 00 0E 15 00 0B 01 00 02  00 88 32 00 00 01 01 0A 02 00 96 92 21 02 00 96 90 21 00 00'
        self._test(data, r'\xtofrom{2}')

    def test_tmpl_arrow3(self):
        """
        肩头上方有数字
        :return:
        """
        data = '03 00 0E 09 00 0B 01 01 01 00 02 00 88 30 00 00 0A 02 00 96 92 21 02 00 96  90 21 00 00'
        self._test(data, r'\xtofrom[0]{}')  # not support

    def test_tmpl_arrow4(self):
        """
        鱼叉箭头肩头上方有数字
        :return:
        """
        data = '03 00 0E 06 00 0B 01 00 02  00 88 32 00 00 01 01 0A 02 00 96 C0 21 02 00 96  BD 21 00 00'
        self._test(data, r'\xrightleftharpoons{2}')  # not support

    def test_tmp_15(self):
        """
        积分,
        :return:
        """
        data = '03 00 0F 01 00 01 00 02 00  88 32 00 02 00 88 30 00 00 0B 01 01 01 01 0D 02  04 86 2B 22 F2 00 00'
        self._test(data, r'\int{20}')

    def test_int(self):
        data = 'd0cf11e0a1b11ae1000000000000000000000000000000003e000300feff0900060000000000000000000000010000000100000000000000001000000200000001000000feffffff0000000000000000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffdffffff04000000feffffff05000000fefffffffeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff52006f006f007400200045006e00740072007900000000000000000000000000000000000000000000000000000000000000000000000000000000000000000016000500ffffffffffffffff0200000003ce020000000000c000000000000046000000000000000000000000000000000000000003000000400200000000000001004f006c00650000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a000201ffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000001400000000000000010043006f006d0070004f0062006a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000120002010100000003000000ffffffff00000000000000000000000000000000000000000000000000000000000000000000000001000000690000000000000003004f0062006a0049006e0066006f0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000012000201ffffffff04000000ffffffff000000000000000000000000000000000000000000000000000000000000000000000000030000000600000000000000feffffff02000000fefffffffeffffff05000000060000000700000008000000feffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff010000020800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100feff030a0000ffffffff03ce020000000000c000000000000046160000004d6174685479706520362e30204571756174696f6e000c0000004d61746854797065204546000f0000004571756174696f6e2e44534d543400f439b2710000000000000000000000000000000000000000000000000000000000000000000000000003000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001c0000000200ecc1fc0000007c013000f0d7540000000000e4003000050100060944534d543600011357696e416c6c4261736963436f6465506167657300110554696d6573204e657720526f6d616e00110353796d626f6c001105436f7572696572204e65770011044d54204578747261001357696e416c6c436f64655061676573001106cbcecce500120008212f458f442f4150f4100f475f4150f21f1e4150f4150f4100f445f425f48f425f4100f4100f435f4100f48f45f42a5f48f48f4100f4100f40f48f417f48f4100f412a5f445f45f45f45f45f410f0c0100010001020202020002000101010003000100040005000a010003000f0100010002004500710075006100740069006f006e0020004e00610074006900760065000000000000000000000000000000000000000000000000000000000000000000000020000200ffffffffffffffffffffffff0000000000000000000000000000000000000000000000000000000000000000000000000400000018010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffff0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffff0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffff0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008832000200883000000b010101010d0204862b22f20000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
        parser = MathTypeParser()
        r = parser.parse(bytes.fromhex(data))
        self.assertEqual(r, r'\int{20}')

    def test_tmp_15_2(self):
        """
        积分,包含上下标内容
        :return:
        """
        data = '03 00 0F 71 00 01 00 02 00 88 38 00 00 0B 01 00 02 00 88 35 00 00 01 00 02  00 88 32 00 00 0D 02 04 86 2B 22 F2 00 00'
        self._test(data, r'\intop_{5}^{2}{8}')

    def test_tmpl_15_3(self):
        data = '03 00 0F 31 00 01 00 02 00 88 38 00 00 0B 01 00 02 00 88 35 00 00 01 00 02  00 88 31 00 00 0D 02 04 86 2B 22 F2 00 00'
        self._test(data, r'\int_{5}^{1}{8}')

    def test_tmpl_15_4(self):
        data = '03 00 0F 15 00 01 00 02 00 88 35 00 00 0B 01 00 02 00 88 32 00 00 01 01 0D 02 04 8B 11 EE D1 02 04 86 2B 22 F2 00 00'
        parser = MathTypeParser()
        parser._data = bytes.fromhex(data)
        parser._position = 0
        r = parser._parse_records()
        self.assertEqual(''.join(r), r'\oint_{2}{5}')
        # self._test(data, r'\oint_{2}{5}')

    def test_tmpl_15_5(self):
        data = '03 00 0F 13 00 01 00 02 00  88 35 00 02 00 88 35 00 00 0B 01 00 02 00 88 31  00 00 01 01 0D 02 04 86 2B 22 F2 02 04 86 2B 22   F2 02 04 86 2B 22 F2 00 00'
        self._test(data, r'\iiint_{1}{55}')

    def test_tmpl_16_sum(self):
        data = '03 00 10 30 00 01 00 02 00 88 32 00 02 00 88 33 00 00 0B 01 00 02 00 88 31  00 00 01 00 02 00 88 33 00 00 0D 02 04 86 11 22 E5 00 00'
        self._test(data, r'\sum_{1}^{3}{23}')

    def test_tmpl_16_sum2(self):
        data = '03 00 10 40 00 01 00 02 00  88 31 00 00 0B 01 01 01 01 0D 02 04 86 11 22 E5  00 00'
        self._test(data, r'\sum{1}')

    def test_tmpl_16_sum3(self):
        data = '03 00 10 50 00 01 00 02 00 88 35 00 00 0B 01 00 02 00 88 31 00 00 01 01 0D 02 04 86 11 22 E5 00 00 00'
        self._test(data, r'\sum_{1}{5}')

    def test_tmpl_19_union(self):
        data = '03 00 13 70 00 01 00 02 00 83 58 00 03 00 1B 00 00 0B 01 00 02 00 83 69 00 00 01 01 00 00 01 00 02 00 83 69 00 02 04 86 3D 00 3D 02 00 88 31 00 00 01 00 02 00 83 6E 00 00  0D 02 04 8B 2A 22 55 00 00'
        self._test(data, r'\bigcup_{i=1}^{n}{X_{i}}')

    def test_tmp_19_union2(self):
        data = '03 00 13 70 00 01 00 02 00 88 35 00 00 0B 01 00 02 00 88 32 00 00 01 00 02 00 88 31 00 00 0D 02 04 8B 2A 22 55 00 00'
        self._test(data, r'\bigcup_{2}^{1}{5}')

    def test_tmp_20_iter(self):
        data = '03 00 14 70 00 01 00 02 00  83 58 00 03 00 1B 00 00 0B 01 00 02 00 83 69 00  00 01 01 00 00 01 00 02 00 83 69 00 02 04 86 3D 00 3D 02 00 88 31 00 00 01 00 02 00 83 6E 00 00 0D 02 04 8B 29 22 49 00 00'
        self._test(data, r'\bigcap_{i=1}^{n}{X_{i}}')

    def test_tmpl_21_integral_style(self):
        data = '03 00 15 20 00 01 01 0B 01 01 01 00 02 00 88 32 00 00 0D 01 00 02 00 88 31 00 00 00 00'
        parser = self.prepare_parser(data)
        r = parser._parse_records()
        self.assertEqual(''.join(r), '1^{2}')

    def test_tmp_17_prod(self):
        data = '03 00 11 50 00 01 00 02 00  88 38 00 02 00 88 38 00 00 0B 01 00 02 00 88 31 00 00 01 01 0D 02 04 86 0F 22 D5 00 00'
        self._test(data, r'\prod_{1}{88}')

    def test_tmpl_23_limit(self):
        data = '03 00 17 10 00 01 00 02 02 82 6C 00 02 00 82 69 00 02 00 82 6D 00 00 0B 01 00 02 00 83 78 00 02 04 86 92 21 AE 02 04 86 1E 22 A5 00 01 01 00 0A 02 00 88 32 00 02 00 88 39  00 02 00 88 33 00 02 00 88 32 00 02 00 88 37 00  02 00 88 38 00 00'
        parser = self.prepare_parser(data)
        r = parser._parse_records()

        self.assertEqual(''.join(r), r'\lim\limits_{ x\to \infty }293278')

    def test_tmpl_23_limit2(self):
        data = '03 00 17 10 00 01 00 02 02 82 6C 00 02 00 82 69 00 02 00 82 6D 00 00 0B 04 00 01 01 01 00 02 00 83 78 00 02 04 86 92 21 AE 02 04 86 1E 22 A5 00 01 00 02 00 88 32 00 00 01 00 02 00 88 33 00 00 00 01 01 00 0A 02 00 88 32  00 00'
        parser = self.prepare_parser(data)
        r = parser._parse_records()

        self.assertEqual(''.join(r), r'\lim\limits_{{{ x\to \infty } \atop {2}} \atop {3}}2')

    def test_tmpl_matrix(self):
        data = '03 00 01 03 00 01 00 05 00 01 01 01 02 02 00 00 01 00 02 00 83 61 00 03 00 1B 00 00 0B 01 00 02 00 88 31 00 02 00 88 31 00  00 01 01 00 00 0A 01 00 02 00 83 61 00 03 00 1B  00 00 0B 01 00 02 00 88 31 00 02 00 88 32 00 00  01 01 00 00 0A 01 00 02 00 83 61 00 03 00 1B 00   00 0B 01 00 02 00 88 32 00 02 00 88 31 00 00 01 01 00 00 0A 01 00 02 00 83 61 00 03 00 1B 00 00  0B 01 00 02 00 88 32 00 02 00 88 32 00 00 01 01  00 00 00 00 0A 02 00 96 28 00 02 00 96 29 00 00 00'
        self._test(data, r'\begin{pmatrix}a_{11} & a_{12} \\ a_{21} & a_{22}\end{pmatrix}')

    def test_tmpl_matrix2(self):
        data = '03 00 01 03 00 01 00 05 00 01 01 01 03 03 00 00 01 00 02 00 83 61 00 03 00 1B 00 00 0B 01 00 02 00 88 31 00 02 00 88 31 00 00 01 01 00 00 0A 01 00 02 04 8B 26 20 4B 00 01 00 02 00 83 61 00 03 00 1B 00 00 0B 01 00 02 00 88 31 00 02 00 83 6E 00 00 01 01 00 00 0A 01 00 02 04 8B EE 22 4D 00 01 00 02 04 8B F1 22 4F 00 01 00 02 04 8B EE 22 4D 00 01 00 02 00 83 61 00 03 00 1B 00 00 0B 01 00 02 00 83 6D 00 02 00 88 31 00 00 01 01 00 00 0A 01 00 02 04 8B EF 22 4C 00 01 00 02 00 83 61 00 03 00 1B 00 00 0B 01 00 02 00 83 6D 00 02 00 83 6E 00 00 01 01 00 00 00 00 0A 02 00 96 28 00 02 00 96 29 00 00 00'
        self._test(data,
                   r'\begin{pmatrix}a_{11} & \ldots  & a_{1n} \\ \vdots  & \ddots  & \vdots  \\ a_{m1} & \cdots  & a_{mn}\end{pmatrix}')

    def test_tmpl_24(self):
        data = '03 00 18 01 00 01 00 02 00  88 31 00 02 00 88 31 00 02 00 88 31 00 00 0B 01  00 02 00 88 32 00 00 0A 02 00 96 37 FE 00 00'
        self._test(data, r'\overbrace{111}^{2}')

    def test_tmpl_25(self):
        data = '03 00 19 00 00 01 00 02 00  88 33 00 02 00 88 33 00 02 00 88 33 00 02 00 88 33 00 02 00 88 33 00 00 0B 01 00 02 00 88 32 00 00 0A 02 00 96 0C EC 00 00'
        self._test(data, r'\underbrace{33333}_{2}')

    def test_tmpl_30(self):
        data = '03 00 1E 03 00 01 00 02 00 88 31 00 00 01 00 02 00 88 32 00 00 02 00 96 2923 02 00 96 07 EC 02 00 96 2A 23 00 00'
        self._test(data, r'\langle{1}|{2}\rangle')

    def test_tmpl_34(self):
        data = '03 00 22 00 00 01 00 02 00 83 41 00 02 00 83 42 00 02 00 83 43 00 00 02 00 96 22 23 00 00'
        self._test(data, r'\overgroup{ABC}')  # MathJax not support

    def test_tmpl_12(self):
        data = '03 00 0C 01 00 01 00 02 00 88 32 00 02 00 88 32 00 02 00 88 32 00 00 00'
        self._test(data, r'\underline{\underline{222}}')

    def test_tmpl_37(self):
        data = '03 00 25 12 00 01 00 02 00 88 31 00 02 00 88 32 00 00 00 00'
        self._test(data, r'\boxed{12}')

    def test_tmpl_sub(self):
        data = '03 00 1C 01 00 0B 01 01 01 00 02 00 88 31 00 00 00 0A 02 00 83 68 00 00'
        self._test(data, r'^{1}')

    def test_color_def(self):
        data = '10 04 E8 03 00 00 00 00 BA EC C9 AB 00 0F 01 01 00 02 00 83 61 00 02 00 83 62 00 02 00 83 63 00 00'
        parser = self.prepare_parser(data)
        r = parser._parse_records()
        self.assertEqual(''.join(r), 'abc')

    # def test_parse(self):
    #     data = '1c0000000200cbc1f40000006c023500f0d75400000000000c003500050100060944534d543600011357696e416c6c4261736963436f6465506167657300110554696d6573204e657720526f6d616e00110353796d626f6c001105436f7572696572204e65770011044d54204578747261001357696e416c6c436f64655061676573001106cbcecce500120008212f27f25f218f212f475f4150f21f1e4150f4150f4100f445f425f48f425f4100f4100f435f4100f21f20a5f20a25f48f21f4100f4100f40f48f417f48f4100f21a5f445f45f45f45f45f410f0c0100010001020202020002000101010003000100040005000a01000300010300010002008832000002009628000200962900000000'
    #     parser = MathTypeParser()
    #
    #     r = parser.parse(bytes.fromhex(data))
    #     self.assertEqual(r, r'\left(2\right)')

    def test_sin(self):
        data = '02 02 82 73 00 02 00 82 69 00 02 00 82 6E 00 03 00 1C 00 00 0B 01 01 01 00 02 04 86 12 22 2D 02 00 88 31 00 00 00 0A 02 04 84 B8 03 71 00'
        parser = self.prepare_parser(data)

        r = parser._parse_records()
        self.assertEqual(''.join(r), r'\sin^{ -1}\theta ')

    def test_2s(self):
        data = '03 00 0B 00 00 01 00 02 04 86 12 22 2D 02 00 83 62 00 02 04 86 B1 00 B1 03 00 0A 00 00 01 00 02 00 83 62 00 03 00 1C 00 00  0B 01 01 01 00 02 00 88 32 00 00 00 0A 02 04 86 12 22 2D 02 00 88 34 00 02 00 83 61 00 02 00 83 63 00 00 0B 01 01 00 00 0A 01 00 02 00 88 32 00 02 00 83 61 00 00 00 00 '
        parser = self.prepare_parser(data)

        r = parser._parse_records()
        self.assertEqual(''.join(r), r'\frac{-b\pm \sqrt{b^{2}-4ac}}{2a}')

    def test_tmpl_01(self):
        data = '03 00 01 03 00 0F 00 01 00 0F 01 03 00 0B 00 00 0F 00 01 00 0F 01 02 00 88 35 00 00 0F 00 01 00 0F 01 02 00 88 32 00 00 00 02 04 86 2B 00 2B 02 00 83 78 00 00 02 00 96 28 00 02 00 96 29 00 00 02 04 86 3D 00 3D'
        parser = self.prepare_parser(data)

        r = parser._parse_records()
        self.assertEqual(''.join(r), r'\left(\frac{5}{2}+x\right)=')

    def test_therefor(self):
        parser = MathTypeParser()
        with open(r'/users/yuanxu/downloads/stream.bin', 'rb') as f:
            data = f.read()
            v = parser.parse_eqn(data)
            print(v)
