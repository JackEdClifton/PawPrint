import flask
import flask_sqlalchemy
import datetime

app = flask.Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = flask_sqlalchemy.SQLAlchemy(app)


class Privileges:
	none = 0		# default value for new accounts
	read_only = 1	# can read/search only
	developer = 2	# can create review tickets
	approver = 3	# can approve tickets
	admin = 4		# can manage user accounts

	@classmethod
	def items(cls):
		return [
			(name, value) for name, value in vars(cls).items()
			if (not name.startswith("__") and isinstance(value, int))
		]


class StatusTypes:
	none = 0		# for new accounts
	review = 1		# initial status for new ticket
	corrections = 2	# reviewer has feedback for changes
	closed = 3		# ticket is closed and not implemented
	approved = 4	# changes can be moved back to main branches
	confirm = 5		# changes have been moved
	complete = 6	# reviewer confirms nothing is missing


class Projects(db.Model):
	project_id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), nullable=False, unique=True)


class Users(db.Model):
	user_id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), nullable=False)
	email = db.Column(db.String(128), nullable=False, unique=True)
	privileges = db.Column(db.Integer, nullable=False, default=Privileges.none)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
	updated_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)


class Review(db.Model):
	review_id = db.Column(db.Integer, primary_key=True)
	project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
	branch = db.Column(db.String(64), nullable=False)
	commits = db.Column(db.Text, nullable=False)
	ers_number = db.Column(db.Integer, nullable=False)
	author_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

	project = db.relationship('Projects', backref=db.backref('reviews', lazy=True))
	author = db.relationship('Users', backref=db.backref('authored_reviews', lazy=True))


class Status(db.Model):
	status_id = db.Column(db.Integer, primary_key=True)
	review_id = db.Column(db.Integer, db.ForeignKey('review.review_id'), nullable=False)
	status = db.Column(db.Integer, nullable=False)
	actor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
	modified_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
	notes = db.Column(db.Text)

	# Relationships
	reviewd = db.relationship('Review', backref=db.backref('status_history', lazy=True, cascade="all, delete-orphan"))
	actors = db.relationship('Users', backref=db.backref('status_actions', lazy=True))





with app.app_context():
	db.create_all()



# a shortcut to return the error page
def get_flask_error(error):
	return flask.render_template("error.html", errorcontent=error)





@app.route("/")
def home():
	return flask.render_template("home.html")


@app.route("/projects", methods=["GET", "POST"])
def projects():

	if flask.request.method == "POST":
		project = flask.request.form.get("project")

		if project:
			new_project = Projects(name=project)
			db.session.add(new_project)
			
			try:
				db.session.commit()
			except:
				db.session.rollback()
				return get_flask_error("A project with that name already exists.")

		else:
			return get_flask_error("New project name is invalid.")

	projects = Projects.query.all()
	return flask.render_template("projects.html", projects=projects)



@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):

	project_obj = Projects.query.filter_by(project_id=project_id).first()

	if not project_obj:
		return get_flask_error("Could not locate project with that ID.")

	db.session.delete(project_obj)
	db.session.commit()

	return flask.redirect("/projects")



@app.route("/projects/<int:project_id>/rename", methods=["POST"])
def rename_project(project_id):

	new_project_name = flask.request.form.get("name", "").strip()

	if not new_project_name:
		return get_flask_error("Invalid project name.")

	project_obj = Projects.query.filter_by(project_id=project_id).first()

	if not project_obj:
		return get_flask_error("Could not locate project with that ID.")

	project_obj.name = new_project_name	
	db.session.commit()

	return flask.redirect("/projects")




@app.route("/users", methods=["GET", "POST"])
def users():

	if flask.request.method == "POST":
		name = flask.request.form.get("name")
		email = flask.request.form.get("email")

		if name and email:
			new_user = Users(name=name, email=email)
			db.session.add(new_user)
			
			try:
				db.session.commit()
			except:
				db.session.rollback()
				return get_flask_error("Could not create user.")

		else:
			return get_flask_error("User details not valid. Please try again.")

	users = Users.query.all()
	return flask.render_template("users.html", users=users, privileges=Privileges.items())



@app.route("/signin", methods=["GET", "POST"])
def signin():

	if flask.request.method == "POST":
		return get_flask_error("Not implemented.")


	return flask.render_template("signin.html")









if __name__ == "__main__":
	app.run(debug=True)
