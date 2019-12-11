from docx.opc.oxml import BaseOxmlElement
from docx.oxml import CT_R
from docx.oxml.simpletypes import BaseStringType
from docx.oxml.xmlchemy import RequiredAttribute, ZeroOrOne


class CT_R2(CT_R):
    embed_object = ZeroOrOne('w:object')
    pict = ZeroOrOne('w:pict')


class CT_OBJECT(BaseOxmlElement):
    """
    ``w:object``
    """
    _tag_seq = (
        'v:shapetype', 'v:shape', 'o:OLEObject'
    )
    shapetype = ZeroOrOne("v:shapetype", successors=_tag_seq[1:])
    shape = ZeroOrOne("v:shape", successors=_tag_seq[2:])
    oleobject = ZeroOrOne("o:OLEObject", successors=_tag_seq[3:])
    del _tag_seq


class CT_OLEOBJECT(BaseOxmlElement):
    """
    OLE Object解析元素

    ``<o:OLEObject>``
    """

    rid = RequiredAttribute('r:id', BaseStringType)


class CT_OMath(BaseOxmlElement):
    """
    OMath Object解析
    `<m:oMath>`
    """


class CT_OMathPara(BaseOxmlElement):
    """
    <m:oMathPara>
    """
