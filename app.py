from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
from dotenv import load_dotenv
from glukos_analys import öppna_fil  # Make sure this matches your filename exactly
from flask import send_file

# Load environment variables from .env.local file for local development
# In production (Render), these will be set via Render's environment variables
load_dotenv('.env.local')

app = Flask(__name__)
# Load secret key from environment variable (required)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable is required. Set it in .env.local for local development or in Render's environment settings for production.")

# Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load user credentials from environment variable
# Format: JSON string like '{"username1": "password1", "username2": "password2"}'
# For Render: Set USER_CREDENTIALS environment variable in Render dashboard
# For local: Set USER_CREDENTIALS in .env.local file
credentials_json = os.environ.get('USER_CREDENTIALS')
if not credentials_json:
    raise ValueError("USER_CREDENTIALS environment variable is required. Set it in .env.local for local development or in Render's environment settings for production.")

try:
    USER_CREDENTIALS = json.loads(credentials_json)
    # Normalize credentials: trim whitespace from usernames
    USER_CREDENTIALS = {username.strip(): password for username, password in USER_CREDENTIALS.items()}
except json.JSONDecodeError:
    raise ValueError("USER_CREDENTIALS must be a valid JSON string. Format: {\"username1\": \"password1\", \"username2\": \"password2\"}")

# Route for the login page
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        # ✅ Kolla om användaren finns och om lösenordet matchar
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['user'] = username  # Spara inloggad användare i session
            return redirect(url_for('selection_page'))
        else:
            # Debug: Log available usernames (only in debug mode)
            if app.debug:
                available_users = list(USER_CREDENTIALS.keys())
                error_msg = f"Ogiltigt användarnamn eller lösenord. Tillgängliga användare: {', '.join(available_users)}"
            else:
                error_msg = "Ogiltigt användarnamn eller lösenord"
            return render_template('login.html', error=error_msg)

    return render_template('login.html')

# Route for the selection page
@app.route('/selection')
def selection_page():
    if 'user' not in session:  # Check if user is logged in
        return redirect(url_for('login'))

    # Updated options
    options = [
        {"name": "OBLA-Test1.0", "link": "/OBLA-Test1.0"},
        {"name": "Ekblom-Bak Test", "link": "/ekblom-bak"},
        {"name": "InBodyMan", "link": "/Inbody-Man1.0"},
        {"name": "InBodyKvinna", "link": "/inbody-kvinna"},
        {"name": "Blodprover", "link": "/blodprover"},
        {"name": "Blodprover - Alla Prover", "link": "/blodprover-alla"},
        {"name": "GlukosAnalys", "link": "/glukos-analys"},
        {"name": "GlukosRapport", "link": "/glukos-rapport"}
    ]
    return render_template('selection.html', options=options)

# Route for logout
@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove user from session
    return redirect(url_for('login'))


@app.route('/obla-test')
def obla_test():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('obla-test.html')

@app.route('/obla-test-running')
def obla_test_running():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('obla-test-running.html')

@app.route('/inbody-man')
def inbody_man():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('inbody-man.html')

@app.route('/inbody-kvinna')
def inbody_kvinna():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('inbody-kvinna.html')

@app.route('/blodprover')
def blodprover():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('blodprover.html')

@app.route('/blodprover-alla')
def blodprover_alla():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('blodprover-alla.html')

@app.route('/glukos-analys')
def glukos_analys():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('glukosanalys.html')

@app.route('/glukos-rapport')
def glukos_rapport():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('glukosrapport.html')

@app.route('/ekblom-bak')
def ekblom_bak():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('ekblom-bak.html')

@app.route('/analyze-file', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    # Save the uploaded file temporarily
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(temp_filepath)

    # Run your analysis function
    result = öppna_fil(filepath=temp_filepath)

    # Remove the temporary uploaded file
    os.remove(temp_filepath)

    if result['success']:
        # Return the path to the generated Excel file
        excel_path = result['excel_filename']
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=os.path.basename(excel_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        return jsonify({'error': result['error']})

@app.route('/analyze-json', methods=['POST'])
def analyze_json():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})

    # Save the uploaded file temporarily
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(temp_filepath)

    # Run your analysis function
    result = öppna_fil(filepath=temp_filepath)

    # Remove the temporary uploaded file
    os.remove(temp_filepath)

    if result['success']:
        # Return the JSON results
        return jsonify({
            'success': True,
            'results': result['results']
        })
    else:
        return jsonify({'success': False, 'error': result['error']})


if __name__ == '__main__':
    app.run(debug=True)
