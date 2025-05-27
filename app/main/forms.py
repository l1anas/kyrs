from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Optional

class ProjectSearchForm(FlaskForm):
    search = StringField('Поиск', validators=[Optional()])
    submit = SubmitField('Найти')
