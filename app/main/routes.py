from flask import render_template, request
from flask_login import login_required, current_user
from app.main import bp
from app.models import Project, User
from sqlalchemy import or_

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    projects = Project.query.paginate(page=page, per_page=10)
    return render_template('main/index.html', title='Home', projects=projects)


@bp.route('/search')
@login_required
def search():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')

    if query:
        projects_query = Project.query.join(User).filter(
            or_(
                Project.title.ilike(f'%{query}%'),
                Project.description.ilike(f'%{query}%'),
                Project.skills_required.ilike(f'%{query}%'),
                User.username.ilike(f'%{query}%')
            )
        )
    else:
        projects_query = Project.query

    projects = projects_query.paginate(page=page, per_page=10)
    return render_template('main/search.html', title='Search', projects=projects, query=query)