from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf.file import FileAllowed


class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[Length(min=2, max=64)])
    email = StringField('Email', validators=[Email()])
    about_me = TextAreaField('О себе', validators=[Length(max=500)])
    skills = StringField('Навыки')
    avatar = FileField('Фото', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения')])
    #submit = SubmitField('Сохранить изменения')
