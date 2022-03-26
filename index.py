from flask import Flask, request, render_template, url_for, redirect, flash, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient('localhost', 27017)
db = client.wad
app = Flask(__name__)
app.secret_key = 'super secret key'
auth = HTTPBasicAuth()


def checkPassword(username, password):
    user = db.users.find_one({"username": username})
    if user:
        if check_password_hash(user['password'], password):
            session['logged'] = f"{user['_id']}"
            return True
    return False

def getLoggedUsername():
    if 'logged' in session:
        user = db.users.find_one(ObjectId(session['logged']))
        if user:
            return user['username']
        session.pop('logged', None)
    return ''

def getProfilePic():
    user = db.users.find_one(ObjectId(session['logged']))
    if user:
        if user['profile_pic'] != '':
            return f"{user['profile_pic']}"
    return 'static/icon.png'

@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        username = getLoggedUsername()
        if username == '':
            return render_template("login.html")
        return redirect(url_for('myProfile'))
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        if checkPassword(username, password):
            return redirect(url_for('myProfile'))
        flash('Login Error', 'danger')
        return redirect(request.url)

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        if username == '':
            flash('Invalid Username', 'danger')
            return redirect(request.url)
        if db.users.find_one({"username": username}) is not None:
            flash('That Username is taken!', 'danger')
            return redirect(request.url)
        if password == '':
            flash('Invalid Password', 'danger')
            return redirect(request.url)
        db.users.insert_one({"username": username, "password": generate_password_hash(password), "profile_pic": ''})
        print(f"{username} - {password} SALVO")
        return redirect('/login')

@app.route('/profile')
def myProfile():
    username = getLoggedUsername()
    if username != '':
        return render_template("myProfile.html", username=username, profilePic=getProfilePic())
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if 'logged' in session:
        session.pop('logged', None)
    return redirect('/')

@app.route('/changePassword', methods=["GET", "POST"])
def changePassword():
    if request.method == "GET":
        return render_template("changePassword.html")
    else:
        username = getLoggedUsername()
        if username == '':
            return redirect(url_for('login'))
        oldPassword = request.form.get("oldPassword")
        newPassword = request.form.get("newPassword")
        if oldPassword == '':
            flash('Invalid Old Password', 'danger')
            return redirect(request.url)
        if newPassword == '':
            flash('Invalid New Password', 'danger')
            return redirect(request.url)
        if checkPassword(username, oldPassword):
            if oldPassword == newPassword:
                flash('New Password must be different from Old Password', 'danger')
                return redirect(request.url)
            db.users.update_one({"username": username}, {"$set": {"password": generate_password_hash(newPassword)}})
            flash('Password Changed', 'success')
            return redirect(url_for('myProfile'))
        flash('Invalid Old Password', 'danger')
        return redirect(request.url)

if __name__ == '__main__':
    db.users.drop()
    from faker import Faker

    faker = Faker()

    db.users.insert_one({"username": "user", "password": generate_password_hash('123'), "profile_pic": ''})

    app.run(host='localhost', port=5000, debug=True)