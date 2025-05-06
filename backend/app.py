from datetime import datetime
import httpx
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, session, make_response, redirect, url_for, flash
from supabase import create_client, Client
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


# Supabase credentials
SUPABASE_URL = "https://ssazaghelgambfsamnmh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNzYXphZ2hlbGdhbWJmc2Ftbm1oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU5MzM4MjksImV4cCI6MjA2MTUwOTgyOX0.ZEQ_HsAAUl2lKAyk2fwhcamQPppb7AsHN7clmOJU7EM"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin credentials (hardcoded for now, can later be replaced with a database check)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"  # Replace with secure password management later

# Admin login route


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True  # Set the admin session
            # Redirect to the admin dashboard
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials", 403  # Return error if credentials are wrong

    # Render the login page for GET requests
    return render_template('admin_login.html')

# Admin dashboard (accessible only if logged in)


@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if the user is logged in as admin
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        # Redirect to admin login if not logged in
        return redirect(url_for('admin_login'))

    try:
        # Fetch movies, showtimes, and seats data for the admin dashboard
        movies_data = supabase.table("movies").select("*").execute()
        showtimes_data = supabase.table("showtimes").select("*").execute()
        seats_data = supabase.table("seats").select("*").execute()

        # Prepare data for rendering
        movies = movies_data.data
        showtimes = showtimes_data.data
        seats = seats_data.data

        return render_template('admin_dashboard.html', movies=movies, showtimes=showtimes, seats=seats)
    except httpx.ConnectError as e:
        return f"Connection Error: {str(e)}", 500
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@app.route('/admin/add_movie', methods=['GET', 'POST'])
def add_movie():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        # Redirect to admin login if not logged in
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        # Retrieve data from form
        title = request.form['title']
        description = request.form['description']
        image_url = request.form['image_url']

        try:
            # Insert movie data into the database
            supabase.table("movies").insert({
                "title": title,
                "description": description,
                "poster_url": image_url
            }).execute()

            # Redirect to admin dashboard after adding movie
            return redirect(url_for('admin_dashboard'))
        except httpx.ConnectError as e:
            return f"Connection Error: {str(e)}", 500
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    return render_template('add_movie.html')


@app.route('/admin/edit_movie/<int:movie_id>', methods=['GET', 'POST'])
def edit_movie(movie_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image_url = request.form['image_url']  # ✅ Match the input field name

        try:
            supabase.table("movies").update({
                "title": title,
                "description": description,
                "poster_url": image_url  # ✅ Correct Supabase column name
            }).eq("id", movie_id).execute()

            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    try:
        response = supabase.table("movies").select(
            "*").eq("id", movie_id).single().execute()
        movie = response.data
    except Exception as e:
        return f"Could not retrieve movie: {str(e)}", 500

    return render_template('edit_movie.html', movie=movie)


@app.route('/admin/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))

    try:
        supabase.table("movies").delete().eq("id", movie_id).execute()
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        return f"An error occurred while deleting the movie: {str(e)}", 500


@app.route('/admin/add_showtime', methods=["GET", "POST"])
def add_showtime():
    if request.method == "POST":
        try:
            movie_id = request.form['movie_id']
            showtime_datetime = request.form['datetime']

            # Convert datetime-local to SQL timestamp
            showtime_datetime_obj = datetime.strptime(
                showtime_datetime, '%Y-%m-%dT%H:%M')
            formatted_datetime = showtime_datetime_obj.strftime(
                '%Y-%m-%d %H:%M:%S')

            # Insert showtime
            insert_response = supabase.table("showtimes").insert({
                "movie_id": movie_id,
                "datetime": formatted_datetime
            }).execute()
            showtime_id = insert_response.data[0]['id']

            # Generate seat entries: a1-1 to e3-10 (15 sections, 10 seats each)
            seat_entries = []
            for row in ['A', 'B', 'C', 'D', 'E']:
                for col in ['1', '2', '3']:
                    section = f"{row}{col}"
                    for i in range(1, 11):
                        seat_entries.append({
                            "showtime_id": showtime_id,
                            "seat_number": f"{section}-{i:02d}",
                            "is_booked": False
                        })

            supabase.table("seats").insert(seat_entries).execute()
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            print("Error adding showtime:", e)
            return jsonify({"error": str(e)}), 500
    else:
        movies = supabase.table('movies').select('*').execute().data
        return render_template('admin_add_showtime.html', movies=movies)


@app.route('/admin/edit_showtime/<int:showtime_id>', methods=['GET', 'POST'])
def edit_showtime(showtime_id):
    # Fetch the showtime to edit
    showtime_response = supabase.table('showtimes').select(
        'id, movie_id, datetime'
    ).eq('id', showtime_id).single().execute()
    showtime = showtime_response.data

    if not showtime:
        flash('Showtime not found.', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        movie_id = request.form.get('movie_id')
        # Input field is still named 'start_time'
        datetime_input = request.form.get('start_time')

        if not movie_id or not datetime_input:
            flash('Movie and start time are required.', 'error')
        else:
            try:
                supabase.table('showtimes').update({
                    'movie_id': int(movie_id),
                    'datetime': datetime_input
                }).eq('id', showtime_id).execute()
                flash('Showtime updated successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                flash('Error updating showtime: ' + str(e), 'error')

    # For GET, fetch movies for dropdown
    movies_response = supabase.table('movies').select('id, title').execute()
    movies = movies_response.data if movies_response.data else []
    return render_template('edit_showtime.html', showtime=showtime, movies=movies)


@app.route('/admin/delete_showtime/<int:showtime_id>', methods=['POST'])
def delete_showtime(showtime_id):
    try:
        supabase.table('showtimes').delete().eq('id', showtime_id).execute()
        flash('Showtime deleted successfully.', 'success')
    except Exception as e:
        flash('Error deleting showtime: ' + str(e), 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/manage-seats')
def manage_seats():
    seats = supabase.table('seats').select('*').execute().data
    showtimes = supabase.table('showtimes').select('*').execute().data
    movies = supabase.table('movies').select('*').execute().data

    movie_titles = {movie['id']: movie['title'] for movie in movies}
    for showtime in showtimes:
        showtime['movie_title'] = movie_titles.get(
            showtime['movie_id'], 'Unknown')

    seats = sorted(seats, key=lambda seat: seat['id'])

    return render_template('admin_manage_seats.html', seats=seats, showtimes=showtimes)


@app.route('/admin/book_seat/<int:seat_id>', methods=["POST"])
def admin_book_seat(seat_id):
    try:
        supabase.table("seats").update({
            "is_booked": True
        }).eq("id", seat_id).execute()

        flash("Seat manually marked as booked.")
        return redirect(request.referrer or url_for('manage_seats'))

    except Exception as e:
        print("Error booking seat manually:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/admin/reset_seats", methods=["POST"])
def reset_seats():
    try:
        seat_id = request.args.get("seat_id")
        if seat_id:
            # Reset specific seat
            supabase.table("bookings").delete().eq(
                "seat_id", int(seat_id)).execute()

            supabase.table("seats").update(
                {"is_booked": False, "user_id": None}
            ).eq("id", int(seat_id)).execute()
            flash(f"Seat {seat_id} has been reset.")
        else:
            # Reset all booked seats
            supabase.table("bookings").delete().neq("id", 0).execute()

            booked_seats = supabase.table("seats").select(
                "id").eq("is_booked", True).execute()
            if booked_seats.data:
                for seat in booked_seats.data:
                    supabase.table("seats").update(
                        {"is_booked": False, "user_id": None}
                    ).eq("id", seat["id"]).execute()
                flash("All booked seats have been reset.")
            else:
                flash("No seats were booked.")
        # adjust this if your route name is different
        return redirect(url_for("manage_seats"))
    except Exception as e:
        print("Error during reset:", e)
        flash("An error occurred while resetting seats.")
        return redirect(url_for("manage_seats"))

# Admin logout route


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)  # Remove admin session
    return redirect(url_for('admin_login'))  # Redirect to login page


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Store user in the database
        try:
            supabase.table("users").insert({
                "username": username,
                "password": hashed_password
            }).execute()
            flash("User created successfully!", "success")
            return redirect(url_for('login'))
        except httpx.ConnectError as e:
            flash("Error connecting to the database.", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user by username
        user_data = supabase.table("users").select(
            '*').eq('username', username).single().execute()
        user = user_data.data

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']  # Store user ID in session
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Remove user session (clear user_id)
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# Assign user_id via cookie or session


@app.route('/')
def index():
    # Redirect to login if not logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Fetch movies
        response = supabase.table("movies").select("*").execute()
        movies = response.data

        return render_template('index.html', movies=movies)
    except httpx.ConnectError as e:
        return f"Connection Error: {str(e)}", 500
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    try:
        movie_data = supabase.table('movies').select(
            '*').eq('id', movie_id).single().execute()
        movie = movie_data.data

        showtimes_data = supabase.table('showtimes').select(
            '*').eq('movie_id', movie_id).execute()
        showtimes = showtimes_data.data

        for showtime in showtimes:
            showtime['datetime_obj'] = datetime.fromisoformat(
                showtime['datetime'])
            seats_data = supabase.table('seats').select(
                '*').eq('showtime_id', showtime['id']).order('seat_number').execute()
            for seat in seats_data.data:
                seat['is_booked'] = seat.get('is_booked', False)
            showtime['seats'] = seats_data.data

        movie['showtimes'] = showtimes
        user_id = session.get('user_id')

        return render_template('movie_detail.html', movie=movie, user_id=user_id)

    except httpx.ConnectError as e:
        return f"Connection Error: {str(e)}", 500
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@app.route('/book', methods=['POST'])
def book_seat():
    data = request.get_json()
    seat_id = data.get('seat_id')
    user_id = data.get('user_id')

    # Logic to mark the seat as booked in the database
    try:
        # Update the seat status to booked in the database
        seat = supabase.table('seats').select(
            '*').eq('id', seat_id).execute().data[0]
        if seat['is_booked']:
            return jsonify({"error": "Seat is already booked"}), 400

        # Mark the seat as booked
        supabase.table('seats').update(
            {"is_booked": True, "user_id": user_id}).eq('id', seat_id).execute()

        return jsonify({"message": "Seat booked"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/my_bookings')
def my_bookings():
    try:
        user_id = session.get("user_id")

        seats_data = supabase.table("seats").select(
            "*").eq("user_id", user_id).execute()
        booked_seats = seats_data.data

        showtime_ids = list(set([seat["showtime_id"]
                            for seat in booked_seats]))
        showtimes_data = supabase.table("showtimes").select(
            "*").in_("id", showtime_ids).execute()
        showtimes = {s["id"]: s for s in showtimes_data.data}

        movie_ids = list(set([show["movie_id"]
                         for show in showtimes.values()]))
        movies_data = supabase.table("movies").select(
            "*").in_("id", movie_ids).execute()
        movies = {m["id"]: m for m in movies_data.data}

        for seat in booked_seats:
            showtime = showtimes.get(seat["showtime_id"])
            movie = movies.get(showtime["movie_id"]) if showtime else None
            seat["showtime"] = showtime
            seat["movie"] = movie

        return render_template("my_bookings.html", seats=booked_seats, user_id=user_id)

    except httpx.ConnectError as e:
        return f"Connection Error: {str(e)}", 500
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


@app.template_filter('datetimeformat')
def datetimeformat(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return value
    elif isinstance(value, datetime):
        dt = value
    else:
        return value
    return dt.strftime('%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    app.run(debug=True)
