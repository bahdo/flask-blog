from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from data import Articles
from flaskext.mysql import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

Articles = Articles()

# Config MySQL
app.config['MYSQL__DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '******'
app.config['MYSQL_DATABASE_DB'] = 'myflaskapp'
app.config['MYSQL_DATABASE_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL()
mysql.init_app(app)


@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/contact')
def contact():
	return render_template('contact.html')

@app.route('/thugger')
def thugger():
	return render_template('thugpage.html')

@app.route('/articles')
def articles():
	cur = mysql.get_db().cursor()

	result = cur.execute("SELECT * FROM articles")

	articles = cur.fetchall()

	if result > 0:
		return render_template('articles.html', articles=result)
	else:
		msg = 'No articles found'
		return render_template('articles.html', msg=msg)

	cur.close()


@app.route('/article/<string:id>/')
def article(id):
	cur = mysql.get_db().cursor()
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
	article = cur.fetchone()
	return render_template('article.html', article=article)

class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		#create cursor
		cur = mysql.get_db().cursor()
		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

		#commit to db
		mysql.get_db().commit()

		#close connection
		cur.close()

		flash('You are now registered and can log in', 'success')

		return redirect(url_for('login'))
	return render_template('register.html', form=form)

#user login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password_candidate = request.form['password']

		cur = mysql.get_db().cursor()

		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		if result > 0:
			data = cur.fetchone()
			password = data[4]

			#compare passwords
			if sha256_crypt.verify(password_candidate, password):
				#passed
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)
			cur.close()

		else:
			error = 'Username not found'
			return render_template('login.html', error=error)

	return render_template('login.html')

#Check if logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

#logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))



#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

	cur = mysql.get_db().cursor()

	result = cur.execute("SELECT * FROM articles")

	articles = cur.fetchall()

	if result > 0:
		return render_template('dashboard.html', articles=Articles)
	else:
		msg = 'No articles found'
		return render_template('dashboard.html', msg=msg)

	cur.close()


class ArticleForm(Form):
	title = StringField('Title', [validators.Length(min=1, max=200)])
	body = TextAreaField('Body', [validators.Length(min=30)])


@is_logged_in
@app.route('/add_article', methods=['GET', 'POST'])
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data

		cur = mysql.get_db().cursor()

		cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

		mysql.get_db().commit()

		cur.close()

		flash('Article Created', 'success')

		return redirect(url_for('dashboard'))

	return render_template('add_article.html', form=form)



@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	cur = mysql.get_db().cursor()

	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

	article = cur.fetchone()
	cur.close()

	form = ArticleForm(request.form)

	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		cur = mysql.get_db().cursor()

		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s", (title, body, id))
		mysql.get_db().commit()

		cur.close()

		flash('Article Updated', 'success')

		return redirect(url_for('dashboard'))

	return render_template('edit_article.html', form=form)

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	cur = mysql.get_db().cursor()

	cur.execute("DELETE FROM articles WHERE id = %s", [id])

	mysql.get_db().commit()

	cur.close()

	flash('Article Deleted', 'success')

	return redirect(url_for('dashboard'))


if __name__ == '__main__':
	app.secret_key='********'
	app.run(debug=True)
