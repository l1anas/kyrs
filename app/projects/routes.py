from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.projects import bp
from app.projects.forms import ProjectForm, TaskForm, InvitationForm
from app.models import User, Project, Task, Application, Invitation, ProjectParticipant, Message, SubTask
from datetime import datetime
from sqlalchemy.orm import subqueryload


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            title=form.title.data,
            description=form.description.data,
            skills_required=form.skills_required.data,
            deadline=form.deadline.data,
            creator_id=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        participant = ProjectParticipant(user_id=current_user.id, project_id=project.id)
        db.session.add(participant)
        db.session.commit()
        flash('Проект создан!', 'success')
        return redirect(url_for('projects.manage', project_id=project.id))
    return render_template('projects/create.html', title='Create Project', form=form)

@bp.route('/project/<int:project_id>/update_deadline', methods=['POST'])
@login_required
def update_project_deadline(project_id):
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы изменять дедлайн проекта', 'danger')
        return redirect(url_for('projects.manage', project_id=project_id))

    deadline_str = request.form.get('deadline')

    try:
        new_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Неверный формат даты', 'danger')
        return redirect(url_for('projects.manage', project_id=project_id))

    project.deadline = new_deadline
    db.session.commit()
    flash('Дедлайн проекта обновлён', 'success')
    return redirect(url_for('projects.manage', project_id=project_id))

@bp.route('/my_projects')
@login_required
def my_projects():
    participant_projects = db.session.query(Project).distinct() \
        .join(Task, Task.project_id == Project.id) \
        .filter(Task.assignee_id == current_user.id) \
        .all()

    created_projects = current_user.created_projects.all()
    projects_set = set(participant_projects) | set(created_projects)
    current_projects = list(projects_set)

    applications = current_user.applications.all()

    invitations = current_user.invitations.filter_by(status='pending').all()

    return render_template('projects/my_projects.html',
                           current_projects=current_projects,
                           created_projects=created_projects,
                           applications=applications,
                           invitations=invitations)

@bp.route('/<int:project_id>/manage', methods=['GET', 'POST'])
@login_required
def manage(project_id):
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы для управления проектом', 'danger')
        return redirect(url_for('main.index'))

    form = TaskForm()
    if form.validate_on_submit():
        assignee_id = request.form.get('assignee')
        task = Task(
            title=form.title.data,
            description=form.description.data,
            deadline=form.deadline.data or project.deadline,
            project_id=project.id,
            assignee_id=int(assignee_id) if assignee_id else None
        )
        db.session.add(task)
        db.session.commit()
        flash('Задача успешно добавлена', 'success')
        return redirect(url_for('projects.manage', project_id=project.id))

    users = User.query.filter(User.id != project.creator_id).all()
    participant_ids = [p.user_id for p in project.participants]
    notusers = User.query.filter(
        User.id != project.creator_id,
        ~User.id.in_(participant_ids)
    ).all()
    unassigned_tasks_count = Task.query.filter_by(project_id=project.id, assignee_id=None).count()
    return render_template('projects/manage.html', project=project, form=form, users=users, notusers=notusers, unassigned_tasks_count=unassigned_tasks_count)

@bp.route('/<int:project_id>/apply')
@login_required
def apply(project_id):
    project = Project.query.get_or_404(project_id)
    if project.creator_id == current_user.id:
        return redirect(url_for('projects.details', project_id=project.id))

    existing_application = Application.query.filter_by(
        user_id=current_user.id,
        project_id=project.id
    ).order_by(Application.applied_at.desc()).first()

    if existing_application and existing_application.status != 'rejected':
        flash('Вы уже подали заявку на этот проект. Она отображена в Мои проекты/Заявки', 'info')
    else:
        application = Application(
            user_id=current_user.id,
            project_id=project.id
        )
        db.session.add(application)
        db.session.commit()
        flash('Заявка отправлена.', 'success')

    return redirect(url_for('projects.details', project_id=project.id))

@bp.route('/applications/<int:application_id>/delete', methods=['POST'])
@login_required
def delete_application(application_id):
    application = Application.query.get_or_404(application_id)

    if application.user_id != current_user.id:
        abort(403)

    db.session.delete(application)
    db.session.commit()
    flash('Заявка удалена.', 'success')

    return redirect(url_for('projects.my_projects'))

@bp.route('/delete/<int:project_id>', methods=['POST'])
@login_required
def delete(project_id):
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        flash('Вы не можете удалить этот проект', 'danger')
        return redirect(url_for('projects.my_projects'))

    db.session.delete(project)
    db.session.commit()
    flash('Проект успешно удален', 'success')
    return redirect(url_for('projects.my_projects'))

@bp.route('/application/<int:application_id>/cancel', methods=['POST'])
@login_required
def cancel_application(application_id):
    application = Application.query.get_or_404(application_id)

    db.session.delete(application)
    db.session.commit()
    return redirect(url_for('projects.my_projects'))

@bp.route('/application/<int:application_id>/accept', methods=['POST'])
@login_required
def accept_application(application_id):
    application = Application.query.get_or_404(application_id)
    project = application.project

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы принимать заявки', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    application.status = 'accepted'
    participant = ProjectParticipant(user_id=application.user_id, project_id=project.id)
    db.session.add(participant)
    db.session.commit()
    flash(f'Заявка от {application.applicant.username} принята', 'success')
    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/application/<int:application_id>/reject', methods=['POST'])
@login_required
def reject_application(application_id):
    application = Application.query.get_or_404(application_id)
    project = application.project

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы отклонять заявки', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    application.status = 'rejected'
    db.session.commit()
    flash(f'Заявка от {application.applicant.username} отклонена', 'success')
    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/invite/<int:project_id>', methods=['POST'])
@login_required
def invite(project_id):
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы приглашать участников', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    is_participant = ProjectParticipant.query.filter_by(project_id=project.id, user_id=user.id).first()
    is_invited = Invitation.query.filter_by(project_id=project.id, user_id=user.id, status='pending').first()

    if is_participant:
        flash('Пользователь уже является участником проекта', 'warning')
    elif is_invited:
        flash('Пользователь уже приглашён', 'warning')
    else:
        invitation = Invitation(user_id=user.id, project_id=project.id, status='pending')
        db.session.add(invitation)
        db.session.commit()
        flash(f'Приглашение отправлено пользователю {user.username}', 'success')

    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/participant/<int:project_id>/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_participant(project_id, user_id):
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы исключать участников', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    participant = ProjectParticipant.query.filter_by(project_id=project.id, user_id=user_id).first()
    if participant:
        Task.query.filter_by(project_id=project.id, assignee_id=user_id).update({'assignee_id': None})
        db.session.delete(participant)
        db.session.commit()
        flash('Участник исключён из проекта и снят с назначенных задач', 'success')
    else:
        flash('Участник не найден', 'warning')

    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/invitation/<int:invitation_id>/accept', methods=['POST'])
@login_required
def accept_invitation(invitation_id):
    invitation = Invitation.query.get_or_404(invitation_id)

    if invitation.user_id != current_user.id:
        flash('Вы не можете принимать приглашения другого пользователя', 'danger')
        return redirect(url_for('projects.my_projects'))

    invitation.status = 'accepted'
    participant = ProjectParticipant(user_id=current_user.id, project_id=invitation.project_id)
    db.session.add(participant)
    db.session.commit()
    flash(f'Вы приняли приглашение в проект "{invitation.project.title}"', 'success')
    return redirect(url_for('projects.my_projects'))

@bp.route('/invitation/<int:invitation_id>/reject', methods=['POST'])
@login_required
def reject_invitation(invitation_id):
    invitation = Invitation.query.get_or_404(invitation_id)

    if invitation.user_id != current_user.id:
        flash('Вы не можете отклонять приглашения другого пользователя', 'danger')
        return redirect(url_for('projects.my_projects'))

    invitation.status = 'rejected'
    db.session.commit()
    flash(f'Вы отклонили приглашение в проект "{invitation.project.title}"', 'success')
    return redirect(url_for('projects.my_projects'))

@bp.route('/task/<int:task_id>/assign', methods=['POST'])
@login_required
def assign_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    if project.creator_id != current_user.id:
        flash('Вы не авторизованы изменять задачу.', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))

    assignee_id = request.form.get('assignee_id')
    task.assignee_id = int(assignee_id) if assignee_id else None
    db.session.commit()
    flash('Ответственный обновлён.', 'success')
    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/invitation/<int:invitation_id>/revoke', methods=['POST'])
@login_required
def revoke_invitation(invitation_id):
    invitation = Invitation.query.get_or_404(invitation_id)

    if invitation.project.creator_id != current_user.id:
        flash('Вы не можете отозвать это приглашение.', 'danger')
        return redirect(url_for('projects.my_projects'))

    project_id = invitation.project_id
    db.session.delete(invitation)
    db.session.commit()
    flash('Приглашение отозвано.', 'success')
    return redirect(url_for('projects.manage', project_id=project_id))

@bp.route('/<int:project_id>')
@login_required
def details(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('projects/details.html', project=project)

@bp.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    deadline_str = request.form.get('deadline')
    assignee_id = request.form.get('assignee_id')
    title = request.form.get('title')
    description = request.form.get('description')
    print("title from form:", repr(request.form.get('title')))
    if not title:
        flash('Название задачи не может быть пустым', 'error')
        return redirect(request.referrer or url_for('projects.manage', project_id=task.project_id))

    old_assignee_id = task.assignee_id

    task.title = title
    task.description = description

    if deadline_str:
        try:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты дедлайна', 'error')

    new_assignee = None
    if assignee_id:
        assignee_user = User.query.get(int(assignee_id))
        if assignee_user:
            new_assignee = assignee_user

    task.assignee = new_assignee
    task.assignee_id = new_assignee.id if new_assignee else None

    if old_assignee_id != task.assignee_id:
        SubTask.query.filter_by(task_id=task.id).delete()

    db.session.commit()
    flash('Задача успешно обновлена', 'success')
    return redirect(url_for('projects.manage', project_id=task.project_id))

@bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    if project.creator_id != current_user.id:
        flash('Вы не можете удалять задачи этого проекта', 'danger')
        return redirect(url_for('projects.manage', project_id=project.id))
    SubTask.query.filter_by(task_id=task.id).delete()
    db.session.delete(task)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('projects.manage', project_id=project.id))

@bp.route('/<int:project_id>/execute', methods=['GET', 'POST'])
@login_required
def execute(project_id):
    project = Project.query.get_or_404(project_id)

    tasks = Task.query.filter(
        Task.project_id == project.id,
        db.or_(
            Task.assignee_id == current_user.id,
            Task.assignee_id == None
        )
    ).order_by(Task.deadline).all()

    hidden_exists = any(task.hidden for task in tasks)

    return render_template(
        'projects/execute.html',
        project=project,
        tasks=tasks,
        hidden_exists=hidden_exists,
        today=datetime.utcnow()
    )


@bp.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)

    if not task.project in [p.project for p in current_user.project_participations]:
        flash('Нет доступа к задаче', 'danger')
        return redirect(url_for('projects.execute', project_id=task.project_id))


    task.completed = 'completed' in request.form
    task.status = 'completed' if task.completed else 'not_started'  # или 'in_progress', как решишь


    if task.completed and task.subtasks:
        if any(not sub.completed for sub in task.subtasks):
            flash('Невозможно завершить: есть незавершённые подзадачи', 'warning')
            return redirect(url_for('projects.execute', project_id=task.project_id))

    db.session.commit()
    flash('Статус задачи обновлен', 'success')
    return redirect(url_for('projects.execute', project_id=task.project_id))


@bp.route('/task/<int:task_id>/assign_self', methods=['POST'])
@login_required
def assign_to_self(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assignee_id is not None:
        flash('Задача уже назначена', 'warning')
    else:
        task.assignee_id = current_user.id
        db.session.commit()
        flash('Вы назначены ответственным', 'success')
    return redirect(url_for('projects.execute', project_id=task.project_id))

@bp.route('/task/<int:task_id>/add_subtask', methods=['POST'])
@login_required
def add_subtask(task_id):
    task = Task.query.get_or_404(task_id)
    title = request.form.get('title')
    deadline_str = request.form.get('deadline')

    try:
        subtask_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Неверный формат даты', 'danger')
        return redirect(url_for('projects.execute', project_id=task.project_id))

    if task.deadline and subtask_deadline > task.deadline.date():
        flash('Дедлайн подзадачи не может быть позже дедлайна основной задачи', 'danger')
        return redirect(url_for('projects.execute', project_id=task.project_id))

    subtask = SubTask(title=title, deadline=subtask_deadline, task=task)
    db.session.add(subtask)
    db.session.commit()
    flash('Подзадача добавлена', 'success')
    return redirect(url_for('projects.execute', project_id=task.project_id))

@bp.route('/projects/<int:project_id>', methods=['GET'])
def view(project_id):
    tab = request.args.get('tab', 'tasks')
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.options(subqueryload(Task.subtasks))\
        .filter_by(project_id=project_id, parent_task_id=None).all()
    return render_template('projects/execute.html', project=project, tasks=tasks, active_tab=tab)

@bp.route('/subtask/<int:subtask_id>/status', methods=['POST'])
@login_required
def update_subtask_status(subtask_id):
    subtask = SubTask.query.get_or_404(subtask_id)
    parent_task = subtask.task
    project_id = parent_task.project_id

    subtask.completed = 'completed' in request.form
    db.session.commit()

    subtasks = SubTask.query.filter_by(task_id=parent_task.id).all()

    if all(sub.completed for sub in subtasks):
        parent_task.status = 'completed'
        parent_task.completed = True
    elif any(sub.completed for sub in subtasks):
        parent_task.status = 'in_progress'
        parent_task.completed = False
    else:
        parent_task.status = 'not_started'
        parent_task.completed = False

    db.session.commit()
    return redirect(url_for('projects.execute', project_id=project_id))

@bp.route('/subtask/<int:subtask_id>/delete', methods=['POST'])
@login_required
def delete_subtask(subtask_id):
    subtask = SubTask.query.get_or_404(subtask_id)
    project_id = subtask.task.project_id
    db.session.delete(subtask)
    db.session.commit()
    return redirect(url_for('projects.execute', project_id=project_id))

@bp.route('/task/<int:task_id>/hide', methods=['POST'])
@login_required
def hide_task(task_id):
    task = Task.query.get_or_404(task_id)

    if not task.project in [p.project for p in current_user.project_participations]:
        flash('Нет доступа к задаче', 'danger')
        return redirect(url_for('projects.execute', project_id=task.project_id))

    task.hidden = True
    db.session.commit()
    flash('Задача скрыта.', 'info')
    return redirect(url_for('projects.execute', project_id=task.project_id))

@bp.route('/<int:project_id>/unhide_all_tasks', methods=['POST'])
@login_required
def unhide_all_tasks(project_id):
    project = Project.query.get_or_404(project_id)
    hidden_tasks = Task.query.filter_by(project_id=project.id, hidden=True).all()
    for task in hidden_tasks:
        task.hidden = False

    db.session.commit()
    return redirect(url_for('projects.execute', project_id=project.id))

@bp.route('/projects/<int:project_id>/messages', methods=['GET'])
@login_required
def get_messages(project_id):
    messages = Message.query.filter_by(project_id=project_id).order_by(Message.timestamp.asc()).all()
    messages_data = [{
        'user_id': msg.user_id,
        'username': msg.user.username,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%H:%M')
    } for msg in messages]
    return jsonify(messages=messages_data)

@bp.route('/projects/<int:project_id>/send_message', methods=['POST'])
@login_required
def send_message(project_id):
    content = request.form.get('content')
    if not content or content.strip() == '':
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400

    message = Message(content=content.strip(), user_id=current_user.id, project_id=project_id)
    db.session.add(message)
    db.session.commit()
    return jsonify({'success': True})
