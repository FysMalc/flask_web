import re
import logging
from datetime import datetime
from typing import Dict, List

class BaplieParser:
    """Parser for BAPLIE EDI messages with support for different formats and scenarios."""

    def __init__(self, segment_mappings=None):
        self.logger = logging.getLogger('BaplieParser')
        self.segment_mappings = segment_mappings or {}
        self.vessel_info = {}
        self.containers = []
        self.current_container_data = None
        self.header_info = {}
        self.current_segment = None
        self.units = {
            'weight': '',
            'oog': '',
            'temp': ''
        }
        self.logger.info("BaplieParser initialized")

    def _pre_scan_units(self, file_path: str) -> None:
        """Pre-scan the file to find all units before actual parsing."""
        self.logger.info(f"Pre-scanning units from file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                segments = re.split("'[\n\r]*", content.strip())

                for segment in segments:
                    if not segment.strip():
                        continue

                    elements = segment.split('+')
                    segment_type = elements[0]

                    # Add logging for each unit found
                    if segment_type == 'MEA' and len(elements) > 3:
                        measurement = elements[3].split(':')
                        if len(measurement) > 1 and not self.units['weight']:
                            self.units['weight'] = measurement[0]
                            self.logger.debug(f"Found weight unit: {measurement[0]}")

                    elif segment_type == 'TMP' and len(elements) > 2:
                        tmp_elements = elements[2].split(':')
                        if len(tmp_elements) > 1 and not self.units['temp']:
                            self.units['temp'] = tmp_elements[1]
                            self.logger.debug(f"Found temperature unit: {tmp_elements[1]}")

                    elif segment_type == 'DIM' and len(elements) > 2:
                        dim_elements = elements[2].split(':')
                        if len(dim_elements) > 0 and not self.units['oog']:
                            self.units['oog'] = dim_elements[0]
                            self.logger.debug(f"Found OOG unit: {dim_elements[0]}")

                    if all(self.units.values()):
                        break

            self.logger.info(f"Units found: {self.units}")
        except Exception as e:
            self.logger.error(f"Error during pre-scanning units: {str(e)}", exc_info=True)
            raise

    def parse_file(self, file_path: str) -> None:
        """Parse a BAPLIE EDI file according to different sections."""
        self.logger.info(f"Starting to parse file: {file_path}")
        try:
            self._pre_scan_units(file_path)

            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            segments = re.split("'[\n\r]*", content.strip())

            # Get the starting line numbers for containers section
            for i, segment in enumerate(segments):
                if not segment.strip():
                    continue

                # Determine which section we're in based on line number
                if segment.strip().startswith('UNB'):
                    self.current_segment = 'header'
                elif segment.strip().startswith('TDT'):
                    self.current_segment = 'vessel'
                elif segment.strip().startswith("LOC+147"):
                    self.current_segment = 'containers'

                if self.current_segment == 'containers':
                    # Check if this matches the container start line pattern
                    if segment.strip().startswith("LOC+147"):
                        # If we have a current container, save it before starting new one
                        if self.current_container_data:
                            flattened_container = self._flatten_container(self.current_container_data)
                            self.containers.append(flattened_container)

                        if not segment.strip().startswith('UNT'):
                            # Initialize new container
                            self.current_container_data = {
                                'locations': [],
                                'FTX': [],
                                'weights': [],
                                'DIM': [],
                                'references': [],
                            }
                    # else:
                        # Parse the segment for the current container
                        # self._parse_container_segment(segment.strip())
                self._parse_segment(segment)
            # Don't forget to add the last container
            if self.current_container_data:
                flattened_container = self._flatten_container(self.current_container_data)
                self.containers.append(flattened_container)

        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            raise

    def _parse_segment(self, segment: str) -> None:
        """Parse individual EDI segments."""
        elements = segment.split('+')
        segment_type = elements[0]

        try:
            if segment_type == 'UNB':
                self._parse_unb(elements)
            elif segment_type == 'UNH':
                self._parse_unh(elements)
            elif segment_type == 'BGM':
                self._parse_bgm(elements)
            elif segment_type == 'DTM':
                self._parse_dtm(elements)
            elif segment_type == 'TDT':
                self._parse_tdt(elements)
            elif segment_type == 'LOC':
                self._parse_loc(elements)
            elif segment_type == 'EQD':
                self._parse_eqd(elements)
            elif segment_type == 'MEA':
                self._parse_mea(elements)
            elif segment_type == 'RFF':
                self._parse_rff(elements)
            elif segment_type == 'NAD':
                self._parse_nad(elements)
            elif segment_type == 'DIM':
                self._parse_dim(elements)
            elif segment_type == 'TMP':
                self._parse_tmp(elements)
            elif segment_type == 'RNG':
                pass
            elif segment_type == 'DGS':
                self._parse_dgs(elements)
        except Exception as e:
            print(f"Error parsing segment {segment}: {str(e)}")

    def _parse_unb(self, elements: List[str]) -> None:
        """Parse UNB (Interchange Header) segment."""
        if len(elements) > 4:
            syntax_info = elements[1].split(':')
            date_time = elements[4].split(':')
            date=''
            # try:
            #     date = datetime.strptime(date_time[0], '%y%m%d')
            #     time = datetime.strptime(date_time[1], '%H%M%s')
            # except Exception as e:
            #     self.logger.info(f"Failed convert to %y%m%d (2 year digit) format, now using %Y%m%d (4 year digit)'")
            #     date = datetime.strptime(date_time[0], '%Y%m%d')
            #     htime = datetime.strptime(date_time[1], '%H%M')

            self.header_info.update({
                'syntax_version': syntax_info[1] if len(syntax_info) > 1 else '',
                'sender': elements[2].split(':')[0],
                # 'recipient': elements[2].split(':')[1],
                # 'date': date + htime ,
            })

    def _parse_unh(self, elements: List[str]) -> None:
        """Parse UNH segment"""
        if len(elements) > 2:
            msg_ref_num = elements[1]
            msg_identifier = elements[2].split(':')
            msg_type_identifier = msg_identifier[0]
            msg_type_ver = msg_identifier[1]
            msg_type_release = msg_identifier[2]
            control_agency = msg_identifier[3]
            association_assigned_code = msg_identifier[4]
            self.header_info.update({
                'msg_ref_num': msg_ref_num,
                'msg_type_identifier': msg_type_identifier,
                'msg_type_ver': msg_type_ver,
                'msg_type_release': msg_type_release,
                'control_agency': control_agency,
                'asso_assigned_code': association_assigned_code
            })

    def _parse_bgm(self, elements: List[str]) -> None:
        """Parse BGM (Beginning of Message) segment."""
        if len(elements) > 2:
            self.header_info['document_number'] = elements[2]

    def _parse_tdt(self, elements: List[str]) -> None:
        """Parse TDT (Transport Information) segment."""
        if len(elements) > 8:
            info = elements[8].split(':')
            self.vessel_info.update({
                'vessel_id': info[0],
                'vessel_name': info[-1] if len(info) > 3 else '',
                'TRANSPORT STAGE QUALIFIER': elements[1],
                'CONVEYANCE REFERRENCE NUMBER': elements[2],
                'MODE OF TRANSPORT': elements[3],
                'TRANSPORT MEANS': elements[4],
                'Carrier identification': elements[5].split(":")[0],
                'Code list qualifier': elements[5].split(":")[1],
                'Code list responsible agency': elements[5].split(":")[2],
                'Transport ID code list': info[1],
                'Transport ID code list responsible agency': info[2]
            })

    def _parse_eqd(self, elements: List[str]) -> None:
        """Parse EQD (Equipment Details) segment."""
        if len(elements) > 2 and self.current_container_data:
            self.current_container_data['container_number'] = elements[2]
            self.current_container_data['equipment_type'] = elements[3] if len(elements) > 3 else ''
            self.current_container_data['freight kind'] = elements[6]
            self.current_container_data['EQM STATUS'] = elements[5]

    def _parse_loc(self, elements: List[str]) -> None:
        """Parse LOC (Location) segment."""
        if not elements or len(elements) < 3:
            return

        loc_type = elements[1]
        loc_info = elements[2].split(':')
        location = {
            'type': loc_type,
            'loc_info': loc_info,
        }

        # All LOC segments are now treated the same way
        if self.current_segment == 'containers':
            if self.current_container_data:
                self.current_container_data['locations'].append(location)
        elif self.current_segment == 'vessel':
            self.vessel_info.setdefault('locations', []).append(location)


    def _parse_mea(self, elements: List[str]) -> None:
        """Parse MEA (Measurements) segment."""
        if len(elements) > 3:
            measurement = elements[3].split(':')
            if len(measurement) > 1:
                weight_data = {
                    'unit': measurement[0],
                    'value': measurement[1]
                }
                if self.current_container_data:
                    self.current_container_data['weights'].append(weight_data)

    def _parse_dtm(self, elements: List[str]) -> None:
        """Parse DTM (Date/Time/Period) segment."""
        if len(elements) > 1:
            dtm_elements = elements[1].split(':')
            if len(dtm_elements) > 2:
                qualifier = dtm_elements[0]
                date_value = dtm_elements[1]
                format_qualifier = dtm_elements[2]

                try:
                    if format_qualifier == '101':
                        parsed_date = datetime.strptime(date_value, '%y%m%d')
                    elif format_qualifier == '201':
                        parsed_date = datetime.strptime(date_value, '%y%m%d%H%M')
                    # elif format_qualifier == '203':
                    #     parsed_date = datetime.strptime(date_value, '%Y%m%d%H%M')
                    else:
                        parsed_date = date_value

                    date_info = {
                        'qualifier': qualifier,
                        'date': parsed_date,
                        'format': format_qualifier
                    }

                    if self.current_segment == 'header':
                        self.header_info['date'] = date_info
                    elif self.current_segment == 'vessel':
                        self.vessel_info.setdefault('dates', []).append(date_info)
                except ValueError as e:
                    print(f"Error parsing date {date_value}: {str(e)}")

    def _parse_rff(self, elements: List[str]) -> None:
        """Parse RFF (Reference) segment."""
        if len(elements) > 1:
            ref_elements = elements[1].split(':')
            if len(ref_elements) > 0:
                ref_data = {
                    'type': ref_elements[0],
                    'number': ref_elements[1] if len(ref_elements) > 1 else ''
                }

                if self.current_segment == 'vessel':
                    self.vessel_info.setdefault('references', []).append(ref_data)

                elif self.current_segment == 'containers':
                    if self.current_container_data:
                        self.current_container_data['references'].append(ref_data)

    def _parse_nad(self, elements: List[str]) -> None:
        """Parse NAD (Name and Address) segment."""
        if len(elements) > 2 and self.current_container_data:
            party_qualifier = elements[1]
            party_id = elements[2].split(':')
            # self.logger.debug(f"NAD parsing - Full elements: {elements}")
            # self.logger.debug(f"NAD parsing - Party ID after split: {party_id}")
            nad = {
                'CA': party_qualifier,
                'party_id': party_id
            }
            # self.logger.debug(f"NAD parsing - Final NAD dict: {nad}")
            self.current_container_data['NAD'] = nad

    def _parse_dim(self, elements: List[str]) -> None:
        """Parse DIM (Dimensions) segment"""
        if len(elements) > 2:
            dim_qualifier = elements[1]
            oog_infos = elements[2].split(":")

            dim_info = {
                'qualifier': dim_qualifier,
                'dim_info': oog_infos
            }

            self.current_container_data['DIM'].append(dim_info)

    def _parse_tmp(self, elements: List[str]) -> None:
        """Parse TMP (Temperature) segment"""
        if len(elements) > 2:
            tmp_info = {
                'tmp': elements[2].split(":")[0],
                'unit': elements[2].split(":")[1]
            }

            self.current_container_data["TMP"] = tmp_info

    def _parse_dgs(self, elements: List[str]) -> None:
        dgs_info = {
            'IMO': elements[2].split(":")[0],
            'UNNO': elements[3].split(":")[0] if len(elements) > 4 else ''
        }

        self.current_container_data['DGS'] = dgs_info

    def _parse_han(self, elements: List[str]) -> None:
        pass

    def _parse_ftx(self, elements: List[str]) -> None:
        pass

    def _parse_eqa(self, elements: List[str]) -> None:
        pass

    def _classify_time(self, qualifier: str, date: str, flattened: Dict) -> Dict:
        if qualifier == '132':
            flattened['Estimated Arrival Date/Time'] = date
        elif qualifier == '178':
            flattened['Actual Arrival Date/Time'] = date
        elif qualifier == '133':
            flattened['Estimated Departure Date/Time'] = date
        elif qualifier == '136':
            flattened['Actual Departure Date/Time'] = date
        elif qualifier == '137':
            flattened['Message creation time'] = date

        return flattened

    def _classify_loc(self, type: str, loc_info: List[str], flattened: Dict) -> Dict:
        if type == '5':
            flattened['Place of Departure'] = loc_info[0]
        elif type == '9':
            flattened['POL'] = loc_info[0]
        elif type == '11':
            flattened['POD'] = loc_info[0]
        elif type == '61':
            flattened['NPOC'] = loc_info[0]
        elif type == '76':
            flattened['OPOD'] = loc_info[0]
        elif type == '83':
            flattened['FPOD'] = loc_info[0]
        elif type == '92':
            flattened['Routing'] = flattened.get('Routing', '') + ' + ' + loc_info[0]
        elif type == '147':
            flattened['CELL'] = loc_info[0]

        return flattened

    def _classify_rff(self, type, number, flattened):
        if type == 'VON':
            flattened['Voyage Number'] = number

        return flattened

    def _flatten_container(self, container: Dict) -> Dict:
        """Flatten nested container data structure with specified order and consistent units."""

        freight_kind_indicator = container.get('freight kind', '')
        freight_kind = ''
        if freight_kind_indicator == '4':
            freight_kind = 'E'
        elif freight_kind_indicator == '5':
            freight_kind = 'F'

        # Extract weight information
        weight_value = ''
        if container.get('weights'):
            weight = container['weights'][0]
            weight_value = weight.get('value', '')

        # Extract reference information
        bl = ''
        ref_num = ''
        if container.get('references'):
            ref = container['references'][0]
            bl = ref.get('type', '')
            ref_num = ref.get('number', '')

        # Extract OOG information
        is_oog = ''
        ovh = ''
        ovl = ''
        ovr = ''
        for oog in container.get('DIM', []):
            qualifier = oog.get('qualifier')
            oog_info = oog.get('dim_info', [])
            if qualifier == '7' or qualifier == '8' or qualifier == '9':
                is_oog = 'Y'
                if qualifier == '7':
                    ovr = oog_info[2] if len(oog_info) > 2 else ''
                elif qualifier == '8':
                    ovl = oog_info[2] if len(oog_info) > 2 else ''
                elif qualifier == '9':
                    ovh = oog_info[3] if len(oog_info) > 3 else ''

        # Extract RF (Temperature) information
        is_rf = ''
        rf_temp = ''
        if container.get('TMP'):
            rf_info = container['TMP']
            is_rf = 'Y'
            rf_temp = rf_info.get('tmp', '')

        # Extract DG (Dangerous Goods) information
        is_dg = ''
        imo = ''
        unno = ''
        if container.get('DGS'):
            dg_info = container['DGS']
            is_dg = 'Y'
            imo = dg_info.get('IMO', '')
            unno = dg_info.get('UNNO', '')

        ops_id: str = ''
        ops_resp_agency = ''
        if container.get('NAD'):
            ops_info = container.get('NAD')
            ops_id = ops_info.get('party_id')[0]
            ops_resp_agency = ops_info.get('party_id')[2]

        eqm_status = container.get

        # Create flattened dictionary with specified order and consistent units
        flattened = {
            'CONT NO.': container.get('container_number', ''),
            'SIZE': container.get('equipment_type', ''),
            'BL': bl,
            'Ref Numb': ref_num,
            'CELL': None,  # populated by _classify_loc
            'FREIGHT KIND': freight_kind,
            'OPS': ops_id,
            f'Weight ({self.units["weight"]})': weight_value,
            'OPOD': container.get('Original POD', ''),
            'POL': None,  # populated by classify_loc
            'POD': None,  # populated by classify_loc
            'FPOD': None,  # populated by classify_loc
            'DG': is_dg,
            'IMO': imo,
            'UNNO': unno,
            'RF': is_rf,
            f'TEMP ({self.units["temp"]})': rf_temp,
            'OOG': is_oog,
            f'OVER HEIGHT ({self.units["oog"]})': ovh,
            f'OVER LEFT ({self.units["oog"]})': ovl,
            f'OVER RIGHT ({self.units["oog"]})': ovr,
            f'OPS RESP AGENCY': ops_resp_agency,
            'EQM STATUS': container.get('EQM STATUS', '')
        }

        # Process locations
        for loc in container.get('locations', []):
            flattened = self._classify_loc(loc['type'], loc['loc_info'], flattened)

        return flattened

    def _flatten_vessel_info(self) -> Dict:
        """Flatten nested vessel information."""
        flattened = {
            'ID': self.vessel_info.get('vessel_id', ''),
            'NAME': self.vessel_info.get('vessel_name', ''),
            'NPOC': None,
            'TRANSPORT STAGE QUALIFIER': self.vessel_info.get('TRANSPORT STAGE QUALIFIER' ''),
            'CONVEYANCE REFERRENCE NUMBER': self.vessel_info.get('CONVEYANCE REFERRENCE NUMBER' ''),
            'MODE OF TRANSPORT': self.vessel_info.get('MODE OF TRANSPORT' ''),
            'TRANSPORT MEANS': self.vessel_info.get('TRANSPORT MEANS' ''),
            'Carrier identification': self.vessel_info.get('Carrier identification' ''),
            'Code list qualifier': self.vessel_info.get('Code list qualifier' ''),
            'Code list responsible agency': self.vessel_info.get('Code list responsible agency' ''),
            'ID of means of transport': self.vessel_info.get('ID of means of transport' ''),
            'Transport ID code list': self.vessel_info.get('Transport ID code list' ''),
            'Transport ID code list responsible agency': self.vessel_info.get('Transport ID code list responsible agency' '')
        }

        # Flatten vessel locations
        for i, loc in enumerate(self.vessel_info.get('locations', [])):
            flattened = self._classify_loc(loc.get('type', ''), loc.get('loc_info'), flattened)

        for i, date_info in enumerate(self.vessel_info.get('dates', [])):
            date_qualifier = date_info.get('qualifier', '')
            date_value = date_info.get('date', '')

            flattened = self._classify_time(date_qualifier, date_value, flattened)

        for i, rff in enumerate(self.vessel_info.get('references', [])):
            ref_type = rff.get('type', '')
            ref_number = rff.get('number', '')

            flattened = self._classify_rff(ref_type, ref_number, flattened)


        return flattened

    def _flatten_header_info(self) -> Dict:
        """Flatten nested header information."""
        flattened = {
            'syntax_version': self.header_info.get('syntax_version', ''),
            'SENDER': self.header_info.get('sender', ''),
            'RECIPIENT': self.header_info.get('recipient', ''),
            'DOC NO.': self.header_info.get('document_number', ''),
            'msg_ref_num': self.header_info.get('msg_ref_num'),
            'msg_type_identifier': self.header_info.get('msg_type_identifier'),
            'msg_type_ver': self.header_info.get('msg_type_ver'),
            'msg_type_release': self.header_info.get('msg_type_release'),
            'control_agency': self.header_info.get('control_agency'),
            'asso_assigned_code': self.header_info.get('asso_assigned_code')
        }

        # Flatten header date
        # date_info = self.header_info['date']
        # date_qualifier = date_info.get('qualifier', '')
        # date_value = date_info.get('date', '')
        #
        # flattened = self._classify_time(date_qualifier, date_value, flattened)

        return flattened
