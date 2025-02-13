from pathlib import Path
import pandas as pd
from typing import Union
from .parser import BaplieParser


class OutputHandler:
    """Handles saving parsed BAPLIE data to different formats."""

    @staticmethod
    def determine_output_path(input_file: str, output_path: Union[str, None]) -> tuple[Path, str]:
        """Determine the base output path and directory."""
        if output_path is None:
            base_path = Path(input_file).stem
            output_dir = Path(input_file).parent
        else:
            output_path = Path(output_path)
            base_path = output_path.stem
            output_dir = output_path.parent
        return output_dir, base_path

    @staticmethod
    def save_to_excel(parser: BaplieParser, output_path: Path) -> None:
        """Save parsed data to Excel file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Header sheet
            pd.DataFrame([parser._flatten_header_info()]).to_excel(
                writer, sheet_name='Header', index=False)

            # Vessel info sheet
            pd.DataFrame([parser._flatten_vessel_info()]).to_excel(
                writer, sheet_name='Vessel', index=False)

            # Containers sheet
            pd.DataFrame(parser.containers).to_excel(
                writer, sheet_name='Containers', index=False)

    @staticmethod
    def save_to_csv(parser: BaplieParser, output_directory: Path) -> None:
        """Save parsed data to CSV files."""
        output_directory.mkdir(parents=True, exist_ok=True)

        # Save header info
        pd.DataFrame([parser._flatten_header_info()]).to_csv(
            output_directory / 'header.csv', index=False)

        # Save vessel info
        pd.DataFrame([parser._flatten_vessel_info()]).to_csv(
            output_directory / 'vessel.csv', index=False)

        # Save containers info
        pd.DataFrame(parser.containers).to_csv(
            output_directory / 'containers.csv', index=False)

    @classmethod
    def save_all_formats(cls, parser: BaplieParser, input_file: str,
                         output_path: Union[str, None] = None) -> None:
        """Save data in both Excel and CSV formats."""
        output_dir, base_path = cls.determine_output_path(input_file, output_path)

        # Save as Excel
        excel_path = output_dir / f"{base_path}.xlsx"
        cls.save_to_excel(parser, excel_path)

        # Save as CSV
        # csv_path = output_dir / f"{base_path}_csv"
        # cls.save_to_csv(parser, csv_path)
