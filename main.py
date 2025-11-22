from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.numeric import DecimalField
from wtforms.validators import DataRequired, NumberRange
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
API_TOKEN = os.getenv('API_TOKEN')
Bootstrap5(app)


class Base(DeclarativeBase):
    pass


# CREATE DB
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///movielist.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[str] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(250))
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=True)


with app.app_context():
    db.create_all()


# Forms
class RateMovieForm(FlaskForm):
    rating = DecimalField('Your Rating Out of 10 e.g. 7.5', places=1, validators=[DataRequired(), NumberRange(min=0, max=10)], render_kw={'step': '0.1'})
    review = StringField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Done')


class AddMovieForm(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


# Routes
@app.route("/")
def home():
    with app.app_context():
        result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc()))
        all_movies = result.scalars().all()
        for movie in all_movies:
            movie.ranking = all_movies.index(movie) + 1
            db.session.commit()
        return render_template("index.html", all_movies=all_movies[::-1])


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = RateMovieForm()
    movie_id = request.args.get('id')
    movie_to_update = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie_to_update.rating = float(form.rating.data)
        movie_to_update.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie_to_update, form=form)


@app.route("/delete")
def delete():
    movie_id = request.args.get('id')
    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/add_movie", methods=["GET", "POST"])
def add_movie():
    form = AddMovieForm()
    if form.validate_on_submit():
        movie_name = form.title.data
        return redirect(url_for('select', movie_name=movie_name))
    return render_template("add.html", form=form)


@app.route("/select", methods=["GET", "POST"])
def select():
    movie_name = request.args.get('movie_name')
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "accept": "application/json",
        "Authorization": API_TOKEN
    }
    params = {
        'query': movie_name
    }
    movie_results = requests.get(url, headers=headers, params=params).json()['results']
    return render_template('select.html', movie_results=movie_results)


@app.route("/movie_selected")
def movie_selected():
    title = request.args.get('title')
    year = request.args.get('year')[:4]
    description = request.args.get('description')
    image_url = f"https://media.themoviedb.org/t/p/w600_and_h900_face{request.args.get('image_url')}"
    with app.app_context():
        new_movie = Movie(
            title=title,
            year=year,
            description=description,
            img_url=image_url
            )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('edit', id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
