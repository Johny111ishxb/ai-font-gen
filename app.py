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
import json
import sys
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sdgdsgdfhrthertgew12432')

# Firebase Admin initialization
if os.environ.get('FIREBASE_CREDENTIALS'):
    cred = credentials.Certificate(json.loads(os.environ.get('FIREBASE_CREDENTIALS')))
    firebase_admin.initialize_app(cred)
else:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logging.warning(f"Failed to initialize Firebase: {e}")

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output_fonts')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
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

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'requires_auth': True
            }), 401
        
        token = auth_header.split('Bearer ')[1]
        decoded_token = verify_firebase_token(token)
        
        if not decoded_token:
            return jsonify({
                'success': False,
                'error': 'Invalid authentication token',
                'requires_auth': True
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/verify-token', methods=['POST'])
def verify_token():
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 400
    
    decoded_token = verify_firebase_token(token)
    if decoded_token:
        session['user_id'] = decoded_token['uid']
        session['email'] = decoded_token.get('email', '')
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/get_sample_form')
def get_sample_form():
    return send_from_directory('static', 'sample_form.pdf')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        # Check if user has already generated once without auth
        has_generated = session.get('has_generated', False)
        
        # Check authentication
        auth_header = request.headers.get('Authorization')
        is_authenticated = False
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            decoded_token = verify_firebase_token(token)
            if decoded_token:
                is_authenticated = True

        # If user has already generated once and is not authenticated, require signup
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

        # Save and process the file
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        try:
            # Use handwrite library directly instead of CLI
            from handwrite import Pipeline
            pipeline = Pipeline()
            output_path = os.path.join(OUTPUT_DIR, f"font_{uuid.uuid4().hex[:8]}.ttf")
            pipeline.run(input_path, output_path)
            
            if not os.path.exists(output_path):
                raise Exception("Font generation failed - output file not created")
            
            # Clean up input file
            os.remove(input_path)
            
            # Generate download URL
            download_url = url_for('download_font', filename=os.path.basename(output_path))
            
            # If user is not authenticated, mark that they've generated once
            if not is_authenticated:
                session['has_generated'] = True
            
            return jsonify({
                'success': True,
                'font_url': download_url,
                'filename': os.path.basename(output_path),
                'first_generation': not has_generated and not is_authenticated
            })
            
        except Exception as e:
            logger.error(f"Font generation error: {str(e)}")
            return jsonify({'success': False, 'error': f'Font generation failed: {str(e)}'})

    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_font(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

def generate_unique_filename():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_string = uuid.uuid4().hex[:8]
    return f"font_{timestamp}_{random_string}.ttf"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
