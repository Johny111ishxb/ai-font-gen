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
import sys
import shutil

app = Flask(__name__)
app.secret_key = 'sdgdsgdfhrthertgew12432'  # Change this to a secure secret key

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
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Path to the handwrite executable
HANDWRITE_PATH = "handwrite"  # If in PATH, or use full path

# FontForge path - this is the exact path provided
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
        
        # Log the paths to help with debugging
        logger.debug(f"Input path: {input_path}")
        logger.debug(f"Output directory: {OUTPUT_DIR}")

        try:
            # Set up environment variables with enhanced PATH
            env = os.environ.copy()
            
            # Add FontForge to the PATH
            if os.path.exists(FONTFORGE_PATH):
                if "PATH" in env:
                    env["PATH"] = f"{FONTFORGE_PATH};{env['PATH']}"
                else:
                    env["PATH"] = FONTFORGE_PATH
                logger.debug(f"Added FontForge to PATH: {FONTFORGE_PATH}")
            else:
                logger.warning(f"FontForge path does not exist: {FONTFORGE_PATH}")
            
            # Log the final PATH for debugging
            logger.debug(f"Using PATH: {env['PATH']}")
            
            # Create a batch file to run handwrite with the correct environment
            script_file = os.path.join(BASE_DIR, 'run_handwrite.sh')
            with open(script_file, 'w') as f:
                    f.write('#!/bin/bash\n')
                    f.write(f'handwrite "{input_path}" "{OUTPUT_DIR}" > handwrite_output.log 2>&1\n')
                    f.write(f'echo $? > handwrite_exit.log\n')
            os.chmod(script_file, 0o755)  # Make script executable

            process = subprocess.run(
                    [script_file],
                    shell=True,
                    timeout=120
                )
            # Read the output logs
            output_log = "No output log found"
            exit_log = "No exit log found"
            
            if os.path.exists('handwrite_output.log'):
                with open('handwrite_output.log', 'r', errors='ignore') as f:
                    output_log = f.read()
                    logger.debug(f"Handwrite output: {output_log}")
            
            if os.path.exists('handwrite_exit.log'):
                with open('handwrite_exit.log', 'r') as f:
                    exit_log = f.read()
                    logger.debug(f"Handwrite exit: {exit_log}")
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"Handwrite process failed with return code: {process.returncode}")
                logger.error(f"Output log: {output_log}")
                logger.error(f"Exit log: {exit_log}")
                return jsonify({
                    'success': False, 
                    'error': 'Font generation failed. Please check server logs for details.'
                })
                
        except Exception as e:
            logger.error(f"Exception running handwrite: {str(e)}")
            return jsonify({'success': False, 'error': f'Error running handwrite: {str(e)}'})
        finally:
            # Clean up batch file
            if os.path.exists(batch_file):
                try:
                    os.remove(batch_file)
                except:
                    pass
            
            # Clean up log files
            for log_file in ['handwrite_output.log', 'handwrite_exit.log']:
                if os.path.exists(log_file):
                    try:
                        os.remove(log_file)
                    except:
                        pass

        # Find the generated font
        generated_font = find_generated_font()
        if not generated_font:
            logger.error("No font file was generated")
            return jsonify({'success': False, 'error': 'No font file was generated'})

        # Create unique filename
        new_filename = generate_unique_filename()
        output_path = os.path.join(OUTPUT_DIR, new_filename)
        
        # Rename the generated font
        os.rename(os.path.join(OUTPUT_DIR, generated_font), output_path)
        logger.debug(f"Renamed font from {generated_font} to {new_filename}")

        # Clean up input file
        os.remove(input_path)

        # Generate download URL
        download_url = url_for('download_font', filename=new_filename)

        # If user is not authenticated, mark that they've generated once
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

if __name__ == '__main__':
    # Check if FontForge exists
    if not os.path.exists(os.path.join(FONTFORGE_PATH, "fontforge.exe")):
        logger.warning(f"FontForge not found at {os.path.join(FONTFORGE_PATH, 'fontforge.exe')}. Font generation may fail.")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
