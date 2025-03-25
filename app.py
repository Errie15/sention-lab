from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from glukos_analys import öppna_fil  # Make sure this matches your filename exactly
from flask import send_file



app = Flask(__name__)
app.secret_key = '1234'  # Required for session management

# Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dummy user credentials for login
USER_CREDENTIALS = {
    "erik": "77994466",
    "linda@sention.health": "Lsention!",
    "per@sention.health": "Psention!"
}

# Route for the login page
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ✅ Kolla om användaren finns och om lösenordet matchar
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['user'] = username  # Spara inloggad användare i session
            return redirect(url_for('selection_page'))
        else:
            return render_template('login.html', error="Ogiltigt användarnamn eller lösenord")

    return render_template('login.html')

# Route for the selection page
@app.route('/selection')
def selection_page():
    if 'user' not in session:  # Check if user is logged in
        return redirect(url_for('login'))

    # Updated options
    options = [
        {"name": "OBLA-Test1.0", "link": "/OBLA-Test1.0"},
        {"name": "InBodyMan", "link": "/Inbody-Man1.0"},
        {"name": "InBodyKvinna", "link": "/inbody-kvinna"},
        {"name": "Blodprover", "link": "/blodprover"},
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
