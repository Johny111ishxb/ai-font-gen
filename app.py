from flask import Flask, request, jsonify, render_template, send_from_directory, url_for, redirect, session
from werkzeug.utils import secure_filename
import os
import subprocess
import logging
import uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from PIL import Image
import sys
import traceback

app = Flask(__name__)
app.secret_key = 'sdgdsgdfhrthertgew12432'

# Firebase Admin initialization
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output_fonts')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Configure logging with more detailed formatting
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():
    try:
        # Check authentication status
        has_generated = session.get('has_generated', False)
        auth_header = request.headers.get('Authorization')
        is_authenticated = False
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            decoded_token = verify_firebase_token(token)
            if decoded_token:
                is_authenticated = True

        if has_generated and not is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Please sign up to generate more fonts',
                'requires_auth': True
            }), 401

        if 'handwriting' not in request.files:
            logger.error("No file part in request")
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['handwriting']
        if file.filename == '':
            logger.error("No file selected")
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'success': False, 'error': 'Invalid file type'})

        # Generate unique filename for input
        input_filename = f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        
        # Save and process the file
        file.save(input_path)
        
        # Ensure the file exists and is readable
        if not os.path.exists(input_path):
            logger.error(f"Failed to save file at {input_path}")
            return jsonify({'success': False, 'error': 'Failed to save uploaded file'})

        # Log file details
        logger.info(f"File saved at: {input_path}")
        logger.info(f"File size: {os.path.getsize(input_path)} bytes")
        
        try:
            # Process image with PIL first
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Save as JPEG
                img.save(input_path, 'JPEG', quality=95)
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            return jsonify({'success': False, 'error': 'Image processing failed'})

        # Run handwrite command with full error capture
        try:
            result = subprocess.run(
                ["handwrite", input_path, OUTPUT_DIR],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Handwrite output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Handwrite command failed with exit code {e.returncode}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            return jsonify({'success': False, 'error': f'Font generation failed: {e.stderr}'})

        # Find the generated font
        generated_font = find_generated_font()
        if not generated_font:
            logger.error("No font file generated")
            return jsonify({'success': False, 'error': 'Font generation failed - no output file'})

        # Create unique filename for output
        new_filename = f"font_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.ttf"
        output_path = os.path.join(OUTPUT_DIR, new_filename)
        
        # Rename the generated font
        os.rename(os.path.join(OUTPUT_DIR, generated_font), output_path)

        # Clean up input file
        try:
            os.remove(input_path)
        except Exception as e:
            logger.warning(f"Failed to remove input file: {str(e)}")

        # Generate download URL
        download_url = url_for('download_font', filename=new_filename)

        if not is_authenticated:
            session['has_generated'] = True

        return jsonify({
            'success': True,
            'font_url': download_url,
            'filename': new_filename,
            'first_generation': not has_generated and not is_authenticated
        })

     except Exception as e:

        logger.error(f"Error in upload: {str(e)}")

        return jsonify({'success': False, 'error': str(e)})

        logger.debug(f"Saving file to: {input_path}")

        file.save(input_path)

        logger.debug(f"File saved successfully")

        logger.debug(f"Running handwrite command on: {input_path}")

        logger.debug(f"Output directory: {OUTPUT_DIR}")

        # Run handwrite command with more detailed error capture

        try:

            result = subprocess.run(

                ["handwrite", input_path, OUTPUT_DIR],

                capture_output=True,

                text=True,

                check=True

            )

            logger.debug(f"Handwrite command output: {result.stdout}")

        except subprocess.CalledProcessError as e:

            logger.error(f"Handwrite command failed with error: {e.stderr}")

            raise

@app.route('/download/<filename>')

def download_font(filename):

    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

def find_generated_font():

    ttf_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.ttf')]

    if not ttf_files:

        return None

    return max(ttf_files, key=lambda f: os.path.getctime(os.path.join(OUTPUT_DIR, f)))

def generate_unique_filename():

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    random_string = uuid.uuid4().hex[:8]

    return f"font_{timestamp}_{random_string}.ttf"

if name == '__main__':

    port = int(environ.get('PORT', 8080))

    app.run(host='0.0.0.0', port=port)
