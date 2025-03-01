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
        if isinstance(value, int):
            return str(int(value))
        # If it's a float, keep it as float
        return str(value)
    return str(value)

def generate_edi_from_discharge(input_file, output_file, opr, VslID):
    # Get current date and time
    now = datetime.now()
    date_time_str = now.strftime('%Y%m%d%H%M')

    # Create the root element
    output_root = ET.Element("edi:dischlistTransactions", attrib={"xmlns:edi": "http://www.navis.com/argo"})

    # Read the input Excel file
    df = pd.read_excel(input_file, engine='openpyxl')

    # Convert DataFrame to dictionary format
    for index, row in df.iterrows():
        row = row.to_dict()
        sequence = ''
        # Create the dischargeListTransaction element
        if find_key(row, 'SEQ'):
            if format_value(row['SEQ']):
                seq = int(row[find_key(row, 'SEQ')])
                format_seq = format(seq, '04d')
                sequence = date_time_str + format_seq

        tran_dict = {
            "edi:msgClass": "DISCHLIST",
            "edi:msgTypeId": "COPRAR",
            "edi:msgFunction": "O",
            "edi:msgReferenceNbr": ""
        }
        dischargeListTransaction = ET.SubElement(output_root, "edi:dischlistTransaction", attrib=tran_dict)

        # Create the Interchange element
        inter_dict = {
            "edi:Date": now.strftime('%Y-%m-%d'),
            "edi:Time": now.strftime('%H:%M:%S'),
            "edi:InterchangeNumber": sequence
        }
        ET.SubElement(dischargeListTransaction, "edi:Interchange", attrib=inter_dict)

        # Create the billOfLading element
        bl_key = find_key(row, 'BL')
        if pd.notna(row[bl_key]):
            ET.SubElement(dischargeListTransaction, 'edi:ediBillOfLading',
                                         attrib={'edi:blNbr': format_value(row[bl_key])})

        # Create the InboundVesselVisit element
        vsl_dict = {
            "edi:vesselId": VslID,
            "edi:vesselIdConvention": "VISITREF"
        }
        ediInboundVesselVisit = ET.SubElement(dischargeListTransaction, "edi:ediInboundVesselVisit", attrib=vsl_dict)
        shippingLine = ET.SubElement(ediInboundVesselVisit, "edi:shippingLine",
                                     attrib={"edi:shippingLineCode": opr})

        # Create the Category element
        ET.SubElement(dischargeListTransaction, "edi:category").text = "IMPRT"

        # Create the FreightKind element
        freight_kind = "FCL" if row[find_key(row, 'FREIGHT KIND (F/E)')] == "F"  or row[find_key(row, 'FREIGHT KIND (F/E)')] == "FCL" else "MTY"
        ET.SubElement(dischargeListTransaction, "edi:freightKind").text = freight_kind

        # Create the ContainerID element
        ET.SubElement(dischargeListTransaction, "edi:containerId").text = format_value(row[find_key(row, 'CNTR_NO')])

        # Create the ContainerType element
        ET.SubElement(dischargeListTransaction, "edi:containerType").text = format_value(row[find_key(row, 'SIZE')])

        # Create the Cell position element
        if pd.notna(row[find_key(row, 'CELL')]):
            ET.SubElement(dischargeListTransaction, "edi:stowageCellPosition").text = format_value(
                row[find_key(row, 'CELL')])

        # Create the ContainerOperator element

        ET.SubElement(dischargeListTransaction, "edi:containerOperator",
                      attrib={"edi:operator": format_value(row[find_key(row, 'OPS (3 LETTERS)')])})


        # Create the ImportRouting element
        import_routing = ET.SubElement(dischargeListTransaction, "edi:importRouting")
        if pd.notna(row[find_key(row, 'POL (5 LETTERS)')]):
            ET.SubElement(import_routing, "edi:loadPort",
                          attrib={"edi:portId": format_value(row[find_key(row, 'POL (5 LETTERS)')])})

        if pd.notna(row[find_key(row, 'POD (5 LETTERS)')]):
            ET.SubElement(import_routing, "edi:dischargePort1",
                          attrib={"edi:portId": format_value(row[find_key(row, 'POD (5 LETTERS)')])})

        # Check if FPOD not null then add in ImportRouting
        fpod_key = find_key(row, 'FPOD (IF ANY)')
        if pd.notna(row[fpod_key]):
            ET.SubElement(import_routing, "edi:dischargePort2",
                          attrib={"edi:portId": format_value(row[fpod_key])})

        # Create the Weight element
        if pd.notna(row[find_key(row, 'Weight (kg)')]):
            ET.SubElement(dischargeListTransaction, "edi:grossWeight",
                          attrib={"edi:wtUnit": "KG",
                                  "edi:wtValue": format_value(row[find_key(row, 'Weight (kg)')])})

        # Create the VGM element
        if pd.notna(row[find_key(row, 'VGM(kg)')]):
            ET.SubElement(dischargeListTransaction, "edi:verifiedGrossMass",
                          attrib={"edi:verifiedGrossWt": format_value(row[find_key(row, 'VGM(kg)')]),
                                  "edi:verifiedGrossWtUnit": "KG"})

        # Create the OOG element
        if row[find_key(row, 'OOG')] == "Y":
            ET.SubElement(dischargeListTransaction, "edi:oogDimensions", attrib={
                "edi:leftUnit": "CM",
                "edi:left": format_value(row[find_key(row, 'OVER LEFT (CM)')]),
                "edi:topUnit": "CM",
                "edi:top": format_value(row[find_key(row, 'OVER HEIGHT (CM)')]),
                "edi:rightUnit": "CM",
                "edi:right": format_value(row[find_key(row, 'OVER RIGHT (CM)')])
            })

        # Create the RF element
        if row[find_key(row, 'RF (Y/N)')] == "Y":
            ET.SubElement(dischargeListTransaction, "edi:temperature", attrib={
                "edi:preferredTemperatureUnit": "C",
                "edi:preferredTemperature": format_value(row[find_key(row, 'TEMP. (\'C)')])
            })

        # Create SealNbr1 element
        if  find_key(row, 'SEAL1'):
            seal_key1 = find_key(row, 'SEAL1')
            if pd.notna(row[seal_key1]):
                ET.SubElement(dischargeListTransaction, "edi:sealNbr1").text = format_value(row[seal_key1])
        if  find_key(row, 'SEAL2'):
            seal_key2 = find_key(row, 'SEAL2')
            if pd.notna(row[seal_key2]):
                ET.SubElement(dischargeListTransaction, "edi:sealNbr2").text = format_value(row[seal_key2])
        if  find_key(row, 'SEAL3'):
            seal_key3 = find_key(row, 'SEAL3')
            if pd.notna(row[seal_key3]):
                ET.SubElement(dischargeListTransaction, "edi:sealNbr3").text = format_value(row[seal_key3])
        if  find_key(row, 'SEAL4'):
            seal_key4 = find_key(row, 'SEAL4')
            if pd.notna(row[seal_key4]):
                ET.SubElement(dischargeListTransaction, "edi:sealNbr4").text = format_value(row[seal_key4])

        # Create the Commodity element
        commo_key = find_key(row, 'COMMODITY DETAIL')
        if pd.notna(row[commo_key]):
            commo_field = ET.SubElement(dischargeListTransaction, "edi:ediCommodity", attrib= {
                "edi:commodityDescription": format_value(row[commo_key])
            })
            # ET.SubElement(flex_field, "edi:commodityDescription").text = format_value(row[commo_key])

        # Create the Ventilation element
        if find_key(row, 'VENTILATION (VALUE)'):
            ventilation_key = find_key(row, 'VENTILATION (VALUE)')
            if pd.notna(row[ventilation_key]):
                edi_commodity = ET.SubElement(dischargeListTransaction, 'edi:ediCommodity')
                if pd.notna(row[ventilation_key]):
                    ET.SubElement(edi_commodity, "commodityVentSettings", attrib={
                        "edi:unit": format_value(row[ventilation_key]),
                        "edi:value": format_value(row[find_key(row, 'VENTILATION (UNIT)')]),
                    })

        # Create the Dangerous Goods element
        if row[find_key(row, 'DG (Y/N)')] == "Y":
            ET.SubElement(dischargeListTransaction, "edi:ediHazard", attrib={
                "edi:imdgClass": format_value(row[find_key(row, 'IMO')]),
                "edi:unNbr": format_value(row[find_key(row, 'UNNO')])
            })

        # Create the Bundle element
        if row[find_key(row, 'BUNDLE (Y/N)')] == "Y":
            for i in range(2, 5):
                bundle_key = find_key(row, f'BUNDLE NO.{i}')
                if pd.notna(row[bundle_key]):
                    ET.SubElement(dischargeListTransaction, "edi:ediAttachedEquipment", attrib={
                        "edi:attachedEquipmentClass": "CONTAINER",
                        "edi:attachedEquipmentNbr": format_value(row[bundle_key]),
                        "edi:attachedEquipmentType": format_value(row[find_key(row, 'SIZE')])
                    })

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
    input_file = input("Input Excel file: ")  # Changed prompt to Excel
    output_file = input("Output XML file: ")
    opr = input("Operator: ")
    VslID = input("Vessel Visit ID: ")

    generate_edi_from_discharge(input_file, output_file, opr, VslID)
