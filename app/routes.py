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

main = Blueprint('main', __name__)
logger = setup_logging()

# Map conversion types to their handlers
CONVERTERS = {
    'Discharge': generate_edi_from_discharge,
    'Load': generate_edi_from_load,
    'CUSCAR': generate_edi_from_cuscar,
    'COPARN': generate_edi_from_coparn
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'edi', 'xlsx', 'xls'}


def ensure_directories():
    """Ensure required directories exist and return their paths"""
    app_root = Path(current_app.root_path)
    upload_folder = app_root / 'uploads'
    output_folder = app_root / 'output'
    upload_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    return upload_folder, output_folder


@main.route('/', methods=['GET'])
def dashboard(): return render_template('excel2xml.html')


@main.route('/baplie2movins', methods=['GET'])
def baplie2movins(): return render_template('BAPLIE2MOVINS.html')


@main.route('/excel2xml', methods=['GET'])
def excel2xml(): return render_template('excel2xml.html')


@main.route('/convert2movins', methods=['POST'])
def convert2movins():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        upload_folder, output_folder = ensure_directories()
        session_id = str(uuid.uuid4())[:8]
        filename_base = secure_filename(file.filename).rsplit('.', 1)[0]
        file_path = upload_folder / f"{session_id}_{secure_filename(file.filename)}"
        file.save(str(file_path))

        try:
            parser = BaplieParser()
            parser.parse_file(str(file_path))
            excel_filename = f"{filename_base}_{session_id}.xlsx"
            excel_output = output_folder / excel_filename
            OutputHandler.save_all_formats(parser, str(file_path), str(excel_output))

            generator = MovinsEdiGenerator(str(excel_output))
            edi_path = generator.generate()
            edi_filename = f"{filename_base}_{session_id}.edi"
            edi_output = output_folder / edi_filename

            if os.path.exists(edi_path):
                shutil.move(edi_path, str(edi_output))
            else:
                raise FileNotFoundError(f"Generated EDI file not found at {edi_path}")

            return url_for('main.show_results', excel_file=excel_filename, edi_file=edi_filename)
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500
        finally:
            if os.path.exists(str(file_path)):
                os.remove(str(file_path))
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}", exc_info=True)
        return jsonify({'error': f"Error saving file: {str(e)}"}), 500


@main.route('/convert2xml', methods=['POST'])
def convert2xml():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Invalid file type. Please upload an Excel file'}), 400

    try:
        upload_folder, output_folder = ensure_directories()
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        filename_base = secure_filename(file.filename).rsplit('.', 1)[0]
        input_file = upload_folder / f"{session_id}_{secure_filename(file.filename)}"
        output_file = output_folder / f"{filename_base}_{timestamp}.xml"
        file.save(str(input_file))

        try:
            conversion_type = request.form.get('conversionType')
            operator = request.form.get('operator')
            vessel_id = request.form.get('vesselId')

            if not all([conversion_type, operator, vessel_id]):
                return jsonify({'error': 'Missing required fields'}), 400

            if conversion_type not in CONVERTERS:
                return jsonify({'error': 'Unsupported conversion type'}), 400

            CONVERTERS[conversion_type](str(input_file), str(output_file), operator, vessel_id)

            return send_file(
                str(output_file),
                mimetype='application/xml',
                as_attachment=True,
                download_name=f"{filename_base}_{timestamp}.xml"
            )
        except Exception as e:
            logger.error(f"Error converting file: {str(e)}", exc_info=True)
            return jsonify({'error': f"{str(e)}"}), 500
        finally:
            if os.path.exists(str(input_file)):
                os.remove(str(input_file))
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@main.route('/download-template/<filename>')
def download_template(filename):
    template_folder = "static/xls_template"
    return send_from_directory(template_folder, filename, as_attachment=True)


@main.route('/results')
def show_results():
    excel_file, edi_file = request.args.get('excel_file'), request.args.get('edi_file')
    if not excel_file or not edi_file:
        return redirect(url_for('main.baplie2movins'))
    return render_template('results.html', excel_file=excel_file, edi_file=edi_file)


@main.route('/download/<filename>')
def download(filename):
    try:
        _, output_folder = ensure_directories()
        file_path = output_folder / secure_filename(filename)

        if not os.path.exists(str(file_path)):
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        logger.info(f"Downloading file: {file_path}")
        return send_file(str(file_path), as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return jsonify({'error': f"Error downloading file: {str(e)}"}), 500


@main.route('/cleanup', methods=['POST'])
def cleanup_files():
    try:
        upload_folder, output_folder = ensure_directories()
        deleted_files = {'uploads': [], 'output': []}

        for folder, list_name in [(upload_folder, 'uploads'), (output_folder, 'output')]:
            for file_path in folder.glob('*'):
                if file_path.is_file():
                    try:
                        os.remove(str(file_path))
                        deleted_files[list_name].append(file_path.name)
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")

        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed successfully',
            'deleted_files': deleted_files
        }), 200
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error during cleanup: {str(e)}'}), 500