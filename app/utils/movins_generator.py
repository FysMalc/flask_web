import pandas as pd
from datetime import datetime
import re
from pathlib import Path


class MovinsEdiGenerator:
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.measurement_configs = {
            'Weight': ('KGM', 'WT'),
            'OVER HEIGHT': ('CMT', '9'),
            'OVER LEFT': ('CMT', '8'),
            'OVER RIGHT': ('CMT', '7'),
            'TEMP': ('CEL', None)
        }
        self.chunk_size = 500
    def find_measurement_columns(self, df):
        """Find all measurement columns and their units"""
        columns = {}
        for base_name, (default_unit, _) in self.measurement_configs.items():
            pattern = f"{base_name}.*\\([^)]+\\)"
            matching_cols = [col for col in df.columns if re.match(pattern, col)]
            if matching_cols:
                unit = re.search(r'\(([^)]+)\)', matching_cols[0]).group(1)
            else:
                unit = default_unit
            columns[base_name] = (matching_cols[0] if matching_cols else None, unit)
        return columns

    @staticmethod
    def write_segment(file, segment, *fields):
        """Write EDI segment with proper formatting, handling nan values"""
        cleaned_fields = []
        for field in fields:
            if pd.isna(field) or field == 'nan':
                cleaned_fields.append('')
            else:
                cleaned_fields.append(str(field).strip())
        fields_str = '+'.join(cleaned_fields)
        file.write(f"{segment}+{fields_str}'\n")

    @staticmethod
    def format_location(location_code):
        """Format location segment"""
        if pd.isna(location_code) or location_code == 'nan':
            return ''
        return f"{location_code}:139:6"

    def write_header_segments(self, f, header_info, vessel_info):
        """Write EDI header segments"""
        current_datetime = datetime.now()
        current_date = current_datetime.strftime('%y%m%d')
        current_time = current_datetime.strftime('%H%M')

        sender = '' if pd.isna(header_info['SENDER']) else header_info['SENDER']
        msg_type_ver = '' if pd.isna(header_info['msg_type_ver']) else header_info['msg_type_ver']
        msg_type_release = '' if pd.isna(header_info['msg_type_release']) else header_info['msg_type_release']
        control_agency = '' if pd.isna(header_info['control_agency']) else header_info['control_agency']
        asso_assigned_code = '' if pd.isna(header_info['asso_assigned_code']) else header_info['asso_assigned_code']
        doc_no = '' if pd.isna(header_info['DOC NO.']) else str(header_info['DOC NO.'])
        MovinsEdiGenerator.write_segment(f, 'UNB', 'UNOA:2', sender, '', f"{current_date}:{current_time}", doc_no)
        MovinsEdiGenerator.write_segment(f, 'UNH', '1',
                                         f'MOVINS:{msg_type_ver}:{msg_type_release}:{control_agency}:{asso_assigned_code}')
        MovinsEdiGenerator.write_segment(f, 'BGM', '', current_datetime.strftime('%Y%m%d%H%M%S'), '9')
        MovinsEdiGenerator.write_segment(f, 'DTM', f"137:{current_date}{current_time}:201")

    def write_vessel_segments(self, f, vessel_info):
        """Write vessel-related segments"""
        current_datetime = datetime.now()
        current_date = current_datetime.strftime('%y%m%d')
        current_time = current_datetime.strftime('%H%M')

        # Create vessel identification string only if all components are present
        vessel_id = ''
        if not pd.isna(vessel_info['Carrier identification']):
            code_list = '' if pd.isna(vessel_info['Code list qualifier']) else vessel_info['Code list qualifier']
            resp_agency = '' if pd.isna(vessel_info['Code list responsible agency']) else vessel_info[
                'Code list responsible agency']
            vessel_id = f"{vessel_info['Carrier identification']}:{code_list}:{resp_agency}"

        # Create transport ID string only if all components are present
        transport_id = ''
        if not pd.isna(vessel_info['ID']):
            id_code_list = '' if pd.isna(vessel_info['Transport ID code list']) else vessel_info[
                'Transport ID code list']
            id_resp_agency = '' if pd.isna(vessel_info['Transport ID code list responsible agency']) else vessel_info[
                'Transport ID code list responsible agency']
            name = '' if pd.isna(vessel_info['NAME']) else vessel_info['NAME']
            transport_id = f"{vessel_info['ID']}:{id_code_list}:{id_resp_agency}:{name}"

        tdt_fields = [
            vessel_info['TRANSPORT STAGE QUALIFIER'] if not pd.isna(vessel_info['TRANSPORT STAGE QUALIFIER']) else '',
            vessel_info['CONVEYANCE REFERRENCE NUMBER'] if not pd.isna(
                vessel_info['CONVEYANCE REFERRENCE NUMBER']) else '',
            vessel_info['MODE OF TRANSPORT'] if not pd.isna(vessel_info['MODE OF TRANSPORT']) else '',
            vessel_info['TRANSPORT MEANS'] if not pd.isna(vessel_info['TRANSPORT MEANS']) else '',
            vessel_id,
            '',
            '',
            transport_id
        ]
        MovinsEdiGenerator.write_segment(f, 'TDT', *tdt_fields)

        if not pd.isna(vessel_info['Place of Departure']):
            MovinsEdiGenerator.write_segment(f, 'LOC', '5', self.format_location(vessel_info['Place of Departure']))
        if not pd.isna(vessel_info['NPOC']):
            MovinsEdiGenerator.write_segment(f, 'LOC', '61', self.format_location(vessel_info['NPOC']))

        MovinsEdiGenerator.write_segment(f, 'DTM', f'133:{current_date}{current_time}:201')

    def write_container_segments(self, f, row, measurement_cols):
        """Write container-related segments"""
        MovinsEdiGenerator.write_segment(f, 'HAN', 'LOA')

        cell = '' if pd.isna(row['CELL']) else row['CELL']
        MovinsEdiGenerator.write_segment(f, 'LOC', '147', f"{cell}::5")

        # Weight measurement
        weight_col, weight_unit = measurement_cols['Weight']
        if weight_col and not pd.isna(row[weight_col]):
            MovinsEdiGenerator.write_segment(f, 'MEA', 'WT', '', f"{weight_unit}:{int(row[weight_col])}")

        # OOG measurements
        if not pd.isna(row.get('OOG')):
            for measure_type in ['OVER HEIGHT', 'OVER LEFT', 'OVER RIGHT']:
                col, unit = measurement_cols[measure_type]
                if col and not pd.isna(row[col]):
                    dim_code = self.measurement_configs[measure_type][1]
                    MovinsEdiGenerator.write_segment(f, 'DIM', dim_code, f"{unit}:::{row[col]}")

        # Temperature for reefer
        temp_col, temp_unit = measurement_cols['TEMP']
        if not pd.isna(row.get('RF')) and temp_col and not pd.isna(row[temp_col]):
            MovinsEdiGenerator.write_segment(f, 'TMP', '2', f"{row[temp_col]}:{temp_unit}")

        # Location information
        for loc_type, qualifier in [('POL', '9'), ('POD', '11'), ('OPOD', '76'), ('FPOD', '83')]:
            if not pd.isna(row[loc_type]):
                MovinsEdiGenerator.write_segment(f, 'LOC', qualifier, self.format_location(row[loc_type]))

        MovinsEdiGenerator.write_segment(f, 'RFF', 'BM:1')

        # Equipment details
        freight_kind = '5' if str(row['FREIGHT KIND']).upper() == 'F' else '4'
        status = int(row['EQM STATUS']) if not pd.isna(row['EQM STATUS']) else ''

        size = ''
        if not pd.isna(row['SIZE']):
            if str(row['SIZE']).replace('.', '').isdigit():
                size = str(int(float(row['SIZE'])))
            else:
                size = row['SIZE']

        cont_no = '' if pd.isna(row['CONT NO.']) else row['CONT NO.']
        MovinsEdiGenerator.write_segment(f, 'EQD', 'CN', cont_no, size, '', status, freight_kind)

        # Carrier information
        if not pd.isna(row['OPS']):
            ops_agency = '' if pd.isna(row['OPS RESP AGENCY']) else row['OPS RESP AGENCY']
            MovinsEdiGenerator.write_segment(f, 'NAD', 'CA', f"{row['OPS']}:172:{ops_agency}")

        # Dangerous goods
        if not pd.isna(row.get('DG')) and not pd.isna(row.get('IMO')) and not pd.isna(row.get('UNNO')):
            MovinsEdiGenerator.write_segment(f, 'DGS', 'IMD', row['IMO'], row['UNNO'], '', '', '', '', '', '')

    def convert_containers_to_csv(self):
        """Convert containers sheet to CSV for chunk processing"""
        containers_df = pd.read_excel(self.excel_file, sheet_name='Containers')
        csv_path = Path("D:/PyProject/PyProject/Edi_extract/output/temp_containers.csv")
        containers_df.to_csv(csv_path, index=False)
        return csv_path

    def generate(self):
        """Generate the MOVINS EDI file and return the output path"""
        try:
            header_df = pd.read_excel(self.excel_file, sheet_name='Header')
            vessel_df = pd.read_excel(self.excel_file, sheet_name='Vessel')

            # Convert containers sheet to CSV
            csv_path = self.convert_containers_to_csv()

            # Read first chunk to get column names and set up measurement configs
            first_chunk = pd.read_csv(csv_path, nrows=1)
            measurement_cols = self.find_measurement_columns(first_chunk)

            vessel_info = vessel_df.iloc[0]
            header_info = header_df.iloc[0]

            # Create output filename based on vessel name or use default
            vessel_name = vessel_info['NAME'] if not pd.isna(vessel_info['NAME']) else 'output'
            output_filename = f"{vessel_name}.edi"
            output_path = Path("output") / output_filename

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                self.write_header_segments(f, header_info, vessel_info)
                self.write_vessel_segments(f, vessel_info)

                # Process containers in chunks
                for chunk in pd.read_csv(csv_path, chunksize=self.chunk_size):
                    for _, row in chunk.iterrows():
                        self.write_container_segments(f, row, measurement_cols)

                MovinsEdiGenerator.write_segment(f, 'UNT', '1', '1')
                MovinsEdiGenerator.write_segment(f, 'UNZ', '1', '1')

            # Clean up temporary CSV file
            csv_path.unlink()

            print(f"Successfully created MOVINS EDI file: {output_path}")
            return output_path

        except Exception as e:
            print(f"Error: {str(e)}")
            # Clean up temporary CSV file if it exists
            if 'csv_path' in locals():
                try:
                    csv_path.unlink()
                except:
                    pass
            raise

if __name__ == "__main__":
    excel_file = "D:\\PyProject\\Edi_extract\\output\\baplie_data.xlsx"
    generator = MovinsEdiGenerator(excel_file)
    generator.generate()
