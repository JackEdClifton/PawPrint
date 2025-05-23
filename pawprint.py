import flask
import flask_sqlalchemy
import datetime

app = flask.Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = flask_sqlalchemy.SQLAlchemy(app)


class Privileges:
	read_only = 0   # can read/search only
	developer = 1   # can create review requests
	approver = 2    # can approve requests
	admin = 3       # can manage user accounts


class Projects(db.Model):
	project_id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(20), nullable=False)


class StatusTypes(db.Model):
	status_id = db.Column(db.Integer, primary_key=True)
	label = db.Column(db.Integer, nullable=False)


class Users(db.Model):
	user_id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), nullable=False)
	email = db.Column(db.String(128), nullable=False)
	privileges = db.Column(db.Integer, nullable=False)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
	updated_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)


class Review(db.Model):
	review_id = db.Column(db.Integer, primary_key=True)
	project_id = db.Column(db.Integer, nullable=False, db.ForeignKey('Projects.project_id'))
	branch = db.Column(db.String(64), nullable=False)
	commits = db.Column(db.Text, nullable=False)
	ers_number = db.Column(db.Integer, nullable=False)
	author_id = db.Column(db.Integer, nullable=False, db.ForeignKey('Users.user_id'))
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

	project = db.relationship('Projects', backref=db.backref('reviews', lazy=True))
	author = db.relationship('Users', backref=db.backref('authored_reviews', lazy=True))


class Status(db.Model):
	status_id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, nullable=False, db.ForeignKey('Review.review_id'))
    status = db.Column(db.Integer, nullable=False, db.ForeignKey('Review.review_id'))
    actor_id = db.Column(db.Integer, nullable=False, db.ForeignKey('Users.user_id'))
    modified_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    notes = db.Column(db.Text)

    # Relationships
    review = db.relationship('Review', backref=db.backref('status_history', lazy=True, cascade="all, delete-orphan"))
    actor = db.relationship('Users', backref=db.backref('status_actions', lazy=True))





with app.app_context():
	db.create_all()



@app.route("/")
def home():
	return flask.render_template("home.html")


@app.route("/jack")
def jack():
	items = Item.query.all()
	return flask.render_template("jack.html", items=items)


@app.route("/add-item", methods=["GET", "POST"])
def add_item():

	if flask.request.method == "GET":
		return flask.render_template("create.html")

	elif flask.request.method == "POST":
		content = flask.request.form.get("content")
		if content:
			new_item = Item(content=content)
			db.session.add(new_item)
			db.session.commit()
		
		return flask.redirect(flask.url_for("jack"))




@app.route("/delete-item")
def delete_item():
	return flask.render_template("delete_item.html")






if __name__ == "__main__":
	app.run(debug=True)
