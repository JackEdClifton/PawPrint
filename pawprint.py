import flask
import flask_sqlalchemy
import flask_login
import werkzeug.security
import datetime

app = flask.Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "pawprint"

db = flask_sqlalchemy.SQLAlchemy(app)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "signin"

@login_manager.user_loader
def load_user(user_id):
	return Users.query.get(int(user_id))

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
	
	@classmethod
	def contains_value(cls, value):
		return value in (v for _, v in cls.items())


class StatusTypes:
	none = 0		# should only occur in error
	review = 1		# initial status for new ticket
	corrections = 2	# reviewer has feedback for changes
	closed = 3		# ticket is closed and not implemented
	approved = 4	# changes can be moved back to main branches
	confirm = 5		# changes have been moved
	complete = 6	# reviewer confirms nothing is missing

	@classmethod
	def name(cls, value):
		for k, v in vars(cls).items():
			if not k.startswith("__") and v == value:
				return k
		return "Not found"


class Projects(db.Model):
	project_id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), nullable=False, unique=True)


class Users(db.Model, flask_login.UserMixin):
	user_id = db.Column(db.Integer, primary_key=True)
	f_name = db.Column(db.String(64), nullable=False)
	s_name = db.Column(db.String(64), nullable=False)
	email = db.Column(db.String(128), nullable=False, unique=True)
	password = db.Column(db.String(128), nullable=False)
	privileges = db.Column(db.Integer, nullable=False, default=Privileges.none)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
	updated_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

	def get_id(self):
		return str(self.user_id)


class Review(db.Model):
	review_id = db.Column(db.Integer, primary_key=True)
	project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
	branch = db.Column(db.String(64), nullable=False)
	head_commit = db.Column(db.String(64), nullable=False)
	base_commit = db.Column(db.String(64), nullable=False)
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
	reviews = db.relationship('Review', backref=db.backref('status_history', lazy=True, cascade="all, delete-orphan"))
	actors = db.relationship('Users', backref=db.backref('status_actions', lazy=True))





with app.app_context():
	db.create_all()

	if Users.query.count() == 0:
		db.session.add(Users(f_name="admin", s_name="user", email="admin@localhost",
			privileges=Privileges.admin,
			password=werkzeug.security.generate_password_hash("admin")
		))
		db.session.commit()



# a shortcut to return the error page
def get_flask_error(error):
	return flask.render_template("error.html", errorcontent=error)


@app.before_request
def load_logged_in_user():
	user_id = flask.session.get("user_id")
	if user_id is None:
		flask.g.user = None
	else:
		flask.g.user = User.query.get(user_id)


@app.route("/")
def home():
	return flask.render_template("home.html")


@app.route("/projects", methods=["GET", "POST"])
@flask_login.login_required
def projects():

	if flask_login.current_user.privileges != Privileges.admin:
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")

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
@flask_login.login_required
def delete_project(project_id):

	if flask_login.current_user.privileges != Privileges.admin:
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")

	project_obj = Projects.query.filter_by(project_id=project_id).first()

	if not project_obj:
		return get_flask_error("Could not locate project with that ID.")

	db.session.delete(project_obj)
	db.session.commit()

	return flask.redirect("/projects")



@app.route("/projects/<int:project_id>/rename", methods=["POST"])
@flask_login.login_required
def rename_project(project_id):

	if flask_login.current_user.privileges != Privileges.admin:
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")

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
@flask_login.login_required
def users():

	if flask_login.current_user.privileges != Privileges.admin:
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")

	if flask.request.method == "POST":
		f_name = flask.request.form.get("f_name")
		s_name = flask.request.form.get("s_name")
		email = flask.request.form.get("email")

		if f_name and s_name and email:
			new_user = Users(f_name=f_name, s_name=s_name, email=email,
				password=werkzeug.security.generate_password_hash("password")
			)
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



@app.route("/users/<int:user_id>/priv", methods=["POST"])
@flask_login.login_required
def update_user_priv(user_id):

	if flask_login.current_user.privileges != Privileges.admin:
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")

	new_priv_value = flask.request.form.get("priv", type=int)

	if not Privileges.contains_value(new_priv_value):
		return get_flask_error("Privilage of that value is not valid.")
	
	user_obj = Users.query.filter_by(user_id=user_id).first()

	user_obj.privileges = new_priv_value
	user_obj.updated_at = datetime.datetime.utcnow()

	try:
		db.session.commit()
	except:
		db.sesion.rollback()
		return get_flask_error("Could not update privilage")

	return flask.redirect("/users")

	
	



@app.route("/signin", methods=["GET", "POST"])
def signin():

	if flask.request.method == "POST":

		email = flask.request.form.get("email")
		password = flask.request.form.get("password")

		if not (email and password):
			return get_flask_error("Invalid login creds.")
		
		user_obj = Users.query.filter_by(email=email).first()

		if not user_obj:
			return get_flask_error("Invalid login creds.")

		if not werkzeug.security.check_password_hash(user_obj.password, password):
			return get_flask_error("Invalid login creds.")
		
		flask_login.login_user(user_obj)
		return flask.redirect("/account")

	return flask.render_template("signin.html")



@app.route("/signout")
@flask_login.login_required
def signout():
	flask_login.logout_user()
	return flask.redirect("/signin")



@app.route("/account")
@flask_login.login_required
def account():
	return flask.render_template("userAccount.html")



@app.route("/account/update-name", methods=["POST"])
@flask_login.login_required
def account_update_name():

	new_f_name = flask.request.form.get("f_name")
	new_s_name = flask.request.form.get("s_name")

	if not (new_f_name and new_s_name):
		return get_flask_error("Could not update name. Ensure new name values are valid.")

	flask_login.current_user.f_name = new_f_name
	flask_login.current_user.s_name = new_s_name

	try:
		db.session.commit()
	except:
		db.session.rollback()
		return get_flask_error("Could not update name. Database error.")

	return flask.redirect("/account")



@app.route("/account/update-email", methods=["POST"])
@flask_login.login_required
def account_update_email():

	new_email = flask.request.form.get("email")

	if not new_email:
		return get_flask_error("Could not update email.")

	flask_login.current_user.email = new_email

	try:
		db.session.commit()
	except:
		db.session.rollback()
		return get_flask_error("Could not update email.")

	return flask.redirect("/account")



@app.route("/account/update-password", methods=["POST"])
@flask_login.login_required
def account_update_password():

	old_password = flask.request.form.get("old_password")
	new_password = flask.request.form.get("new_password")

	if not new_password:
		return get_flask_error("Could not update password.")


	if not werkzeug.security.check_password_hash(flask_login.current_user.password, old_password):
		return get_flask_error("Could not update password. Old password provided does not match existing password.")

	flask_login.current_user.password = werkzeug.security.generate_password_hash(new_password)

	try:
		db.session.commit()
	except:
		db.session.rollback()
		return get_flask_error("Could not update password. Database error")

	return flask.redirect("/account")


@app.route("/reviews", methods=["GET", "POST"])
@flask_login.login_required
def reviews():

	if flask.request.method == "POST":

		if not flask_login.current_user.privileges in (
			Privileges.admin,
			Privileges.approver,
			Privileges.developer
		):
			return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")


		project_id = flask.request.form.get("project_id", type=int)
		branch = flask.request.form.get("branch")
		ers_number = flask.request.form.get("ers_number", type=int)
		head_commit = flask.request.form.get("head_commit")
		base_commit = flask.request.form.get("base_commit")
		notes = flask.request.form.get("notes", "")

		if not (branch and head_commit and base_commit):
			return get_flask_error("Input data is not valid. Review could not be created. Please try again.")

		print(f"*** CREATING USER *** id={project_id}")

		new_review = Review(
			project_id=project_id,
			branch=branch,
			head_commit=head_commit,
			base_commit=base_commit,
			ers_number=ers_number,
			author_id=flask_login.current_user.user_id
		)

		db.session.add(new_review)
		db.session.flush()

		new_status = Status(
			review_id=new_review.review_id,
			status=StatusTypes.review,
			actor_id=flask_login.current_user.user_id,
			modified_at=datetime.datetime.utcnow(),
			notes=notes
		)


		db.session.add(new_status)

		try:
			db.session.commit()
		except:
			db.session.rollback()
			return get_flask_error("Could not create review. Please check your data and try again, or contact your admin.")

	projects = Projects.query.all()
	reviews = Review.query.order_by(Review.created_at.desc()).all()
	return flask.render_template("reviews.html", projects=projects, reviews=reviews,
		StatusTypes=StatusTypes)




@app.route("/reviews/<int:review_id>")
@flask_login.login_required
def review(review_id):

	if not flask_login.current_user.privileges in (
		Privileges.admin,
		Privileges.approver,
		Privileges.developer,
		Privileges.read_only
	):
		return get_flask_error("Insufficient privileges. Please contact your admin or log into another account.")
	
	review = Review.query.filter_by(review_id=review_id).first()
	statusList = Status.query.filter_by(review_id=review_id).order_by(Status.modified_at.asc()).all()

	if not review:
		return get_flask_error("Could not load that review ID.")

	
	current_review_status = statusList[-1].status if statusList else 0

	previously_approved = any(s.status == StatusTypes.approved for s in statusList)

	class ReviewStatusBtn:
		def __init__(self, text, value, enabled=False):
			self.text = text
			self.value = value
			self.display_text = text.capitalize()
			self.enabled = enabled
	
	buttons = [
		ReviewStatusBtn("review", StatusTypes.review),
		ReviewStatusBtn("corrections", StatusTypes.corrections),
		ReviewStatusBtn("closed", StatusTypes.closed),
		ReviewStatusBtn("approved", StatusTypes.approved),
		ReviewStatusBtn("confirm", StatusTypes.confirm),
		ReviewStatusBtn("complete", StatusTypes.complete)
	]

	if flask_login.current_user.privileges == Privileges.developer:
		if not previously_approved:
			buttons[0].enabled = True
		else:
			buttons[4].enabled = True


	elif flask_login.current_user.privileges == Privileges.approver:
		buttons[1].enabled = True
		buttons[2].enabled = True
		if not previously_approved:
			buttons[3].enabled = True
		else:
			buttons[5].enabled = True
		
	
	elif flask_login.current_user.privileges == Privileges.admin:
		for i, btn in enumerate(buttons):
			buttons[i].enabled = True



	return flask.render_template("review.html", review=review, statusList=statusList, StatusTypes=StatusTypes,
	current_review_status=current_review_status,
	buttons=buttons)


@app.route("/reviews/<int:review_id>/update", methods=["POST"])
@flask_login.login_required
def review_update(review_id):
	
	new_status = flask.request.form.get("status", type=int)
	notes = flask.request.form.get("notes")

	if flask_login.current_user.privileges not in (
		Privileges.developer,
		Privileges.approver,
		Privileges.admin,
	):
		return get_flask_error("Insufficient privileges to perform this action. Your account does not allow changes. Please ensure you are logged into the correct account.")

	if flask_login.current_user.privileges == Privileges.developer:
		if new_status in (StatusTypes.approved, StatusTypes.complete):
			return get_flask_error("Insufficient privileges to perform this action. Please contact your admnin if you believe this is an error")

	latest_status = Status.query.filter_by(review_id=review_id).order_by(Status.modified_at.desc()).first()

	new_status = Status(
		review_id=latest_status.review_id,
		status=new_status,
		actor_id=flask_login.current_user.user_id,
		modified_at=datetime.datetime.utcnow(),
		notes=notes
	)

	db.session.add(new_status)

	try:
		db.session.commit()
	except:
		db.session.rollback()
		return get_flask_error("Could not create review. Please check your data and try again, or contact your admin.")

	return flask.redirect(f"/reviews/{review_id}")


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=80)
