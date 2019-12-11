import sys
from pyquery import PyQuery




class AftQuestion(object):
    def __init__(self, pyquery):
        self.d = pyquery
        self.skip_ele = 0
        self.replace_pair = ()

    def parse_element(self, d=None):
        metadata = ''
        if not d:
            d = self.d

        for sub_d in d.children().items():

            if not self.skip_ele:
                # 分式
                if sub_d.has_class('dR'):
                    metadata += self.parse_fraction(sub_d)

                # 上标
                elif sub_d.has_class('eZ'):
                    metadata += self.parse_sup_corner(sub_d)

                # 下标
                elif sub_d.has_class('eY'):
                    metadata += self.parse_sub_corner(sub_d)

                elif sub_d.has_class('eP'):
                    # 向量

                    if '⃗' in sub_d.text():
                        metadata += self.parse_vec(sub_d)
                    if '→' in sub_d.text():
                        metadata += self.parse_overrightarrow(sub_d)
                    # overline
                    elif set(sub_d.text().replace(' ', '')) == {'¯'}:
                        metadata += self.parse_overline(sub_d)
                    # hat
                    elif sub_d.text() == '̂':
                        metadata += self.parse_hat(sub_d)
                    # overset
                    elif sub_d.text() == '⌢':
                        metadata += self.parse_overset(sub_d)
                    # widehat
                    elif sub_d.text() == '∧':
                        metadata += self.parse_widehat(sub_d)

                        # 开方
                elif sub_d.has_class('fA'):
                    metadata += self.parse_sqrt(sub_d)

                # 开n次方
                elif sub_d.has_class('eT'):
                    metadata += self.parse_nsqrt(sub_d)

                # 积分
                elif sub_d.has_class('cZ') and sub_d.text() == '∫':
                    metadata += self.parse_integral(sub_d)

                elif sub_d.has_class('dV') and sub_d.text():
                    # 方程组
                    if sub_d.text()[0] in ('{', '⎧') and sub_d.next()('.eG:first > .fB > .eJ ').length:
                        metadata += self.parse_case(sub_d)
                    # 矩阵
                    elif sub_d.text()[0] in ('⎡'):
                        metadata += self.parse_matrix(sub_d)
                    # pmatrix
                    elif sub_d.text()[0] in ('(', '⎛') and sub_d.next().children('.fB:first > .eJ').length:
                        metadata += self.parse_pmatrix(sub_d)
                    # Vmatrix
                    elif set(sub_d.text().replace(' ', '').replace('\\n', '')) == {'∣'} and sub_d.next().children(
                            '.fB:first > .eJ').length:
                        metadata += self.parse_vmatrix(sub_d)

                    else:
                        metadata += self.parse_element(sub_d)

                # 求和
                elif sub_d.has_class('dL') and sub_d('.eU:first').text().endswith('∑'):
                    metadata += self.parse_sum(sub_d)

                # underbrace
                elif not sub_d.children().length and sub_d.text() == '\ue152':
                    metadata = self.parse_underbrace(sub_d)

                elif list(sub_d.children()):
                    metadata += self.parse_element(sub_d)
                else:
                    metadata += sub_d.text().replace('{', '\\{').replace('}', '\\}')

            else:
                self.skip_ele -= 1

        metadata = metadata.replace(' ', '')
        if 'lim' in metadata and '\\lim' not in metadata:
            metadata = metadata.replace('lim', '\\lim')

        if self.replace_pair and self.replace_pair[0] in metadata:
            metadata = metadata.replace(self.replace_pair[0], self.replace_pair[1], 1)
            self.replace_pair = ()

        return metadata

    def parse_vec(self, d):
        """向量 class: eP"""

        if '⃗' in d.text():
            vec_data = '\\vec{%s}' % self.parse_element(d.next())
            self.skip_ele = 1
            return vec_data

        raise Exception('不可识别的符号: %s' % d.outer_html())

    def parse_overrightarrow(self, d):
        """overrightarrow class:eP"""

        if '→' in d.text():
            vec_data = '\\overrightarrow{%s}' % self.parse_element(d.next())
            self.skip_ele = 1
            return vec_data

        raise Exception('不可识别的符号: %s' % d.outer_html())

    def parse_overline(self, d):
        """overline class: eP"""
        meta_data = self.parse_element(d.next())
        self.skip_ele = 1

        return '\\overline{%s}' % meta_data

    def parse_fraction(self, d):
        """分式 class: dR"""

        # 分子
        molecule = ''
        # 分母
        denominator = ''

        for sub_d in d('.dB:first').children().items():
            if sub_d.has_class('eN'):
                molecule += self.parse_element(sub_d)
            elif sub_d.has_class('dJ'):
                denominator += self.parse_element(sub_d)

        return "\\frac{%s}{%s}" % (molecule, denominator)

    def parse_sup_corner(self, d):
        """上标 class: eZ"""
        return "^{%s}" % self.parse_element(d)

    def parse_sub_corner(self, d):
        """下标 class: eY"""
        return "_{%s}" % self.parse_element(d)

    def parse_sqrt(self, d):
        """开方 class: fA"""
        if d.text().split()[-1] in ['√', '⎷']:
            sqrt_data = '\\sqrt{%s}' % self.parse_element(d.next())
            self.skip_ele = 1
            return sqrt_data

        raise Exception('不可识别的符号: %s' % d.outer_html())

    def parse_integral(self, d):
        """积分 class: cZ"""
        if '∫' == d.text():
            return '\int'

        raise Exception('不可识别的符号: %s' % d.outer_html())

    def parse_case(self, d):
        """矩阵 class: dV"""
        text = d.text()
        if '{' == text or '⎧' in text:
            case_data = '\\begin{cases}%s\\end{cases}'
            next_ele = d.next()
            params = []
            for sub_d in next_ele('.fB:first > .eJ').items():
                params.append(self.parse_element(sub_d))
            self.skip_ele = 1
            return case_data % '\\\\'.join(params)

        raise Exception('不可识别的符号: %s' % d.outer_html())

    def parse_nsqrt(self, d):
        """开n次根 class: eT"""
        n = d.text()
        next_ele = d.next()

        if next_ele('.fA:first').text() != '√':
            raise Exception('不可识别的符号: %s' % d.outer_html())

        sqrt_data = self.parse_element(next_ele.children().eq(1))
        self.skip_ele = 1

        return '\\sqrt[%s]{%s}' % (n, sqrt_data)

    def parse_sum(self, d):
        """求和 class: dL"""
        if d.children().length != 2:
            raise Exception('不可识别的符号: %s' % d.outer_html())

        d1, d2 = d.children().items()
        d1_data = d1.text().split()
        if d1_data[1] != '∑':
            raise Exception('不可识别的符号: %s' % d.outer_html())

        d2_data = self.parse_element(d2)
        return '\\sum_{%s}^{%s}' % (d2_data, d1_data[0])

    def parse_hat(self, d):
        """hat class: eP"""

        hat_data = '\\hat{%s}' % self.parse_element(d.next())
        self.skip_ele = 1
        return hat_data

    def parse_overset(self, d):
        """overset class: eP"""

        overset_data = '\\overset{\\frown} {%s}' % self.parse_element(d.next())
        self.skip_ele = 1
        return overset_data

    def parse_widehat(self, d):
        """widehat class: eP"""

        widehat_data = '\\widehat{%s}' % self.parse_element(d.next())
        self.skip_ele = 1
        return widehat_data

    def parse_matrix(self, d):
        """矩阵 class: dV"""
        matrix_data = '\\begin{bmatrix}%s\\end{bmatrix}'
        params_data = []

        for sub_d in d.next()('.fB > .eJ').items():
            descendant_data = []
            for descendant_d in sub_d('.eJ > .eH').items():
                descendant_data.append(self.parse_element(descendant_d))
            params_data.append('&'.join(descendant_data))

        self.skip_ele = 2
        return matrix_data % '\\\\'.join(params_data)

    def parse_pmatrix(self, d):
        """pmatrix class: dV"""
        pmatrix_data = '\\begin{pmatrix}%s\\end{pmatrix}'
        param_data = []
        for sub_d in d.next().children('.fB:first > .eJ').items():
            children_data = []
            for child_d in sub_d('.eJ > .eH').items():
                children_data.append(self.parse_element(child_d))
            param_data.append('&'.join(children_data))

        self.skip_ele = 2
        return pmatrix_data % '\\\\'.join(param_data)

    def parse_underbrace(self, d):
        """underbrace class: dD aR"""

        pre_eu = d.closest('.eU').prev()
        prev_data = self.parse_element(pre_eu)
        next_data = self.parse_element(pre_eu.parents('.eU').next('.eU'))
        self.skip_ele = d.next_all().length + 1
        underbrace_data = '\\underbrace{%s}_{%s}' % (prev_data, next_data)
        self.replace_pair = [prev_data + underbrace_data, underbrace_data]

        return underbrace_data

    def parse_vmatrix(self, d):
        """Vmatrix class:dV"""

        pmatrix_data = '\\begin{vmatrix}%s\\end{vmatrix}'
        param_data = []
        for sub_d in d.next().children('.fB:first > .eJ').items():
            children_data = []
            for child_d in sub_d('.eJ > .eH').items():
                children_data.append(self.parse_element(child_d))
            param_data.append('&'.join(children_data))

        self.skip_ele = 2
        return pmatrix_data % '\\\\'.join(param_data)


if __name__ == '__main__':
    parser = AftQuestion(PyQuery(sys.argv[1]))
    print(parser.parse_element())
