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


def group_containers_by_booking(path):
    """
    Group containers by booking number and provide container details.

    Returns:
    dict: A dictionary with booking details including containers and count
    """
    # Read the Excel file
    df = pd.read_excel(path, engine='openpyxl')

    for index, row in df.iterrows():
        size_key = find_key(row, 'SIZE')
        booking_key = find_key(row, 'Booking')
        ops_key = find_key(row, 'OPS (3 LETTERS)')
        pol_key = find_key(row, 'POL (6 LETTERS)')
        pod_key = find_key(row, 'POD (6 LETTERS)')

    # Remove rows with empty booking numbers
    df_with_booking = df[df[booking_key].notna()]

    # Booking groups to store results
    booking_groups = {}

    # Group containers by booking number
    for booking in df_with_booking[booking_key].unique():
        # Find all containers for this booking
        booking_containers = df[df[booking_key] == booking]

        # Validate OPS, POL, POD consistency
        ops_values = booking_containers[ops_key].unique()
        pol_values = booking_containers[pol_key].unique()
        pod_values = booking_containers[pod_key].unique()

        if len(ops_values) > 1:
            raise ValueError(f"Inconsistent OPS values for Booking {booking}: {ops_values}")
        if len(pol_values) > 1:
            raise ValueError(f"Inconsistent POL values for Booking {booking}: {pol_values}")
        if len(pod_values) > 1:
            raise ValueError(f"Inconsistent POD values for Booking {booking}: {pod_values}")


        # Group containers by size
        size_counts = booking_containers[size_key].value_counts().to_dict()
        unique_sizes = booking_containers[size_key].unique().tolist()

        # Prepare the booking group summary
        booking_groups[booking] = {
            'OPS': ops_values[0],
            'POL': pol_values[0],
            'POD': pod_values[0],
            'container_count': len(booking_containers),
            'size_counts': size_counts,
            'unique_sizes': unique_sizes
        }

    return booking_groups


def generate_edi_from_coparn(input_file, output_file, opr, VslID):
    # Get current date and time
    now = datetime.now()
    date_time_str = now.strftime('%Y%m%d%H%M')

    # Create the root element
    output_root = ET.Element("edi:bookingTransactions", attrib={"xmlns:edi": "http://www.navis.com/argo"})

    # Read the input Excel file
    df = pd.read_excel(input_file, engine='openpyxl')
    grouped_booking = group_containers_by_booking(input_file)

    for index, (key, value) in enumerate(grouped_booking.items()):
        format_seq = format(index, '04d')
        sequence = date_time_str + format_seq

        tran_dict = {
            "edi:msgClass": "BOOKING",
            "edi:msgTypeId": "coparn",
            "edi:msgFunction": "O",
            "edi:msgReferenceNbr": sequence
        }

        bookingTransaction = ET.SubElement(output_root, "edi:bookingTransaction", attrib=tran_dict)

        inter_dict = {
            "edi:Date": now.strftime('%Y-%m-%d'),
            "edi:Time": now.strftime('%H:%M:%S'),
            "edi:InterchangeNumber": sequence
        }
        ET.SubElement(bookingTransaction, "edi:Interchange", attrib=inter_dict)

        vsl_dict = {
            "edi:vesselId": VslID,
            "edi:vesselIdConvention": "VISITREF"
        }
        ediVesselVisit = ET.SubElement(bookingTransaction, "edi:ediVesselVisit", attrib=vsl_dict)
        ET.SubElement(ediVesselVisit, "edi:shippingLine",
                      attrib={"edi:shippingLineCode": opr})

        ET.SubElement(bookingTransaction, 'edi:ediBooking',
                      attrib = {"edi:bookingNbr": format_value(key)})

        ET.SubElement(bookingTransaction, 'edi:loadPort',
                      attrib = {"edi:portId": grouped_booking[key]['POL']})
        ET.SubElement(bookingTransaction, 'edi:Destination',
                      attrib = {"edi:Destination": grouped_booking[key]['POD']})


        for size in grouped_booking[key]['size_counts']:
            bookingItem = ET.SubElement(bookingTransaction, 'edi:ediBookingItem')

            ET.SubElement(bookingItem, 'edi:quantity').text = format_value(grouped_booking[key]['size_counts'][size])
            ET.SubElement(bookingItem, 'edi:ISOcode').text = format_value(size)

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

    generate_edi_from_coparn(input_file, output_file, opr, VslID)
