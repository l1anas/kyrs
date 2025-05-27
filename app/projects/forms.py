from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired

class ProjectForm(FlaskForm):
    title = StringField(
        'Название проекта',
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Введите название"}
    )
    description = TextAreaField(
        'Описание',
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Опишите проект", "rows": 5}
    )
    skills_required = StringField(
        'Требуемые навыки',
        render_kw={"class": "form-control", "placeholder": "Python, HTML, CSS"}
    )
    deadline = DateField(
        'Дедлайн',
        format='%Y-%m-%d',
        render_kw={"class": "form-control"}
    )
    submit = SubmitField(
        'Создать проект',
        render_kw={"class": "btn btn-primary"}
    )


class TaskForm(FlaskForm):
    title = StringField(
        'Название задачи',
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Например: Верстка"}
    )
    description = TextAreaField(
        'Описание',
        render_kw={"class": "form-control", "placeholder": "Подробности", "rows": 3}
    )
    deadline = DateField(
        'Дедлайн',
        format='%Y-%m-%d',
        render_kw={"class": "form-control"}
    )
    submit = SubmitField(
        'Добавить задачу',
        render_kw={"class": "btn btn-primary"}
    )


class InvitationForm(FlaskForm):
    username = StringField(
        'Имя пользователя',
        validators=[DataRequired()],
        render_kw={"class": "form-control", "placeholder": "Введите имя"}
    )
    submit = SubmitField(
        'Пригласить',
        render_kw={"class": "btn btn-primary"}
    )
