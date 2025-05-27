from flask import render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import login_required, current_user
import os
import uuid

from app import db
from app.models import User
from app.profile import bp
from app.profile.forms import ProfileForm

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    user = User.query.get_or_404(user_id)
    if user != current_user:
        abort(403)

    form = ProfileForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.about_me = form.about_me.data
        user.skills = request.form.get('skills', '').strip()
        skills_str = request.form.get('skills', '').strip()
        user.skills = skills_str

        if 'delete_avatar' in request.form and request.form.get('delete_avatar') == 'on':
            if user.avatar:
                avatar_path = os.path.join(current_app.root_path, 'static', user.avatar)
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)
                user.avatar = None

        file = request.files.get('avatar')
        if file and file.filename != '':
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(file_path)


                if user.avatar:
                    old_path = os.path.join(current_app.root_path, 'static', user.avatar)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                user.avatar = f"uploads/avatars/{unique_filename}"
            else:
                flash('Недопустимый формат файла для аватара.', 'danger')
                return redirect(url_for('profile.edit', user_id=user.id))

        db.session.commit()
        flash('Профиль успешно обновлен!', 'success')
        return redirect(url_for('profile.view', user_id=user.id))
    return render_template('profile/edit.html', user=user, form=form)

@bp.route('/<int:user_id>', endpoint='view')
@login_required
def view(user_id):

    user = User.query.get_or_404(user_id)
    form = ProfileForm()
    form.username.data = user.username
    form.email.data = user.email
    form.about_me.data = user.about_me
    form.skills.data = user.skills

    return render_template('profile/view.html', title='Profile', user=user, form=form)

@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    db.session.delete(current_user)
    db.session.commit()
    flash('Ваша учетная запись была удалена.', 'success')
    return redirect(url_for('auth.register'))
