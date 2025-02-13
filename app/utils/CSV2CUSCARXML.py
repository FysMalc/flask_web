import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom
from .find_key import find_key
from datetime import datetime

def format_value(value):
    """Convert numeric values to appropriate format without unnecessary decimal places"""
    if pd.isna(value):
        return ''
    if isinstance(value, (int, float)):
        # If it's a whole number, convert to int
        if value.is_integer():
            return str(int(value))
        # If it's a float, keep it as float
        return str(value)
    return str(value)


def generate_edi_from_cuscar(input_file, output_file, opr, VslID):
    # Get current date and time
    now = datetime.now()
    date_time_str = now.strftime('%Y%m%d%H%M')

    # Create the root element
    output_root = ET.Element("edi:blTransactions", attrib={"xmlns:edi": "http://www.navis.com/argo"})

    # Read the input Excel file
    df = pd.read_excel(input_file, engine='openpyxl')

    # Convert DataFrame to dictionary format
    for index, row in df.iterrows():
        row = row.to_dict()

        # Use the find_key function to get the correct keys
        seq = int(row[find_key(row, 'SEQ')])
        format_seq = format(seq, '04d')
        sequence = date_time_str + format_seq

        tran_dict = {
            "edi:msgClass": "MANIFEST",
            "edi:msgTypeId": "CUSCAR",
            "edi:msgFunction": "O",
            "edi:msgReferenceNbr": sequence
        }
        blTransaction = ET.SubElement(output_root, "edi:blTransaction", attrib=tran_dict)

        # Create edi:Interchange element
        inter_dict = {
            "edi:Date": now.strftime('%Y-%m-%d'),
            "edi:Time": now.strftime('%H:%M:%S'),
            "edi:InterchangeNumber": sequence
        }
        ET.SubElement(blTransaction, "edi:Interchange", attrib=inter_dict)

        # Create edi:blNbr element
        bl_key = find_key(row, 'BL')
        if pd.notna(row[bl_key]):
            ET.SubElement(blTransaction, "edi:ediBillOfLading",
                          attrib={'edi:blNbr': format_value(row[bl_key])})

        # Create the edi:ediVesselVisit element
        vsl_dict = {
            "edi:vesselId": VslID,
            "edi:vesselIdConvention": "VISITREF"
        }
        ediVesselVisit = ET.SubElement(blTransaction, "edi:ediVesselVisit", attrib=vsl_dict)
        ET.SubElement(ediVesselVisit, "edi:shippingLine",
                      attrib={"edi:shippingLineCode": opr})

        # Create the edi:shipper element
        shipper_key = find_key(row, 'SHIPPER')
        if pd.notna(row[shipper_key]):
            ET.SubElement(blTransaction, 'edi:shipper',
                          attrib={"edi:shipperName": format_value(row[shipper_key])})

        # Create the edi:consignee element
        consignee_key = find_key(row, 'CONSIGNEE')
        if pd.notna(row[consignee_key]):
            ET.SubElement(blTransaction, 'edi:consignee',
                          attrib={"edi:consigneeName": format_value(row[consignee_key]).strip('\n')})

        ediBlEquipment = ET.SubElement(blTransaction, 'edi:ediBlEquipment')

        ediCont_attr = {
            'edi:containerNbr': format_value(row[find_key(row, 'CNTR_NO')]),
        }

        ediContainer = ET.SubElement(ediBlEquipment, "edi:ediContainer", attrib=ediCont_attr)

        commodity_key = find_key(row, 'COMMODITY DETAIL')
        if pd.notna(row[commodity_key]):
            flex_field = ET.SubElement(ediBlEquipment, "edi:ediFlexFields")
            ET.SubElement(flex_field, "edi:ufvFlexString09").text = format_value(row[commodity_key])

    # Clean None values
    clean_none_values(output_root)

    # Create the XML tree and write it to the output XML file
    xml_str = ET.tostring(output_root, encoding='utf-8', method='xml')
    dom = xml.dom.minidom.parseString(xml_str)
    pretty_xml_str = dom.toprettyxml(indent="    ")

    with open(output_file, "w", encoding='UTF-8') as output_file:
        output_file.write(pretty_xml_str)


def clean_none_values(element):
    for attr, value in list(element.attrib.items()):
        if value is None:
            element.attrib[attr] = ''
    for child in element:
        if child.text is None:
            child.text = ''
        if child.tail is None:
            child.tail = ''
        clean_none_values(child)


if __name__ == "__main__":
    input_file = input("Input Excel file: ")
    output_file = input("Output XML file: ")
    opr = input("Operator: ")
    VslID = input("Vessel Visit ID: ")

    generate_edi_from_cuscar(input_file, output_file, opr, VslID)
