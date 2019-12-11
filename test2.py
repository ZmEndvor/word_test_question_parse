# -*- coding: UTF-8 -*-
# @Author ：Jerrmy_Z
# @Time ：2019/11/19 15:22

import re


x = """
41. A. leave 			B. fail 			C. appear 			D. rise
42. A. cooling 		B. beating 		C. warming 			D. heating
43. A. helpful 		B. harmful 		C. useful 			D. careful 
44. A. taken in 		B. given off 		C. given away  		D. taken out
45. A. effects 			B. changes 		C. plans 				D. chances 
46. A. rescued 		B. destroyed 		C. cured 				D. improved 
47. A. recycled 		B. buried 		C. solved 			D. promised 
48. A. bag 			B. can 			C. bottle 				D. waste
49. A. interest 		B. benefit 		C. nature 			D. belief
50. A. influence 		B. fashion 		C. trend 				D. pollution
51. A. bedroom 		B. plant 			C. kitchen 			D. office
"""

y = """<b>"""
# num = re.compile(r'\d+\.').findall(x)
# print(num)
# l = re.compile(r'([A-Z]\.\s\S+|[A-Z][．|\.]\S+)').findall(x)
# print(l)

# answer = re.compile(r'答案(\s\S)+').findall(y)
# print(answer)

# sourceText = re.compile(r'([\[|\(|（]\S+[\]|\)|）]<\/?.*?>|[\[|\(|\（]\S+[\]|\)|\）])').findall(y)
# if sourceText:
#     if len(sourceText[0]) > 1 and sourceText[0][1:3] not in ["多选"]:
#         sourceText_label = re.compile(r'<(.*?)>').findall(sourceText[0])
#         if sourceText_label:
#             sourceText[0] = '<' + sourceText_label[0].replace('/', '') + '>' + sourceText[0]
#         print(sourceText[0])

# 选项：通过A-Z以及.匹配内容多次得到选项以及内容，最后通过切片将选项与选项内容分离为option与content

from collections import Counter
# options = re.compile(r'(?<=[A-Z])[^A-Z]+').findall(y)

# options = re.compile(r'([A-Z][^A-Z]+)').findall(x)
# print(options)
# opts = re.compile(r'[A-Z]').findall(x)
# c = Counter(opts)
# for i in range(0, len(options), len(c)):
#     print(options[i:i+len(c)])
# for opt in options:
#     if opt:
#         option = {"option": opt[0], "content": opt[2:]}
#         if 'options' not in c:
#             c['options'] = [option]
#         else:
#             c['options'].append(option)
# ct = re.compile(r'[]|)|】](\S+[\n|\S].*?[^A-Z])').findall(y)
# ct1 = re.compile(r'[a-zA-Z]+\s\S+[^A-Z]').findall(y)
# print(ct)
# print(ct1)

# p = re.split(r'\d+[．|.\n]', y)
# print(p)
# for i in p:
#     print(1, i)
# print(p[1])
# h = """24. Some countries that hold a negative attitude toward the Initiative mainly doubt its__________.
#    A. intention        B mystery     C power    D potential .
#
# """
#
#
# options = re.compile(r'[A-F][.|．|\s][\s\S]+').findall(h)
# opts = re.compile(r'[A-Z][．|\.|\s]').findall(h)
# print(options)
# print(opts)
import keyboard

# u = """
# <b>（</b><b>2019</b><b>年新课标卷</b><b>Ⅰ</b><b>·27</b><b>）</b>明中后期，大运河流经的东昌府是山东 最重要的棉花产区，所产棉花多由江淮商人坐地收揽，沿运河运至江南，而后返销棉布。这一现象产生的主要因素是\\xa0\\nA．交通方式 的变革 B．土地制度的调整 C．货币制度的改变 D．地区经济的差异\\n答案 D\\n解析 本题考查的是明朝商业发展特点。题干材料说的 意思是，北方所产棉花被贩运到江南，加工成布匹后，再返销到北方。结合基础知识可知，南宋时经济重心南移完成，江南农业手工业的发展超越北方；元朝时，棉纺织专家黄道婆的发明和推广先进的棉纺织技术，使江南棉纺织业迅速发展；明朝时期，地区经济差异造成了长途贩运贸易的兴盛。综上可以推知，北方种植棉花，但棉纺织技术比较落后，棉花被贩运到，为江南发达的棉纺织业提供了原料；江南利用先进的棉纺织技术，将北方贩运而来的棉花加工布匹，再返销北方。简言之，造成这种区域分工的主要原因，就是南北方经济差异造成的。故D项为正确答案。A项，不符合史实，明朝时期，交通方式没有什么大的变革，此时的交通方式还是传统的牛马拉车和船运；不符合逻辑推理，交通方式变革与棉花南运、棉布返销北方没有必然的因果关系。故错误。B项，不符合史实和逻辑推理，明中后期，土地制 度没有什么调整，还是君主、地主和自耕农土地所有制三种形式，地主土地私有制居支配地位也没有能改变；即使调整，与题干所述现象也没有逻辑关系。故错误。C项，不符合逻辑推理，货币制度改变与因地区差异造成题干所述现象没有必然的逻辑因果关系，故错误。
# """
# n = re.compile(r'解析([\s\S]+)').findall(u)
# print(n)


def _options_result(i, li):
    o = re.compile(r'([A-F][\.|．][\s\S]+)[A-F][\.|．]').findall(i)
    li.extend(o)
    return li if not o else _options_result(o[0], li)


i = """
3．（2019年北京卷·12）在中国新疆乌鲁木齐南山矿区以及俄罗斯阿尔泰山北麓等地，出土了公元前7～前5世纪楚国生产的风鸟纹刺绣丝绸。据此可以判断 
A．东周时期丝织品做工精良，远播西域地区B．楚国是中西交通起点，楚文化有明显西域特征
C．汉代丝路开通之前，中原与西域没有交往D．东周时期楚国与西域交流广泛，生活方式趋同 
"""
# options = re.compile(r'[A-F][\.|．].*[^A-F]').findall(i)
# new_options = []
# for i in options:
#     old_options = [i]
#     k = _options_result(i, old_options)
#     k.reverse()
#     for item, j in enumerate(k):
#         if item == 0:
#             new_options.append(j)
#         else:
#             new_options.append(k[-1][len(k[item - 1]):len(j)])
# print(new_options)

# p = '(1)0.4 s\u3000\u3000(2)<i>L</i>≥\n'
# j = re.compile(r'([\(|\（]\d+[\)|\）])').findall(p)
# h = re.split(r'([\(|\（]\d+[\)|\）])', p)
# for item, i in enumerate(h):
#     if i and re.compile(r'^([\(|\（]\d+[\)|\）])').findall(i):
#         h[item] = "".join(h[item:item+2])
#         h.pop(item+1)
# print(h)

s = ['']
print(s[0])
