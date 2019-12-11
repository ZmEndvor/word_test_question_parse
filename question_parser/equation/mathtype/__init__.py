from docx.oxml import register_element_cls, nsmap

from question_parser.equation.mathtype.docx_ext import CT_OBJECT, CT_OLEOBJECT, CT_R2, CT_OMath, CT_OMathPara

nsmap['o'] = ('urn:schemas-microsoft-com:office:office')
nsmap['m'] = ('http://schemas.openxmlformats.org/officeDocument/2006/math')
nsmap['v']=('urn:schemas-microsoft-com:vml')
register_element_cls('w:object', CT_OBJECT)
register_element_cls('o:OLEObject', CT_OLEOBJECT)
register_element_cls('w:r', CT_R2)
register_element_cls('m:oMathPara', CT_OMathPara)
register_element_cls('m:oMath', CT_OMath)
