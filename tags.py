
from Autodesk.Revit.DB import IndependentTag, Reference, TagMode, TagOrientation

def tag_element(doc, view, elem, symbol=None):
    try:
        loc=getattr(elem,"Location",None); pt=getattr(loc,"Point",None)
        if not pt: return False
        tag=IndependentTag.Create(doc, view.Id, Reference(elem), False,
                                  TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, pt)
        if symbol:
            try: tag.ChangeTypeId(symbol.Id)
            except: pass
        return True
    except: return False
