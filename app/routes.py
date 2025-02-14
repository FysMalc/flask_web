from flask import Blueprint, render_template, request, send_file, current_app, jsonify, url_for, redirect, send_from_directory
from werkzeug.utils import secure_filename
import os
from app.utils.logger import setup_logging
from app.utils.parser import BaplieParser
from app.utils.output_handler import OutputHandler
from app.utils.movins_generator import MovinsEdiGenerator
from app.utils.CSV2DischListXML import generate_edi_from_discharge
from app.utils.CSV2CUSCARXML import generate_edi_from_cuscar
from app.utils.CSV2LoadListXML import generate_edi_from_load
from app.utils.CSV2COPARNXML import generate_edi_from_coparn
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import time

main = Blueprint('main', __name__)
logger = setup_logging()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'edi'}

def ensure_directories():
    """Ensure required directories exist and return their paths"""
    # Get the absolute path of the application root
    app_root = Path(current_app.root_path)

    # Define paths relative to the application root
    upload_folder = app_root / 'uploads'
    output_folder = app_root / 'output'

    # Create directories if they don't exist
    upload_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    return upload_folder, output_folder


@main.route('/', methods=['GET'])
def dashboard():
    # return render_template('dashboard.html')
    return render_template('excel2xml.html')

@main.route('/baplie2movins', methods=['GET'])
def baplie2movins():
    return render_template('BAPLIE2MOVINS.html')

@main.route('/excel2xml', methods=['GET'])
def excel2xml():
    return render_template('excel2xml.html')

@main.route('/convert2movins', methods=['POST'])
def convert2movins():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        try:
            # Ensure directories exist and get their paths
            upload_folder, output_folder = ensure_directories()

            # Generate unique identifier for this conversion
            session_id = str(uuid.uuid4())[:8]

            # Save uploaded file with unique name
            original_filename = secure_filename(file.filename)
            filename_base = original_filename.rsplit('.', 1)[0]
            file_path = upload_folder / f"{session_id}_{original_filename}"
            file.save(str(file_path))

            try:
                # Process BAPLIE file
                parser = BaplieParser()
                parser.parse_file(str(file_path))

                # Save Excel output with unique name
                excel_filename = f"{filename_base}_{session_id}.xlsx"
                excel_output = output_folder / excel_filename
                OutputHandler.save_all_formats(parser, str(file_path), str(excel_output))

                # Generate MOVINS EDI with unique name
                generator = MovinsEdiGenerator(str(excel_output))
                edi_path = generator.generate()
                edi_filename = f"{filename_base}_{session_id}.edi"

                # Move the EDI file to output folder with unique name
                edi_output = output_folder / edi_filename
                if os.path.exists(edi_path):
                    shutil.move(edi_path, str(edi_output))
                else:
                    raise FileNotFoundError(f"Generated EDI file not found at {edi_path}")

                # Return URL for the results page
                results_url = url_for('main.show_results',
                                      excel_file=excel_filename,
                                      edi_file=edi_filename)
                return results_url

            except Exception as e:
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                return jsonify({'error': f"Error processing file: {str(e)}"}), 500

            finally:
                # Clean up uploaded file
                try:
                    if os.path.exists(str(file_path)):
                        os.remove(str(file_path))
                except Exception as e:
                    logger.error(f"Error cleaning up file: {str(e)}")

        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}", exc_info=True)
            return jsonify({'error': f"Error saving uploaded file: {str(e)}"}), 500

    return jsonify({'error': 'Invalid file type'}), 400


@main.route('/convert2xml', methods=['POST'])
def convert2xml():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file type. Please upload an Excel file'}), 400

        # Ensure directories exist and get their paths
        upload_folder, output_folder = ensure_directories()

        # Generate unique identifier for this conversion
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save uploaded file with unique name
        original_filename = secure_filename(file.filename)
        filename_base = original_filename.rsplit('.', 1)[0]
        input_file = upload_folder / f"{session_id}_{original_filename}"
        output_file = output_folder / f"{filename_base}_{timestamp}.xml"

        file.save(str(input_file))

        try:
            # Get form data
            conversion_type = request.form.get('conversionType')
            operator = request.form.get('operator')
            vessel_id = request.form.get('vesselId')

            if not all([conversion_type, operator, vessel_id]):
                return jsonify({'error': 'Missing required fields'}), 400

            # Generate XML based on conversion type
            if conversion_type == 'Discharge':
                generate_edi_from_discharge(str(input_file), str(output_file), operator, vessel_id)
            elif conversion_type == 'Load':
                generate_edi_from_load(str(input_file), str(output_file), operator, vessel_id)
            elif conversion_type == 'CUSCAR':
                generate_edi_from_cuscar(str(input_file), str(output_file), operator, vessel_id)
            elif conversion_type == 'COPARN':
                generate_edi_from_coparn(str(input_file), str(output_file), operator, vessel_id)
            else:
                return jsonify({'error': 'Unsupported conversion type'}), 400

            # Return the generated XML file
            return send_file(
                str(output_file),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f"{filename_base}_{timestamp}.xml"
            )

        except Exception as e:
            logger.error(f"Error converting file: {str(e)}", exc_info=True)
            return jsonify({'error': f"Error converting file: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@main.route('/download-template/<filename>')
def download_template(filename):
    # Define the folder where templates are stored
    template_folder = "static/xls_template"

    try:
        return send_from_directory(template_folder, filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404


@main.route('/results')
def show_results():
    excel_file = request.args.get('excel_file')
    edi_file = request.args.get('edi_file')

    if not excel_file or not edi_file:
        return redirect(url_for('main.baplie2movins'))

    return render_template('results.html',
                           excel_file=excel_file,
                           edi_file=edi_file)

@main.route('/download/<filename>')
def download(filename):
    try:
        # Ensure directories exist and get their paths
        _, output_folder = ensure_directories()

        # Construct the full file path
        file_path = output_folder / secure_filename(filename)

        # Check if file exists
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        # Log the file path being accessed
        logger.info(f"Attempting to download file: {file_path}")

        # Set content disposition and filename
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return jsonify({'error': f"Error downloading file: {str(e)}"}), 500


# Optional: Add a cleanup route or function to remove old files
@main.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Remove all files from uploads and output folders"""
    try:
        upload_folder, output_folder = ensure_directories()
        deleted_files = {
            'uploads': [],
            'output': []
        }

        # Clean uploads folder
        for file_path in upload_folder.glob('*'):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_files['uploads'].append(file_path.name)
                except Exception as e:
                    logger.error(f"Error deleting upload file {file_path}: {str(e)}")
                    continue

        # Clean output folder
        for file_path in output_folder.glob('*'):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_files['output'].append(file_path.name)
                except Exception as e:
                    logger.error(f"Error deleting output file {file_path}: {str(e)}")
                    continue

        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed successfully',
            'deleted_files': deleted_files
        }), 200

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error during cleanup: {str(e)}'
        }), 500
