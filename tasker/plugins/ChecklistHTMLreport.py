"""
Checklist HTML Reprot

Brute force get the checklists and produce an HTML report

"""

import logging
import pathlib
import tempfile
import os

try:
    from lxml import etree as ET
except ImportError:
    import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
CHECKLISTS = HERE / 'checklists'


def table_checklist(xmlpath):
    node = ET.parse(str(xmlpath))
    template = node.find('_template')
    print(node)
    t = ET.Element('table', border="1")
    thead = ET.SubElement(t, 'thead')
    tr = ET.SubElement(thead, 'tr')
    ET.SubElement(tr, 'th').text = ""
    tr2 = ET.SubElement(thead, 'tr')
    ET.SubElement(tr2, 'th').text = "Name"
    for group in template.findall('group'):
        cols = len(group.findall('subgroup'))
        th = ET.SubElement(tr, 'th', colspan="%d" % cols)
        th.text = group.get('name')
        for subgroup in group.findall('subgroup'):
            cell = ET.SubElement(tr2, 'th')
            cell.text = subgroup.get('name')
    tbody = ET.SubElement(t, 'tbody')

    for instance in node.findall('instance'):
        row = ET.SubElement(tbody, 'tr')
        ET.SubElement(row, 'td').text = instance.get('id')
    return t


if __name__ == '__main__':

    html = ET.Element('html')
    body = ET.SubElement(html, 'body')
    for fname in CHECKLISTS.glob("*.xml"):
        h = ET.SubElement(body, 'h1')
        h.text = fname.stem
        logging.debug('Loading %s', fname)
        body.append(table_checklist(fname))

    fp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    fp.write(ET.tostring(html))
    fp.close()
    print(fp.name)
    os.startfile(fp.name)
