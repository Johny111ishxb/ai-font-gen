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
import io
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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login')
def login():
    return render_template('login.html')

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

        # Process and save file
        try:
            # Read image data
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Generate unique filename
            input_filename = f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            input_path = os.path.join(UPLOAD_FOLDER, input_filename)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save processed image
            image.save(input_path, 'JPEG', quality=95)
            
            logger.info(f"Processed and saved image at: {input_path}")
            
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to process image'})

        # Run handwrite command
        try:
            result = subprocess.run(
                ["handwrite", input_path, OUTPUT_DIR],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Handwrite output: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Handwrite command failed:")
            logger.error(f"Return code: {e.returncode}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            return jsonify({'success': False, 'error': f'Font generation failed: {e.stderr}'})

        # Find generated font
        generated_font = find_generated_font()
        if not generated_font:
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
        logger.error(f"Unexpected error in upload: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_font(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

def find_generated_font():
    ttf_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.ttf')]
    if not ttf_files:
        return None
    return max(ttf_files, key=lambda f: os.path.getctime(os.path.join(OUTPUT_DIR, f)))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
