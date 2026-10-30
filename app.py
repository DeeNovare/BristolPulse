

from re import search

from flask import Flask, render_template, request, redirect, url_for, flash, session
import dbfunc
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-only-change-me")




@app.route('/')
def home():
    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.event_id, e.event_name, v.venue_name
        FROM Event e
        JOIN Venue v ON e.venue_id = v.venue_id
        WHERE e.is_active = TRUE
        LIMIT 3
    """)

    events = cursor.fetchall()
    conn.close()

    return render_template('Homepage2.html', events=events, current_page='home')




@app.route('/about')
def about():
   return render_template('About.html', current_page='about')




@app.route('/contact')
def contact():
   return render_template('ContactUs.html', current_page='contact')




@app.route('/events')
def events():
    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    search = request.args.get('search')
    category = request.args.get('category')
    date = request.args.get('date')

    query = """
    SELECT 
        e.event_id, 
        e.event_name, 
        e.event_description, 
        MIN(d.day_date) AS start_date, 
        MAX(d.day_date) AS end_date, 
        MIN(d.start_datetime) AS start_time, 
        MAX(d.end_datetime) AS end_time, 
        MIN(d.day_price) AS price
    FROM Event e
    JOIN EventDay d ON e.event_id = d.event_id
    WHERE e.is_active = TRUE
    """

    params = []

    if search:
        query += " AND e.event_name LIKE %s"
        params.append(f"%{search}%")

    if category:
        query += " AND e.category_id = %s"
        params.append(category)

    if date:
        query += " AND d.day_date = %s"
        params.append(date)

    query += " GROUP BY e.event_id ORDER BY start_date"

    cursor.execute(query, params)
    events = cursor.fetchall()

    conn.close()
    return render_template('Events.html', events=events, current_page='events')
   

@app.route('/event/<int:event_id>')
def event_details(event_id):
    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Main event info
    event_query = """
        SELECT
            e.event_id, 
            e.event_name, 
            e.event_description, 
            v.venue_name, 
            v.address, 
            c.category_name, 
            MIN(d.day_price) AS price
        FROM Event e
        JOIN Venue v ON e.venue_id = v.venue_id
        JOIN EventCategory c ON e.category_id = c.category_id
        JOIN EventDay d ON e.event_id = d.event_id
        WHERE e.event_id = %s
        GROUP BY e.event_id
    """
    cursor.execute(event_query, (event_id,))
    event = cursor.fetchone()
    # All dates / times for this event
    dates_query = """
        SELECT event_day_id, day_date, start_datetime, end_datetime, day_price
        FROM EventDay
        WHERE event_id = %s
        ORDER BY day_date, start_datetime
    """
    cursor.execute(dates_query, (event_id,))
    event_days = cursor.fetchall()
    conn.close()

    if not event:
        return "Event not found", 404

    return render_template('event_detail.html', event=event, event_days=event_days, current_page='event_details')



@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            b.booking_id,
            b.num_tickets,
            b.status,
            b.booking_datetime,
            b.refund_amount,
            e.event_name,
            v.venue_name,
            d.day_date,
            d.start_datetime,
            d.end_datetime,
            d.day_price
        FROM Booking b
        JOIN EventDay d ON b.event_day_id = d.event_day_id
        JOIN Event e ON d.event_id = e.event_id
        JOIN Venue v ON e.venue_id = v.venue_id
        WHERE b.user_id = %s
        ORDER BY d.day_date ASC
    """

    cursor.execute(query, (session['user_id'],))
    bookings = cursor.fetchall()
    conn.close()

    return render_template('my_bookings.html', bookings=bookings, current_page='my_bookings')

@app.route('/book/<int:event_id>', methods=['POST'])
def book_event(event_id):
    if 'user_id' not in session:
        flash('Please log in to book tickets.', 'warning')
        return redirect(url_for('login'))

    event_day_id = request.form['event_day_id']
    num_tickets = int(request.form['num_tickets'])

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor()

    # --- Get base price ---
    cursor.execute("""
        SELECT day_price FROM EventDay WHERE event_day_id = %s
    """, (event_day_id,))
    price = cursor.fetchone()[0]

    total_price = price * num_tickets

    # --- Check if user is a student ---
    cursor.execute("""
        SELECT is_student FROM User WHERE user_id = %s
    """, (session['user_id'],))
    user = cursor.fetchone()

    discount_applied = False

    if user and user[0]:  # is_student = True
        total_price *= Decimal('0.9')  # 10% discount
        discount_applied = True

    total_price = Decimal(total_price).quantize(Decimal('0.01'))  # Round to 2 decimal places

    print("SESSION USER ID:", session.get('user_id'))
    # --- Insert booking ---
    query = """
        INSERT INTO Booking (user_id, event_day_id, num_tickets, status, total_price)
        VALUES (%s, %s, %s, 'confirmed', %s)
    """

    cursor.execute(query, (
        session['user_id'],
        event_day_id,
        num_tickets,
        round(total_price, 2)  # clean money value
    ))

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # --- Feedback ---
    if discount_applied:
        flash('Booking successful! Student discount applied 🎓', 'success')
    else:
        flash('Booking successful!', 'success')

    return redirect(url_for('receipt', booking_id=booking_id))

@app.route('/receipt/<int:booking_id>')
def receipt(booking_id):
    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            b.booking_id,
            b.num_tickets,
            b.total_price,
            b.booking_datetime,
            e.event_name,
            v.venue_name,
            ed.day_date,
            u.is_student,
            ed.day_price,
            ed.start_datetime,
            ed.end_datetime
        FROM Booking b
        JOIN User u ON b.user_id = u.user_id
        JOIN EventDay ed ON b.event_day_id = ed.event_day_id
        JOIN Event e ON ed.event_id = e.event_id
        JOIN Venue v ON e.venue_id = v.venue_id
        WHERE b.booking_id = %s
    """

    cursor.execute(query, (booking_id,))
    booking = cursor.fetchone()
    if booking:
        if booking['is_student']:
            discount = booking['total_price'] * Decimal('0.10')
        else:
            discount = 0

    final_price = booking['total_price'] - discount
    conn.close()

    return render_template("receipt.html", booking=booking, discount=discount, final_price=final_price)

# CANCEL BOOKING
@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        flash('Please log in.', 'warning')
        return redirect(url_for('login'))

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get booking info
    cursor.execute("""
    SELECT b.booking_id, b.booking_datetime, d.day_date, b.total_price
    FROM Booking b
    JOIN EventDay d ON b.event_day_id = d.event_day_id
    WHERE b.booking_id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']))

    booking = cursor.fetchone()

    if not booking:
        conn.close()
        return "Booking not found", 404

    # --- BASIC cancellation logic ---
    from datetime import datetime

    event_date = booking['day_date']
    today = datetime.now().date()

    days_left = (event_date - today).days
    

    # Simple rule 
    if days_left >= 40:
        penalty = Decimal('0')
    elif 25 <= days_left < 40:
        penalty = Decimal('0.4')
    else:
        penalty = Decimal('1.0')

    total_price = booking['total_price']

    refund = total_price * (Decimal('1.0') - penalty)

    

    # Update booking
    cursor.execute("""
    UPDATE Booking
    SET status = 'cancelled',
        cancellation_datetime = NOW(),
        refund_amount = %s
    WHERE booking_id = %s
    """, (refund, booking_id))

    conn.commit()
    conn.close()

    flash(f'Booking cancelled. Refund: £{refund:.2f} (Penalty: {int(penalty*100)}%)', 'info')
    
    return redirect(url_for('my_bookings'))







@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = dbfunc.get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM User WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['first_name'] = user['first_name']
            session['user_type'] = user['user_type']

            flash('Login successful!', 'success')
            
            if user['user_type'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('events'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', current_page='login')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'), code=303,)  # Use 303 to redirect after GET



@app.route('/signup', methods=['GET', 'POST'])
def signup():
   if request.method == 'POST': # here below is so that flask will read and actually do shit with user data
      first_name = request.form['first_name']
      last_name = request.form['last_name']
      email = request.form['email']
      password = request.form['password']
      confirm_password = request.form['confirm_password']
      if password != confirm_password:
        return render_template('signup.html', error="Passwords are not identical", first_name=first_name, last_name=last_name, email=email)
      password_hash = generate_password_hash(password)
      is_student = 'is_student' in request.form
      
      conn = dbfunc.get_db_connection()
      cursor = conn.cursor()

      cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
      existing_user = cursor.fetchone()
      if existing_user:
        return render_template('signup.html', error="Email already registered", first_name=first_name, last_name=last_name)

# wtf does this query do????what does it mean??? It does shit from the databaseeeeee
      query = """
      INSERT INTO User (first_name, last_name, email, password_hash, is_student, user_type)
      VALUES (%s,%s,%s,%s,%s,'standard')
      """
      # get the new user's ID
      user_id = cursor.lastrowid

        # store in session
      session['user_id'] = user_id
      session['first_name'] = first_name
      session['user_type'] = 'standard'
      cursor.execute(query, (first_name, last_name, email, password_hash, is_student))

      conn.commit()
      conn.close()

      flash('Account created successfully!', 'success')
      return redirect(url_for('events'))
   return render_template('signup.html', current_page='signup')



# ------------ADMIN SIDE OF ROUTES:

def is_admin():
    return 'user_id' in session and session.get('user_type') == 'admin'

@app.route('/admin')
def admin_dashboard():
    if not is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # EVENT TABLE
    query = """
        SELECT e.event_id, e.event_name, e.is_active, v.venue_name
        FROM Event e
        JOIN Venue v ON e.venue_id = v.venue_id
        ORDER BY e.event_id DESC
    """

    cursor.execute(query)
    events = cursor.fetchall()
    

    # BOOKINGS REPORT
    cursor.execute("""
    SELECT e.event_name, COUNT(b.booking_id) AS total_bookings
    FROM Event e
    LEFT JOIN EventDay d ON e.event_id = d.event_id
    LEFT JOIN Booking b ON d.event_day_id = b.event_day_id
    GROUP BY e.event_id
    """)
    bookings_report = cursor.fetchall()

    # REVENUE REPORT
    cursor.execute("""
    SELECT e.event_name, SUM(b.total_price) AS revenue
    FROM Event e
    LEFT JOIN EventDay d ON e.event_id = d.event_id
    LEFT JOIN Booking b ON d.event_day_id = b.event_day_id
    WHERE b.status = 'confirmed'
    GROUP BY e.event_id
    """)
    revenue_report = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', events=events, current_page='admin_dashboard', bookings_report=bookings_report, revenue_report=revenue_report)

# Toggle event active/inactive
@app.route('/toggle-event/<int:event_id>', methods=['POST'])
def toggle_event(event_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        return "Access denied", 403

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Event SET is_active = NOT is_active WHERE event_id = %s
    """, (event_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))



# ---EVENT MANAGEMENT ROUTES:

@app.route('/add-event', methods=['GET', 'POST'])
def add_event():
    if session.get('user_type') != 'admin':
        return "Access denied", 403

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_description = request.form['event_description']
        venue_id = request.form['venue_id']
        category_id = request.form['category_id']

        day_date = request.form['day_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        price = request.form['price']

        # Insert into Event
        cursor.execute("""
            INSERT INTO Event (venue_id, category_id, event_name, event_description, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (venue_id, category_id, event_name, event_description))

        event_id = cursor.lastrowid

        # Insert into EventDay
        cursor.execute("""
            INSERT INTO EventDay (event_id, day_date, start_datetime, end_datetime, day_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            event_id,
            day_date,
            f"{day_date} {start_time}",
            f"{day_date} {end_time}",
            price
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('add_event.html', current_page='add_event')

@app.route('/admin/edit-event/<int:event_id>', methods=['GET'])
def edit_event(event_id):
    if not is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('events'))

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT event_id, event_name, event_description, venue_id, category_id
        FROM Event
        WHERE event_id = %s
    """
    cursor.execute(query, (event_id,))
    event = cursor.fetchone()

    conn.close()

    return render_template('edit_event.html', event=event, current_page='edit_event')  

@app.route('/admin/edit-event/<int:event_id>', methods=['POST'])
def update_event(event_id):
    if not is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('events'))

    event_name = request.form['event_name']
    event_description = request.form['event_description']
    venue_id = request.form['venue_id']
    category_id = request.form['category_id']

    conn = dbfunc.get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE Event
        SET event_name=%s,
            event_description=%s,
            venue_id=%s,
            category_id=%s
        WHERE event_id=%s
    """

    cursor.execute(query, (
        event_name,
        event_description,
        venue_id,
        category_id,
        event_id
    ))

    conn.commit()
    conn.close()

    flash('Event updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'), code=303)  # Use 303 to redirect after POST

   


# remember to take this out:
if __name__ == '__main__':
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")