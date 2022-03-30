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
        user = findById(session['logged'])
        if user:
            return user['username']
        session.pop('logged', None)
    return ''

def findById(id):
    return db.users.find_one(ObjectId(id))

def getProfilePic():
    user = db.users.find_one(ObjectId(session['logged']))
    if user:
        if user['profile_pic'] != '':
            return f"{user['profile_pic']}"
    return 'static/icon.png'

def getPostVisibility():
    if request.form.get("visibility") == 'public':
        return True
    return False

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
        flash('Account Created!', 'success')
        return redirect('/')

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

@app.route('/newPost', methods=["GET", "POST"])
def newPost():
    username = getLoggedUsername()
    if username == '':
        flash('Please, login first', 'danger')
        return redirect(url_for('login'))
    if request.method == "GET":
        return render_template("newPost.html")
    else:
        visibility = getPostVisibility()
        postTitle = request.form.get("postTitle")
        postContent = request.form.get("postContent")
        if postTitle == '':
            flash('The title of the post is empty', 'danger')
            return redirect(url_for('newPost', previousContent = postContent))
        if postContent == '':
            flash('The content of the post is empty', 'danger')
            return redirect(url_for('newPost',  previousTitle = postTitle))
        db.posts.insert_one({"title": postTitle, "content": postContent, "owner": username, "public": visibility})
        flash('Posted!', 'success')
        return redirect(url_for('myProfile'))

@app.route('/posts/update/<postId>', methods=["GET", "POST"])
def updatePost(postId):
    username = getLoggedUsername()
    if username == '':
        flash('Please, login first', 'danger')
        return redirect(url_for('login'))
    if request.method == "GET":
        post = db.posts.find_one(ObjectId(postId))
        if post:
            if post['owner'] != username:
                flash('You are not the owner of that post', 'danger')
                return redirect(url_for('myProfile'))
            return render_template("updatePost.html", postId=post['_id'], previousTitle = post['title'], previousContent = post['content'], public = post['public'])
        flash('Post not found', 'danger')
        return redirect(url_for('myProfile'))
    else:
        postId = request.form.get("postId")
        postTitle = request.form.get("postTitle")
        postContent = request.form.get("postContent")
        visibility = getPostVisibility()
        post = db.posts.find_one(ObjectId(postId))
        if post and post['owner'] != username:
            flash('You are not the owner of that post', 'danger')
            return redirect(url_for('myProfile'))
        if postTitle == '':
            flash('The title of the post is empty', 'danger')
            return render_template("updatePost.html", postId=postId, previousTitle = post['title'], previousContent = postContent, public = visibility)
        if postContent == '':
            flash('The content of the post is empty', 'danger')
            return render_template("updatePost.html", postId=postId, previousTitle = postTitle, previousContent = post['content'], public = visibility)
        db.posts.update_one({"_id": ObjectId(postId)}, {"$set": {"title": postTitle, "content": postContent, "public": visibility}})
        flash('Post Updated', 'success')
        return redirect(url_for('posts'))

@app.route('/posts')
def posts():
    username = getLoggedUsername()
    posts = db.posts.find({"public": True})
    return render_template("posts.html", posts=posts, username=username)

@app.route('/myPosts')
def myPosts():
    username = getLoggedUsername()
    if username != '':
        posts = db.posts.find({"owner": username})
        return render_template("posts.html", posts=posts, username=username)
    return redirect(url_for('login'))


if __name__ == '__main__':
    db.users.drop()
    from faker import Faker

    faker = Faker()

    db.users.insert_one({"username": "user", "password": generate_password_hash('123'), "profile_pic": ''})

    app.run(host='localhost', port=5000, debug=True)