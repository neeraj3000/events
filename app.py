from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, make_response, render_template_string
import mysql.connector
from mysql.connector import Error
from fpdf import FPDF
import uuid
import os,re
import tempfile

app = Flask(__name__)
app.secret_key = '123'

# MySQL configurations
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'rgukt'
}

def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"Error: '{e}'")
    return connection

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    html_content = """alert(Entered details are invalid..)"""
    mail = request.form['mail']
    password = request.form['password']
    role = request.form['role']
    print(role)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accounts WHERE mail=%s AND password=%s AND role=%s', (mail, password, role))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        session['mail'] = mail
        print(session['mail'])
        return redirect(url_for('homepage'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM managers WHERE mail=%s AND password=%s AND role=%s', (mail, password, role))
    manager = cursor.fetchone()
    cursor.close()
    conn.close()

    
    if manager:
        session['mail'] = mail
        return redirect(url_for('eveorg'))
    else:
        flash('Invalid username or password', 'danger')
        # return render_template_string(html_content)
        return redirect(url_for('home'))
    
@app.route('/reguser')
def reguser():
    return render_template('reguser.html')

@app.route('/reguser', methods=['POST'])
def register_post():
    name = request.form['name']
    id = request.form['id_number']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    password_regex = re.compile(
        r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    )

    if password != confirm_password:
        flash('Passwords do not match')
        return redirect(url_for('reguser'))

    if not password_regex.match(password):
        flash('Password must contain at least one capital letter, one symbol, and one number','error')
        return redirect(url_for('reguser'))

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM accounts WHERE mail=%s', (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash('Account already exists')
    else:
        cursor.execute('INSERT INTO accounts (name, id_num, mail, password, role) VALUES (%s, %s, %s, %s, %s)', (name, id, email, password, 'Student'))
        conn.commit()
        flash('Registration successful, please log in', 'success')

    cursor.close()
    conn.close()

    return redirect(url_for('home'))

@app.route('/homepage')
def homepage():
    mail = session['mail']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM accounts WHERE mail = %s', (mail,))
    user = cursor.fetchone()
    cursor.close()

    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    cursor.close()
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM past_events')
    past_events = cursor.fetchall()
    cursor.close()
    connection.close()


    return render_template('rgukt.html',user=user, events=events, past_events=past_events)

@app.route('/eveorg')
def eveorg():
    mail = session['mail']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM managers WHERE mail = %s', (mail,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM past_events')
    past_events = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('startorg.html',user=user, events=events, past_events=past_events)

@app.route('/enroll')
def enroll():
    return render_template('form.html')


@app.route('/events')
def events():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('index.html', events=events)

@app.route('/user-event')
def user_event():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('event.html', events=events)

# @app.route('/users')
# def users():
#     connection = get_db_connection()
#     cursor = connection.cursor(dictionary=True)
#     cursor.execute('SELECT * FROM accounts')
#     users = cursor.fetchall()
#     cursor.close()
#     connection.close()
#     return render_template('profile.html', users=users)

@app.route('/book/<event>', methods=['GET', 'POST'])
def book(event):
    time_slots = ["9:00 AM - 11:00 AM", "11:00 AM - 1:00 PM", "2:00 PM - 4:00 PM", "4:00 PM - 6:00 PM"]
    if request.method == 'POST':
        team_leader_name = request.form['team_leader_name']
        team_leader_email = request.form['team_leader_email']
        team_name = request.form['team_name']
        team_size = request.form['team_size']
        time_slot = request.form['time_slot']

        # Generate a unique ticket ID
        ticket_id = str(uuid.uuid4())

        # Insert booking into the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (ticket_id, name, date, venue, team_name, time_slot, team_leader_name, team_leader_email, team_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (ticket_id, event, 'TBD', 'TBD', team_name, time_slot, team_leader_name, team_leader_email, team_size))
        conn.commit()
        cursor.close()
        conn.close()

        # Generate the ticket PDF
        pdf_path = generate_ticket_pdf(ticket_id, event, team_name, time_slot)

        return send_file(pdf_path, as_attachment=True, download_name=f"ticket_{ticket_id}.pdf")

    return render_template('booking.html', event=event, time_slots=time_slots)

def generate_ticket_pdf(ticket_id, event, team_name, time_slot):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Event Ticket", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Ticket ID: {ticket_id}", ln=True)
    pdf.cell(200, 10, txt=f"Event: {event}", ln=True)
    pdf.cell(200, 10, txt=f"Team Name: {team_name}", ln=True)
    pdf.cell(200, 10, txt=f"Time Slot: {time_slot}", ln=True)
    pdf.cell(200, 10, txt="Date: TBD", ln=True)
    pdf.cell(200, 10, txt="Venue: TBD", ln=True)

    # Save the PDF to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)

    return temp_file.name

@app.route('/add-event', methods=['GET', 'POST'])
def add_event():
    return render_template('add.html')

@app.route('/add-event-past', methods=['GET', 'POST'])
def add_event_past():
    return render_template('add_past.html')


@app.route('/add-events', methods=['GET', 'POST'])
def add_events():
    if request.method == 'POST':
        title = request.form['name']
        description = request.form['description']
        date = request.form['date']
        venue = request.form['venue']  # Assuming you have a column for venue in your database
        created_by = 'event_manager'  # Replace with actual user identification

        # Get the uploaded image
        image_file = request.files['file']
        image_data = image_file.read()

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO events (name, description, date, venue, created_by, image) VALUES (%s, %s, %s, %s, %s, %s)',
                    (title, description, date, venue, created_by, image_data))
        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('eveorg'))

@app.route('/add-events-past', methods=['GET', 'POST'])
def add_events_past():
    if request.method == 'POST':
        title = request.form['name']
        description = request.form['description']
        date = request.form['date']
        venue = request.form['venue']  # Assuming you have a column for venue in your database
        created_by = 'event_manager'  # Replace with actual user identification

        # Get the uploaded image
        image_file = request.files['file']
        image_data = image_file.read()

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO past_events (name, description, date, venue, created_by, image) VALUES (%s, %s, %s, %s, %s, %s)',
                    (title, description, date, venue, created_by, image_data))
        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('eveorg'))

@app.route('/get_image/<int:id>')
def get_image(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT image FROM events WHERE id = %s', (id,))
    image_data = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if image_data and image_data[0]:
        # Send the image as a response
        response = make_response(image_data[0])
        response.headers.set('Content-Type', 'image/jpg')  # Set appropriate content type
        return response
    return '', 404

@app.route('/get_image_past/<int:id>')
def get_image_past(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT image FROM past_events WHERE id = %s', (id,))
    image_data = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if image_data and image_data[0]:
        # Send the image as a response
        response = make_response(image_data[0])
        response.headers.set('Content-Type', 'image/jpg')  # Set appropriate content type
        return response
    return '', 404


@app.route('/event/<int:id>')
def event_details(id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events WHERE id = %s', (id,))
    event = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if event:
        return render_template('event_details.html', event=event)
    return 'Event not found', 404

@app.route('/event/<string:name>')
def event_details_admin(name):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM events WHERE name = %s', (name,))
    event = cursor.fetchone()
    cursor.close()
    connection.close()
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM bookings WHERE name = %s', (name,))
    bookings = cursor.fetchall()
    cursor.close()
    connection.close()
    if event:
        return render_template('sample2.html', event=event, bookings=bookings)
    return 'Event not found', 404

@app.route('/profile/<string:name>')
def profile(name):
    mail = session['mail']
    print(mail)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM accounts WHERE name = %s', (name,))
    user = cursor.fetchone()

    cursor.close()
    if not user:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM managers WHERE name = %s', (name,))
        user = cursor.fetchone()
        cursor.close()
    conn.close()
    
    if user:
        return render_template('profile.html', user=user)
    else:
        return "User not found", 404

@app.route('/logout')
def logout():
    # session.pop('mail', None)
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route("/feedbacksubmit", methods=['POST'])
def feedbacksubmit():
    name = request.form['name']
    email = request.form['email']
    feedback = request.form['feedback']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('INSERT INTO feedback(name, email, feedback) VALUES(%s,%s,%s)', (name,email,feedback))
    conn.commit()
    flash('Feedback submitted successfully', 'success')
    cursor.close()
    conn.close()

    return redirect(url_for('homepage'))

if __name__ == '__main__':
    app.run(debug=True)

