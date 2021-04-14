import warnings
warnings.filterwarnings('ignore')
import random
import string
import time
import threading
import datetime
from profanity_check import predict
from flask import Flask, render_template, request, redirect, flash, session, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = '45tjrgklvnfehndvjkdsndfrhsejdjhrtrjkghjvffjfbg;ghnjhftkgbjbdfskdlgn'
socketio = SocketIO(app, manage_session=False)
socketio.init_app(app, cors_allowed_origins='*')
csrf = CSRFProtect(app)

play_time = 5 # minutes
queue = []

def val_name(name):
    if predict([name])[0] == 1:
        return 'No profanity lol'
    if 3 > len(name):
        return 'Enter a longer name'
    if 25 < len(name):
        return 'Enter a shorter name'
    return 'success'

def get_keys():
    return [q['key'] for q in queue]

def get_loc(key):
    i = 0
    for person in queue:
        if person['key'] == key:
            return i
        i += 1

def rem(key):
    global queue
    queue = [q for q in queue if q['key'] != key]

@app.before_request
def set_key():
    if not 'key' in session:
        session['key'] = ''.join(random.choices(string.ascii_letters, k=20))

@app.route('/leave')
def leave():
    if session['key'] in get_keys():
        rem(session['key'])
        flash('You left the line')
    return redirect('/')

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'name' in request.form:
            result = val_name(request.form['name'])
            if result == 'success':
                session['name'] = request.form['name']
                queue.append({'key': session['key'], 'name': session['name'], 'start': '', 'end': '', 'sid': ''})
            else:
                flash(result)
        else:
            flash('Invalid input')
        return redirect('/')
    if session['key'] in get_keys() and 'name' in session:
        return render_template('queue.html', name=session['name'])
    else:
        return render_template('home.html')

@socketio.on('connection')
def connect():
    session['sid'] = request.sid
    if session['key'] in get_keys():
        join_room(session['key'])
        if get_loc(session['key']) != None and get_loc(session['key']) != 0:
            emit('queue update', {'location': str(get_loc(session['key'])), 'wait': str(get_loc(session['key']) * play_time)}, room=session['key'])
        if get_loc(session['key']) != None and get_loc(session['key']) == 0:
            end_time = datetime.datetime.now() + datetime.timedelta(minutes=play_time)
            end_time = end_time.strftime('%I:%M %p')
            queue[get_loc(session['key'])]['start'] = datetime.datetime.now().strftime('%I:%M %p')
            queue[get_loc(session['key'])]['end'] = end_time
            msg = f'''
            <div id='info'>
            <p>{session['name']},</p>
        <h2>It's time to play!!!</h2>
        <p><mark>You have until {end_time} to play</mark></p>
        <br>
        <a href="/leave">I'm done</a>
        </div>
        '''
            emit('front of queue', msg, room=session['key'])

@socketio.on('heartbeat')
def update():
    session['sid'] = request.sid
    if len(queue) > 0 and queue[0]['end'] != '' and datetime.datetime.now().time() > datetime.datetime.strptime(queue[0]['end'], '%I:%M %p').time():
        msg = f'''
            <div id='info'>
            <p>{queue[0]['name']},</p>
            <h2>Your time is up!</h2>
            <br>
            <a href="/">Rejoin the line</a>
            </div>
            '''
        socketio.emit('done', msg, room=session['key'])
        rem(session['key'])

    if get_loc(session['key']) != None and get_loc(session['key']) != 0:
        emit('queue update', {'location': str(get_loc(session['key'])), 'wait': str(get_loc(session['key']) * play_time)}, room=session['key'])
    if get_loc(session['key']) != None and get_loc(session['key']) == 0:
        end_time = datetime.datetime.now() + datetime.timedelta(minutes=play_time)
        end_time = end_time.strftime('%I:%M %p')
        queue[get_loc(session['key'])]['start'] = datetime.datetime.now().strftime('%I:%M %p')
        queue[get_loc(session['key'])]['end'] = end_time
        msg = f'''
        <div id='info'>
        <p>{session['name']},</p>
        <h2>It's time to play!!!</h2>
        <p><mark>You have until {end_time} to play</mark></p>
        <br>
        <a href="/leave">I'm done</a>
        </div>
        '''
        emit('front of queue', msg, room=session['key'])

if __name__ == '__main__':
    app.run(port=80, debug=True)