import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom
from .utils import *
from datetime import datetime

def generate_edi_from_load(input_file, output_file, opr, VslID):
    # Get current date and time
    now = datetime.now()
    date_time_str = now.strftime('%Y%m%d%H%M')

    # Create the root element
    output_root = ET.Element("edi:loadlistTransactions", attrib={"xmlns:edi": "http://www.navis.com/argo"})

    # Read the input Excel file - convert_float=False to preserve number formatting
    df = pd.read_excel(input_file, engine='openpyxl', dtype=str)
    first_row = df.iloc[0].to_dict() if not df.empty else {}

    key_map = {
        'SEQ': find_key(first_row, 'SEQ') or raise_missing_column('SEQ'),
        'SIZE': find_key(first_row, 'SIZE') or raise_missing_column('SIZE'),
        'BOOKING': find_key(first_row, 'Booking') or raise_missing_column('Booking'),
        'SEAL1': find_key(first_row, 'SEAL1') or raise_missing_column('SEAL1'),
        'SEAL2': find_key(first_row, 'SEAL2') or raise_missing_column('SEAL2'),
        'SEAL3': find_key(first_row, 'SEAL3') or raise_missing_column('SEAL3'),
        'SEAL4': find_key(first_row, 'SEAL4') or raise_missing_column('SEAL4'),
        'CNTR_NO': find_key(first_row, 'CNTR_NO') or raise_missing_column('CNTR_NO'),
        'WEIGHT': find_key(first_row, 'Weight (kg)') or raise_missing_column('Weight (kg)'),
        'VGM': find_key(first_row, 'VGM(kg)') or raise_missing_column('VGM(kg)'),
        'FREIGHT_KIND': find_key(first_row, 'FREIGHT KIND (F/E)') or raise_missing_column('FREIGHT KIND (F/E)'),
        'OPS': find_key(first_row, 'OPS (3 LETTERS)') or raise_missing_column('OPS (3 LETTERS)'),
        'POL': find_key(first_row, 'POL (5 LETTERS)') or raise_missing_column('POL (5 LETTERS)'),
        'POD': find_key(first_row, 'POD (5 LETTERS)') or raise_missing_column('POD (5 LETTERS)'),
        'FPOD': find_key(first_row, 'FPOD (IF ANY)') or raise_missing_column('FPOD (IF ANY)'),
        'DG': find_key(first_row, 'DG (Y/N)') or raise_missing_column('DG (Y/N)'),
        'IMO': find_key(first_row, 'IMO') or raise_missing_column('IMO'),
        'UNNO': find_key(first_row, 'UNNO') or raise_missing_column('UNNO'),
        'RF': find_key(first_row, 'RF (Y/N)') or raise_missing_column('RF (Y/N)'),
        'VENT_VALUE': find_key(first_row, 'VENTILATION (VALUE)') or raise_missing_column('VENTILATION (VALUE)'),
        'VENT_UNIT': find_key(first_row, 'VENTILATION (UNIT)') or raise_missing_column('VENTILATION (UNIT)'),
        'TEMP': find_key(first_row, 'TEMP. (\'C)') or raise_missing_column('TEMP. (\'C)'),
        'OOG': find_key(first_row, 'OOG') or raise_missing_column('OOG'),
        'OVER_HEIGHT': find_key(first_row, 'OVER HEIGHT (CM)') or raise_missing_column('OVER HEIGHT (CM)'),
        'OVER_LEFT': find_key(first_row, 'OVER LEFT (CM)') or raise_missing_column('OVER LEFT (CM)'),
        'OVER_RIGHT': find_key(first_row, 'OVER RIGHT (CM)') or raise_missing_column('OVER RIGHT (CM)'),
        'BUNDLE': find_key(first_row, 'BUNDLE (Y/N)') or raise_missing_column('BUNDLE (Y/N)'),
        'BUNDLE2': find_key(first_row, 'BUNDLE NO.2') or raise_missing_column('BUNDLE NO.2'),
        'BUNDLE3': find_key(first_row, 'BUNDLE NO.3') or raise_missing_column('BUNDLE NO.3'),
        'BUNDLE4': find_key(first_row, 'BUNDLE NO.4') or raise_missing_column('BUNDLE NO.4'),
        'SPECIAL_STOW': find_key(first_row, 'SPECIAL STOW (CODE)') or raise_missing_column('SPECIAL STOW (CODE)'),
        'COMMODITY': find_key(first_row, 'COMMODITY DETAIL') or raise_missing_column('COMMODITY DETAIL'),
    }

    # Convert DataFrame to dictionary format similar to CSV reader
    for index, row in df.iterrows():
        try:
            row = row.to_dict()

            # Create the loadListTransaction element
            seq = int(row[key_map['SEQ']])
            format_seq = format(seq, '04d')
            sequence = date_time_str + format_seq
            tran_dict = {
                "edi:msgClass": "LOADLIST",
                "edi:msgTypeId": "COPRAR",
                "edi:msgFunction": "O",
                "edi:msgReferenceNbr": sequence
            }
            loadListTransaction = ET.SubElement(output_root, "edi:loadlistTransaction", attrib=tran_dict)

            # Create the Interchange element
            inter_dict = {
                "edi:Date": now.strftime('%Y-%m-%d'),
                "edi:Time": now.strftime('%H:%M:%S'),
                "edi:InterchangeNumber": sequence
            }
            ET.SubElement(loadListTransaction, "edi:Interchange", attrib=inter_dict)

            # Create the outBoundVesselVisit element
            vsl_dict = {
                "edi:vesselId": VslID,
                "edi:vesselIdConvention": "VISITREF"
            }
            ediOutboundVesselVisit = ET.SubElement(loadListTransaction, "edi:ediOutboundVesselVisit", attrib=vsl_dict)
            shippingLine = ET.SubElement(ediOutboundVesselVisit, "edi:shippingLine",
                                         attrib={"edi:shippingLineCode": opr})

            # Create the Category element
            ET.SubElement(loadListTransaction, "edi:category").text = "EXPRT"

            # Create the FreightKind element
            freight_kind = "FCL" if str(row[key_map['FREIGHT_KIND']]).strip().upper() == "F" or str(row[key_map['FREIGHT_KIND']]).strip().upper() == "FCL" else "MTY"
            ET.SubElement(loadListTransaction, "edi:freightKind").text = freight_kind

            # Create the ContainerID element
            ET.SubElement(loadListTransaction, "edi:containerId").text = row[key_map['CNTR_NO']].strip()

            # Create the ContainerType element
            ET.SubElement(loadListTransaction, "edi:containerType").text = row[key_map['SIZE']].strip()

            # Create the ContainerOperator element
            ET.SubElement(loadListTransaction, "edi:containerOperator",
                          attrib={"edi:operator": row[key_map['OPS']].strip()})

            # Create the orderNbr element
            if pd.notna(row[key_map['BOOKING']]):
                ET.SubElement(loadListTransaction, 'edi:orderNbr').text = row[key_map['BOOKING']].strip()

            # Create the ExportRouting element
            import_routing = ET.SubElement(loadListTransaction, "edi:exportRouting")

            if pd.notna(row[key_map['POL']]):
                ET.SubElement(import_routing, "edi:loadPort",
                              attrib={"edi:portId": str(row[key_map['POL']]).strip()})

            if pd.notna(row[key_map['POD']]):
                ET.SubElement(import_routing, "edi:dischargePort1",
                              attrib={"edi:portId": row[key_map['POD']].strip()})

            if pd.notna(row[key_map['FPOD']]):
                ET.SubElement(import_routing, "edi:dischargePort2",
                              attrib={"edi:portId": row[key_map['FPOD']].strip()})

            # Create the Weight element
            if pd.notna(row[key_map['WEIGHT']]):
                ET.SubElement(loadListTransaction, "edi:grossWeight",
                              attrib={
                                  "edi:wtValue": row[key_map['WEIGHT']].strip(),
                                  "edi:wtUnit": "KG"
                                }
                              )

            # Create the VGM element
            if pd.notna(row[key_map['VGM']]):
                ET.SubElement(loadListTransaction, "edi:verifiedGrossMass",
                              attrib={"edi:verifiedGrossWt": row[key_map['VGM']].strip(),
                                      "edi:verifiedGrossWtUnit": "KG"})

            # Create the OOG element
            if row[key_map['OOG']] == "Y":
                ET.SubElement(loadListTransaction, "edi:oogDimensions", attrib={
                    "edi:leftUnit": "CM",
                    "edi:left": row[key_map['OVER_LEFT']].strip(),
                    "edi:topUnit": "CM",
                    "edi:top": row[key_map['OVER_HEIGHT']].strip(),
                    "edi:rightUnit": "CM",
                    "edi:right": row[key_map['OVER_RIGHT']].strip()
                })

            # Create the RF element
            if row[key_map['RF']] == "Y":
                ET.SubElement(loadListTransaction, "edi:temperature", attrib={
                    "edi:preferredTemperatureUnit": "C",
                    "edi:preferredTemperature": row[key_map['TEMP']].strip()
                })

            # Create SealNbr element
            for i in range(1, 5):
                if key_map[f"SEAL{i}"]:
                    seal_key = key_map[f"SEAL{i}"]
                    if pd.notna(row[seal_key]):
                        ET.SubElement(loadListTransaction, f"edi:sealNbr{i}").text = row[seal_key].strip()

            commo_dict = {}
            # Create the Commodity element
            if pd.notna(row[key_map['COMMODITY']]):
                commo_dict["edi:commodityCode"] = row[key_map['COMMODITY']].strip()
                commo_dict["edi:commodityDescription"] = row[key_map['COMMODITY']].strip()

            if commo_dict:
                ET.SubElement(loadListTransaction, "edi:ediCommodity", attrib=commo_dict)

            # Create the Dangerous Goods element
            if row[key_map['DG']] == "Y":
                ET.SubElement(loadListTransaction, "edi:ediHazard", attrib={
                    "edi:imdgClass": row[key_map['IMO']].strip(),
                    "edi:unNbr": row[key_map['UNNO']].strip()
                })

            # Create the Ventilation element
            if pd.notna(row[key_map['VENT_VALUE']]):
                attribs = {"edi:rfVentRequired": row[key_map['VENT_VALUE']].strip()}

                if pd.notna(row[key_map["VENT_UNIT"]]):
                    attribs['edi:rfVentRequiredUnit'] = row[key_map['VENT_UNIT']].strip()

                ET.SubElement(loadListTransaction, "edi:ediReeferRqmnts", attrib=attribs)

            # Create the Special Stow element
            if pd.notna(row[key_map['SPECIAL_STOW']]) and row[key_map['SPECIAL_STOW']].strip() != "":
                ET.SubElement(loadListTransaction, "edi:containerHandlingInstructions").text = row[key_map['SPECIAL_STOW']].strip

            # Create the Bundle element
            if row[key_map['BUNDLE']] == "Y":
                for i in range(2, 5):
                    if pd.notna(row[key_map[f'BUNDLE{i}']]):
                        ET.SubElement(loadListTransaction, "edi:ediAttachedEquipment", attrib={
                            "edi:attachedEquipmentClass": "CONTAINER",
                            "edi:attachedEquipmentNbr": row[key_map[f'BUNDLE{i}']].strip(),
                            "edi:attachedEquipmentType": row[key_map['SIZE']].strip()
                        })
        except Exception as e:
            raise ValueError(f"Error processing row {index + 1}: {str(e)}")
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

    generate_edi_from_load(input_file, output_file, opr, VslID)
