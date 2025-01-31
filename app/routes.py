from flask import Flask, request, jsonify, redirect, url_for, render_template, session, flash, current_app
from app import app, db
from app.models import User, Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from flask_login import login_user, current_user, LoginManager, logout_user, login_required
from app.forms import LoginForm
from urllib.parse import urlparse
from sqlalchemy import func, extract
import json
import random
from huggingface_hub import InferenceClient


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/')
def home():
    user = session.get('user')
    if user:
        return render_template('index.html', user=user)
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Username already exists'})
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(email=email).first():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Email already registered'})
            flash('Email already registered. Please use another email or login.', 'danger')
            return redirect(url_for('signup'))
        
        # Validate required fields
        required_fields = {
            'username': username,
            'email': email,
            'password': password,
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'occupation': request.form.get('occupation')
        }
        
        for field, value in required_fields.items():
            if not value:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': f'Please fill in your {field}'})
                flash(f'Please fill in your {field}.', 'danger')
                return redirect(url_for('signup'))
        
        # Validate goals and distractions
        goals = request.form.getlist('goals')
        distractions = request.form.getlist('distractions')
        
        if not goals or not distractions:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Please select at least one goal and distraction'})
            flash('Please select at least one goal and distraction.', 'danger')
            return redirect(url_for('signup'))
        
        # Create new user
        try:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                age=request.form.get('age'),
                gender=request.form.get('gender'),
                occupation=request.form.get('occupation'),
                goals=",".join(goals),
                distractions=",".join(distractions)
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Force logout if there's any existing session
    if current_user.is_authenticated or 'user' in session:
        logout_user()
        session.clear()
        return redirect(url_for('login'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            # Clear any existing session data before login
            session.clear()
            
            # Log the user in
            login_user(user, remember=False)
            
            # Create new session
            session['user'] = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'login_time': datetime.utcnow().timestamp()
            }
            
            # Get the next page or default to timer
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('timer')
            
            flash('Successfully logged in!', 'success')
            return redirect(next_page)
        
        flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    # First clear Flask-Login
    logout_user()
    
    # Clear Flask session completely
    session.clear()
    
    # Clear all cookies
    response = redirect(url_for('home'))
    response.delete_cookie('remember_token')
    response.delete_cookie('session')
    
    # Clear any other potential cookies
    for cookie in request.cookies:
        response.delete_cookie(cookie)
    
    flash('You have been successfully logged out.', 'success')
    return response

@app.route('/timer')
@login_required
def timer():
    print("\n=== Timer Route ===")
    print(f"Current user authenticated: {current_user.is_authenticated}")
    print(f"Session data: {session}")
    return render_template('timer.html')

@app.route('/save-session', methods=['POST'])
@login_required
def save_session():
    data = request.get_json()
    user_id = current_user.id

    new_session = Session(
        user_id=user_id,
        session_type=data['session_type'],
        duration=data['duration'],
        timestamp=datetime.utcnow()
    )

    db.session.add(new_session)
    db.session.commit()

    return jsonify({'message': 'Session saved successfully'})

@app.route('/profile')
@login_required
def profile():
    # Verify user is properly authenticated
    if not current_user.is_authenticated or 'user' not in session:
        logout_user()
        session.clear()
        flash('Please login to view your profile.', 'info')
        return redirect(url_for('login'))
    
    # Get user's sessions
    sessions = Session.query.filter_by(user_id=current_user.id).order_by(Session.timestamp.desc()).limit(10).all()
    
    # Calculate total sessions and hours
    total_sessions = Session.query.filter_by(user_id=current_user.id).count()
    total_seconds = db.session.query(db.func.sum(Session.duration)).filter_by(user_id=current_user.id).scalar() or 0
    total_hours = round(total_seconds / 3600, 1)  # Convert seconds to hours
    
    return render_template('profile.html', 
                         sessions=sessions,
                         total_sessions=total_sessions,
                         total_hours=total_hours)

# Add this to ensure user session is checked on each request
@app.before_request
def before_request():
    # Skip check for login and static routes
    if request.endpoint in ['login', 'static', 'logout', 'home']:
        return

    if current_user.is_authenticated:
        # Verify session is valid and not expired
        user_session = session.get('user')
        if not user_session or user_session.get('id') != current_user.id:
            # Invalid session, force logout
            logout_user()
            session.clear()
            flash('Your session has expired. Please login again.', 'info')
            return redirect(url_for('login'))
        
        # Check session age (optional: logout after 24 hours)
        login_time = user_session.get('login_time', 0)
        if datetime.utcnow().timestamp() - login_time > 86400:  # 24 hours
            logout_user()
            session.clear()
            flash('Your session has expired. Please login again.', 'info')
            return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Example: Fetch user-specific data if needed
    # user_data = fetch_user_data(current_user.id)

    # Prepare any other necessary data for the dashboard
    # For now, we are focusing on activity suggestions

    # Get activity suggestions
    activity_suggestions = suggest_activities(current_user)

    return render_template('dashboard.html',
                           activity_suggestions=activity_suggestions)

def calculate_streak(daily_sessions):
    if not daily_sessions:
        return {'current_streak': 0, 'best_streak': 0}

    current_streak = 0
    best_streak = 0
    
    # Ensure we're working with a date object
    current_date = datetime.utcnow().date()

    # Debug print
    print("First few daily sessions:", [session.date for session in daily_sessions[:3]])
    
    # Convert daily_sessions dates to datetime.date objects
    session_dates = set()
    for session in daily_sessions:
        try:
            # Print the type and value of session.date for debugging
            print(f"Processing date: {session.date}, Type: {type(session.date)}")
            
            if isinstance(session.date, str):
                date_obj = datetime.strptime(session.date, '%Y-%m-%d').date()
            elif isinstance(session.date, datetime):
                date_obj = session.date.date()
            else:
                date_obj = session.date
            
            session_dates.add(date_obj)
            print(f"Converted to: {date_obj}, Type: {type(date_obj)}")
            
        except Exception as e:
            print(f"Error processing date: {e}")
            continue

    print("Processed dates:", sorted(list(session_dates)))

    # Calculate current streak
    temp_date = current_date
    while temp_date in session_dates:
        current_streak += 1
        temp_date = temp_date - timedelta(days=1)

    # Calculate best streak
    dates_list = sorted(list(session_dates))
    
    if not dates_list:
        return {'current_streak': 0, 'best_streak': 0}
    
    temp_streak = 1
    best_streak = 1
    
    for i in range(1, len(dates_list)):
        if (dates_list[i] - dates_list[i-1]).days == 1:
            temp_streak += 1
            best_streak = max(best_streak, temp_streak)
        else:
            temp_streak = 1

    return {
        'current_streak': current_streak,
        'best_streak': best_streak
    }

def suggest_activities(user):
    activities = []

    # Example interests and corresponding activities
    interest_activities = {
        'reading': ['Read a chapter of a book', 'Explore a new article'],
        'fitness': ['Do a quick workout', 'Take a brisk walk'],
        'meditation': ['Practice mindfulness', 'Try a breathing exercise'],
        'creativity': ['Sketch something', 'Write a short story'],
    }

    # Example goals and corresponding activities
    goal_activities = {
        'learn a new language': ['Practice vocabulary', 'Watch a short video in the language'],
        'improve fitness': ['Do a quick workout', 'Stretch'],
        'reduce stress': ['Meditate', 'Listen to calming music'],
    }

    # Suggest activities based on interests
    for interest in user.interests:
        if interest in interest_activities:
            activities.extend(interest_activities[interest])

    # Suggest activities based on goals
    for goal in user.goals:
        if goal in goal_activities:
            activities.extend(goal_activities[goal])

    # Filter activities based on preferred break activities
    if user.preferred_break_activities:
        activities = [activity for activity in activities if any(pref in activity for pref in user.preferred_break_activities)]

    # Limit to a few suggestions
    return activities[:3]

def suggest_stress_relief_activity():
    activities = [
        'Take a 5-minute walk outside',
        'Do a quick stretching routine',
        'Practice deep breathing for 3 minutes',
        'Listen to your favorite song',
        'Doodle or draw something fun',
        'Watch a short, funny video',
        'Try a quick meditation session',
        'Play a quick online game',
        'Write a short, positive note to yourself',
        'Solve a small puzzle or brain teaser'
    ]
    return random.choice(activities)

def suggest_ai_break_activity(break_type='short'):
    try:
        print("\n=== Starting AI Break Activity Suggestion ===")
        
        client = InferenceClient(
            "mistralai/Mistral-Nemo-Instruct-2407",
            token=current_app.config['HUGGING_FACE_API_KEY']
        )
        
        current_hour = datetime.now().hour
        time_of_day = (
            "morning" if 5 <= current_hour < 12
            else "afternoon" if 12 <= current_hour < 17
            else "evening"
        )
        
        duration = "5 minutes" if break_type == 'short' else "15-20 minutes"
        
        prompt = f"""<|im_start|>user
Create a fun and energizing {duration} break activity for {time_of_day}!
Rules:
- Must be specific and actionable
- Include a fun element or challenge
- Keep it under 3 sentences
- No passive activities
- Must be doable at or near desk
- Add an emoji at the start

Example format:
🎯 Quick Challenge: Do 5 desk push-ups, then try balancing a pencil on your nose for 10 seconds. Beat your record!

Please provide ONE activity following this format.<|im_end|>
<|im_start|>assistant"""

        response = client.text_generation(
            prompt,
            max_new_tokens=100,
            temperature=0.9,
            top_p=0.9,
            repetition_penalty=1.2,
            do_sample=True,
            seed=random.randint(1, 1000)
        )
        
        suggestion = response.strip()
        suggestion = suggestion.split("assistant")[-1].strip()
        suggestion = suggestion.split("<|im_")[0].strip()
        
        if not suggestion or "snooze" in suggestion.lower():
            raise Exception("Invalid response from model")
            
        return suggestion

    except Exception as e:
        print(f"\nError in AI suggestion: {e}")
        default_activities = {
            'short': [
                "🎯 Quick Challenge: Do 5 desk push-ups, then try balancing a pencil on your nose for 10 seconds!",
                "💪 Power Break: 10 jumping jacks + 5 arm circles + Strike a superhero pose!",
                "🎨 Creative Burst: Speed-draw a funny doodle in 1 minute using your non-dominant hand.",
                "🌟 Energy Boost: Dance to your favorite song's chorus, then do 5 star jumps!",
                "🎪 Circus Time: Practice juggling with 2 stress balls for 1 minute - how many catches can you make?",
                "🎭 Mirror Game: Make 5 funny faces in the mirror, hold each for 10 seconds!",
                "🎪 Balance Master: Stand on one leg while spelling your name backwards!",
                "🎯 Office Olympics: Paper ball basketball - 3 shots into the bin from increasing distances!",
                "🌈 Rainbow Stretch: Touch 5 different colored objects while stretching different muscles!",
                "🎪 Desk Acrobat: Do 5 chair spins while lifting your feet off the ground!"
            ],
            'long': [
                "🎮 Movement Quest: Complete 3 rounds of desk exercises, level up by adding 2 reps each round!",
                "🎨 Creative Circuit: Draw, stretch, and dance - 5 minutes each, make it fun and silly!",
                "🎯 Office Adventure: Create a mini obstacle course using office items, beat your best time!",
                "🎪 Circus Training: Learn a simple juggling pattern, practice for 10 minutes!",
                "🎭 Drama Break: Act out 5 different emotions while doing simple exercises!",
                "🌈 Color Challenge: Find and touch objects of every rainbow color while exercising!",
                "🎪 Balance Master Pro: Practice flamingo stands while doing arm exercises!",
                "🎯 Skill Builder: Learn a new pen spinning trick while taking a walking break!",
                "🎨 Art & Move: Draw something while standing on one leg, switch legs every minute!",
                "🎮 Office Game: Create and complete a fun workout using only office supplies!"
            ]
        }
        return random.choice(default_activities[break_type])

@app.route('/start_break', methods=['POST'])
@login_required
def start_break():
    data = request.get_json()
    break_type = data.get('type', 'short')
    
    print(f"\n=== Starting Break Session ===")
    print(f"Break type: {break_type}")
    
    # Get AI-generated activity suggestion
    activity_suggestion = suggest_ai_break_activity(break_type)
    
    print(f"Final activity suggestion: {activity_suggestion}")
    
    return jsonify({'activity': activity_suggestion})